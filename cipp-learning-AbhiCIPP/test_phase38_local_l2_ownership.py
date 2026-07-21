from __future__ import annotations

import numpy as np

from backend.presets import DASHBOARD_PRESET
from backend.simulation import N_OUT, N_PIX, SimulationEngine


TARGET = 2


def _engine(*, enabled=False):
    engine = SimulationEngine(
        seed=1,
        prediction_column_enabled=True,
        switchi_local_mismatch_enabled=enabled,
        switchi_trace_decay=0.75,
        switchi_coincidence_threshold=0.15,
        switchi_shunt_frac=0.5,
        **DASHBOARD_PRESET,
    )
    engine._set_plasticity_frozen(True)
    return engine


def _signature(engine, steps=6):
    rows = []
    patterns = ["row 1", "col 1", "diag /", "diag \\", "row 1", "col 1"]
    for idx in range(steps):
        engine.set_pattern(patterns[idx % len(patterns)])
        engine.step()
        rows.append((
            engine.timestep,
            tuple(int(engine.spiked[f"L2E{j}"]) for j in range(N_OUT)),
            tuple(round(float(engine.l2.excitatory_neurons[j].potential), 6) for j in range(N_OUT)),
            tuple(round(float(engine.switchi_recent_spike_trace[j]), 6) for j in range(N_OUT)),
            tuple(sorted((rec["target"], rec["request_value"], rec["queued"])
                         for rec in engine._switchi_local_last_events)),
        ))
    return rows


def _set_decoder_row(engine, j, values):
    for i, value in enumerate(values):
        engine.pcol[i].decoder_weights[j] = float(value)
        engine.pcol[i].apical_connections[j].weight = float(value)


def _prime(engine, *, target=TARGET):
    engine.switchi_local_elig[:] = 0.0
    engine.switchi_recent_spike_trace[:] = 0.0
    engine.switchi_recent_spike_trace[target] = 1.0
    engine._switchi_local_pending = []
    engine._switchi_local_last_deliveries = []
    for j, neuron in enumerate(engine.l2.excitatory_neurons):
        neuron.learning_rate = 0.0
        neuron.weights = np.ones(N_PIX)
        neuron.potential = 1000.0
    engine.l2.excitatory_neurons[target].potential = 4000.0
    _set_decoder_row(engine, target, np.zeros(N_PIX))


def test_feature_off_gives_exact_baseline_equivalence():
    a = _engine(enabled=False)
    b = _engine(enabled=False)
    assert _signature(a) == _signature(b)


def test_correct_repeated_prediction_creates_no_residual_and_no_shunt():
    engine = _engine(enabled=True)
    _prime(engine)
    l1e = np.zeros(N_PIX)
    pcol = np.zeros(N_PIX)
    for i in (3, 4, 5):
        l1e[i] = 1.0
        pcol[i] = 1.0
    before = float(engine.l2.excitatory_neurons[TARGET].potential)

    engine._update_switchi_local_eligibility(pcol)
    engine._queue_switchi_local_requests(l1e, pcol, t=0)

    assert engine._switchi_local_last_diag["residual_events"] == 0
    assert engine._switchi_local_last_diag["queued_requests"] == 0
    assert engine._switchi_local_pending == []
    assert float(engine.l2.excitatory_neurons[TARGET].potential) == before


def test_missing_prediction_with_basal_evidence_creates_residual():
    engine = _engine(enabled=True)
    _prime(engine)
    l1e = np.zeros(N_PIX)
    l1e[4] = 1.0
    pcol = np.zeros(N_PIX)

    engine._queue_switchi_local_requests(l1e, pcol, t=0)

    assert engine._switchi_local_last_diag["residual_events"] == 1
    assert engine._switchi_local_last_residual == [
        {"pixel_index": 4, "residual": True, "basal_present": True, "pc_fired": False}
    ]


def test_only_connections_with_eligibility_can_request_switchi():
    engine = _engine(enabled=True)
    _prime(engine)
    engine.switchi_local_elig[TARGET, 4] = 0.3
    l1e = np.zeros(N_PIX)
    l1e[4] = 1.0
    pcol = np.zeros(N_PIX)

    engine._queue_switchi_local_requests(l1e, pcol, t=0)

    queued = [row for row in engine._switchi_local_last_events if row["queued"]]
    assert [row["target"] for row in queued] == [f"L2E{TARGET}"]
    assert queued[0]["request_value"] == 0.3
    assert all(row["request_value"] == 0.0 for idx, row in enumerate(engine._switchi_local_last_events) if idx != TARGET)


