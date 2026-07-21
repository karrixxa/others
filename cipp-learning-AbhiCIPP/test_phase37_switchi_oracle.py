"""Deterministic smoke tests for the Phase 37 paired SwitchI oracle ablation."""

import numpy as np

from backend.presets import DASHBOARD_PRESET
from backend.simulation import N_PIX, SimulationEngine


TARGET = 2


def _engine(enabled=True):
    engine = SimulationEngine(
        seed=1,
        switchi_paired_shunt_enabled=enabled,
        switchi_trace_decay=0.75,
        switchi_coincidence_threshold=0.15,
        switchi_shunt_frac=0.5,
        **DASHBOARD_PRESET,
    )
    engine._set_plasticity_frozen(True)
    return engine


def _prime_local_residual(engine, target=TARGET):
    ff_vec = np.zeros(N_PIX)
    ff_vec[[3, 4, 5]] = 1.0
    for j, neuron in enumerate(engine.l2.excitatory_neurons):
        neuron.learning_rate = 0.0
        neuron.weights = np.full(N_PIX, 1.0)
        neuron.potential = 1000.0 if j != target else 4000.0
    strong = np.full(N_PIX, 1.0)
    strong[[3, 4, 5]] = 3000.0
    engine.l2.excitatory_neurons[target].weights = strong
    engine.switchi_recent_spike_trace[:] = 0.0
    engine.switchi_recent_spike_trace[target] = 1.0
    return ff_vec


def test_switchi_default_off_is_inert():
    engine = _engine(enabled=False)
    ff_vec = _prime_local_residual(engine)
    before = float(engine.l2.excitatory_neurons[TARGET].potential)

    engine._apply_switchi_paired_shunt(ff_vec, t=0)

    assert engine._switchi_last_events == []
    assert float(engine.l2.excitatory_neurons[TARGET].potential) == before


def test_switchi_shunts_only_the_paired_l2e_when_local_coincidence_is_present():
    engine = _engine(enabled=True)
    ff_vec = _prime_local_residual(engine)
    before_target = float(engine.l2.excitatory_neurons[TARGET].potential)
    before_other = float(engine.l2.excitatory_neurons[1].potential)

    engine._apply_switchi_paired_shunt(ff_vec, t=0)

    fired = [row for row in engine._switchi_last_events if row["fired"]]
    assert [row["target"] for row in fired] == [f"L2E{TARGET}"]
    assert np.isclose(engine.l2.excitatory_neurons[TARGET].potential, before_target * 0.5)
    assert float(engine.l2.excitatory_neurons[1].potential) == before_other


def test_switchi_requires_both_residual_input_and_recent_spike_trace():
    engine = _engine(enabled=True)
    ff_vec = _prime_local_residual(engine)
    engine.switchi_recent_spike_trace[TARGET] = 0.0
    before = float(engine.l2.excitatory_neurons[TARGET].potential)

    engine._apply_switchi_paired_shunt(ff_vec, t=0)
    assert not any(row["fired"] for row in engine._switchi_last_events)
    assert float(engine.l2.excitatory_neurons[TARGET].potential) == before

    ff_vec[:] = 0.0
    engine.switchi_recent_spike_trace[TARGET] = 1.0
    engine._apply_switchi_paired_shunt(ff_vec, t=1)
    assert not any(row["fired"] for row in engine._switchi_last_events)
    assert float(engine.l2.excitatory_neurons[TARGET].potential) == before
