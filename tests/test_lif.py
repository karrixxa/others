import unittest

from cognative_paradigm.domain.lif_dynamics import LifDynamics, LifParameters
from cognative_paradigm.domain.neuron import Neuron
from cognative_paradigm.domain.register_state import RegisterState
from cognative_paradigm.lines import LINES
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import deterministic_dynamics, learn_catalog_line


class LifDynamicsTests(unittest.TestCase):
    def test_leak_decays_toward_rest(self) -> None:
        neuron = Neuron(id="n0", threshold=10.0)
        neuron.membrane = 2.0
        lif = LifDynamics(LifParameters(membrane_tau=5.0))

        lif.leak(neuron)

        self.assertLess(neuron.membrane, 2.0)
        self.assertGreater(neuron.membrane, 0.0)

    def test_subthreshold_stays_z(self) -> None:
        neuron = Neuron(id="n0", threshold=5.0)
        lif = LifDynamics()
        lif.leak(neuron)
        lif.integrate_synaptic_drive(neuron, 0.5)

        fired = lif.try_spike(neuron, timestep=1)

        self.assertFalse(fired)
        self.assertEqual(neuron.register, RegisterState.Z)

    def test_threshold_crossing_fires_and_resets(self) -> None:
        neuron = Neuron(id="n0", threshold=1.0, refractory_period=1)
        lif = LifDynamics(LifParameters(reset_potential=0.0))
        neuron.membrane = 1.5

        fired = lif.try_spike(neuron, timestep=1)

        self.assertTrue(fired)
        self.assertEqual(neuron.register, RegisterState.ONE)
        self.assertEqual(neuron.membrane, 0.0)
        self.assertTrue(neuron.is_refractory(1))

    def test_refractory_blocks_second_spike(self) -> None:
        neuron = Neuron(id="n0", threshold=0.5, refractory_period=2)
        lif = LifDynamics()
        neuron.membrane = 2.0
        lif.try_spike(neuron, timestep=1)
        neuron.membrane = 2.0

        fired = lif.try_spike(neuron, timestep=2)

        self.assertFalse(fired)
        self.assertEqual(neuron.register, RegisterState.ONE)


class LifSimulatorTests(unittest.TestCase):
    def test_simulator_learns_with_lif_dynamics(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        result = learn_catalog_line(sim, "H1")

        self.assertTrue(sim.neuron.memory.is_bound())
        self.assertIsNotNone(result.output_symbol)

    def test_weak_line_pulse_may_not_fire_immediately(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        for competitor in sim.nucleus.ring:
            competitor.neuron.threshold = 2.0

        result = sim.stimulate_pattern(LINES["H1"])

        self.assertEqual(result.neuron_register, "Z")

    def test_state_exposes_membrane(self) -> None:
        sim = BrainSimulator()
        sim.stimulate_pattern(LINES["H1"])
        state = sim.get_state()

        self.assertIn("membrane", state)
        self.assertIn("threshold", state)


if __name__ == "__main__":
    unittest.main()
