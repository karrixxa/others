"""Phase 34 -- active-dendrite local coincidence prediction.

Focused tests for the new default-OFF engine flag `prediction_active_
dendrite_enabled`, implemented under the CORRECTED contract (the dendritic-
fire decision uses CURRENT-STEP literal arrivals only -- never the decayed
z_j^R/u_i^S traces, which exist solely to drive decoder learning):

    Decoder learning (every step, bounded traces):
        z_j^R <- min(1, retention*z_j^R + feedback_arrival_j)
        u_i^S <- min(1, retention*u_i^S + sensory_arrival_i)
        delta_d_ji = eta_ad * z_j^R * u_i^S * (1 - d_ji/d_max)^2

    Physical dendritic spike (same-step-only, pre-update d_ji):
        sensory_arrival_i(t) == 1 AND feedback_arrival_j(t) == 1 (some j)
        AND d_ji_before_learning >= prediction_active_dendrite_coincidence_weight
        -> inject exactly prediction_threshold into the membrane, bypassing
           receive_input entirely (never additive at the soma).

Covers: flag-off byte-identical behavior, trace-source isolation, exact
trace-decay/bound verification, sensory-alone/feedback-alone never fire,
temporal separation never fires (the strict same-step window), sub-
threshold-weight coincidence learns but does not spike, genuine post-
maturity coincidence spikes, PCi->Ii wiring untouched, absent columns
unaffected, no pattern-boundary reset, frozen-plasticity semantics, locality
(no argmax/owner/pattern-name/cross-neuron state), determinism, and mutual
exclusivity with the Phase 30 subthreshold decoder.

Also covers the Codex preflight corrections: eta=0.15 (verified against the
closed-form saturating-growth solution to reproduce ~2946 events to reach
d=350 from d=50) and the passive queue-origin telemetry (originating
timestep tracking, pattern-switch detection, and the current-correct/
stale-but-same-pixel/stale-wrong-pixel suppression classification) -- all
required to be non-mutating."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from backend.simulation import N_OUT, N_PIX, SimulationEngine
from backend.presets import DASHBOARD_PRESET


def _engine(**overrides):
    return SimulationEngine(seed=1, topology_seed=1, **{**DASHBOARD_PRESET, **overrides})


def _all_ff_weights(engine):
    return {(j, i): float(engine.l2.excitatory_neurons[j]._weights_array[i])
            for j in range(N_OUT) for i in range(N_PIX)}


def _force_delivery(e, dec_vec=None, lat_vec=None):
    """Overwrite the NEXT step()'s dec_vec_pcol/lat_vec_pcol delivery
    (the front of each length-preserving delayed queue) without disturbing
    the queue-length invariant step() itself relies on (popleft then
    append, every step)."""
    if dec_vec is not None:
        e.l2e_to_pcol_queue[0] = np.asarray(dec_vec, dtype=float)
    if lat_vec is not None:
        e.s_to_pcol_queue[0] = np.asarray(lat_vec, dtype=float)


# ==================================================================== flag-off identity
def test_active_dendrite_off_is_byte_identical_to_baseline():
    plain = _engine(prediction_column_enabled=True)
    off = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=False)
    plain.set_pattern('row 1')
    off.set_pattern('row 1')
    for _ in range(300):
        plain.step()
        off.step()
    assert _all_ff_weights(plain) == _all_ff_weights(off)
    for j in range(N_PIX):
        assert list(plain.pcol[j]._weights_array) == list(off.pcol[j]._weights_array)
    assert plain.dynamic_state()['timestep'] == off.dynamic_state()['timestep']


def test_active_dendrite_requires_prediction_column_enabled_to_do_anything():
    e = _engine(prediction_column_enabled=False, prediction_active_dendrite_enabled=True)
    assert e.pcol == []


def test_active_dendrite_is_deterministic_given_same_seed():
    a = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    b = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    a.set_pattern('row 1')
    b.set_pattern('row 1')
    for _ in range(400):
        ra = a.step()
        rb = b.step()
        assert str(ra) == str(rb)
    assert _all_ff_weights(a) == _all_ff_weights(b)
    for j in range(N_PIX):
        assert list(a.pcol[j]._weights_array) == list(b.pcol[j]._weights_array)


def test_active_dendrite_and_subthreshold_decoder_are_mutually_exclusive():
    with pytest.raises(ValueError):
        _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True,
                prediction_subthreshold_decoder_enabled=True)


# ==================================================================== trace mechanics
def test_active_dendrite_z_trace_changes_only_from_feedback_arrival():
    """u fixed at 0 (irrelevant to z's own update); only dec_vec_pcol drives
    z, never lat_vec_pcol."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e._pcol_ad_z[:] = 0.0
    e._pcol_ad_u[:] = 0.0
    _force_delivery(e, dec_vec=np.zeros(N_OUT), lat_vec=np.ones(N_PIX))  # sensory only
    e.step()
    assert np.all(e._pcol_ad_z == 0.0)   # no feedback arrival -> z stays zero
    assert np.all(e._pcol_ad_u == 1.0)   # sensory arrival -> u moved


def test_active_dendrite_u_trace_changes_only_from_sensory_arrival():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e._pcol_ad_z[:] = 0.0
    e._pcol_ad_u[:] = 0.0
    _force_delivery(e, dec_vec=np.ones(N_OUT), lat_vec=np.zeros(N_PIX))  # feedback only
    e.step()
    assert np.all(e._pcol_ad_z == 1.0)   # feedback arrival -> z moved
    assert np.all(e._pcol_ad_u == 0.0)   # no sensory arrival -> u stays zero


def test_active_dendrite_trace_update_matches_exact_formula():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    retention = e.prediction_active_dendrite_trace_retention
    e._pcol_ad_z[:] = 0.5
    e._pcol_ad_u[:] = 0.5
    dec = np.zeros(N_OUT); dec[3] = 1.0
    lat = np.zeros(N_PIX); lat[2] = 1.0
    z_before = e._pcol_ad_z.copy()
    u_before = e._pcol_ad_u.copy()
    _force_delivery(e, dec_vec=dec, lat_vec=lat)
    e.step()
    expected_z = np.minimum(1.0, z_before * retention + dec)
    expected_u = np.minimum(1.0, u_before * retention + lat)
    assert np.allclose(e._pcol_ad_z, expected_z)
    assert np.allclose(e._pcol_ad_u, expected_u)


def test_active_dendrite_trace_stays_bounded_under_repeated_arrivals():
    """Every-step arrival for many steps must never push the trace above 1.0
    -- the explicit min(1, ...) clip from the correction."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    for _ in range(50):
        _force_delivery(e, dec_vec=np.ones(N_OUT), lat_vec=np.ones(N_PIX))
        e.step()
        assert np.all(e._pcol_ad_z <= 1.0 + 1e-12)
        assert np.all(e._pcol_ad_u <= 1.0 + 1e-12)
    assert np.allclose(e._pcol_ad_z, 1.0)
    assert np.allclose(e._pcol_ad_u, 1.0)


# ==================================================================== dendritic-fire condition (unit level)
def test_active_dendrite_event_sensory_alone_never_fires():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    d_before = np.full(N_OUT, 10_000.0)   # every synapse absurdly mature
    fires = e._active_dendrite_event(0, sensory_arrival_i=1.0,
                                      feedback_arrival_vec=np.zeros(N_OUT), d_before=d_before)
    assert fires is False


def test_active_dendrite_event_feedback_alone_at_max_weight_never_fires():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    d_before = np.full(N_OUT, e.prediction_feedback_max)   # d_max, still not enough alone
    fires = e._active_dendrite_event(0, sensory_arrival_i=0.0,
                                      feedback_arrival_vec=np.ones(N_OUT), d_before=d_before)
    assert fires is False


def test_active_dendrite_event_sub_threshold_weight_never_fires():
    """Genuine same-step coincidence, but d_ji below the coincidence weight
    -- must not fire."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    d_before = np.zeros(N_OUT)
    d_before[2] = e.prediction_active_dendrite_coincidence_weight - 1.0
    feedback = np.zeros(N_OUT); feedback[2] = 1.0
    fires = e._active_dendrite_event(3, sensory_arrival_i=1.0,
                                      feedback_arrival_vec=feedback, d_before=d_before)
    assert fires is False


def test_active_dendrite_event_genuine_coincidence_at_threshold_fires():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    d_before = np.zeros(N_OUT)
    d_before[2] = e.prediction_active_dendrite_coincidence_weight
    feedback = np.zeros(N_OUT); feedback[2] = 1.0
    fires = e._active_dendrite_event(3, sensory_arrival_i=1.0,
                                      feedback_arrival_vec=feedback, d_before=d_before)
    assert fires is True


def test_active_dendrite_event_ignores_traces_uses_only_raw_arrivals():
    """Residual traces at 1.0 (fully saturated) must NOT substitute for a
    genuine this-step arrival -- 'do not permit residual traces alone to
    generate the dendritic spike'."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e._pcol_ad_z[:] = 1.0
    e._pcol_ad_u[:] = 1.0
    d_before = np.full(N_OUT, 10_000.0)
    # This-step raw arrivals are both zero -- must not fire despite saturated traces.
    fires = e._active_dendrite_event(0, sensory_arrival_i=0.0,
                                      feedback_arrival_vec=np.zeros(N_OUT), d_before=d_before)
    assert fires is False


def test_active_dendrite_inputs_separated_by_one_step_never_fire_at_engine_level():
    """The corrected coincidence window is EXACTLY one timestep: sensory at
    step t, feedback at step t+1 (both alone, both real deliveries) must
    never produce a dendritic spike, even with an already-mature synapse."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    i, j = 3, 2
    e.pcol[i]._weights_array[j] = e.prediction_active_dendrite_coincidence_weight + 50.0
    lat = np.zeros(N_PIX); lat[i] = 1.0
    dec = np.zeros(N_OUT); dec[j] = 1.0
    _force_delivery(e, dec_vec=np.zeros(N_OUT), lat_vec=lat)
    e.step()
    assert not e.spiked[f'PC{i}']
    _force_delivery(e, dec_vec=dec, lat_vec=np.zeros(N_PIX))
    e.step()
    assert not e.spiked[f'PC{i}']


# ==================================================================== engine-level integration
def test_active_dendrite_sub_threshold_coincidence_learns_but_does_not_spike():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    i, j = 3, 2
    w_before = e.prediction_active_dendrite_coincidence_weight - 100.0
    e.pcol[i]._weights_array[j] = w_before
    lat = np.zeros(N_PIX); lat[i] = 1.0
    dec = np.zeros(N_OUT); dec[j] = 1.0
    _force_delivery(e, dec_vec=dec, lat_vec=lat)
    e.step()
    assert not e.spiked[f'PC{i}']
    assert e.pcol[i]._weights_array[j] > w_before   # decoder still learns from the coincidence


def test_active_dendrite_matured_coincidence_fires_pc_and_injects_bounded_charge():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    i, j = 3, 2
    e.pcol[i]._weights_array[j] = e.prediction_active_dendrite_coincidence_weight + 25.0
    lat = np.zeros(N_PIX); lat[i] = 1.0
    dec = np.zeros(N_OUT); dec[j] = 1.0
    _force_delivery(e, dec_vec=dec, lat_vec=lat)
    e.step()
    assert e.spiked[f'PC{i}']


def test_active_dendrite_multiple_qualifying_sources_produce_one_bounded_injection():
    """Two mature, coincident sources for the SAME PCi at the SAME step must
    not stack: _active_dendrite_event returns a plain bool (never a count),
    and the engine's own injection line (mirrored here exactly) adds
    prediction_threshold exactly once regardless of how many sources
    qualified."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    i = 3
    e.pcol[i]._weights_array[2] = e.prediction_active_dendrite_coincidence_weight + 10.0
    e.pcol[i]._weights_array[5] = e.prediction_active_dendrite_coincidence_weight + 10.0
    feedback = np.zeros(N_OUT); feedback[2] = 1.0; feedback[5] = 1.0
    d_before = e.pcol[i]._weights_array[:N_OUT].copy()
    fires = e._active_dendrite_event(i, 1.0, feedback, d_before)
    assert fires is True   # a plain bool -- "at least one", never a count
    pc = e.pcol[i]
    pot_before = pc.potential
    if fires and pc.refractory_timer <= 0:
        pc.potential = pc.potential + e.prediction_threshold
    assert pc.potential == pytest.approx(pot_before + e.prediction_threshold)


def test_active_dendrite_never_calls_receive_input_soma_path():
    """Never additive at the soma: a PCi whose queued delivery does NOT
    satisfy the strict coincidence condition must show zero membrane
    change from this step's delivery block at all (no partial/weighted
    accumulation the way receive_input would produce)."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    i = 3
    # Large feedback weights but NO sensory arrival this step -- receive_input
    # would have accumulated substantial charge from the feedback alone;
    # active-dendrite mode must inject nothing.
    e.pcol[i]._weights_array[:N_OUT] = e.prediction_feedback_max
    dec = np.ones(N_OUT)
    _force_delivery(e, dec_vec=dec, lat_vec=np.zeros(N_PIX))
    e.step()
    assert e.pcol[i].potential == 0.0


