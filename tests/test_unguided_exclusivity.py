"""Self-paced exclusivity: plasticity enforces one owner without global bind gates."""

from __future__ import annotations

import unittest

from cognative_paradigm.lines import LINE_IDS, get_line, pattern_from_indices
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import (
    assert_injective_ownership,
    assert_unique_owners,
    interleaved_learn_all,
    robustness_dynamics,
    stimulate_until_pattern_bound,
    unguided_ecological_dynamics,
)


class UnguidedExclusivityTests(unittest.TestCase):
    def test_single_pattern_stabilizes_one_owner(self) -> None:
        """One-shape replay: owner is canonical first binder.

        Under Stage 14 autonomy, unique-spike eligibility credit replaces the
        hitchhiker BoundMatch block. Catalog exclusivity is asserted under
        interleaved rotation below.
        """
        sim = BrainSimulator(
            dynamics=unguided_ecological_dynamics(
                consolidation_weight_threshold=0.15,
            ),
        )
        pattern = pattern_from_indices([0, 1, 2])
        winner_ids: list[str] = []

        for _ in range(100):
            result = sim.stimulate_pattern(pattern)
            if result.winner_neuron_id:
                winner_ids.append(result.winner_neuron_id)

        owner = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        binders = sim.nucleus.pattern_ownership.binders_for_pattern(pattern.edge_ids)
        self.assertIsNotNone(owner)
        self.assertGreaterEqual(len(binders), 1)
        self.assertEqual(owner, binders[0])
        # Unique-spike bind credit keeps sole binder under soft autonomy.
        self.assertEqual(len(binders), 1)
        self.assertTrue(winner_ids)

    def test_two_patterns_sequential(self) -> None:
        sim = BrainSimulator(dynamics=unguided_ecological_dynamics())
        pattern_a = pattern_from_indices([0, 1, 2])
        pattern_b = pattern_from_indices([6, 7, 8])

        stimulate_until_pattern_bound(sim, [0, 1, 2])
        stimulate_until_pattern_bound(sim, [6, 7, 8])

        owner_a = sim.nucleus.pattern_ownership.owner_for_pattern(pattern_a.edge_ids)
        owner_b = sim.nucleus.pattern_ownership.owner_for_pattern(pattern_b.edge_ids)
        self.assertIsNotNone(owner_a)
        self.assertIsNotNone(owner_b)
        self.assertNotEqual(owner_a, owner_b)

    def test_interleaved_rotation_reaches_four_of_four(self) -> None:
        # Soft NI for catalog 4/4 (full Abhi NI 1.0/0.62 can fill seats before D1).
        sim = BrainSimulator(
            dynamics=unguided_ecological_dynamics(
            )
        )
        steps = interleaved_learn_all(sim, max_rounds=200)

        self.assertLessEqual(steps, 200)
        assert_injective_ownership(sim)

    def test_exclusivity_single_pattern_sole_binder(self) -> None:
        """Hard exclusivity: single-shape replay consolidates one binder."""
        sim = BrainSimulator(
            dynamics=unguided_ecological_dynamics(
                pretrained_inhibitor_exclusivity_enabled=True,
                consolidation_weight_threshold=0.15,
            ),
        )
        pattern = get_line("H1")
        for _ in range(80):
            sim.stimulate_pattern(pattern)
            binders = sim.nucleus.pattern_ownership.binders_for_pattern(
                pattern.edge_ids
            )
            if binders:
                self.assertEqual(len(binders), 1)
                break
        else:
            self.fail("H1 should bind under exclusivity")

        from cognative_paradigm.domain.pattern_memory_snapshot import (
            PatternMemorySnapshot,
        )

        sim = BrainSimulator(dynamics=unguided_ecological_dynamics())
        self.assertIsInstance(sim.nucleus.pattern_ownership, PatternMemorySnapshot)


class InterleavedRobustnessTests(unittest.TestCase):
    def test_robustness_stack_reaches_four_of_four(self) -> None:
        sim = BrainSimulator(dynamics=unguided_ecological_dynamics())
        interleaved_learn_all(sim, max_rounds=200)
        assert_unique_owners(sim, owners=list(sim.nucleus.pattern_ownership.as_dict().values()))
        self.assertEqual(len(sim.nucleus.pattern_ownership.as_dict()), len(LINE_IDS))


if __name__ == "__main__":
    unittest.main()
