import unittest

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.domain.pattern import Pattern
from cognative_paradigm.domain.register_state import RegisterState
from cognative_paradigm.domain.symbol_registry import SymbolConflictError
from cognative_paradigm.lines import LINES, LINE_INDICES, get_line, index_to_edge_id
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import (
    deterministic_dynamics,
    learn_catalog_line,
    stimulate_until_pattern_bound,
)


class V01MilestoneTests(unittest.TestCase):
    def test_event_log_never_contains_z(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        sim.stimulate(LINES["H1"], duration=4)
        for entry in sim.event_log.entries:
            self.assertIn(entry["type"], EventType.__members__)

    def test_refractory_prevents_double_fire(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        target = sim.nucleus.competitor_by_id("nucleus_e_0")
        assert target is not None
        target.neuron.threshold = 0.18
        target.neuron.membrane = 0.20
        target.neuron.refractory_period = 2
        first = sim.step(LINES["H1"])
        second = sim.step(LINES["H1"])
        self.assertEqual(first.neuron_register, "1")
        self.assertEqual(target.neuron.register, RegisterState.Z)

    def test_learns_one_pattern_and_recognizes(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        result = learn_catalog_line(sim, "H1")
        self.assertTrue(sim.neuron.memory.is_bound())
        self.assertEqual(result.output_symbol, sim.neuron.bound_symbol_id)
        self.assertIsNotNone(result.output_symbol)
        pattern = get_line("H1")
        owner = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertIsNotNone(owner)

    def test_different_pattern_no_false_symbol(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_catalog_line(sim, "H1")
        result = sim.stimulate_pattern(get_line("V1"))
        self.assertIsNone(result.output_symbol)

    def test_second_pattern_rejected_on_same_neuron(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        stimulate_until_pattern_bound(sim, LINE_INDICES["H1"])
        pattern = get_line("H1")
        owner_id = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertIsNotNone(owner_id)
        registry = sim.symbols
        pattern_b = Pattern(edge_ids=frozenset({index_to_edge_id(2)}))
        with self.assertRaises(SymbolConflictError):
            registry.create(str(owner_id), pattern_b)


if __name__ == "__main__":
    unittest.main()
