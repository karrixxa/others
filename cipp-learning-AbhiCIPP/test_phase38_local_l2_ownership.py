from __future__ import annotations

import copy

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


def _decoder_row(engine, j, values):
    for i, weight in enumerate(values):
        engine.pcol[i].decoder_weights[j] = float(weight)
        engine.pcol[i].apical_connections[j].weight = float(weight)


def _prime_target(engine, *, target=TARGET):
    for j, neuron in enumerate(engine.l2.excitatory_neurons):
        neuron.learning_rate = 0.0
        neuron.weights = np.ones(N_PIX)
        neuron.potential = 1200.0
    engine.l2.excitatory_neurons[target].potential = 4000.0
    engine.switchi_recent_spike_trace[:] = 0.0
    engine.switchi_recent_spike_trace[target] = 1.0
    _decoder_row(engine, target, np.zeros(N_PIX))


def _step_signature(engine, steps=6):
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
            engine.winner,
            tuple(sorted((k, round(v, 6)) for k, v in engine.l2_charge.items())),
        ))
    return rows


def test_disabled_is_exact_baseline_equivalence():
    baseline = _engine(enabled=False)
    explicit_off = _engine(enabled=False)
    assert _step_signature(baseline) == _step_signature(explicit_off)


def test_matching_prediction_does_not_shunt():
    engine = _engine(enabled=True)
    _prime_target(engine)
    match_pixels = [3, 4, 5]
    _decoder_row(engine, TARGET, [3000.0 if i in match_pixels else 0.0 for i in range(N_PIX)])
    engine.l2.excitatory_neurons[TARGET].weights = np.array(
        [1.0, 1.0, 1.0, 3000.0, 3000.0, 3000.0, 1.0, 1.0, 1.0]
    )
    l1e = np.zeros(N_PIX)
    pcol = np.zeros(N_PIX)
    for i in match_pixels:
        l1e[i] = 1.0
        pcol[i] = 1.0
    before = float(engine.l2.excitatory_neurons[TARGET].potential)

    engine._apply_switchi_local_mismatch_shunt(l1e, pcol, t=0)

    fired = [row for row in engine._switchi_local_last_events if row["fired"]]
    assert fired == []
    assert float(engine.l2.excitatory_neurons[TARGET].potential) == before
    assert engine._switchi_local_last_events[TARGET]["mismatch_drive"] == 0.0


def test_mismatch_activates_only_paired_switchi():
    engine = _engine(enabled=True)
    _prime_target(engine)
    predicted = [3, 4, 5]
    current = [1, 4, 7]
    _decoder_row(engine, TARGET, [3000.0 if i in predicted else 0.0 for i in range(N_PIX)])
    engine.l2.excitatory_neurons[TARGET].weights = np.array(
        [1.0, 3200.0, 1.0, 1.0, 3200.0, 1.0, 1.0, 3200.0, 1.0]
    )
    before_target = float(engine.l2.excitatory_neurons[TARGET].potential)
    before_other = float(engine.l2.excitatory_neurons[1].potential)
    l1e = np.zeros(N_PIX)
    pcol = np.zeros(N_PIX)
    for i in current:
        l1e[i] = 1.0
    for i in predicted:
        pcol[i] = 1.0

    engine._apply_switchi_local_mismatch_shunt(l1e, pcol, t=0)

    fired = [row for row in engine._switchi_local_last_events if row["fired"]]
    assert [row["target"] for row in fired] == [f"L2E{TARGET}"]
    assert np.isclose(float(engine.l2.excitatory_neurons[TARGET].potential), before_target * 0.5)
    assert float(engine.l2.excitatory_neurons[1].potential) == before_other


def test_other_l2_neurons_remain_directly_unaffected():
    engine = _engine(enabled=True)
    _prime_target(engine)
    _decoder_row(engine, TARGET, [3000.0 if i in (0, 1, 2) else 0.0 for i in range(N_PIX)])
    engine.l2.excitatory_neurons[TARGET].weights = np.array(
        [1.0, 1.0, 1.0, 3200.0, 3200.0, 3200.0, 1.0, 1.0, 1.0]
    )
    others_before = [float(engine.l2.excitatory_neurons[j].potential) for j in range(N_OUT) if j != TARGET]
    l1e = np.zeros(N_PIX)
    pcol = np.zeros(N_PIX)
    l1e[[3, 4, 5]] = 1.0
    pcol[[0, 1, 2]] = 1.0

    engine._apply_switchi_local_mismatch_shunt(l1e, pcol, t=0)

    others_after = [float(engine.l2.excitatory_neurons[j].potential) for j in range(N_OUT) if j != TARGET]
    assert others_after == others_before


def test_no_oracle_label_or_argmax_dependency():
    engine_a = _engine(enabled=True)
    engine_b = _engine(enabled=True)
    for engine in (engine_a, engine_b):
        _prime_target(engine)
        _decoder_row(engine, TARGET, [3000.0 if i in (0, 1, 2) else 0.0 for i in range(N_PIX)])
        engine.l2.excitatory_neurons[TARGET].weights = np.array(
            [1.0, 1.0, 1.0, 3200.0, 3200.0, 3200.0, 1.0, 1.0, 1.0]
        )
    engine_b.winner = "L2E7"
    engine_b._presentation_first_spiker = "L2E7"
    engine_b._presentation_l2i_first_source = "oracle"
    engine_b._pattern_last_winner["row 1"] = 7
    l1e = np.zeros(N_PIX)
    pcol = np.zeros(N_PIX)
    l1e[[3, 4, 5]] = 1.0
    pcol[[0, 1, 2]] = 1.0

    engine_a._apply_switchi_local_mismatch_shunt(l1e, pcol, t=0)
    engine_b._apply_switchi_local_mismatch_shunt(l1e, pcol, t=0)

    assert engine_a._switchi_local_last_events == engine_b._switchi_local_last_events
    assert np.allclose(
        [n.potential for n in engine_a.l2.excitatory_neurons],
        [n.potential for n in engine_b.l2.excitatory_neurons],
    )