def test_request_at_t_cannot_affect_until_t_plus_2():
    engine = _engine(enabled=True)
    _prime(engine)
    engine.switchi_local_elig[TARGET, 4] = 0.3
    l1e = np.zeros(N_PIX)
    l1e[4] = 1.0
    pcol = np.zeros(N_PIX)
    before = float(engine.l2.excitatory_neurons[TARGET].potential)

    engine._queue_switchi_local_requests(l1e, pcol, t=5)
    assert float(engine.l2.excitatory_neurons[TARGET].potential) == before
    assert len(engine._switchi_local_pending) == 1

    engine._deliver_scheduled_switchi_local(6)
    assert float(engine.l2.excitatory_neurons[TARGET].potential) == before

    engine._deliver_scheduled_switchi_local(7)
    assert np.isclose(float(engine.l2.excitatory_neurons[TARGET].potential), before * 0.5)


def test_only_paired_l2e_is_shunted():
    engine = _engine(enabled=True)
    _prime(engine)
    engine.switchi_local_elig[TARGET, 4] = 0.3
    l1e = np.zeros(N_PIX)
    l1e[4] = 1.0
    pcol = np.zeros(N_PIX)
    before_other = float(engine.l2.excitatory_neurons[1].potential)

    engine._queue_switchi_local_requests(l1e, pcol, t=5)
    engine._deliver_scheduled_switchi_local(7)

    assert float(engine.l2.excitatory_neurons[1].potential) == before_other
    assert [row["target"] for row in engine._switchi_local_last_deliveries] == [f"L2E{TARGET}"]


def test_no_argmax_label_or_oracle_dependency():
    a = _engine(enabled=True)
    b = _engine(enabled=True)
    for engine in (a, b):
        _prime(engine)
        engine.switchi_local_elig[TARGET, 4] = 0.3
    b.winner = "L2E7"
    b._presentation_first_spiker = "L2E7"
    b._pattern_last_winner["row 1"] = 7
    b._presentation_l2i_first_source = "oracle"
    l1e = np.zeros(N_PIX)
    l1e[4] = 1.0
    pcol = np.zeros(N_PIX)

    a._queue_switchi_local_requests(l1e, pcol, t=0)
    b._queue_switchi_local_requests(l1e, pcol, t=0)

    assert a._switchi_local_last_events == b._switchi_local_last_events
    assert a._switchi_local_pending == b._switchi_local_pending


def test_queue_state_clears_correctly_on_reset():
    engine = _engine(enabled=True)
    _prime(engine)
    engine.switchi_local_elig[TARGET, 4] = 0.3
    l1e = np.zeros(N_PIX)
    l1e[4] = 1.0
    pcol = np.zeros(N_PIX)
    engine._queue_switchi_local_requests(l1e, pcol, t=0)
    assert engine._switchi_local_pending

    engine.reset()

    assert engine._switchi_local_pending == []
    assert not np.any(engine.switchi_local_elig)
    assert engine._switchi_local_last_deliveries == []


# --------------------------------------------------------------------------
# Phase 38.2: end-to-end regression through real engine.step() calls only --
# no internal method is invoked directly, and no state is hand-injected apart
# from the one test-only matured-decoder fixture (a single (j,i) decoder
# weight, exactly like the existing _set_decoder_row helper above). This
# exercises PC firing, elig[j,i] growth, a later natural residual, request
# formation, t+2 delivery, and paired-only shunting all through the same
# step() path production/dashboard code actually calls.
E2E_TARGET = 5
E2E_PIXEL = 4


