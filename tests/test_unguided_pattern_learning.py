"""Milestone: repeated sensory patterns stabilize on one ring neuron via WTA."""

import unittest

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import pattern_from_indices
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.nucleus_line_competition import (
    COMPETITION_EQUILIBRIUM,
    COMPETITION_LEARNING,
)
from tests.simulation_helpers import biology_dynamics, deterministic_dynamics


class UnguidedPatternLearningTests(unittest.TestCase):
    def test_repeated_pattern_stabilizes_one_owner(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(consolidation_weight_threshold=0.15),
        )
        pattern = pattern_from_indices([0, 1, 2])
        winner_ids: list[str] = []

        for _ in range(100):
            result = sim.stimulate_pattern(pattern)
            if result.winner_neuron_id:
                winner_ids.append(result.winner_neuron_id)

        bound = [c for c in sim.nucleus.ring if c.neuron.memory.is_bound()]
        self.assertEqual(len(bound), 1, "one neuron should own the pattern")

        owner_id = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertIsNotNone(owner_id)
        self.assertEqual(bound[0].neuron.id, owner_id)

        late_winners = [wid for wid in winner_ids[-20:] if wid is not None]
        self.assertTrue(late_winners, "owner should keep winning after bind")
        self.assertIn(owner_id, set(late_winners))

        nucleus = sim.get_state()["nucleus"]
        self.assertEqual(nucleus["competition_phase"], COMPETITION_EQUILIBRIUM)

    def test_learning_phase_precedes_equilibrium(self) -> None:
        sim = BrainSimulator(
            dynamics=biology_dynamics(consolidation_weight_threshold=0.15),
        )
        pattern = pattern_from_indices([0, 1, 2])
        phases: list[str] = []
        for _ in range(80):
            sim.stimulate_pattern(pattern)
            phases.append(sim.get_state()["nucleus"]["competition_phase"])
            if sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids):
                break
        else:
            self.fail("pattern did not consolidate within 80 presentations")

        self.assertIn(COMPETITION_LEARNING, phases)
        sim.stimulate_pattern(pattern)
        self.assertEqual(
            sim.get_state()["nucleus"]["competition_phase"],
            COMPETITION_EQUILIBRIUM,
        )

    def test_two_patterns_claim_two_neurons(self) -> None:
        sim = BrainSimulator(
            dynamics=biology_dynamics(consolidation_weight_threshold=0.15),
        )
        pattern_a = pattern_from_indices([0, 1, 2])
        pattern_b = pattern_from_indices([6, 7, 8])

        for _ in range(60):
            sim.stimulate_pattern(pattern_a)
            if sim.nucleus.pattern_ownership.owner_for_pattern(pattern_a.edge_ids):
                break
        for _ in range(60):
            sim.stimulate_pattern(pattern_b)
            if sim.nucleus.pattern_ownership.owner_for_pattern(pattern_b.edge_ids):
                break

        owner_a = sim.nucleus.pattern_ownership.owner_for_pattern(pattern_a.edge_ids)
        owner_b = sim.nucleus.pattern_ownership.owner_for_pattern(pattern_b.edge_ids)
        self.assertIsNotNone(owner_a)
        self.assertIsNotNone(owner_b)
        self.assertNotEqual(owner_a, owner_b)

    def test_pattern_bind_emits_no_catalog_line_id(self) -> None:
        sim = BrainSimulator(
            dynamics=biology_dynamics(consolidation_weight_threshold=0.15),
        )
        pattern = pattern_from_indices([3, 4, 5])
        bound = False
        for _ in range(150):
            result = sim.stimulate_pattern(pattern)
            bound_events = [
                event
                for event in result.step_events
                if event["type"] == EventType.PATTERN_BOUND.name
            ]
            if bound_events:
                bound = True
                symbol = bound_events[0].get("symbol") or result.output_symbol
                self.assertTrue(str(symbol).startswith("sigma_"))
                break
        self.assertTrue(bound)


if __name__ == "__main__":
    unittest.main()
