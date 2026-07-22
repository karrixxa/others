import unittest

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.domain.relay_conductance_map import RelayConductanceMap
from cognative_paradigm.learning.conductance_plasticity import (
    ConductancePlasticityConfig,
    ConductancePlasticityLearner,
)
from cognative_paradigm.learning.relay_conductance_initializer import RelayConductanceInitializer
from cognative_paradigm.lines import LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.nucleus_ring_competitor import NUCLEUS_RING_SIZE, NucleusRingCompetitor
from tests.simulation_helpers import deterministic_dynamics


class L2RelayPlasticityTests(unittest.TestCase):
    def test_relay_conductances_potentiate_for_active_l1_relays(self) -> None:
        learner = ConductancePlasticityLearner(
            ConductancePlasticityConfig(e_plasticity_threshold=1.85)
        )
        conductances = RelayConductanceMap(0.22)
        active = frozenset({"l1_e_1", "l1_e_4", "l1_e_7"})
        before = conductances.drive_for(active)
        conductances.apply_plasticity(learner, active)
        after = conductances.drive_for(active)
        self.assertGreater(after, before)

    def test_ring_starts_with_randomized_relay_maps(self) -> None:
        initializer = RelayConductanceInitializer(
            center_weight=0.22,
            spread=0.25,
            seed=7,
        )
        maps = initializer.create_ring_maps(8)
        flattened = [weight for relay_map in maps for weight in relay_map.as_dict().values()]
        self.assertEqual(len(flattened), 72)
        self.assertGreater(len(set(round(weight, 6) for weight in flattened)), 1)
        self.assertTrue(all(0.01 <= weight <= 2.0 for weight in flattened))

    def test_relay_plasticity_follows_authentic_spikers(self) -> None:
        """Each authentic spiker updates its own maps; non-spikers stay put."""
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                wta_rng_seed=11,
                relay_weight_init_spread=0.25,
            )
        )
        pattern = get_line("H1")
        relay_ids = frozenset(f"l1_e_{index}" for index in LINE_INDICES["H1"])
        for _ in range(80):
            before = {
                competitor.neuron.id: competitor.relay_conductances.active_weight_sum(
                    relay_ids
                )
                for competitor in sim.nucleus.ring
            }
            sim.stimulate_pattern(pattern)
            spike_ids = set(sim.nucleus.last_population_spike_ids)
            if not spike_ids:
                continue
            after = {
                competitor.neuron.id: competitor.relay_conductances.active_weight_sum(
                    relay_ids
                )
                for competitor in sim.nucleus.ring
            }
            gained = [
                neuron_id
                for neuron_id in spike_ids
                if after[neuron_id] > before[neuron_id]
            ]
            if not gained:
                continue
            for neuron_id, weight_before in before.items():
                if neuron_id not in spike_ids:
                    self.assertEqual(
                        after[neuron_id],
                        weight_before,
                        f"{neuron_id} must not LTP without an authentic spike",
                    )
            return
        self.fail("expected authentic-spiker relay plasticity within stimulation window")

    def test_loser_membranes_stay_subthreshold_during_repeated_stim(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                wta_rng_seed=17,
                relay_weight_init_spread=0.25,
            )
        )
        pattern = get_line("H1")
        for _ in range(24):
            sim.stimulate_pattern(pattern)

        threshold = sim.nucleus.ring[0].neuron.threshold
        winner_id = sim.get_state().get("winner_neuron_id")
        for competitor in sim.nucleus.ring:
            if competitor.neuron.id == winner_id:
                continue
            self.assertLess(
                competitor.neuron.membrane,
                threshold,
                f"{competitor.neuron.id} membrane should stay below threshold",
            )

    def test_all_ring_neurons_integrate_l1_drive_on_same_spike(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                wta_rng_seed=13,
                relay_weight_init_spread=0.25,
            )
        )
        for competitor in sim.nucleus.ring:
            competitor.neuron.membrane = 0.2

        before = [competitor.neuron.membrane for competitor in sim.nucleus.ring]
        sim.stimulate_pattern(get_line("H1"))
        after = [competitor.neuron.membrane for competitor in sim.nucleus.ring]
        deltas = [round(after[index] - before[index], 6) for index in range(NUCLEUS_RING_SIZE)]

        self.assertTrue(all(delta > 0 for delta in deltas), f"expected positive deltas, got {deltas}")

    def test_ring_spikes_match_population_ids(self) -> None:
        """Event log and population_spike_ids stay honest; multi-spike allowed."""
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                membrane_noise_std=0.08,
                wta_fair_ties=True,
                wta_rng_seed=3,
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
                ring = sim.get_state()["nucleus"]["ring"]
                registers_one = {n["id"] for n in ring if n["register"] == "1"}
                self.assertEqual(registers_one, set(population))
                return
        self.fail("expected a ring E spike during stimulation")

    def test_compute_drive_uses_per_relay_conductances(self) -> None:
        competitor = NucleusRingCompetitor(ring_index=0, relay_weight=0.2)
        weights = competitor.relay_conductances.as_dict()
        weights["l1_e_0"] = 0.5
        weights["l1_e_1"] = 0.1
        competitor.relay_conductances.replace_weights(weights)
        drive = competitor.compute_drive(frozenset({"l1_e_0", "l1_e_1"}))
        self.assertAlmostEqual(drive, 0.6)


if __name__ == "__main__":
    unittest.main()
