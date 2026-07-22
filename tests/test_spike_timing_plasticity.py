"""Pairwise and triplet STDP unit tests (Phase 2 scaffold)."""

from __future__ import annotations

import unittest

from cognative_paradigm.learning.spike_timing_plasticity import (
    SpikeTimingPlasticityConfig,
    SpikeTimingPlasticityLearner,
)
from cognative_paradigm.learning.triplet_plasticity import TripletPlasticityLearner


class SpikeTimingPlasticityTests(unittest.TestCase):
    def test_causal_pre_before_post_is_ltp(self) -> None:
        learner = SpikeTimingPlasticityLearner()
        self.assertGreater(learner.delta_w(5.0), 0.0)

    def test_anti_causal_pre_after_post_is_ltd(self) -> None:
        learner = SpikeTimingPlasticityLearner()
        self.assertLess(learner.delta_w(-5.0), 0.0)

    def test_sensory_spike_increases_weight_on_ltp(self) -> None:
        learner = SpikeTimingPlasticityLearner(
            SpikeTimingPlasticityConfig(a_plus=0.05, a_minus=0.01)
        )
        weights = {"input_r1_c1": 0.5}
        learner.apply_sensory_postsynaptic_spike(
            weights,
            frozenset({"input_r1_c1"}),
            pre_spike_times_ms={"input_r1_c1": 0.0},
            post_spike_time_ms=5.0,
        )
        self.assertGreater(weights["input_r1_c1"], 0.5)

    def test_inactive_edges_untouched(self) -> None:
        learner = SpikeTimingPlasticityLearner()
        weights = {"input_r0_c0": 0.4, "input_r1_c1": 0.4}
        learner.apply_sensory_postsynaptic_spike(
            weights,
            frozenset({"input_r1_c1"}),
        )
        self.assertEqual(weights["input_r0_c0"], 0.4)
        self.assertGreater(weights["input_r1_c1"], 0.4)


class TripletPlasticityTests(unittest.TestCase):
    def test_triplet_mode_increases_after_post_burst(self) -> None:
        learner = TripletPlasticityLearner()
        weights = {"input_r1_c1": 0.5}
        for _ in range(3):
            learner.apply_sensory_postsynaptic_spike(
                weights,
                frozenset({"input_r1_c1"}),
            )
        self.assertGreater(weights["input_r1_c1"], 0.5)


if __name__ == "__main__":
    unittest.main()
