"""Per-neuron sensory conductance plasticity — Tenant 9 local learning."""

import unittest

from cognative_paradigm.lines import LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import (
    deterministic_dynamics,
    stimulate_until_pattern_bound,
    stimulate_until_recognized,
)


class LocalSensoryPlasticityTests(unittest.TestCase):
    def test_non_spikers_keep_initial_center_weight(self) -> None:
        """Only authentic spikers may LTP their own maps (no primary-only force)."""
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        others_before = {
            c.neuron.id: c.sensory_conductances.weight_for("input_r1_c1")
            for c in sim.nucleus.ring
        }
        pattern = get_line("H1")
        ever_spiked: set[str] = set()
        for _ in range(150):
            sim.stimulate_pattern(pattern)
            ever_spiked.update(sim.nucleus.last_population_spike_ids)
            if sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids):
                break
        else:
            self.fail("H1 did not bind within stimulation window")

        self.assertTrue(ever_spiked)
        for competitor in sim.nucleus.ring:
            if competitor.neuron.id in ever_spiked:
                continue
            after = competitor.sensory_conductances.weight_for("input_r1_c1")
            self.assertEqual(
                after,
                others_before[competitor.neuron.id],
                f"{competitor.neuron.id} center weight changed without an authentic spike",
            )

    def test_winner_active_sensory_weights_increase_after_spike(self) -> None:
        """Growth is asserted on unbound winner re-spikes (Rule 7.2 freezes after bind)."""
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        pattern = get_line("H1")
        active = pattern.edge_ids

        before = None
        winner = None
        for _ in range(40):
            sim.stimulate_pattern(pattern)
            candidate = sim.nucleus.last_winner
            if candidate is None:
                continue
            # Snapshot after an unbound winner spike; later rematches may be sparse.
            if candidate.neuron.memory.is_bound():
                continue
            before = {
                edge_id: candidate.sensory_conductances.weight_for(edge_id)
                for edge_id in active
            }
            winner = candidate
            break

        self.assertIsNotNone(winner)
        self.assertIsNotNone(before)
        assert winner is not None
        assert before is not None

        for _ in range(40):
            sim.stimulate_pattern(pattern)
            increased = sum(
                1
                for edge_id in active
                if winner.sensory_conductances.weight_for(edge_id) > before[edge_id]
            )
            if increased > 0:
                return
            if winner.neuron.memory.is_bound():
                # Bound after further unbound LTP should already have grown; if not, fail.
                break

        self.fail(
            "Winner sensory weights on active pattern cells should strengthen "
            "on unbound winner spikes"
        )

    def test_rule_72_matched_bound_freezes_excitatory_ltp(self) -> None:
        """Rule 7.2 sole binder: rematch does not change sensory/relay weights."""
        from tests.simulation_helpers import force_sole_binder

        sim = BrainSimulator(dynamics=deterministic_dynamics())
        pattern = get_line("H1")
        stimulate_until_pattern_bound(sim, LINE_INDICES["H1"])
        stimulate_until_recognized(sim, LINE_INDICES["H1"])
        force_sole_binder(sim, pattern)

        owner_id = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertIsNotNone(owner_id)
        owner = sim.nucleus.competitor_by_id(owner_id)
        self.assertIsNotNone(owner)
        assert owner is not None
        self.assertTrue(owner.neuron.memory.is_bound())
        self.assertTrue(owner.neuron.prediction.matches(pattern.edge_ids))

        relay_ids = frozenset(f"l1_e_{index}" for index in LINE_INDICES["H1"])
        sensory_before = {
            edge_id: owner.sensory_conductances.weight_for(edge_id)
            for edge_id in pattern.edge_ids
        }
        relay_before = dict(owner.relay_conductances.as_dict())

        for _ in range(8):
            sim.stimulate_pattern(pattern)

        for edge_id, weight in sensory_before.items():
            self.assertEqual(
                owner.sensory_conductances.weight_for(edge_id),
                weight,
                f"sensory {edge_id} changed after bind+match rematch",
            )
        self.assertEqual(
            owner.relay_conductances.as_dict(),
            relay_before,
            "relay map changed after bind+match rematch",
        )
        # Relay active sum frozen as an easy second check.
        self.assertEqual(
            owner.relay_conductances.active_weight_sum(relay_ids),
            sum(relay_before[edge_id] for edge_id in relay_ids),
        )

    def test_sensory_maps_start_randomized_with_seed(self) -> None:
        sim_a = BrainSimulator(dynamics=deterministic_dynamics())
        sim_b = BrainSimulator(dynamics=deterministic_dynamics())
        grids_a = [c.sensory_conductances.as_grid() for c in sim_a.nucleus.ring]
        grids_b = [c.sensory_conductances.as_grid() for c in sim_b.nucleus.ring]
        self.assertEqual(grids_a, grids_b)

        centers = {
            c.neuron.id: c.sensory_conductances.weight_for("input_r1_c1")
            for c in sim_a.nucleus.ring
        }
        self.assertEqual(len(set(centers.values())), len(centers))

    def test_input_edges_remain_fixed_baseline(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        baseline = sim._dynamics.sensory_baseline_weight
        for _ in range(30):
            sim.stimulate_pattern(get_line("H1"))
        for edge in sim._edges.values():
            self.assertAlmostEqual(edge.weight, baseline)


if __name__ == "__main__":
    unittest.main()
