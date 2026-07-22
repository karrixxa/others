import unittest

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import deterministic_dynamics


class PopulationSpikeLoggingTests(unittest.TestCase):
    def test_layer1_inhibitory_spikes_are_logged(self) -> None:
        # Production gain is gradual (< E′ θ). Override to one-shot so logging
        # asserts stay short under sparse L2E + leak.
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                pretrained_inhibitor_exclusivity_enabled=True,
                descending_mode="force",
                l2_to_l1_i_gain=0.32,
            ),
        )
        inhibitory_logged = False
        secondary_logged = False
        for _ in range(100):
            result = sim.stimulate_pattern(get_line("H1"))
            i_spikes = [
                event
                for event in result.step_events
                if event["type"] == EventType.SPIKE.name
                and str(event["neuron_id"]).startswith("l1_i_")
            ]
            ep_spikes = [
                event
                for event in result.step_events
                if event["type"] == EventType.SPIKE.name
                and str(event["neuron_id"]).startswith("l1_ep_")
            ]
            if ep_spikes:
                secondary_logged = True
            if i_spikes:
                inhibitory_logged = True
                self.assertTrue(
                    all(nid.startswith("l1_i_") for nid in (e["neuron_id"] for e in i_spikes))
                )
                break
        self.assertTrue(
            secondary_logged,
            "expected L1 E′ SPIKE before or with L1 I force-fire",
        )
        self.assertTrue(
            inhibitory_logged,
            "expected L1 inhibitory SPIKE after L2 → E′ feedback",
        )

    def test_contested_wta_logs_population_ring_spikes(self) -> None:
        """Population spike log stays honest under contested WTA (multi-OK)."""
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                membrane_noise_std=0.08,
                wta_fair_ties=True,
                wta_rng_seed=3,
                collateral_gain=0.9,
            )
        )
        for _ in range(80):
            result = sim.stimulate_pattern(get_line("H1"))
            ring_spikes = [
                event["neuron_id"]
                for event in result.step_events
                if event["type"] == EventType.SPIKE.name
                and str(event["neuron_id"]).startswith("nucleus_e_")
            ]
            if ring_spikes:
                population = list(sim.nucleus.last_population_spike_ids)
                self.assertEqual(sorted(ring_spikes), sorted(population))
                self.assertGreaterEqual(len(ring_spikes), 1)
                return
        self.fail("expected at least one ring E SPIKE from authentic competition")


if __name__ == "__main__":
    unittest.main()
