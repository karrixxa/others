import unittest

from cognative_paradigm.domain.eligibility_trace import EligibilityTrace
from cognative_paradigm.domain.input_edge import InputEdge
from cognative_paradigm.domain.neuron import Neuron
from cognative_paradigm.domain.sensory_conductance_map import SensoryConductanceMap
from cognative_paradigm.learning.conductance_plasticity import (
    ConductancePlasticityConfig,
    ConductancePlasticityLearner,
)
from cognative_paradigm.learning.eligibility_consolidator import EligibilityConsolidator
from cognative_paradigm.learning.weight_consolidation import pattern_weight_score
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics


class ConductancePlasticityTests(unittest.TestCase):
    def test_excitatory_potentiates_when_headroom_positive(self) -> None:
        learner = ConductancePlasticityLearner(
            ConductancePlasticityConfig(
                e_plasticity_threshold=1.85,
                min_weight=0.01,
                e_max_weight=2.0,
            )
        )
        edge = InputEdge(id="input_r1_c0", row=1, col=0, weight=0.5)
        edge.register_event(1)
        learner.apply_excitatory([edge], frozenset({edge.id}), timestep=1)
        self.assertGreater(edge.weight, 0.5)

    def test_excitatory_saturates_near_max(self) -> None:
        learner = ConductancePlasticityLearner(
            ConductancePlasticityConfig(
                e_plasticity_threshold=1.85,
                min_weight=0.01,
                e_max_weight=1.0,
            )
        )
        edge = InputEdge(id="input_r1_c0", row=1, col=0, weight=0.99)
        edge.register_event(1)
        before = edge.weight
        learner.apply_excitatory([edge], frozenset({edge.id}), timestep=1)
        self.assertLessEqual(edge.weight, 1.0)
        self.assertGreater(edge.weight, before - 0.05)

    def test_inhibitory_channel_moves_toward_central_charge(self) -> None:
        learner = ConductancePlasticityLearner()
        updated = learner.update_inhibitory_channel(0.5, central_charge=1.2)
        self.assertGreater(updated, 0.5)

    def test_postsynaptic_spike_uses_aggregate_free_energy(self) -> None:
        """F_E = theta_E - sum(w_active), not theta_E - w per synapse."""
        learner = ConductancePlasticityLearner(
            ConductancePlasticityConfig(
                e_plasticity_threshold=1.85,
                e_learning_rate=0.1,
                min_weight=0.01,
                e_max_weight=2.0,
            )
        )
        conductances = {
            "input_r1_c0": 0.5,
            "input_r1_c1": 0.5,
            "input_r1_c2": 0.5,
        }
        active = frozenset(conductances.keys())
        learner.apply_relay_postsynaptic_spike(conductances, active)
        per_synapse_wrong = 0.5 + 0.1 * (1.85 - 0.5) * (1 - (0.5 / 2.0) ** 2)
        aggregate_right = 0.5 + 0.1 * (1.85 - 1.5) * (1 - (0.5 / 2.0) ** 2)
        self.assertAlmostEqual(conductances["input_r1_c0"], aggregate_right, places=4)
        self.assertLess(conductances["input_r1_c0"], per_synapse_wrong - 0.05)

    def test_sensory_ltp_plateau_respects_plasticity_threshold(self) -> None:
        """3-edge sensory LTP plateaus near θ_s/3; score ≈ (θ_s/3)/e_max."""
        theta = 1600.0
        e_max = 1000.0
        learner = ConductancePlasticityLearner(
            ConductancePlasticityConfig(
                e_plasticity_threshold=1.85,
                sensory_plasticity_threshold=theta,
                min_weight=1.0,
                e_max_weight=e_max,
                e_learning_rate=0.05,
                sensory_plasticity_scale=2.3,
            )
        )
        edge_ids = ("input_r0_c0", "input_r0_c1", "input_r0_c2")
        conductances = {edge_id: 240.0 for edge_id in edge_ids}
        active = frozenset(edge_ids)
        for _ in range(800):
            learner.apply_sensory_postsynaptic_spike(conductances, active)

        mean_w = sum(conductances.values()) / len(edge_ids)
        expected_mean = theta / len(edge_ids)
        self.assertAlmostEqual(mean_w, expected_mean, delta=40.0)
        score = pattern_weight_score(conductances, active, e_max_weight=e_max)
        self.assertAlmostEqual(score, expected_mean / e_max, delta=0.04)
        self.assertGreater(score, 0.40)

    def test_consolidation_040_binds_when_plasticity_plateau_allows(self) -> None:
        """With sensory θ=1600, sensory score can exceed 0.40 and consolidator binds."""
        dynamics = LearningDynamics(
            e_plasticity_threshold=1.85,
            sensory_plasticity_threshold=1600.0,
            consolidation_weight_threshold=0.40,
            eligibility_threshold=0.50,
            e_min_weight=1.0,
            e_max_weight=1000.0,
        )
        learner = ConductancePlasticityLearner(
            ConductancePlasticityConfig(
                e_plasticity_threshold=dynamics.e_plasticity_threshold,
                sensory_plasticity_threshold=dynamics.sensory_plasticity_threshold,
                min_weight=dynamics.e_min_weight,
                e_max_weight=dynamics.e_max_weight,
                e_learning_rate=0.05,
                sensory_plasticity_scale=2.3,
            )
        )
        edge_ids = ("input_r0_c0", "input_r0_c1", "input_r0_c2")
        weights = {edge_id: 240.0 for edge_id in edge_ids}
        active = frozenset(edge_ids)
        for _ in range(800):
            learner.apply_sensory_postsynaptic_spike(weights, active)

        score = pattern_weight_score(
            weights, active, e_max_weight=dynamics.e_max_weight
        )
        self.assertGreater(score, 0.40)

        sensory = SensoryConductanceMap(240.0)
        sensory.replace_weights(weights)
        neuron = Neuron(id="nucleus_e_0", threshold=1.05, refractory_period=2)
        trace = EligibilityTrace(trace=0.95, last_active_edges=active)
        consolidator = EligibilityConsolidator(dynamics)
        symbol = consolidator.try_consolidate(
            neuron,
            trace,
            active,
            sensory,
            symbol_factory=lambda _nid, _pattern: "σ_test",
        )
        self.assertEqual(symbol, "σ_test")
        self.assertTrue(neuron.memory.is_bound())


if __name__ == "__main__":
    unittest.main()