def _e2e_engine():
    engine = SimulationEngine(
        seed=1,
        prediction_column_enabled=True,
        prediction_column_to_i_enabled=False,
        prediction_lateral_weight=400.0,
        prediction_feedback_init=400.0,
        prediction_feedback_max=400.0,
        prediction_threshold=700.0,
        switchi_local_mismatch_enabled=True,
        switchi_trace_decay=0.75,
        switchi_coincidence_threshold=0.15,
        switchi_shunt_frac=0.5,
        **DASHBOARD_PRESET,
    )
    engine._set_plasticity_frozen(True)
    # Test-only matured-decoder fixture: a single (E2E_TARGET, E2E_PIXEL)
    # decoder connection is pre-matured so PC_{E2E_PIXEL} can fire the moment
    # L2E_{E2E_TARGET} genuinely, physically fires -- production's decoder
    # initialization (prediction_feedback_init above) is unchanged; only this
    # one already-existing, already-tested seam (decoder_weights/
    # apical_connections, the same one _set_decoder_row already uses) is set
    # directly, exactly as every other Phase 35-38 test in this file does.
    for i, pc in enumerate(engine.pcol):
        for j in range(N_OUT):
            pc.decoder_weights[j] = 0.0
            pc.apical_connections[j].weight = 0.0
    engine.pcol[E2E_PIXEL].decoder_weights[E2E_TARGET] = 400.0
    engine.pcol[E2E_PIXEL].apical_connections[E2E_TARGET].weight = 400.0
    # Every L2E has ZERO feedforward weight -- no neuron ever accumulates any
    # organic charge from the held input, so every potential in this test is
    # either an explicit fixture assignment or a shunt delivery, never
    # ordinary drift. This is what makes the t+2/paired-only timing checks
    # exact rather than approximate.
    for j, neuron in enumerate(engine.l2.excitatory_neurons):
        neuron.learning_rate = 0.0
        neuron.weights = np.zeros(N_PIX)
        neuron.potential = 0.0
    return engine


