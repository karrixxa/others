import unittest

from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.layer1_lateral import grid_neighbors


class Layer1LateralTests(unittest.TestCase):
    def test_grid_neighbors_center_has_four(self) -> None:
        self.assertEqual(sorted(grid_neighbors(4)), [1, 3, 5, 7])

    def test_grid_neighbors_corner_has_two(self) -> None:
        self.assertEqual(sorted(grid_neighbors(0)), [1, 3])

    def test_neighbor_membrane_reduced_after_relay_spike(self) -> None:
        sim = BrainSimulator()
        neighbor = sim.layer1.pairs[1]
        neighbor.excitatory.membrane = 0.6

        sim.stimulate_pattern(get_line("H1"))
        self.assertLess(neighbor.excitatory.membrane, 0.6)


if __name__ == "__main__":
    unittest.main()