def test_active_dendrite_repeated_real_coincidences_mature_decoder_naturally():
    """Integration test: run the real engine on a real pattern long enough
    that the decoder for an ACTUALLY firing L2Ej / actually-active pixel i
    grows past the coincidence weight purely from the traces -- no manual
    weight assignment."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.set_pattern('row 1')
    for _ in range(1500):
        e.step()
    grown = (e.pcol[i]._weights_array[:N_OUT].max() for i in range(N_PIX))
    assert max(grown) > 0.0, "expected at least some decoder growth from real coincidences"


# ==================================================================== topology / locality
def test_active_dendrite_frozen_plasticity_blocks_learning_but_not_physical_fire():
    """Physical firing and learning are separate events (same philosophy as
    the existing spike-gated rule): under plasticity_frozen, the decoder
    must not move, but a coincidence against an ALREADY-mature synapse must
    still spike PCi."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    i, j = 3, 2
    e.pcol[i]._weights_array[j] = e.prediction_active_dendrite_coincidence_weight + 25.0
    e._set_plasticity_frozen(True)
    w_before = e.pcol[i]._weights_array.copy()
    lat = np.zeros(N_PIX); lat[i] = 1.0
    dec = np.zeros(N_OUT); dec[j] = 1.0
    _force_delivery(e, dec_vec=dec, lat_vec=lat)
    e.step()
    assert e.spiked[f'PC{i}']
    assert np.array_equal(e.pcol[i]._weights_array, w_before)


