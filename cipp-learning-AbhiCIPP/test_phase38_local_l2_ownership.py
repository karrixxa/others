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
