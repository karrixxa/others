import unittest

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import LINES, LINE_IDS, LINE_INDICES, get_line
from cognative_paradigm.simulation.nucleus_ring_competitor import NUCLEUS_RING_SIZE
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import (
    deterministic_dynamics,
    force_cascade_dynamics,
    learn_all_catalog_lines,
    learn_catalog_line,
    stimulate_until_pattern_bound,
    stimulate_until_recognized,
)


class NucleusWtaTests(unittest.TestCase):
    def test_four_ring_neurons_and_central_inhibitor(self) -> None:
        sim = BrainSimulator()
        self.assertEqual(len(sim.nucleus.ring), NUCLEUS_RING_SIZE)
        self.assertEqual(sim.nucleus.central_inhibitor.neuron.id, "nucleus_i")

    def test_authentic_spikers_match_population_ids(self) -> None:
        """Registers ONE and diagnostic winner stay honest with population_spike_ids."""
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(relay_weight_init_spread=0.0),
        )
        population: tuple[str, ...] = ()
        for _ in range(20):
            sim.stimulate_pattern(get_line("H1"))
            population = sim.nucleus.last_population_spike_ids
            if population:
                break

        self.assertGreaterEqual(len(population), 1)
        winners = [
            n for n in sim.get_state()["nucleus"]["ring"] if n["register"] == "1"
        ]
        self.assertEqual({n["id"] for n in winners}, set(population))
        winner_id = sim.get_state().get("winner_neuron_id")
        self.assertIn(winner_id, set(population))

    def test_fair_ties_spread_winners_across_ring(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                membrane_noise_std=0.05,
                wta_fair_ties=True,
                wta_rng_seed=7,
                e_learning_rate=0.0,
            )
        )
        winner_ids: set[str] = set()
        for _ in range(80):
            sim.stimulate_pattern(get_line("H1"))
            winner_id = sim.get_state().get("winner_neuron_id")
            if winner_id:
                winner_ids.add(winner_id)
            if len(winner_ids) >= 3:
                break
        self.assertGreaterEqual(
            len(winner_ids),
            2,
            f"Expected biological WTA to engage multiple ring neurons, got {winner_ids}",
        )

    def test_central_i_fires_after_authentic_spikes_charge_it(self) -> None:
        # Production force cascade: first authentic L2E force-fires NI.
        sim = BrainSimulator(dynamics=force_cascade_dynamics())
        central_fired = False
        for _ in range(40):
            sim.stimulate_pattern(get_line("H1"))
            state = sim.get_state()["nucleus"]
            if state["wta_central_fired"]:
                central_fired = True
                ring_ones = {
                    neuron["id"]
                    for neuron in state["ring"]
                    if neuron["register"] == "1"
                }
                population = set(sim.nucleus.last_population_spike_ids)
                self.assertEqual(ring_ones, population)
                self.assertGreaterEqual(len(ring_ones), 1)
                break
        self.assertTrue(
            central_fired,
            "central I should fire once authentic spikes have charged it",
        )

    def test_membrane_accumulates_before_first_spike(self) -> None:
        sim = BrainSimulator(
            lif_parameters=DEFAULT_LEARNING_DYNAMICS.lif_parameters(),
            dynamics=deterministic_dynamics(),
        )
        sim.stimulate_pattern(get_line("H1"))
        membrane = sim.nucleus.ring[0].neuron.membrane
        self.assertGreater(membrane, 0.0)
        self.assertLess(membrane, DEFAULT_LEARNING_DYNAMICS.nucleus_threshold)

    def test_learns_h1_with_symbol(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        result = learn_catalog_line(sim, "H1")
        self.assertTrue(str(result.output_symbol).startswith("sigma_"))
        pattern = get_line("H1")
        owner = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertTrue(str(owner).startswith("nucleus_e_"))

    def test_second_pattern_binds_after_first(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        stimulate_until_pattern_bound(sim, LINE_INDICES["H1"])
        training = sim.get_state()["training"]
        self.assertEqual(training["bound_pattern_count"], 1)

    def test_equilibrium_after_all_eight_patterns(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_all_catalog_lines(sim)
        training = sim.get_state()["training"]
        self.assertTrue(training["equilibrium"])
        self.assertEqual(training["progress"], f"{len(LINE_IDS)}/{len(LINE_IDS)}")

    def test_different_pattern_prediction_error(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_catalog_line(sim, "H1")
        result = sim.stimulate_pattern(get_line("V1"))
        for _ in range(10):
            if any(event["type"] == "PREDICTION_ERROR" for event in result.step_events):
                break
            result = sim.stimulate_pattern(get_line("V1"))
        self.assertIsNone(result.output_symbol)
        events = [event["type"] for event in result.step_events]
        self.assertIn("PREDICTION_ERROR", events)

    def test_state_includes_nucleus_ring(self) -> None:
        sim = BrainSimulator()
        sim.stimulate_pattern(get_line("H1"))
        state = sim.get_state()
        self.assertIn("nucleus", state)
        self.assertEqual(len(state["nucleus"]["ring"]), NUCLEUS_RING_SIZE)
        self.assertIn("training", state)

    def test_equilibrium_recognizes_learned_pattern(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_all_catalog_lines(sim)
        result = stimulate_until_recognized(sim, LINE_INDICES["H1"], max_steps=80)
        self.assertTrue(str(result.output_symbol).startswith("sigma_"))

    def test_event_log_never_contains_z(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        sim.stimulate(LINES["H1"], duration=4)
        for entry in sim.event_log.entries:
            self.assertIn(entry["type"], EventType.__members__)


if __name__ == "__main__":
    unittest.main()
