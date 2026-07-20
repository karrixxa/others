"""Exact Phase 35 Gate A contract. Run from the repository source directory."""

import numpy as np

from backend.presets import DASHBOARD_PRESET
from backend.simulation import SimulationEngine
from neuron_flexible import Neuron
from snn.dendrite import (CoincidencePyramidalCell, DendriteCompartment,
                          DendriteRole)


def cell(apical=400.0, basal=150.0, threshold=500.0):
    soma = Neuron(n_inputs=1, threshold=threshold, refractory_period=0,
                  learning_rate=0.0, leak_rate=0.0)
    soma._weights_array = np.array([1.0])
    return CoincidencePyramidalCell(soma, "L1E0", ["L2E0"], basal,
                                    [apical], threshold)


def test_construction_and_roles():
    pc = cell()
    assert isinstance(pc.basal, DendriteCompartment)
    assert pc.basal.role is DendriteRole.BASAL
    assert pc.apical.role is DendriteRole.APICAL
    assert pc.basal_connection.target is pc.basal
    assert pc.apical_connections[0].target is pc.apical
    assert pc.soma is not pc.basal and pc.soma is not pc.apical


def test_negative_controls_and_exact_step():
    pc = cell()
    pc.deliver_basal(1.0, 4)
    assert not pc.resolve_coincidence(4) and pc.potential == 0.0
    pc.update()
    pc.deliver_apical(0, 1.0, 5)
    assert not pc.resolve_coincidence(5) and pc.potential == 0.0
    pc.update()
    pc.deliver_basal(1.0, 6); pc.deliver_apical(0, 1.0, 6)
    assert pc.resolve_coincidence(6)


def test_offsets_rejected_and_clearing():
    for basal_step, apical_step in ((7, 8), (8, 7)):
        pc = cell()
        if basal_step < apical_step:
            pc.deliver_basal(1.0, basal_step); pc.update(); pc.deliver_apical(0, 1.0, apical_step)
        else:
            pc.deliver_apical(0, 1.0, apical_step); pc.update(); pc.deliver_basal(1.0, basal_step)
        assert not pc.resolve_coincidence(max(basal_step, apical_step))
        assert pc.potential == 0.0
    pc.update()
    assert pc.basal.delivery_step is None and pc.apical.delivery_step is None
    assert not pc.basal.deliveries and not pc.apical.deliveries


def test_no_trace_driven_firing():
    pc = cell()
    pc.deliver_basal(1.0, 1); pc.update()
    for _ in range(10): pc.update()
    pc.deliver_apical(0, 1.0, 12)
    assert not pc.resolve_coincidence(12)
    assert pc.potential == 0.0


def test_ordinary_neuron_unchanged():
    a = Neuron(n_inputs=1, threshold=10.0, refractory_period=0, learning_rate=0.0, leak_rate=0.0)
    b = Neuron(n_inputs=1, threshold=10.0, refractory_period=0, learning_rate=0.0, leak_rate=0.0)
    for n in (a, b): n._weights_array = np.array([4.0])
    for signal in (1.0, 0.0, 1.0, 1.0):
        for n in (a, b):
            n.receive_input(np.array([signal]));
            if n.check_threshold(): n.fire()
            n.update()
        assert a.potential == b.potential
        assert a.refractory_timer == b.refractory_timer
        assert a.spiked == b.spiked
        assert np.array_equal(a._weights_array, b._weights_array)


def test_default_off_equivalence():
    a = SimulationEngine(seed=71, **DASHBOARD_PRESET)
    b = SimulationEngine(seed=71, prediction_column_enabled=False, **DASHBOARD_PRESET)
    for _ in range(60): a.step(); b.step()
    assert a.dynamic_state() == b.dynamic_state()
    assert a.topology() == b.topology()


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests: test(); print("PASS", test.__name__)
    print(f"GATE_A_PASS {len(tests)}")
