"""Assembly flow credit on central NI and descending L1 I afferents."""

import unittest

from cognative_paradigm.domain.assembly_afferent_map import AssemblyAfferentMap
from cognative_paradigm.learning.assembly_flow_credit import (
    AssemblyFlowCreditConfig,
    AssemblyFlowCreditLearner,
)
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics
from cognative_paradigm.lines import get_line


class AssemblyAfferentMapTests(unittest.TestCase):
    def test_weighted_pool_favors_high_weight_source(self) -> None:
        afferents = AssemblyAfferentMap(2, init_weight=0.25)
        afferents.weights = [0.2, 1.0]
        uniform = afferents.weighted_membrane_drive(
            [1.0, 1.0], threshold=1.0, gain=1.0
        )
        skewed = afferents.weighted_membrane_drive(
            [0.2, 1.0], threshold=1.0, gain=1.0
        )
        self.assertGreater(skewed, uniform * 0.5)


class AssemblyFlowCreditLearnerTests(unittest.TestCase):
    def test_dominant_contributor_gains_more_weight(self) -> None:
        afferents = AssemblyAfferentMap(2, init_weight=0.5, max_weight=1.5)
        afferents.traces = [0.1, 0.9]
        learner = AssemblyFlowCreditLearner(
            AssemblyFlowCreditConfig(learning_rate=0.05, decay_frac=0.5)
        )
        learner.apply_on_fire(afferents, v_pre=0.9, theta=1.0)
        self.assertGreater(afferents.weights[1], afferents.weights[0])

    def test_non_contributor_decays_toward_floor(self) -> None:
        afferents = AssemblyAfferentMap(1, init_weight=0.8, min_weight=0.05, max_weight=1.5)
        afferents.traces = [0.0]
        learner = AssemblyFlowCreditLearner(
            AssemblyFlowCreditConfig(learning_rate=0.05, decay_frac=0.5)
        )
        learner.apply_on_fire(afferents, v_pre=1.0, theta=1.0)
        self.assertLess(afferents.weights[0], 0.8)


class AssemblyIntegrationTests(unittest.TestCase):
    def test_central_afferents_differentiate_after_training(self) -> None:
        dynamics = LearningDynamics(
            assembly_flow_credit_enabled=True,
            temporal_integration_enabled=False,
            excitatory_flow_rate_enabled=False,
            membrane_noise_std=0.0,
            wta_rng_seed=3,
            relay_weight_init_spread=0.0,
            sensory_weight_init_spread=0.0,
            central_inhibitor_threshold=0.35,
            collateral_gain=0.9,
            pretrained_inhibitor_exclusivity_enabled=False,
            central_pool_gain=0.50,
            central_competition_ni_discharge_fraction=0.70,
            assembly_afferent_init_weight=0.25,
            assembly_afferent_max_weight=1.5,
            e_learning_rate=0.05,
        )
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")
        for _ in range(120):
            sim.step(pattern)

        weights = sim.nucleus.central_inhibitor.excitatory_afferents.weights
        self.assertGreater(max(weights) - min(weights), 0.02)

    def test_descending_afferents_enabled_without_error(self) -> None:
        dynamics = LearningDynamics(
            assembly_flow_credit_enabled=True,
            l2_to_l1_i_gain=0.25,
            membrane_noise_std=0.0,
            wta_rng_seed=1,
        )
        sim = BrainSimulator(dynamics=dynamics)
        for line in ("H1", "V1", "D0", "D1"):
            for _ in range(8):
                sim.step(get_line(line))
        weights = sim._descending.assembly_afferents.weights
        self.assertEqual(len(weights), 9)


if __name__ == "__main__":
    unittest.main()