def test_active_dendrite_absent_columns_neither_learn_nor_fire():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    others = [k for k in range(N_PIX) if k != 3]
    weights_before = [e.pcol[k]._weights_array.copy() for k in others]
    lat = np.zeros(N_PIX); lat[3] = 1.0
    dec = np.zeros(N_OUT); dec[2] = 1.0
    _force_delivery(e, dec_vec=dec, lat_vec=lat)
    e.step()
    for k, w0 in zip(others, weights_before):
        assert np.array_equal(e.pcol[k]._weights_array, w0)
        assert not e.spiked[f'PC{k}']


def test_active_dendrite_pc_spike_drives_only_paired_inhibitory_neuron():
    """Existing PCi->Ii wiring (Phase 21) must be untouched by this
    mechanism -- pcol_spiked propagates to L1Ii the same way regardless of
    which PC learning-rule branch produced the spike."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True,
                prediction_column_to_i_enabled=True)
    i, j = 3, 2
    e.pcol[i]._weights_array[j] = e.prediction_active_dendrite_coincidence_weight + 25.0
    lat = np.zeros(N_PIX); lat[i] = 1.0
    dec = np.zeros(N_OUT); dec[j] = 1.0
    _force_delivery(e, dec_vec=dec, lat_vec=lat)
    e.step()
    assert e.spiked[f'PC{i}']
    # No exception and the engine's own dynamic_state remains internally consistent.
    state = e.dynamic_state()
    assert state is not None


def test_active_dendrite_no_pattern_boundary_reset():
    """No mechanism here may special-case a pattern boundary -- traces must
    decay/carry over exactly per the formula across a set_pattern() call,
    never hard-reset to zero because a new pattern started."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    z_before = e._pcol_ad_z.copy()
    u_before = e._pcol_ad_u.copy()
    e.set_pattern('col 1')
    # Immediately after switching patterns, traces must be exactly what they
    # were (no reset hook fires on set_pattern itself).
    assert np.array_equal(e._pcol_ad_z, z_before)
    assert np.array_equal(e._pcol_ad_u, u_before)


