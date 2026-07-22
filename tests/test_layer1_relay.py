import unittest

from cognative_paradigm.lines import LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.layer1_relay import l1_relay_id
from tests.simulation_helpers import (
    deterministic_dynamics,
    learn_catalog_line,
    stimulate_until_pattern_bound,
)


class Layer1RelayTests(unittest.TestCase):
    def test_active_line_cells_fire_layer1_relay(self) -> None:
        sim = BrainSimulator()
        result = None
        for _ in range(5):
            result = sim.stimulate_pattern(get_line("H1"))
            if result.relay_indices:
                break

        assert result is not None
        self.assertEqual(sorted(result.relay_indices), [3, 4, 5])
        state = sim.get_state()
        fired = [
            pair
            for pair in state["layer1"]["pairs"]
            if pair["excitatory_register"] == "1"
        ]
        self.assertEqual(len(fired), 3)

    def test_nucleus_receives_layer1_relay(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        stimulate_until_pattern_bound(sim, LINE_INDICES["H1"])

        self.assertTrue(sim.get_state()["bound"])
        pattern = get_line("H1")
        owner = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertIsNotNone(owner)

    def test_inactive_cells_do_not_relay(self) -> None:
        sim = BrainSimulator()
        sim.stimulate_pattern(get_line("H1"))
        state = sim.get_state()
        inactive = [
            pair
            for pair in state["layer1"]["pairs"]
            if pair["grid_index"] == 0
        ]
        self.assertEqual(inactive[0]["excitatory_register"], "Z")

    def test_relay_ids_match_grid_indices(self) -> None:
        self.assertEqual(l1_relay_id(4), "l1_e_4")


if __name__ == "__main__":
    unittest.main()
