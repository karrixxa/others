"""Full Pfister–Gerstner triplet plasticity tests."""

import pytest

from cognative_paradigm.learning.triplet_plasticity import (
    TripletPlasticityConfig,
    TripletPlasticityLearner,
)


@pytest.mark.biological_lab
class TestTripletPlasticity:
    def test_four_traces_are_updated(self) -> None:
        learner = TripletPlasticityLearner()
        weights = {"input_r1_c1": 0.5}
        learner.apply_sensory_postsynaptic_spike(
            weights,
            frozenset(weights),
            pre_spike_times_ms={"input_r1_c1": 1.0},
            post_spike_time_ms=5.0,
        )

        trace = learner.trace_bank.trace_for("input_r1_c1")
        assert trace.r1 > 0.0
        assert trace.r2 > 0.0
        assert trace.o1 > 0.0
        assert trace.o2 > 0.0

    def test_causal_pair_potentiates(self) -> None:
        learner = TripletPlasticityLearner()
        weights = {"input_r1_c1": 0.5}
        learner.apply_sensory_postsynaptic_spike(
            weights,
            frozenset(weights),
            pre_spike_times_ms={"input_r1_c1": 1.0},
            post_spike_time_ms=5.0,
        )
        assert weights["input_r1_c1"] > 0.5

    def test_anti_causal_pair_depresses_after_post_trace_exists(self) -> None:
        learner = TripletPlasticityLearner(
            TripletPlasticityConfig(a3_plus=0.0, a3_minus=0.001)
        )
        weights = {"input_r1_c1": 0.5}
        learner.apply_sensory_postsynaptic_spike(
            weights,
            frozenset(weights),
            pre_spike_times_ms={"input_r1_c1": 10.0},
            post_spike_time_ms=5.0,
        )
        assert weights["input_r1_c1"] < 0.5

    def test_high_frequency_burst_has_triplet_ltp_gain(self) -> None:
        low = TripletPlasticityLearner()
        high = TripletPlasticityLearner()
        low_weights = {"input_r1_c1": 0.5}
        high_weights = {"input_r1_c1": 0.5}

        for index in range(4):
            low_post = 5.0 + index * 200.0
            high_post = 5.0 + index * 10.0
            low.apply_sensory_postsynaptic_spike(
                low_weights,
                frozenset(low_weights),
                pre_spike_times_ms={"input_r1_c1": low_post - 4.0},
                post_spike_time_ms=low_post,
            )
            high.apply_sensory_postsynaptic_spike(
                high_weights,
                frozenset(high_weights),
                pre_spike_times_ms={"input_r1_c1": high_post - 4.0},
                post_spike_time_ms=high_post,
            )

        assert high_weights["input_r1_c1"] > low_weights["input_r1_c1"]
