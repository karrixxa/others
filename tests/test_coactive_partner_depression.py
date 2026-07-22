"""SG-1 co-active partner LTD + SG-2 sole-owner freeze tests."""

from __future__ import annotations

import unittest

from cognative_paradigm.learning.coactive_partner_depression import (
    CoActivePartnerDepressionConfig,
    CoActivePartnerDepressionPolicy,
)
from cognative_paradigm.lines import LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from cognative_paradigm.simulation.wta_coordinator import WtaOutcome
from tests.simulation_helpers import (
    deterministic_dynamics,
    force_sole_binder,
    stimulate_until_pattern_bound,
    stimulate_until_recognized,
)


class CoActivePartnerDepressionUnitTests(unittest.TestCase):
    def test_defaults_match_dynamics(self) -> None:
        policy = CoActivePartnerDepressionPolicy()
        self.assertTrue(policy.config.enabled)
        self.assertAlmostEqual(policy.config.eta_scale, 0.30)
        self.assertTrue(DEFAULT_LEARNING_DYNAMICS.coactive_partner_ltd_enabled)
        self.assertAlmostEqual(
            DEFAULT_LEARNING_DYNAMICS.coactive_partner_ltd_eta_scale, 0.30
        )

    def test_k_one_yields_zero_rates(self) -> None:
        policy = CoActivePartnerDepressionPolicy()
        rates = policy.depression_rates_by_neuron(
            {"n0": 1.5},
            e_learning_rate=0.016,
        )
        self.assertEqual(rates, {"n0": 0.0})

    def test_k_two_weaker_gets_higher_rate(self) -> None:
        policy = CoActivePartnerDepressionPolicy()
        eta_e = 0.016
        rates = policy.depression_rates_by_neuron(
            {"strong": 1.2, "weak": 0.4},
            e_learning_rate=eta_e,
        )
        eta_cross = 0.30 * eta_e
        self.assertAlmostEqual(rates["strong"], eta_cross * (1.0 - 1.2 / 1.6))
        self.assertAlmostEqual(rates["weak"], eta_cross * (1.0 - 0.4 / 1.6))
        self.assertGreater(rates["weak"], rates["strong"])
        self.assertAlmostEqual(sum(rates.values()), eta_cross * (2 - 1))

    def test_disabled_yields_zeros(self) -> None:
        policy = CoActivePartnerDepressionPolicy(
            CoActivePartnerDepressionConfig(enabled=False)
        )
        rates = policy.depression_rates_by_neuron(
            {"a": 1.0, "b": 1.0},
            e_learning_rate=0.016,
        )
        self.assertEqual(rates, {"a": 0.0, "b": 0.0})


class BinderGroundTruthTests(unittest.TestCase):
    def test_binders_for_pattern_lists_all_and_owner_is_first(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        pattern = get_line("H1")
        a, b = sim.nucleus.ring[0], sim.nucleus.ring[1]
        a.neuron.memory.bind(pattern, 1.0)
        a.neuron.prediction.update_from_pattern(pattern.edge_ids)
        b.neuron.memory.bind(pattern, 1.0)
        b.neuron.prediction.update_from_pattern(pattern.edge_ids)

        binders = sim.nucleus.pattern_ownership.binders_for_pattern(pattern.edge_ids)
        self.assertEqual(binders, [a.neuron.id, b.neuron.id])
        self.assertEqual(
            sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids),
            a.neuron.id,
        )


