"""L2E → L1E′ gradual charge → force L1I."""

import unittest

from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.domain.register_state import RegisterState
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.descending_inhibition import DescendingInhibition
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.layer1_network import Layer1Relay
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import deterministic_dynamics
from tests.test_descending_inhibition import h1_grid_indices


class SecondaryL1EDescendingTests(unittest.TestCase):
    def test_default_secondary_threshold(self) -> None:
        self.assertAlmostEqual(
            DEFAULT_LEARNING_DYNAMICS.l1_secondary_excitatory_threshold, 0.26
        )
        relay = Layer1Relay(LifDynamics())
        self.assertAlmostEqual(relay.pairs[0].secondary_excitatory.threshold, 0.26)

    def test_l2_charge_hits_ep_not_i(self) -> None:
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        # Unit weight so membrane == raw gain for this assertion.
        di = DescendingInhibition(lif, gain=0.10, afferent_init_weight=1.0)
        targets = frozenset({4})
        di.enqueue_from_population_spikes(("nucleus_e_0",), targets)
        fired = di.apply_pending(relay, timestep=1)
        self.assertEqual(fired, frozenset())
        pair = relay.pairs[4]
        self.assertAlmostEqual(pair.secondary_excitatory.membrane, 0.10, places=4)
        self.assertAlmostEqual(pair.inhibitory.membrane, 0.0)
        self.assertEqual(pair.inhibitory.register, RegisterState.Z)

    def test_ep_threshold_force_fires_i(self) -> None:
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        di = DescendingInhibition(lif, gain=0.30, afferent_init_weight=1.0)
        targets = frozenset({2})
        di.enqueue_from_population_spikes(("nucleus_e_0",), targets)
        fired = di.apply_pending(relay, timestep=1)
        self.assertIn("l1_ep_2", fired)
        self.assertIn("l1_i_2", fired)
        self.assertEqual(relay.pairs[2].inhibitory.register, RegisterState.ONE)

    def test_serialize_exposes_secondary_fields(self) -> None:
        relay = Layer1Relay(LifDynamics())
        state = relay.serialize_state()
        pair = state["pairs"][0]
        self.assertIn("secondary_excitatory_register", pair)
        self.assertIn("secondary_excitatory_membrane", pair)

    def test_production_gain_one_shot_ep_spike(self) -> None:
        """Production gain ≥ θ_E′: one L2E delivery spikes E′ and force-fires I."""
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        gain = DEFAULT_LEARNING_DYNAMICS.l2_to_l1_i_gain
        self.assertGreaterEqual(
            gain, DEFAULT_LEARNING_DYNAMICS.l1_secondary_excitatory_threshold
        )
        di = DescendingInhibition(lif, gain=gain, afferent_init_weight=1.0)
        targets = frozenset({2})
        di.enqueue_from_population_spikes(("nucleus_e_0",), targets)
        fired = di.apply_pending(relay, timestep=1)
        self.assertIn("l1_ep_2", fired)
        self.assertIn("l1_i_2", fired)
        self.assertEqual(relay.pairs[2].inhibitory.register, RegisterState.ONE)

    def test_engine_exclusivity_charges_ep_then_i(self) -> None:
        """Default gradual gain: E′ membrane climbs, then E′ and I spike."""
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                pretrained_inhibitor_exclusivity_enabled=True,
                descending_mode="force",
                temporal_integration_enabled=False,
                excitatory_flow_rate_enabled=False,
                l2_to_l1_i_gain=0.18,
                assembly_flow_credit_enabled=True,
            )
        )
        pattern = get_line("H1")
        targets = h1_grid_indices()
        saw_ep_charge = False
        saw_ep_spike = False
        saw_i = False
        for _ in range(120):
            result = sim.stimulate_pattern(pattern)
            for pair in sim.layer1.pairs:
                if pair.grid_index not in targets:
                    continue
                if pair.secondary_excitatory.membrane > 0.0:
                    saw_ep_charge = True
            for event in result.step_events:
                nid = str(event["neuron_id"])
                if nid.startswith("l1_ep_"):
                    saw_ep_spike = True
                if nid.startswith("l1_i_"):
                    saw_i = True
            if saw_ep_spike and saw_i:
                break
        self.assertTrue(saw_ep_charge, "expected gradual E′ membrane charge")
        self.assertTrue(saw_ep_spike, "expected E′ spike at threshold")
        self.assertTrue(saw_i, "expected L1 I force-fire after E′")


if __name__ == "__main__":
    unittest.main()
