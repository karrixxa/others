"""Pre-trained I exclusivity: membrane wipe + forced NI / L1 I."""

import unittest

from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.domain.register_state import RegisterState
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.central_inhibitor import CentralInhibitoryNeuron
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics
from cognative_paradigm.simulation.nucleus_ring_competitor import (
    NUCLEUS_RING_SIZE,
    NucleusRingCompetitor,
)
from cognative_paradigm.simulation.wta_coordinator import WtaCoordinator
from tests.simulation_helpers import deterministic_dynamics


class PretrainedInhibitorExclusivityTests(unittest.TestCase):
    def test_first_spike_forces_ni_and_wipes_other_membranes(self) -> None:
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=9.0, inhibition_strength=1.1)
        wta = WtaCoordinator(
            lif,
            central,
            collateral_gain=0.5,
            membrane_noise_std=0.0,
            pretrained_exclusivity=True,
        )
        ring = [
            NucleusRingCompetitor(index, relay_weight=0.2)
            for index in range(NUCLEUS_RING_SIZE)
        ]
        relay_ids = frozenset({"l1_e_0", "l1_e_1", "l1_e_2"})
        for competitor in ring:
            competitor.neuron.membrane = 1.2
        ring[0].neuron.membrane = 1.6

        outcome = wta.run(ring, relay_ids, timestep=1, skip_integration=True)
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertTrue(outcome.central_fired)
        self.assertEqual(len(outcome.population_spike_ids), 1)
        winner_id = outcome.population_spike_ids[0]
        for competitor in ring:
            if competitor.neuron.id == winner_id:
                continue
            self.assertEqual(competitor.neuron.membrane, 0.0)

    def test_soft_path_allows_multi_spike_when_flag_off(self) -> None:
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=2.0, inhibition_strength=0.1)
        wta = WtaCoordinator(
            lif,
            central,
            collateral_gain=0.1,
            membrane_noise_std=0.0,
            pretrained_exclusivity=False,
        )
        ring = [
            NucleusRingCompetitor(index, relay_weight=0.2) for index in range(3)
        ]
        for competitor in ring:
            competitor.neuron.membrane = 1.5
        outcome = wta.run(
            ring, frozenset({"l1_e_0"}), timestep=1, skip_integration=True
        )
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertGreaterEqual(len(outcome.population_spike_ids), 2)

    def test_i_channels_frozen_under_exclusivity(self) -> None:
        dynamics = deterministic_dynamics(
            pretrained_inhibitor_exclusivity_enabled=True,
            inhibitory_turnover_enabled=True,
        )
        sim = BrainSimulator(dynamics=dynamics)
        before = list(sim.nucleus.central_inhibitor.inhibition_channels)
        pattern = get_line("H1")
        for _ in range(30):
            sim.stimulate_pattern(pattern)
        after = list(sim.nucleus.central_inhibitor.inhibition_channels)
        self.assertEqual(before, after)

    def test_immediate_l1_i_wipes_paired_l1_e(self) -> None:
        dynamics = LearningDynamics(
            pretrained_inhibitor_exclusivity_enabled=True,
            descending_mode="force",
            emergent_autonomy_enabled=False,
            membrane_noise_std=0.0,
            temporal_integration_enabled=False,
        )
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")
        wiped = False
        for _ in range(80):
            for pair in sim.layer1.pairs:
                pair.excitatory.membrane = 0.8
            result = sim.stimulate_pattern(pattern)
            if not any(
                str(event["neuron_id"]).startswith("l1_i_")
                for event in result.step_events
            ):
                continue
            from cognative_paradigm.lines import edge_id_to_index

            active = {edge_id_to_index(e) for e in pattern.edge_ids}
            for pair in sim.layer1.pairs:
                if pair.grid_index not in active:
                    continue
                self.assertEqual(pair.excitatory.membrane, 0.0)
                self.assertEqual(pair.inhibitory.register, RegisterState.ONE)
                wiped = True
            if wiped:
                break
        self.assertTrue(wiped)

    def test_biological_profile_cannot_enable_force_exclusivity(self) -> None:
        from cognative_paradigm.simulation.learning_dynamics import (
            validate_learning_dynamics,
        )

        dynamics = LearningDynamics(
            lab_profile_enabled=True,
            column_architecture_profile="hybrid_cortical_biological",
            pretrained_inhibitor_exclusivity_enabled=True,
            descending_mode="graded",
        )
        with self.assertRaises(ValueError) as ctx:
            validate_learning_dynamics(dynamics)
        self.assertIn("pretrained_inhibitor_exclusivity", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
