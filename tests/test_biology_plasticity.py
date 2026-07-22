import unittest

from cognative_paradigm.domain.eligibility_trace import EligibilityTrace
from cognative_paradigm.domain.input_edge import InputEdge
from cognative_paradigm.domain.sensory_conductance_map import SensoryConductanceMap
from cognative_paradigm.learning.synaptic_scaling import SynapticScalingHomeostasis
from cognative_paradigm.learning.weight_consolidation import pattern_weight_score
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics


class EligibilityTraceTests(unittest.TestCase):
    def test_decay_and_increment(self) -> None:
        trace = EligibilityTrace()
        edges = frozenset({"input_r0_c0", "input_r0_c1", "input_r0_c2"})
        trace.on_matching_spike(edges, 0.5)
        self.assertAlmostEqual(trace.trace, 0.5)
        trace.decay(0.1)
        self.assertAlmostEqual(trace.trace, 0.45)
        trace.on_matching_spike(edges, 0.5)
        self.assertAlmostEqual(trace.trace, 0.95)


class WeightConsolidationTests(unittest.TestCase):
    def test_pattern_weight_score_normalized(self) -> None:
        sensory = SensoryConductanceMap(0.5)
        sensory.replace_weights(
            {
                "input_r0_c0": 1.0,
                "input_r0_c1": 1.0,
                "input_r0_c2": 1.0,
            }
        )
        score = pattern_weight_score(
            sensory,
            frozenset(sensory.as_dict().keys()),
            e_max_weight=2.0,
        )
        self.assertAlmostEqual(score, 0.5)


class SynapticScalingTests(unittest.TestCase):
    def test_high_rate_leaves_inhibition_strength_frozen(self) -> None:
        from cognative_paradigm.domain.inhibitory_coupling import InhibitoryCoupling

        scaling = SynapticScalingHomeostasis(
            target_rate=0.1,
            eta=0.1,
            window=5,
            i_min=0.1,
            i_max=0.5,
        )
        coupling = InhibitoryCoupling(
            feedforward_gain=0.4,
            inhibition_strength=0.28,
            e_collateral=0.55,
        )
        edge = InputEdge(id="input_r0_c0", row=0, col=0, weight=0.8)
        start_weight = edge.weight
        for _ in range(20):
            coupling, edge = scaling.update(coupling, 0, True, edge)
        self.assertAlmostEqual(coupling.inhibition_strength, 0.28)
        self.assertEqual(edge.weight, start_weight)


if __name__ == "__main__":
    unittest.main()