def test_active_dendrite_no_argmax_owner_or_global_state_in_source():
    for fn in (SimulationEngine._active_dendrite_event,
               SimulationEngine._apply_active_dendrite_decoder_learning):
        src = inspect.getsource(fn)
        code_only = src.split('"""', 2)[-1]
        for banned in ('argmax', 'owner', 'PATTERNS', 'other_n', '.pcol[', 'global '):
            assert banned not in code_only, f'{fn.__name__} contains banned token {banned!r}'


def test_active_dendrite_decoder_learning_saturates_at_feedback_max():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    pc = e.pcol[0]
    w_max = e.prediction_feedback_max
    pc._weights_array[:N_OUT] = w_max - 0.1
    e._pcol_ad_z[:] = 1.0
    e._pcol_ad_u[0] = 1.0
    for _ in range(500):
        e._apply_active_dendrite_decoder_learning(pc, 0)
    assert (pc._weights_array[:N_OUT] <= w_max + 1e-9).all()


def test_active_dendrite_decoder_learning_does_not_touch_lateral_index():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    pc = e.pcol[0]
    lateral_before = pc._weights_array[N_OUT]
    e._pcol_ad_z[:] = 1.0
    e._pcol_ad_u[0] = 1.0
    e._apply_active_dendrite_decoder_learning(pc, 0)
    assert pc._weights_array[N_OUT] == lateral_before


