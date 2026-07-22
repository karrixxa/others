"""Phase 5 lab homeostasis: L1 scaling + L2 sensory scaling."""

from __future__ import annotations

import unittest
from dataclasses import replace

from cognative_paradigm.domain.inhibitory_coupling import default_inhibitory_coupling
from cognative_paradigm.domain.input_edge import InputEdge
from cognative_paradigm.domain.sensory_conductance_map import SensoryConductanceMap
from cognative_paradigm.learning.sensory_homeostasis import SensoryHomeostasis
from cognative_paradigm.learning.synaptic_scaling import SynapticScalingHomeostasis
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import deterministic_dynamics


class LabSynapticScalingTests(unittest.TestCase):
    def test_lab_scaling_adjusts_l1_coupling(self) -> None:
        homeostasis = SynapticScalingHomeostasis(
            target_rate=0.15,
            eta=0.05,
            window=5,
            i_min=0.1,
            i_max=0.5,
            lab_enabled=True,
            lab_eta=0.05,
        )
        coupling = default_inhibitory_coupling()
        coupling = replace(coupling, inhibition_strength=0.3)
        edge = InputEdge(id="input_r0_c0", row=0, col=0)

        for _ in range(40):
            coupling, _ = homeostasis.update(
                coupling, grid_index=0, e_fired=True, input_edge=edge
            )

        self.assertNotAlmostEqual(coupling.inhibition_strength, 0.3, places=3)

    def test_production_scaling_stays_frozen(self) -> None:
        homeostasis = SynapticScalingHomeostasis.from_dynamics(
            DEFAULT_LEARNING_DYNAMICS
        )
        coupling = default_inhibitory_coupling()
        strength = coupling.inhibition_strength
        edge = InputEdge(id="input_r0_c0", row=0, col=0)
        for _ in range(30):
            coupling, _ = homeostasis.update(
                coupling, grid_index=0, e_fired=True, input_edge=edge
            )
        self.assertAlmostEqual(coupling.inhibition_strength, strength)


class SensoryHomeostasisTests(unittest.TestCase):
    def test_lab_scales_sensory_map(self) -> None:
        dynamics = replace(
            DEFAULT_LEARNING_DYNAMICS,
            scaling_lab_enabled=True,
            scaling_lab_eta=0.02,
        )
        homeostasis = SensoryHomeostasis(dynamics)
        sensory = SensoryConductanceMap(0.48)
        before = sensory.as_dict()["input_r1_c1"]
        for _ in range(50):
            homeostasis.update(
                "nucleus_e_0",
                spiked=False,
                sensory_conductances=sensory,
            )
        after = sensory.as_dict()["input_r1_c1"]
        self.assertNotAlmostEqual(before, after, places=4)


class LabHomeostasisIntegrationTests(unittest.TestCase):
    def test_engine_lab_coupling_moves(self) -> None:
        dynamics = replace(
            deterministic_dynamics(),
            scaling_lab_enabled=True,
            scaling_lab_eta=0.01,
        )
        sim = BrainSimulator(dynamics=dynamics)
        before = sim.layer1.pairs[0].coupling.inhibition_strength
        for _ in range(60):
            sim.stimulate_pattern(get_line("H1"))
        after = sim.layer1.pairs[0].coupling.inhibition_strength
        self.assertNotAlmostEqual(before, after, places=3)

    def test_production_coupling_unchanged(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        before = [
            pair.coupling.inhibition_strength for pair in sim.layer1.pairs
        ]
        for _ in range(40):
            sim.stimulate_pattern(get_line("H1"))
        after = [pair.coupling.inhibition_strength for pair in sim.layer1.pairs]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