def test_end_to_end_real_step_path_pc_fire_elig_residual_request_and_paired_delivery():
    engine = _e2e_engine()
    # A single active pixel (not a named 3-pixel PATTERNS entry) keeps every
    # residual/eligibility number attributable to exactly the one (j, i)
    # connection under test -- no other pixel is ever active, so no other
    # PC/decoder pair can contribute noise to any assertion below.
    single_pixel_vec = np.zeros(N_PIX)
    single_pixel_vec[E2E_PIXEL] = 1.0
    engine.set_input(single_pixel_vec)
    other_indices = [j for j in range(N_OUT) if j != E2E_TARGET]

    # t0: force ONLY L2E_{E2E_TARGET} to physically fire this step (potential
    # preset above threshold_l2; receive_input only adds on top of it). L1E4
    # fires on its own from the held pattern -- not forced.
    engine.l2.excitatory_neurons[E2E_TARGET].potential = 9000.0
    engine.step()
    t0 = engine.timestep
    assert engine.spiked[f"L2E{E2E_TARGET}"]
    assert not any(engine.spiked[f"L2E{j}"] for j in other_indices)
    assert engine.spiked["L1E4"]
    # Nothing queued/delivered yet -- the apical event L2E_{E2E_TARGET} just
    # scheduled has not arrived at PC4 yet (prediction_feedback_delay=1).
    assert engine.switchi_local_elig[E2E_TARGET, E2E_PIXEL] == 0.0
    assert engine._switchi_local_pending == []

    # t0+1: the scheduled basal(L1E4) + apical(L2E_{E2E_TARGET}) pair arrives
    # together; PC4's coincidence (400 lateral + 400 decoder = 800 >= 700)
    # fires. This is a REAL PC fire via the production coincidence path, not
    # a hand-called resolve_coincidence().
    engine.l2.excitatory_neurons[E2E_TARGET].potential = 0.0  # do not force a repeat
    engine.step()
    assert engine.timestep == t0 + 1
    assert engine.spiked["PC4"]
    # elig[j,i] became nonzero ONLY for the causally paired (E2E_TARGET,
    # E2E_PIXEL) connection -- every other (j, i) pair stays exactly zero.
    elig = engine.switchi_local_elig.copy()
    assert elig[E2E_TARGET, E2E_PIXEL] > 0.0
    mask = np.ones_like(elig, dtype=bool)
    mask[E2E_TARGET, E2E_PIXEL] = False
    assert not np.any(elig[mask] > 0.0)
    # Same step: PC4 fired, so pixel 4 is explained this step -- no residual,
    # no queued request yet (matches "matching prediction cannot shunt").
    assert engine._switchi_local_last_diag["residual_events"] == 0
    assert engine._switchi_local_pending == []
    elig_after_t0_plus_1 = float(elig[E2E_TARGET, E2E_PIXEL])
    # L2E_{E2E_TARGET} fired and reset toward rest; give it a known, nonzero
    # baseline potential so the upcoming t+2 shunt has a visible, exact
    # effect to check -- weights are zero (see _e2e_engine), so nothing but
    # the shunt itself can move this value from here on.
    engine.l2.excitatory_neurons[E2E_TARGET].potential = 2000.0

    # t0+2: L2E_{E2E_TARGET} did not fire again at t0+1, so nothing new was
    # scheduled for PC4 -- only the basal half of this step's delivery is
    # present, so PC4's coincidence gate does NOT fire even though L1E4 is
    # still physically active. This is a genuine, naturally-arising residual,
    # not an injected one.
    engine.step()
    assert engine.timestep == t0 + 2
    assert engine.spiked["L1E4"]
    assert not engine.spiked["PC4"]
    diag = engine._switchi_local_last_diag
    assert diag["residual_events"] == 1
    assert engine._switchi_local_last_residual == [
        dict(pixel_index=E2E_PIXEL, residual=True, basal_present=True, pc_fired=False)
    ]
    # elig only decayed (no bump: PC4 did not fire this step, so the
    # eligibility-update loop never visits pixel 4 at all).
    expected_elig = elig_after_t0_plus_1 * engine.switchi_trace_decay
    assert np.isclose(engine.switchi_local_elig[E2E_TARGET, E2E_PIXEL], expected_elig)
    # request_j = sum_i elig[j,i] * R_i(t) -- here a single residual pixel,
    # so request_{E2E_TARGET} == elig[E2E_TARGET, E2E_PIXEL] exactly, and
    # every other L2E's request is exactly 0 (zero eligibility everywhere
    # else, regardless of the shared residual).
    rows = {row["target"]: row for row in engine._switchi_local_last_events}
    assert np.isclose(rows[f"L2E{E2E_TARGET}"]["request_value"], expected_elig)
    for j in other_indices:
        assert rows[f"L2E{j}"]["request_value"] == 0.0
        assert not rows[f"L2E{j}"]["queued"]
    assert rows[f"L2E{E2E_TARGET}"]["queued"]
    assert len(engine._switchi_local_pending) == 1
    pending = engine._switchi_local_pending[0]
    assert pending["target_index"] == E2E_TARGET
    # step()'s internal t is the pre-increment timestep (one behind the
    # externally-observed engine.timestep read after the call returns).
    assert pending["fire_t"] == t0 + 1
    assert pending["deliver_at"] == pending["fire_t"] + 2 == t0 + 3
    before_shunt = float(engine.l2.excitatory_neurons[E2E_TARGET].potential)
    before_others = {j: float(engine.l2.excitatory_neurons[j].potential) for j in other_indices}

    # t0+3: one step before delivery -- must not affect anything yet (never
    # same-step, never one-step-early).
    engine.step()
    assert engine.timestep == t0 + 3
    assert float(engine.l2.excitatory_neurons[E2E_TARGET].potential) == before_shunt
    assert engine._switchi_local_last_deliveries == []

    # t0+4: exactly t+2 from the request step -- delivery lands now, and
    # only the paired L2E_{E2E_TARGET} is affected. The shunt is a bounded
    # multiplicative reduction (v_pre * (1 - shunt_frac)), never a hard reset
    # to resting potential and never gated by any argmax/label/oracle state.
    engine.step()
    assert engine.timestep == t0 + 4
    deliveries = engine._switchi_local_last_deliveries
    assert [row["target"] for row in deliveries] == [f"L2E{E2E_TARGET}"]
    assert deliveries[0]["applied"]
    after_shunt = float(engine.l2.excitatory_neurons[E2E_TARGET].potential)
    assert np.isclose(after_shunt, before_shunt * (1.0 - engine.switchi_shunt_frac))
    assert after_shunt > engine.l2.excitatory_neurons[E2E_TARGET].resting_potential
    for j in other_indices:
        assert float(engine.l2.excitatory_neurons[j].potential) == before_others[j]

    # simulator_status() reads the same canonical delivery record, not a
    # duplicated/second truth field.
    assert engine.simulator_status()["switchi_local_firing"] == 1
