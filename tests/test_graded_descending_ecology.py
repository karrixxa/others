"""Graded descending inhibition ecology tests (Phase 6)."""

from __future__ import annotations

import unittest
from dataclasses import replace

import pytest

from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.domain.register_state import RegisterState
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.descending_inhibition import DescendingInhibition
from cognative_paradigm.simulation.descending_inhibition_mode import (
    DescendingInhibitionMode,
)
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.layer1_network import Layer1Relay
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import interleaved_learn_all, ownership_owner_ids, unguided_ecological_dynamics


class GradedDescendingUnitTests(unittest.TestCase):
    def test_graded_mode_does_not_force_i_threshold(self) -> None:
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        pair = relay.pairs[2]
        pair.inhibitory.membrane = 0.0
        di = DescendingInhibition(
            lif,
            gain=0.30,
            mode=DescendingInhibitionMode.GRADED,
            afferent_init_weight=1.0,
            wipe_primary_excitatory_on_i_fire=False,
        )
        di.enqueue_from_population_spikes(("nucleus_e_0",), frozenset({2}))
        di.apply_pending(relay, timestep=1)
        self.assertLess(pair.inhibitory.membrane, pair.inhibitory.threshold)

    def test_force_mode_still_force_fires_i(self) -> None:
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        di = DescendingInhibition(
            lif,
            gain=0.30,
            mode=DescendingInhibitionMode.FORCE,
            afferent_init_weight=1.0,
        )
        di.enqueue_from_population_spikes(("nucleus_e_0",), frozenset({2}))
        fired = di.apply_pending(relay, timestep=1)
        self.assertIn("l1_i_2", fired)
        self.assertEqual(relay.pairs[2].inhibitory.register, RegisterState.ONE)


@pytest.mark.biological_lab
class GradedDescendingEcologyTests(unittest.TestCase):
    def test_graded_lab_stack_learns_without_force_wipe(self) -> None:
        dynamics = replace(
            unguided_ecological_dynamics(),
            descending_mode="graded",
            pretrained_inhibitor_exclusivity_enabled=False,
            plastic_ni_enabled=True,
            inhibitory_stdp_enabled=True,
        )
        sim = BrainSimulator(dynamics=dynamics)
        interleaved_learn_all(sim, max_rounds=250)
        self.assertGreaterEqual(len(ownership_owner_ids(sim)), 2)

    def test_production_force_mode_is_doctrine(self) -> None:
        self.assertEqual(DEFAULT_LEARNING_DYNAMICS.descending_mode, "force")
        sim = BrainSimulator()
        self.assertEqual(sim._descending.mode, DescendingInhibitionMode.FORCE)

    def test_graded_mode_still_selectable_as_labeled_control(self) -> None:
        from cognative_paradigm.simulation.learning_dynamics import LearningDynamics

        sim = BrainSimulator(
            dynamics=LearningDynamics(
                descending_mode="graded",
                pretrained_inhibitor_exclusivity_enabled=False,
                emergent_autonomy_enabled=True,
            )
        )
        self.assertEqual(sim._descending.mode, DescendingInhibitionMode.GRADED)


if __name__ == "__main__":
    unittest.main()