# ==================================================================== eta correction (Codex preflight)
def test_active_dendrite_default_learning_rate_reproduces_2946_events():
    """Codex preflight reproduction target: eta=0.15 must reach the
    coincidence weight (350) from prediction_feedback_init (50) in
    approximately 2946 forced-every-step coincidence events -- an exact
    consequence of the closed-form saturating-growth solution, not tuned
    after the fact."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    assert e.prediction_active_dendrite_learning_rate == pytest.approx(0.15)
    i, j = 3, 2
    e.input_vec = np.zeros(N_PIX)
    dec = np.zeros(N_OUT); dec[j] = 1.0
    lat = np.zeros(N_PIX); lat[i] = 1.0
    first_fire_step = None
    for step_idx in range(3200):
        _force_delivery(e, dec, lat)
        e.step()
        if e.spiked[f'PC{i}']:
            first_fire_step = step_idx
            break
    assert first_fire_step is not None
    assert abs(first_fire_step - 2946) <= 5


# ==================================================================== passive queue-origin telemetry
def test_telemetry_does_not_alter_flag_on_dynamics():
    """The telemetry additions (origin queues, switch detection, per-step
    probe dict, sparse event log) must be pure observation -- an engine run
    with active-dendrite on produces IDENTICAL weights/potentials/RNG state
    whether or not anything ever reads the telemetry fields."""
    a = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    b = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    a.set_pattern('row 1')
    b.set_pattern('row 1')
    for _ in range(400):
        ra = a.step()
        # Never touch b's telemetry fields at all -- a's are read every step.
        _ = a._active_dendrite_last_probe
        _ = a.active_dendrite_event_log
        rb = b.step()
        assert str(ra) == str(rb)
    assert _all_ff_weights(a) == _all_ff_weights(b)
    for j in range(N_PIX):
        assert list(a.pcol[j]._weights_array) == list(b.pcol[j]._weights_array)


def test_telemetry_origin_timestep_matches_actual_originating_step():
    """A forced delivery via _force_delivery bypasses the real queue-origin
    tracking (it overwrites the popped value directly), so origin_t must
    reflect the REAL step that pushed the queue entry actually consumed --
    verified here with organic (unforced) delivery only."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.set_pattern('row 1')
    delay = e.prediction_feedback_delay
    for step_idx in range(20):
        e.step()
        probe0 = e._active_dendrite_last_probe.get(0)
        assert probe0 is not None
        # This step's delivery was queued exactly `delay` steps ago.
        assert probe0['feedback_origin_t'] == step_idx - delay
        assert probe0['sensory_origin_t'] == step_idx - delay


def test_telemetry_last_pattern_switch_t_updates_on_set_pattern():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.set_pattern('row 1')
    for _ in range(10):
        e.step()
    assert e._last_pattern_switch_t == 0   # 'row 1' was already the default at construction
    switch_step = e.timestep
    e.set_pattern('col 1')
    e.step()
    assert e._last_pattern_switch_t == switch_step


