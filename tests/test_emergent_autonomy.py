"""Stage 14 — emergent autonomy: BoundMatch soft gates retire."""

from __future__ import annotations

import unittest

from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import (
    DEFAULT_LEARNING_DYNAMICS,
    LearningDynamics,
)
from tests.simulation_helpers import deterministic_dynamics


class EmergentAutonomyDefaultsTests(unittest.TestCase):
    def test_production_autonomy_off_under_force(self) -> None:
        self.assertFalse(DEFAULT_LEARNING_DYNAMICS.emergent_autonomy_enabled)
        self.assertTrue(
            DEFAULT_LEARNING_DYNAMICS.pretrained_inhibitor_exclusivity_enabled
        )
        self.assertEqual(DEFAULT_LEARNING_DYNAMICS.descending_mode, "force")

    def test_autonomy_forbids_force_exclusivity(self) -> None:
        with self.assertRaises(ValueError):
            LearningDynamics(
                emergent_autonomy_enabled=True,
                pretrained_inhibitor_exclusivity_enabled=True,
            ).validate()
        with self.assertRaises(ValueError):
            LearningDynamics(
                emergent_autonomy_enabled=True,
                descending_mode="force",
            ).validate()


class EmergentAutonomySoftGateTests(unittest.TestCase):
    def test_autonomy_disables_rematch_freeze_and_attenuation(self) -> None:
        dynamics = deterministic_dynamics(emergent_autonomy_enabled=True)
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")
        owner = sim.nucleus.ring[0]
        peer = sim.nucleus.ring[1]
        owner.neuron.memory.bind(pattern, 1.0)
        owner.neuron.prediction.update_from_pattern(pattern.edge_ids)

        modulator = sim.nucleus._prediction_modulator
        self.assertFalse(modulator.soft_gates_active)
        self.assertFalse(
            modulator.plasticity_frozen(owner.neuron, pattern.edge_ids)
        )
        self.assertAlmostEqual(
            modulator.recall_drive_gain(owner.neuron, pattern.edge_ids), 1.0
        )
        self.assertTrue(
            modulator.spike_eligible(
                peer.neuron, pattern.edge_ids, pattern_has_binder=True
            )
        )
        self.assertTrue(
            sim.nucleus._plasticity_eligible(owner.neuron, pattern.edge_ids)
        )
        self.assertTrue(
            sim.nucleus._plasticity_eligible(peer.neuron, pattern.edge_ids)
        )

    def test_labeled_control_restores_bound_match_gates(self) -> None:
        dynamics = deterministic_dynamics(emergent_autonomy_enabled=False)
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")
        owner = sim.nucleus.ring[0]
        peer = sim.nucleus.ring[1]
        owner.neuron.memory.bind(pattern, 1.0)
        owner.neuron.prediction.update_from_pattern(pattern.edge_ids)

        modulator = sim.nucleus._prediction_modulator
        self.assertTrue(modulator.soft_gates_active)
        self.assertTrue(
            modulator.plasticity_frozen(owner.neuron, pattern.edge_ids)
        )
        self.assertAlmostEqual(
            modulator.recall_drive_gain(owner.neuron, pattern.edge_ids), 0.7
        )
        self.assertFalse(
            modulator.spike_eligible(
                peer.neuron, pattern.edge_ids, pattern_has_binder=True
            )
        )
        self.assertFalse(
            sim.nucleus._plasticity_eligible(owner.neuron, pattern.edge_ids)
        )

    def test_rematch_still_updates_sensory_weights_under_autonomy(self) -> None:
        dynamics = deterministic_dynamics(emergent_autonomy_enabled=True)
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")
        owner = sim.nucleus.ring[0]
        owner.neuron.memory.bind(pattern, 1.0)
        owner.neuron.prediction.update_from_pattern(pattern.edge_ids)
        # Soft gates retired → rematch remains plasticity-eligible.
        self.assertTrue(
            sim.nucleus._plasticity_eligible(owner.neuron, pattern.edge_ids)
        )
        before = sum(
            weight
            for edge_id, weight in owner.sensory_conductances.as_dict().items()
            if edge_id in pattern.edge_ids
        )
        plasticity = sim._plasticity
        owner.apply_sensory_spike_plasticity(plasticity, pattern.edge_ids)
        after = sum(
            weight
            for edge_id, weight in owner.sensory_conductances.as_dict().items()
            if edge_id in pattern.edge_ids
        )
        self.assertGreater(after, before)


class EmergentAutonomyEcologySmokeTests(unittest.TestCase):
    def test_autonomy_rotation_learns_at_least_two_owners(self) -> None:
        from tests.simulation_helpers import (
            ownership_owner_ids,
            unguided_ecological_dynamics,
        )

        dynamics = unguided_ecological_dynamics(emergent_autonomy_enabled=True)
        sim = BrainSimulator(dynamics=dynamics)
        from cognative_paradigm.lines import LINE_IDS, get_line

        for round_index in range(160):
            sim.stimulate_pattern(get_line(LINE_IDS[round_index % len(LINE_IDS)]))
            if len(ownership_owner_ids(sim)) >= 2:
                break
        self.assertGreaterEqual(len(ownership_owner_ids(sim)), 2)

    def test_first_commit_wins_keeps_sole_binder(self) -> None:
        from cognative_paradigm.lines import pattern_from_indices

        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                emergent_autonomy_enabled=True,
                consolidation_weight_threshold=0.15,
            )
        )
        pattern = pattern_from_indices([0, 1, 2])
        for _ in range(120):
            sim.stimulate_pattern(pattern)
            binders = sim.nucleus.pattern_ownership.binders_for_pattern(
                pattern.edge_ids
            )
            if binders:
                self.assertEqual(len(binders), 1)
                break
        else:
            self.fail("expected a sole binder under autonomy first-commit consolidator")



if __name__ == "__main__":
    unittest.main()
