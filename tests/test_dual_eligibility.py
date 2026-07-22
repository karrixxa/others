"""Dual eligibility trace and neuromodulator gate unit tests."""

from __future__ import annotations

import unittest

from cognative_paradigm.domain.dual_eligibility_trace import DualEligibilityTrace
from cognative_paradigm.domain.eligibility_trace import EligibilityTrace
from cognative_paradigm.domain.neuron import Neuron
from cognative_paradigm.learning.eligibility_consolidator import EligibilityConsolidator
from cognative_paradigm.learning.neuromodulator_gate import NeuromodulatorGate
from cognative_paradigm.learning.neuron_readiness import NeuronReadiness
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics


class DualEligibilityTraceTests(unittest.TestCase):
    def test_ltp_and_ltd_are_distinct(self) -> None:
        edges = frozenset({"input_r1_c1"})
        trace = DualEligibilityTrace()
        trace.on_matching_spike(edges, 0.4)
        trace.on_mismatch_spike(edges, 0.2)
        self.assertGreater(trace.trace_ltp, 0.0)
        self.assertGreater(trace.trace_ltd, 0.0)

    def test_trace_property_aliases_ltp(self) -> None:
        trace = DualEligibilityTrace(trace_ltp=0.55, trace_ltd=0.1)
        self.assertEqual(trace.trace, 0.55)


class NeuromodulatorGateTests(unittest.TestCase):
    def test_learn_modulator_zero_when_bound(self) -> None:
        neuron = Neuron(id="nucleus_e_0")
        neuron.memory.bind(
            __import__(
                "cognative_paradigm.domain.pattern", fromlist=["Pattern"]
            ).Pattern(edge_ids=frozenset({"a"})),
            confidence=0.9,
        )
        gate = NeuromodulatorGate(LearningDynamics())
        self.assertEqual(gate.learn_modulator(neuron), 0.0)

    def test_error_modulator_on_mismatch(self) -> None:
        neuron = Neuron(id="nucleus_e_0")
        pattern = __import__(
            "cognative_paradigm.domain.pattern", fromlist=["Pattern"]
        ).Pattern(edge_ids=frozenset({"input_r0_c0"}))
        neuron.memory.bind(pattern, confidence=0.9)
        neuron.prediction.update_from_pattern(frozenset({"input_r0_c0"}))
        gate = NeuromodulatorGate(LearningDynamics())
        self.assertGreater(
            gate.error_modulator(neuron, frozenset({"input_r1_c1"})),
            0.0,
        )


class DualConsolidatorTests(unittest.TestCase):
    def test_dual_mode_uses_readiness_hysteresis(self) -> None:
        dynamics = LearningDynamics(
            dual_eligibility_enabled=True,
            eligibility_threshold=0.80,
            eligibility_alpha=0.45,
            consolidation_weight_threshold=0.25,
        )
        consolidator = EligibilityConsolidator(dynamics)
        trace = DualEligibilityTrace(
            trace_ltp=0.50,
            last_active_edges=frozenset({"input_r1_c1"}),
        )
        neuron = Neuron(id="nucleus_e_0")
        from cognative_paradigm.domain.sensory_conductance_map import (
            SensoryConductanceMap,
        )

        sensory = SensoryConductanceMap(0.5)
        symbol = consolidator.try_consolidate(
            neuron,
            trace,
            frozenset({"input_r1_c1"}),
            sensory,
            lambda nid, pat: "sigma_0",
        )
        self.assertIsNone(symbol)


if __name__ == "__main__":
    unittest.main()