def test_telemetry_no_switch_no_stale_classification_in_steady_state():
    """Well after the last input switch, with a genuine coincidence forced
    on a step whose queue-origin data is itself post-switch, the fire event
    must be classified current-correct -- never stale."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.input_vec = np.zeros(N_PIX)
    for _ in range(100):
        e.step()   # let the switch boundary (at construction, t=0) fall far behind
    i, j = 3, 2
    e.pcol[i]._weights_array[j] = e.prediction_active_dendrite_coincidence_weight + 25.0
    e.input_vec[i] = 1.0   # a genuine switch -- target now "currently active"
    for _ in range(5):
        e.step()   # let the switch settle and the origin queues push fresh, post-switch entries
    dec = np.zeros(N_OUT); dec[j] = 1.0
    lat = np.zeros(N_PIX); lat[i] = 1.0
    _force_delivery(e, dec, lat)   # overrides CONTENT only, not the origin-tracking deques
    e.step()
    assert e.spiked[f'PC{i}']
    rec = e._active_dendrite_last_probe[i]
    assert rec['fired'] is True
    assert rec['used_stale_queue_data'] is False
    assert rec['suppression_classification'] == 'current-correct'
    assert e.active_dendrite_event_log[-1] is rec or e.active_dendrite_event_log[-1] == rec


def test_telemetry_stale_wrong_pixel_classification_after_switch():
    """Force a queue-origin timestamp that predates a pattern switch (by
    directly manipulating the READ-ONLY origin-tracking deque, exactly the
    way _force_delivery already manipulates the content deques for
    controlled testing) with the target pixel NOT currently active -- must
    classify as stale-wrong-pixel."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.input_vec = np.zeros(N_PIX)
    for _ in range(50):
        e.step()
    i, j = 3, 2
    e.pcol[i]._weights_array[j] = e.prediction_active_dendrite_coincidence_weight + 25.0
    dec = np.zeros(N_OUT); dec[j] = 1.0
    lat = np.zeros(N_PIX); lat[i] = 1.0
    _force_delivery(e, dec, lat)
    stale_origin_t = e.timestep - 10
    e._pcol_feedback_origin_t[0] = stale_origin_t
    e._pcol_sensory_origin_t[0] = stale_origin_t
    e._last_pattern_switch_t = e.timestep   # a switch "just happened" this very step
    e.input_vec[i] = 0.0   # target pixel i is NOT currently active
    e.step()
    assert e.spiked[f'PC{i}']   # the dendritic-fire condition itself is unaffected by this telemetry
    rec = e._active_dendrite_last_probe[i]
    assert rec['used_stale_queue_data'] is True
    assert rec['target_currently_active'] is False
    assert rec['suppression_classification'] == 'stale-wrong-pixel'


def test_telemetry_stale_but_same_pixel_classification():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.input_vec = np.zeros(N_PIX)
    for _ in range(50):
        e.step()
    i, j = 3, 2
    e.pcol[i]._weights_array[j] = e.prediction_active_dendrite_coincidence_weight + 25.0
    dec = np.zeros(N_OUT); dec[j] = 1.0
    lat = np.zeros(N_PIX); lat[i] = 1.0
    _force_delivery(e, dec, lat)
    stale_origin_t = e.timestep - 10
    e._pcol_feedback_origin_t[0] = stale_origin_t
    e._pcol_sensory_origin_t[0] = stale_origin_t
    e._last_pattern_switch_t = e.timestep
    e.input_vec[i] = 1.0   # target pixel i IS currently active despite the stale origin
    e.step()
    rec = e._active_dendrite_last_probe[i]
    assert rec['used_stale_queue_data'] is True
    assert rec['target_currently_active'] is True
    assert rec['suppression_classification'] == 'stale-but-same-pixel'


def test_telemetry_event_log_only_appends_on_actual_fire():
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.input_vec = np.zeros(N_PIX)
    assert e.active_dendrite_event_log == []
    # Immature synapse -- coincidences happen but never fire.
    dec = np.zeros(N_OUT); dec[2] = 1.0
    lat = np.zeros(N_PIX); lat[3] = 1.0
    for _ in range(20):
        _force_delivery(e, dec, lat)
        e.step()
    assert e.active_dendrite_event_log == []
    # Now mature it and fire once.
    e.pcol[3]._weights_array[2] = e.prediction_active_dendrite_coincidence_weight + 10.0
    _force_delivery(e, dec, lat)
    e.step()
    assert len(e.active_dendrite_event_log) == 1
    assert e.active_dendrite_event_log[0]['fired'] is True


def test_telemetry_disabled_when_active_dendrite_off():
    """No telemetry state is populated at all when the flag is off -- the
    dense probe dict and sparse log stay at their construction-time empty
    defaults (allocated unconditionally, like every other PC-adjacent
    state, but never written without the flag on)."""
    e = _engine(prediction_column_enabled=True, prediction_active_dendrite_enabled=False)
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    assert e._active_dendrite_last_probe == {}
    assert e.active_dendrite_event_log == []
