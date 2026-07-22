"""Learning vs recall: reduced rematch drive after bind + force I cascade."""

import unittest

from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.domain.register_state import RegisterState
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.bound_match_recall_policy import BoundMatchRecallPolicy
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.l1_relay_broadcast import L1RelayBroadcastIntegrator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import deterministic_dynamics


class BoundMatchRecallPolicyTests(unittest.TestCase):
    def test_defaults_force_cascade_and_bound_match_gates(self) -> None:
        self.assertTrue(DEFAULT_LEARNING_DYNAMICS.pretrained_inhibitor_exclusivity_enabled)
        self.assertEqual(DEFAULT_LEARNING_DYNAMICS.descending_mode, "force")
        self.assertFalse(DEFAULT_LEARNING_DYNAMICS.emergent_autonomy_enabled)
        self.assertAlmostEqual(
            DEFAULT_LEARNING_DYNAMICS.bound_match_recall_drive_gain, 0.7
        )

    def test_drive_gain_attenuated_on_bound_match(self) -> None:
        policy = BoundMatchRecallPolicy()
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(emergent_autonomy_enabled=False)
        )
        pattern = get_line("H1")
        owner = sim.nucleus.ring[0]
        peer = sim.nucleus.ring[1]
        owner.neuron.memory.bind(pattern, 1.0)
        owner.neuron.prediction.update_from_pattern(pattern.edge_ids)

        self.assertAlmostEqual(
            policy.drive_gain(owner.neuron, pattern.edge_ids), 0.7
        )
        self.assertAlmostEqual(policy.drive_gain(peer.neuron, pattern.edge_ids), 1.0)
        self.assertTrue(policy.plasticity_frozen(owner.neuron, pattern.edge_ids))
        self.assertFalse(policy.plasticity_frozen(peer.neuron, pattern.edge_ids))
        self.assertTrue(policy.spike_eligible(owner.neuron, pattern.edge_ids))
        self.assertFalse(
            policy.spike_eligible(
                peer.neuron, pattern.edge_ids, pattern_has_binder=True
            )
        )
        self.assertTrue(
            policy.spike_eligible(peer.neuron, pattern.edge_ids, free_seats_exist=True)
        )
        self.assertFalse(
            policy.spike_eligible(
                owner.neuron,
                get_line("V1").edge_ids,
                free_seats_exist=True,
            )
        )
        self.assertTrue(
            policy.spike_eligible(
                owner.neuron,
                get_line("V1").edge_ids,
                free_seats_exist=False,
            )
        )

    def test_bound_mismatch_keeps_full_drive(self) -> None:
        policy = BoundMatchRecallPolicy()
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(emergent_autonomy_enabled=False)
        )
        h1 = get_line("H1")
        v1 = get_line("V1")
        owner = sim.nucleus.ring[0]
        owner.neuron.memory.bind(h1, 1.0)
        owner.neuron.prediction.update_from_pattern(h1.edge_ids)

        self.assertAlmostEqual(policy.drive_gain(owner.neuron, v1.edge_ids), 1.0)
        self.assertFalse(policy.plasticity_frozen(owner.neuron, v1.edge_ids))


class BoundMatchRecallIntegrationTests(unittest.TestCase):
    def test_relay_charge_attenuated_for_bound_matcher(self) -> None:
        dynamics = deterministic_dynamics(
            emergent_autonomy_enabled=False,
            excitatory_flow_rate_enabled=False,
            inhibitory_flow_rate_enabled=False,
        )
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")
        owner = sim.nucleus.ring[0]
        peer = sim.nucleus.ring[1]
        owner.neuron.memory.bind(pattern, 1.0)
        owner.neuron.prediction.update_from_pattern(pattern.edge_ids)

        relay_ids = frozenset({"l1_e_0", "l1_e_1", "l1_e_2"})
        for competitor in (owner, peer):
            competitor.neuron.membrane = 0.0
            weights = {
                edge_id: 0.2 if edge_id in relay_ids else weight
                for edge_id, weight in competitor.relay_conductances.as_dict().items()
            }
            for edge_id in relay_ids:
                weights[edge_id] = 0.2
            competitor.relay_conductances.replace_weights(weights)

        lif = LifDynamics()
        broadcast = L1RelayBroadcastIntegrator(lif, dynamics)
        gains = sim.nucleus._relay_drive_gains(pattern.edge_ids)
        broadcast.apply_ring_charge(
            [owner, peer],
            relay_ids,
            timestep=1,
            drive_gains_by_neuron_id=gains,
        )
        self.assertAlmostEqual(gains[owner.neuron.id], 0.7)
        self.assertAlmostEqual(gains[peer.neuron.id], 1.0)
        self.assertAlmostEqual(owner.neuron.membrane, peer.neuron.membrane * 0.7)

    def test_default_cascade_forces_ni_and_l1i_on_spike(self) -> None:
        dynamics = deterministic_dynamics(
            pretrained_inhibitor_exclusivity_enabled=True,
            descending_mode="force",
            temporal_integration_enabled=False,
        )
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")
        wiped = False
        l1i_forced = False
        for _ in range(40):
            for pair in sim.layer1.pairs:
                pair.excitatory.membrane = 0.8
            sim.stimulate_pattern(pattern)
            if not sim.nucleus.last_population_spike_ids:
                continue
            self.assertTrue(sim.nucleus._last_wta_central_fired)
            winner_id = sim.nucleus.last_population_spike_ids[0]
            for competitor in sim.nucleus.ring:
                if competitor.neuron.id == winner_id:
                    continue
                self.assertEqual(competitor.neuron.membrane, 0.0)
            from cognative_paradigm.lines import edge_id_to_index

            active = {edge_id_to_index(e) for e in pattern.edge_ids}
            for pair in sim.layer1.pairs:
                if pair.grid_index not in active:
                    continue
                self.assertEqual(pair.excitatory.membrane, 0.0)
                wiped = True
                if pair.inhibitory.register is RegisterState.ONE:
                    l1i_forced = True
            if wiped and l1i_forced:
                break
        self.assertTrue(wiped)
        # EP path: L2E→E′ at ~0.18/spike needs ~2 hits under θ≈0.26.
        self.assertTrue(l1i_forced)

    def test_bound_rematch_skips_ltp(self) -> None:
        dynamics = deterministic_dynamics(
            emergent_autonomy_enabled=False,
            heterosynaptic_depression_enabled=True,
            prediction_error_ltd_enabled=True,
        )
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")
        owner = sim.nucleus.ring[0]
        owner.neuron.memory.bind(pattern, 1.0)
        owner.neuron.prediction.update_from_pattern(pattern.edge_ids)
        edge = next(iter(pattern.edge_ids))
        owner.sensory_conductances.replace_weights(
            {
                **owner.sensory_conductances.as_dict(),
                edge: 0.8,
            }
        )
        before = owner.sensory_conductances.weight_for(edge)
        self.assertFalse(
            sim.nucleus._plasticity_eligible(owner.neuron, pattern.edge_ids)
        )

        for _ in range(6):
            sim.stimulate_pattern(pattern)

        self.assertEqual(owner.sensory_conductances.weight_for(edge), before)


if __name__ == "__main__":
    unittest.main()
