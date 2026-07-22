"""Bound/unbound competition is membrane + inhibition — not a coordinator filter."""

import unittest

from cognative_paradigm.domain.pattern import Pattern
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import deterministic_dynamics


class BoundSpikeGatingTests(unittest.TestCase):
    def test_bound_mismatch_yields_to_free_seats(self) -> None:
        """Bound∧mismatch is ineligible while unbound seats remain (recall gate)."""
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        bound = sim.nucleus.ring[0]
        foreign = Pattern(edge_ids=frozenset({"edge_a", "edge_b", "edge_c"}))
        bound.neuron.memory.bind(foreign, 1.0)
        other = frozenset({"edge_x", "edge_y", "edge_z"})

        eligible = sim.nucleus._spike_eligible_competitors(other)
        self.assertNotIn(bound, eligible)
        self.assertEqual(
            len(eligible),
            len(sim.nucleus.ring) - 1,
            "free seats keep first-spike races; bound foreign sits out",
        )

    def test_bound_mismatch_eligible_when_ring_full(self) -> None:
        """With no free seats, bound∧mismatch may compete (PE-LTD / reassignment)."""
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        patterns = [
            Pattern(edge_ids=frozenset({f"p{i}_a", f"p{i}_b", f"p{i}_c"}))
            for i in range(len(sim.nucleus.ring))
        ]
        for competitor, pattern in zip(sim.nucleus.ring, patterns):
            competitor.neuron.memory.bind(pattern, 1.0)
        probe = frozenset({"edge_x", "edge_y", "edge_z"})
        eligible = sim.nucleus._spike_eligible_competitors(probe)
        self.assertEqual(len(eligible), len(sim.nucleus.ring))

    def test_eligible_pool_length_equals_ring_size(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        active = frozenset({"any_edge"})
        eligible = sim.nucleus._spike_eligible_competitors(active)
        self.assertEqual(len(eligible), len(sim.nucleus.ring))


if __name__ == "__main__":
    unittest.main()
