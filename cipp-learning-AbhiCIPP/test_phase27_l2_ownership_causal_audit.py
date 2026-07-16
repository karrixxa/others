"""Phase 27 -- focused tests for the L2 ownership causal audit tooling
itself (not the engine). Verifies the tracer is truly non-mutating, that
every weight delta reconciles against the engine's own live weights, that
the residual-unattributed safety net actually catches a real unattributed
mutation, that presentation/timestep and center/peripheral attribution are
correct, that prediction flags stay off, that the ownership-collision
detectors contain no hardcoded owner/outcome, and that identical seeds
reproduce identically."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from backend.simulation import N_OUT, N_PIX
from diagnostic_schedule import CYCLE_ORDER, PRESENTATION_STEPS
from phase27_l2_ownership_causal_audit import (
    CENTER_PIXEL, PATTERN_ACTIVE, CausalTracer, build_engine,
    find_earliest_modal_collision, find_persistent_ownership_collision,
    reconstruct_weight, run_interleaved_causal_audit, run_long_hold_causal_audit,
)


def _all_ff_weights(engine):
    return {(j, i): float(engine.l2.excitatory_neurons[j]._weights_array[i])
           for j in range(N_OUT) for i in range(N_PIX)}


# --------------------------------------------------------------------- non-mutation
def test_audit_reads_do_not_change_spikes_weights_or_timing():
    plain = build_engine(1, 1)
    traced = build_engine(1, 1)
    CausalTracer(traced)
    for _ in range(400):
        plain.step()
        traced.step()
    assert plain.timestep == traced.timestep
    assert _all_ff_weights(plain) == _all_ff_weights(traced)
    for j in range(N_OUT):
        assert plain._neuron_total_spikes.get(f'L2E{j}', 0) == traced._neuron_total_spikes.get(f'L2E{j}', 0)
    assert plain._neuron_total_spikes.get('L2I', 0) == traced._neuron_total_spikes.get('L2I', 0)


def test_prediction_flags_remain_off():
    engine = build_engine(1, 1)
    assert engine.prediction_column_enabled is False
    assert engine.prediction_excitatory_enabled is False


# --------------------------------------------------------------------- reconciliation
def test_all_weight_deltas_reconcile_with_actual_before_after_weights():
    engine, tracer, plog, initial_w = run_interleaved_causal_audit(1, 1, cycles=8)
    final_w = _all_ff_weights(engine)
    for j in range(N_OUT):
        for i in range(N_PIX):
            reconstructed = reconstruct_weight(initial_w, tracer.weight_delta_records, f'L2E{j}', i, engine.timestep)
            assert abs(reconstructed - final_w[(j, i)]) < 1e-3, (j, i, reconstructed, final_w[(j, i)])


def test_residual_bucket_catches_a_real_unattributed_mutation():
    engine = build_engine(1, 1)
    tracer = CausalTracer(engine)
    orig_deliver = engine._deliver_scheduled_l2_inhibition
    injected = {'done': False}

    def sneaky(t):
        result = orig_deliver(t)
        # A single, one-time direct weight mutation with NO patched hook
        # involved -- exactly the class of event the residual bucket exists
        # to catch. Guarded to fire exactly once (this method runs every
        # step) so the expected total is unambiguous.
        if not injected['done']:
            engine.l2.excitatory_neurons[0]._weights_array[0] += 5.0
            injected['done'] = True
        return result
    engine._deliver_scheduled_l2_inhibition = sneaky

    engine.set_pattern('row 1')
    for _ in range(60):
        engine.step()

    residual = [r for r in tracer.weight_delta_records if r['cause'] == 'residual_unattributed'
               and r['neuron'] == 'L2E0' and r['pixel'] == 0]
    assert residual, "the sneaky +5.0 mutation must be caught by the residual bucket"
    # Total residual delta attributed to this synapse equals the injected
    # mutation exactly (no absorption into any other bucket, no double count).
    assert abs(sum(r['delta'] for r in residual) - 5.0) < 1e-6


def test_no_residual_in_a_normal_unmodified_run():
    _engine, tracer, _plog, _initial_w = run_interleaved_causal_audit(2, 1, cycles=8)
    assert tracer._residual_seen == 0
    assert not any(r['cause'] == 'residual_unattributed' for r in tracer.weight_delta_records)


# --------------------------------------------------------------------- attribution
def test_presentation_and_timestep_attribution_are_correct():
    _engine, tracer, plog, _initial_w = run_interleaved_causal_audit(1, 1, cycles=5)
    # Windows are contiguous, ordered, non-overlapping, each exactly PRESENTATION_STEPS wide.
    for a, b in zip(plog, plog[1:]):
        assert a['t_end'] == b['t_start']
        assert a['presentation_index'] + 1 == b['presentation_index']
    for r in plog:
        assert r['t_end'] - r['t_start'] == PRESENTATION_STEPS

    # Every recorded spike falls inside exactly the presentation window whose
    # [t_start, t_end) contains its t.
    for sr in tracer.spike_records:
        matches = [r for r in plog if r['t_start'] <= sr['t'] < r['t_end']]
        assert len(matches) == 1, sr


def test_center_peripheral_attribution_is_correct():
    # CENTER_PIXEL must be the one pixel active in EVERY trained pattern --
    # verified against PATTERN_ACTIVE (derived from PATTERNS), not assumed.
    for pattern, active in PATTERN_ACTIVE.items():
        assert CENTER_PIXEL in active
    peripheral = [i for i in range(N_PIX) if i != CENTER_PIXEL]
    assert len(peripheral) == N_PIX - 1
    # No single peripheral pixel is active in all four patterns (that would
    # make CENTER_PIXEL's specialness arbitrary rather than structural).
    for i in peripheral:
        assert not all(i in active for active in PATTERN_ACTIVE.values())


# --------------------------------------------------------------------- collision detectors
def test_no_hardcoded_owner_or_outcome_in_collision_detectors():
    """Feed the detectors a synthetic log with neuron/pattern labels that do
    NOT match this codebase's own naming (no 'L2E', no real pattern names) --
    if the outcome still comes out correct, the logic is genuinely generic,
    not keyed to a hardcoded id string."""
    log = []
    idx = 0
    # 'alpha' and 'beta' both settle on 'Neuron_Z'; 'gamma' stays with 'Neuron_Y'.
    schedule = [('alpha', 'Neuron_Z')] * 5 + [('beta', 'Neuron_W')] * 3 + [('beta', 'Neuron_Z')] * 5 \
        + [('gamma', 'Neuron_Y')] * 6
    for pattern, spiker in schedule:
        log.append(dict(presentation_index=idx, cycle=idx, pattern=pattern, first_l2e_spiker=spiker))
        idx += 1
    persistent = find_persistent_ownership_collision(log)
    assert persistent is not None
    assert persistent['neuron'] == 'Neuron_Z'
    assert set(persistent['patterns_collided']) == {'alpha', 'beta'}
    assert persistent['displaced_competitor'] == 'Neuron_W'

    no_collision_log = [dict(presentation_index=i, cycle=i, pattern=p, first_l2e_spiker=f'N{p}')
                        for i, p in enumerate(['a', 'b', 'c'] * 4)]
    assert find_earliest_modal_collision(no_collision_log) is None
    assert find_persistent_ownership_collision(no_collision_log) is None


def test_collision_detectors_never_reference_real_pattern_or_neuron_names():
    import inspect
    import phase27_l2_ownership_causal_audit as mod
    src_earliest = inspect.getsource(mod.find_earliest_modal_collision)
    src_persistent = inspect.getsource(mod.find_persistent_ownership_collision)
    for banned in ('row 1', 'col 1', 'diag', 'L2E0', 'L2E1', 'L2E2', 'L2E3',
                  'L2E4', 'L2E5', 'L2E6', 'L2E7'):
        assert banned not in src_earliest
        assert banned not in src_persistent


# --------------------------------------------------------------------- determinism
def test_repeated_identical_seeds_are_deterministic():
    e1, t1, p1, w1 = run_interleaved_causal_audit(3, 1, cycles=6)
    e2, t2, p2, w2 = run_interleaved_causal_audit(3, 1, cycles=6)
    assert p1 == p2
    assert _all_ff_weights(e1) == _all_ff_weights(e2)
    assert len(t1.weight_delta_records) == len(t2.weight_delta_records)
    assert t1.weight_delta_records == t2.weight_delta_records
    assert w1 == w2


def test_long_hold_schedule_is_deterministic_and_separate_from_interleaved():
    e1, t1, p1, _w1 = run_long_hold_causal_audit(1, 1)
    e2, t2, p2, _w2 = run_long_hold_causal_audit(1, 1)
    assert p1 == p2
    assert _all_ff_weights(e1) == _all_ff_weights(e2)
    patterns_seen = {r['pattern'] for r in p1}
    assert patterns_seen == {'row 1', 'col 1'}
    assert 'diag \\' not in patterns_seen and 'diag /' not in patterns_seen


# --------------------------------------------------------------------- counting distinctions
def test_synapse_deltas_target_applications_and_l2i_deliveries_stay_distinct_counts():
    """Do not repeat Phase 13's counting ambiguity: these three counts
    measure different things and must not be silently equal by construction."""
    _engine, tracer, _plog, _w = run_interleaved_causal_audit(1, 1, cycles=15)
    loser_synapse_deltas = [r for r in tracer.weight_delta_records if r['cause'] == 'l2i_loser_depression']
    assert len(tracer.target_applications) > 0
    assert len(tracer.l2i_delivery_records) > 0
    # The three counts must be genuinely distinct measurements, not
    # accidentally-equal proxies for each other (Phase 13's own ambiguity):
    # one application can yield 0 synapse deltas (p_loss==0 / no eligible
    # synapse) or several (one per depressed pixel), so neither count implies
    # the other; and each delivery event fans out to multiple (up to N_OUT)
    # target applications, so the exhaustive delivery count is strictly
    # smaller than the total application count for any real run.
    assert len({len(loser_synapse_deltas), len(tracer.target_applications),
               len(tracer.l2i_delivery_records)}) == 3
    assert len(tracer.l2i_delivery_records) <= len(tracer.target_applications)
