"""Phase 9: PredictionErrorModulator unit + nucleus integration tests."""

import unittest

import pytest

from cognative_paradigm.learning.prediction_error_modulator import PredictionErrorModulator
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import deterministic_dynamics, force_sole_binder


class PredictionErrorModulatorUnitTests(unittest.TestCase):
    def test_default_neuromod_error_gain_is_behavior_neutral(self) -> None:
        self.assertAlmostEqual(DEFAULT_LEARNING_DYNAMICS.neuromod_error_gain, 1.0)
        self.assertAlmostEqual(
            DEFAULT_LEARNING_DYNAMICS.bound_match_recall_drive_gain, 0.7
        )
        self.assertFalse(DEFAULT_LEARNING_DYNAMICS.emergent_autonomy_enabled)

    def test_classification_bound_match_and_mismatch(self) -> None:
        # Labeled-control soft gates (autonomy OFF) still freeze rematch.
        dynamics = deterministic_dynamics(emergent_autonomy_enabled=False)
        modulator = PredictionErrorModulator(dynamics)
        sim = BrainSimulator(dynamics=dynamics)
        h1 = get_line("H1")
        v1 = get_line("V1")
        owner = sim.nucleus.ring[0].neuron
        owner.memory.bind(h1, 1.0)
        owner.prediction.update_from_pattern(h1.edge_ids)

        self.assertTrue(modulator.is_bound_match(owner, h1.edge_ids))
        self.assertFalse(modulator.is_bound_mismatch(owner, h1.edge_ids))
        self.assertTrue(modulator.plasticity_frozen(owner, h1.edge_ids))
        self.assertAlmostEqual(modulator.recall_drive_gain(owner, h1.edge_ids), 0.7)
        self.assertAlmostEqual(modulator.pe_ltd_rate_scale(owner, h1.edge_ids), 0.0)

        self.assertFalse(modulator.is_bound_match(owner, v1.edge_ids))
        self.assertTrue(modulator.is_bound_mismatch(owner, v1.edge_ids))
        self.assertFalse(modulator.plasticity_frozen(owner, v1.edge_ids))
        self.assertAlmostEqual(modulator.recall_drive_gain(owner, v1.edge_ids), 1.0)
        self.assertAlmostEqual(modulator.pe_ltd_rate_scale(owner, v1.edge_ids), 1.0)

    def test_unbound_neuron_is_neither_match_nor_mismatch(self) -> None:
        dynamics = deterministic_dynamics(emergent_autonomy_enabled=False)
        modulator = PredictionErrorModulator(dynamics)
        sim = BrainSimulator(dynamics=dynamics)
        free = sim.nucleus.ring[2].neuron
        pattern = get_line("D0")

        self.assertFalse(modulator.is_bound_match(free, pattern.edge_ids))
        self.assertFalse(modulator.is_bound_mismatch(free, pattern.edge_ids))
        self.assertAlmostEqual(modulator.pe_ltd_rate_scale(free, pattern.edge_ids), 0.0)

    def test_nucleus_owns_prediction_modulator(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        self.assertIsInstance(sim.nucleus._prediction_modulator, PredictionErrorModulator)

    def test_production_bound_match_gates_active(self) -> None:
        modulator = PredictionErrorModulator(DEFAULT_LEARNING_DYNAMICS)
        self.assertTrue(modulator.soft_gates_active)


@pytest.mark.biological_lab
class PredictionErrorModulatorIntegrationTests(unittest.TestCase):
    def test_mismatch_isolates_unrelated_pattern_and_peer_weights(self) -> None:
        """PE-LTD on mismatch must not touch inactive edges, peer maps, or relays."""
        dynamics = deterministic_dynamics(
            emergent_autonomy_enabled=False,
            heterosynaptic_depression_enabled=True,
            prediction_error_ltd_enabled=True,
            heterosynaptic_inactive_ltd_enabled=False,
            hot_nonspiker_ltd_enabled=False,
            pretrained_inhibitor_exclusivity_enabled=False,
        )
        sim = BrainSimulator(dynamics=dynamics)
        h1 = get_line("H1")
        v1 = get_line("V1")
        owner = sim.nucleus.ring[0]
        peer = sim.nucleus.ring[1]

        owner.neuron.memory.bind(h1, 1.0)
        owner.neuron.prediction.update_from_pattern(h1.edge_ids)
        peer.neuron.memory.bind(v1, 1.0)
        peer.neuron.prediction.update_from_pattern(v1.edge_ids)

        owner_sensory = dict(owner.sensory_conductances.as_dict())
        peer_sensory_before = dict(peer.sensory_conductances.as_dict())
        relay_before = dict(owner.relay_conductances.as_dict())

        inactive_edges = [
            edge_id
            for edge_id in owner_sensory
            if edge_id not in v1.edge_ids
        ]
        self.assertTrue(inactive_edges)

        for _ in range(12):
            sim.stimulate_pattern(v1)

        for edge_id in inactive_edges:
            self.assertEqual(
                owner.sensory_conductances.weight_for(edge_id),
                owner_sensory[edge_id],
                f"inactive sensory {edge_id} changed on mismatch",
            )
        self.assertEqual(peer.sensory_conductances.as_dict(), peer_sensory_before)
        self.assertEqual(owner.relay_conductances.as_dict(), relay_before)

        # Active mismatch edges may depress only when this neuron authentic-spikes;
        # isolation of inactive sensory, peer maps, and relay is the acceptance gate.
        for edge_id in v1.edge_ids:
            if edge_id not in owner_sensory:
                continue
            self.assertLessEqual(
                owner.sensory_conductances.weight_for(edge_id),
                owner_sensory[edge_id],
                f"active mismatch edge {edge_id} must not potentiate",
            )

    def test_bound_rematch_zero_weight_delta_and_recall_drive(self) -> None:
        """Bound∧match rematch: no sensory/relay drift; recall drive stays 0.7."""
        dynamics = deterministic_dynamics(
            emergent_autonomy_enabled=False,
            heterosynaptic_depression_enabled=True,
            prediction_error_ltd_enabled=True,
            heterosynaptic_inactive_ltd_enabled=True,
            hot_nonspiker_ltd_enabled=True,
        )
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")
        owner = sim.nucleus.ring[0]
        owner.neuron.memory.bind(pattern, 1.0)
        owner.neuron.prediction.update_from_pattern(pattern.edge_ids)
        force_sole_binder(sim, pattern, keep_id=owner.neuron.id)

        gains = sim.nucleus._relay_drive_gains(pattern.edge_ids)
        self.assertAlmostEqual(gains[owner.neuron.id], 0.7)

        sensory_before = {
            edge_id: owner.sensory_conductances.weight_for(edge_id)
            for edge_id in owner.sensory_conductances.as_dict()
        }
        relay_before = dict(owner.relay_conductances.as_dict())

        for _ in range(10):
            sim.stimulate_pattern(pattern)

        for edge_id, weight in sensory_before.items():
            self.assertEqual(
                owner.sensory_conductances.weight_for(edge_id),
                weight,
                f"sensory {edge_id} drifted on bound rematch",
            )
        self.assertEqual(owner.relay_conductances.as_dict(), relay_before)


if __name__ == "__main__":
    unittest.main()
