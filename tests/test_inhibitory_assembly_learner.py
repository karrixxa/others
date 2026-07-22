"""Unit tests for InhibitoryAssemblyLearner (hot-gated NI→E headroom)."""

import unittest

from cognative_paradigm.learning.inhibitory_assembly_learner import (
    InhibitoryAssemblyLearner,
    InhibitoryAssemblyLearnerConfig,
)


class InhibitoryAssemblyLearnerTests(unittest.TestCase):
    def test_hot_entry_strengthens_more_than_cold(self) -> None:
        learner = InhibitoryAssemblyLearner(
            InhibitoryAssemblyLearnerConfig(i_max_weight=2.25, eta_up=0.03)
        )
        theta = 1.05
        init = 1.1
        cold = learner.update_channel(init, v_pre=0.2, theta=theta)
        hot = learner.update_channel(init, v_pre=1.0, theta=theta)
        self.assertGreater(hot, cold)
        self.assertGreater(hot, init)

    def test_repeated_hot_inhibition_raises_channel_above_init(self) -> None:
        learner = InhibitoryAssemblyLearner()
        theta = 1.05
        channel = 1.1
        for _ in range(40):
            channel = learner.update_channel(channel, v_pre=1.0, theta=theta)
        self.assertGreater(channel, 1.1)
        self.assertLessEqual(channel, learner.config.i_max_weight)

    def test_channel_clamped_to_i_max_weight(self) -> None:
        learner = InhibitoryAssemblyLearner(
            InhibitoryAssemblyLearnerConfig(i_max_weight=2.25, eta_up=0.2)
        )
        channel = 2.2
        for _ in range(80):
            channel = learner.update_channel(channel, v_pre=2.0, theta=1.0)
        self.assertLessEqual(channel, 2.25)
        self.assertGreaterEqual(channel, learner.config.i_min_weight)

    def test_hot_gate_floor_still_updates_cold_slightly(self) -> None:
        learner = InhibitoryAssemblyLearner(
            InhibitoryAssemblyLearnerConfig(
                hot_gate_enabled=True,
                hot_gate_floor=0.15,
                eta_down=0.0,
            )
        )
        cold = learner.update_channel(1.1, v_pre=0.1, theta=1.05)
        # With eta_down=0 and positive (small) κ_eff, channel should not collapse.
        self.assertGreaterEqual(cold, 1.1)


if __name__ == "__main__":
    unittest.main()
