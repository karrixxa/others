import unittest

from cognative_paradigm.domain.input_edge import InputEdge
from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.domain.register_state import RegisterState
from cognative_paradigm.lines import index_to_edge_id
from cognative_paradigm.simulation.layer1_pair import Layer1Pair
from cognative_paradigm.simulation.layer1_pair_dynamics import Layer1PairDynamics


class Layer1PairDynamicsTests(unittest.TestCase):
    def test_stimulus_drives_excitatory_only(self) -> None:
        lif = LifDynamics()
        dynamics = Layer1PairDynamics(lif)
        pair = Layer1Pair(4)
        edge = InputEdge(id=index_to_edge_id(4), row=1, col=1, weight=0.75)

        fired = dynamics.process_active_pair(pair, edge, timestep=1)

        self.assertTrue(fired)
        self.assertEqual(pair.excitatory.register, RegisterState.ONE)
        self.assertEqual(pair.inhibitory.register, RegisterState.Z)

    def test_descending_inhibition_blocks_relay(self) -> None:
        lif = LifDynamics()
        dynamics = Layer1PairDynamics(lif)
        pair = Layer1Pair(4)
        edge = InputEdge(id=index_to_edge_id(4), row=1, col=1, weight=0.5)

        pair.inhibitory.fire(timestep=1)

        fired = dynamics.process_active_pair(pair, edge, timestep=1)

        self.assertFalse(fired)
        self.assertEqual(pair.excitatory.register, RegisterState.Z)
        self.assertEqual(pair.inhibitory.register, RegisterState.ONE)


if __name__ == "__main__":
    unittest.main()