class SoleOwnerFreezeTests(unittest.TestCase):
    def test_sole_binder_freezes_plasticity_gate(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        pattern = get_line("H1")
        owner = sim.nucleus.ring[0]
        owner.neuron.memory.bind(pattern, 1.0)
        owner.neuron.prediction.update_from_pattern(pattern.edge_ids)

        self.assertTrue(
            sim.nucleus._bound_match_sole_freeze(owner.neuron, pattern.edge_ids)
        )
        self.assertFalse(
            sim.nucleus._plasticity_eligible(owner.neuron, pattern.edge_ids)
        )

    def test_plural_binders_freeze_plasticity_on_rematch(self) -> None:
        """After bind, any bound∧match rematch freezes learning (half-rate recall)."""
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        pattern = get_line("H1")
        a, b = sim.nucleus.ring[0], sim.nucleus.ring[1]
        for competitor in (a, b):
            competitor.neuron.memory.bind(pattern, 1.0)
            competitor.neuron.prediction.update_from_pattern(pattern.edge_ids)

        self.assertFalse(
            sim.nucleus._bound_match_sole_freeze(a.neuron, pattern.edge_ids)
        )
        self.assertFalse(
            sim.nucleus._plasticity_eligible(a.neuron, pattern.edge_ids)
        )
        self.assertFalse(
            sim.nucleus._plasticity_eligible(b.neuron, pattern.edge_ids)
        )

    def test_site_b_skips_bound_match_rematch(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                heterosynaptic_depression_enabled=True,
                hot_nonspiker_ltd_enabled=True,
            )
        )
        pattern = get_line("H1")
        sole = sim.nucleus.ring[0]
        sole.neuron.memory.bind(pattern, 1.0)
        sole.neuron.prediction.update_from_pattern(pattern.edge_ids)

        edge = next(iter(pattern.edge_ids))
        sole.sensory_conductances.replace_weights(
            {
                **sole.sensory_conductances.as_dict(),
                edge: 0.9,
            }
        )
        before_sole = sole.sensory_conductances.weight_for(edge)
        hot = (
            DEFAULT_LEARNING_DYNAMICS.central_competition_hot_fraction
            * DEFAULT_LEARNING_DYNAMICS.nucleus_threshold
        )
        outcome = WtaOutcome(
            winner=None,
            candidate_count=1,
            central_fired=True,
            arbitration_required=False,
            inhibited_ring_indices=(0,),
            inhibited_entry_membranes=((0, hot + 0.05),),
        )
        sim.nucleus._apply_hot_nonspiker_ltd(outcome, pattern.edge_ids)
        self.assertEqual(sole.sensory_conductances.weight_for(edge), before_sole)

        # Dual-bind rematch also freezes Site B (recall stop-learning).
        hitch = sim.nucleus.ring[1]
        hitch.neuron.memory.bind(pattern, 1.0)
        hitch.neuron.prediction.update_from_pattern(pattern.edge_ids)
        hitch.sensory_conductances.replace_weights(
            {
                **hitch.sensory_conductances.as_dict(),
                edge: 0.9,
            }
        )
        before_hitch = hitch.sensory_conductances.weight_for(edge)
        outcome_plural = WtaOutcome(
            winner=None,
            candidate_count=1,
            central_fired=True,
            arbitration_required=False,
            inhibited_ring_indices=(1,),
            inhibited_entry_membranes=((1, hot + 0.05),),
        )
        sim.nucleus._apply_hot_nonspiker_ltd(outcome_plural, pattern.edge_ids)
        self.assertEqual(hitch.sensory_conductances.weight_for(edge), before_hitch)

    def test_rule_72_sole_rematch_still_freezes_weights(self) -> None:
        """Sole owner rematch: sensory/relay weights unchanged (Rule 7.2)."""
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                heterosynaptic_depression_enabled=True,
                prediction_error_ltd_enabled=True,
                heterosynaptic_inactive_ltd_enabled=True,
                hot_nonspiker_ltd_enabled=True,
                coactive_partner_ltd_enabled=True,
            )
        )
        pattern = get_line("H1")
        stimulate_until_pattern_bound(sim, LINE_INDICES["H1"])
        stimulate_until_recognized(sim, LINE_INDICES["H1"])
        force_sole_binder(sim, pattern)

        owner_id = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertIsNotNone(owner_id)
        binders = sim.nucleus.pattern_ownership.binders_for_pattern(pattern.edge_ids)
        self.assertEqual(len(binders), 1)

        owner = sim.nucleus.competitor_by_id(owner_id)
        assert owner is not None
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
                f"sensory {edge_id} changed on sole rematch",
            )
        self.assertEqual(owner.relay_conductances.as_dict(), relay_before)


class NucleusCoActiveWiringTests(unittest.TestCase):
    def test_nucleus_wires_coactive_from_dynamics(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        config = sim.nucleus._coactive_partner.config
        self.assertTrue(config.enabled)
        self.assertAlmostEqual(config.eta_scale, 0.30)


if __name__ == "__main__":
    unittest.main()
