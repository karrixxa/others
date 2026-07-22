"""Unit + Rule 7.2 freeze tests for HeterosynapticDepressionPolicy."""

import unittest

from cognative_paradigm.learning.heterosynaptic_depression import (
    HeterosynapticDepressionConfig,
    HeterosynapticDepressionPolicy,
)
from cognative_paradigm.lines import LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import (
    deterministic_dynamics,
    force_sole_binder,
    stimulate_until_pattern_bound,
    stimulate_until_recognized,
)


class HeterosynapticDepressionUnitTests(unittest.TestCase):
    def test_default_site_b_enabled(self) -> None:
        """Site B hot-nonspiker LTD is ON by default (policy + LearningDynamics)."""
        policy = HeterosynapticDepressionPolicy()
        self.assertTrue(policy.config.hot_nonspiker_ltd)
        self.assertAlmostEqual(policy.config.hot_nonspiker_eta_scale, 0.20)
        self.assertAlmostEqual(policy.config.eta_ltd_scale, 0.40)
        self.assertAlmostEqual(policy.config.min_weight, 1.0)
        self.assertAlmostEqual(policy.config.hot_nonspiker_floor, 25.0)
        self.assertTrue(DEFAULT_LEARNING_DYNAMICS.hot_nonspiker_ltd_enabled)
        self.assertAlmostEqual(
            DEFAULT_LEARNING_DYNAMICS.hot_nonspiker_ltd_eta_scale, 0.20
        )
        self.assertAlmostEqual(DEFAULT_LEARNING_DYNAMICS.ltd_eta_scale, 0.40)

    def test_site_b_depresses_hot_active_above_floor(self) -> None:
        policy = HeterosynapticDepressionPolicy()
        weights = {
            "hot": 400.0,
            "cold": 20.0,
            "inactive": 400.0,
        }
        active = frozenset({"hot", "cold"})
        before = dict(weights)
        rate = policy.hot_nonspiker_rate(0.016)
        self.assertGreater(rate, 0.0)
        policy.depress_hot_nonspiker_active(weights, active, rate=rate)
        self.assertLess(weights["hot"], before["hot"])
        self.assertEqual(weights["cold"], before["cold"])
        self.assertEqual(weights["inactive"], before["inactive"])

    def test_pe_ltd_decreases_active_weights(self) -> None:
        policy = HeterosynapticDepressionPolicy()
        weights = {
            "input_r0_c0": 400.0,
            "input_r0_c1": 400.0,
            "input_r1_c1": 400.0,
            "input_r2_c2": 400.0,
        }
        active = frozenset({"input_r0_c0", "input_r0_c1", "input_r1_c1"})
        before = dict(weights)
        rate = policy.ltd_rate(0.016)
        policy.depress_active(weights, active, rate=rate)
        for edge_id in active:
            self.assertLess(weights[edge_id], before[edge_id])
        self.assertEqual(weights["input_r2_c2"], before["input_r2_c2"])
        self.assertGreaterEqual(min(weights.values()), policy.config.min_weight)

    def test_heterosynaptic_inactive_decreases_off_edges(self) -> None:
        policy = HeterosynapticDepressionPolicy()
        weights = {
            "a": 350.0,
            "b": 350.0,
            "c": 350.0,
            "d": 350.0,
        }
        active = frozenset({"a", "b"})
        before = dict(weights)
        rate = policy.ltd_rate(0.016)
        policy.depress_inactive(weights, active, rate=rate)
        for edge_id in active:
            self.assertEqual(weights[edge_id], before[edge_id])
        for edge_id in ("c", "d"):
            self.assertLess(weights[edge_id], before[edge_id])

    def test_soft_sat_floors_at_min_weight(self) -> None:
        policy = HeterosynapticDepressionPolicy(
            HeterosynapticDepressionConfig(min_weight=0.01, eta_ltd_scale=5.0)
        )
        weights = {"a": 0.02}
        for _ in range(200):
            policy.depress_active(weights, frozenset({"a"}), rate=0.5)
        self.assertAlmostEqual(weights["a"], 0.01)


class HeterosynapticDepressionIntegrationTests(unittest.TestCase):
    def test_nucleus_wires_site_b_from_dynamics(self) -> None:
        """Nucleus depression config inherits Site B defaults from LearningDynamics."""
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        config = sim.nucleus._depression.config
        self.assertTrue(config.enabled)
        self.assertTrue(config.hot_nonspiker_ltd)
        self.assertAlmostEqual(config.hot_nonspiker_eta_scale, 0.20)
        self.assertAlmostEqual(config.eta_ltd_scale, 0.40)

    def test_rule_72_rematch_freezes_ltp_and_ltd(self) -> None:
        """Rule 7.2 sole binder: rematch owner — no LTP and no LTD."""
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                heterosynaptic_depression_enabled=True,
                prediction_error_ltd_enabled=True,
                heterosynaptic_inactive_ltd_enabled=True,
                hot_nonspiker_ltd_enabled=True,
            )
        )
        pattern = get_line("H1")
        stimulate_until_pattern_bound(sim, LINE_INDICES["H1"])
        stimulate_until_recognized(sim, LINE_INDICES["H1"])
        force_sole_binder(sim, pattern)

        owner_id = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertIsNotNone(owner_id)
        self.assertEqual(
            len(sim.nucleus.pattern_ownership.binders_for_pattern(pattern.edge_ids)),
            1,
        )
        owner = sim.nucleus.competitor_by_id(owner_id)
        assert owner is not None
        self.assertTrue(owner.neuron.memory.is_bound())
        self.assertTrue(owner.neuron.prediction.matches(pattern.edge_ids))

        sensory_before = {
            edge_id: owner.sensory_conductances.weight_for(edge_id)
            for edge_id in owner.sensory_conductances.as_dict()
        }
        relay_before = dict(owner.relay_conductances.as_dict())

        for _ in range(8):
            sim.stimulate_pattern(pattern)

        for edge_id, weight in sensory_before.items():
            self.assertEqual(
                owner.sensory_conductances.weight_for(edge_id),
                weight,
                f"sensory {edge_id} changed on rematch (LTP or LTD leaked)",
            )
        self.assertEqual(owner.relay_conductances.as_dict(), relay_before)


if __name__ == "__main__":
    unittest.main()
