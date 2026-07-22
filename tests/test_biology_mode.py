"""Biology mode: eligibility consolidation and pattern ownership."""

import unittest

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import pattern_from_indices
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.nucleus_line_competition import (
    COMPETITION_EQUILIBRIUM,
    COMPETITION_LEARNING,
)
from tests.simulation_helpers import biology_dynamics, deterministic_dynamics


class BiologyModeTests(unittest.TestCase):
    def test_repeated_pattern_stabilizes_one_owner(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(consolidation_weight_threshold=0.15),
        )
        pattern = pattern_from_indices([0, 1, 2])
        winner_ids: list[str] = []
        post_bind_winners: list[str] = []
        owner_id: str | None = None

        for _ in range(150):
            result = sim.stimulate_pattern(pattern)
            if result.winner_neuron_id:
                winner_ids.append(result.winner_neuron_id)
            if owner_id is None:
                owner_id = sim.nucleus.pattern_ownership.owner_for_pattern(
                    pattern.edge_ids
                )
            elif result.winner_neuron_id:
                post_bind_winners.append(result.winner_neuron_id)

        bound = [c for c in sim.nucleus.ring if c.neuron.memory.is_bound()]
        self.assertEqual(len(bound), 1)

        self.assertIsNotNone(owner_id)
        self.assertEqual(bound[0].neuron.id, owner_id)

        self.assertGreaterEqual(len(post_bind_winners), 10)
        self.assertIn(owner_id, set(post_bind_winners[-15:]))

        self.assertEqual(
            sim.get_state()["nucleus"]["competition_phase"],
            COMPETITION_EQUILIBRIUM,
        )

    def test_learning_phase_precedes_equilibrium(self) -> None:
        sim = BrainSimulator(
            dynamics=biology_dynamics(consolidation_weight_threshold=0.15),
        )
        pattern = pattern_from_indices([0, 1, 2])
        phases: list[str] = []
        for _ in range(100):
            sim.stimulate_pattern(pattern)
            phases.append(sim.get_state()["nucleus"]["competition_phase"])
            if sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids):
                break
        else:
            self.fail("pattern did not consolidate within 100 presentations")

        self.assertIn(COMPETITION_LEARNING, phases)

    def test_two_patterns_claim_two_neurons(self) -> None:
        sim = BrainSimulator(
            dynamics=biology_dynamics(consolidation_weight_threshold=0.15),
        )
        pattern_a = pattern_from_indices([0, 1, 2])
        pattern_b = pattern_from_indices([6, 7, 8])

        for _ in range(80):
            sim.stimulate_pattern(pattern_a)
            if sim.nucleus.pattern_ownership.owner_for_pattern(pattern_a.edge_ids):
                break
        for _ in range(80):
            sim.stimulate_pattern(pattern_b)
            if sim.nucleus.pattern_ownership.owner_for_pattern(pattern_b.edge_ids):
                break

        owner_a = sim.nucleus.pattern_ownership.owner_for_pattern(pattern_a.edge_ids)
        owner_b = sim.nucleus.pattern_ownership.owner_for_pattern(pattern_b.edge_ids)
        self.assertIsNotNone(owner_a)
        self.assertIsNotNone(owner_b)
        self.assertNotEqual(owner_a, owner_b)

    def test_eligibility_trace_in_ring_state(self) -> None:
        sim = BrainSimulator(dynamics=biology_dynamics())
        pattern = pattern_from_indices([0, 1, 2])
        saw_positive_trace = False
        for _ in range(30):
            sim.stimulate_pattern(pattern)
            ring = sim.get_state()["nucleus"]["ring"]
            traces = [
                entry["eligibility_trace"]
                for entry in ring
                if entry.get("eligibility_trace") is not None
            ]
            self.assertTrue(traces)
            if max(traces) > 0:
                saw_positive_trace = True
        self.assertTrue(saw_positive_trace)

    def test_pattern_bind_emits_symbol(self) -> None:
        sim = BrainSimulator(dynamics=biology_dynamics())
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
