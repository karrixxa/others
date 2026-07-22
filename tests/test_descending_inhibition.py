import unittest
from dataclasses import replace

from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.domain.register_state import RegisterState
from cognative_paradigm.lines import get_line, edge_id_to_index
from cognative_paradigm.simulation.descending_inhibition import DescendingInhibition
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.layer1_network import Layer1Relay
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics
from tests.simulation_helpers import deterministic_dynamics, learn_catalog_line


def h1_grid_indices() -> frozenset[int]:
    pattern = get_line("H1")
    return frozenset(edge_id_to_index(edge) for edge in pattern.edge_ids)


class DescendingInhibitionUnitTests(unittest.TestCase):
    def test_enqueue_excludes_central_inhibitor(self) -> None:
        di = DescendingInhibition(LifDynamics(), gain=0.08)
        di.enqueue_from_population_spikes(
            ("nucleus_e_0", "nucleus_e_1", "nucleus_i"),
            frozenset({4}),
            central_inhibitor_id="nucleus_i",
        )
        self.assertAlmostEqual(di.pending_charge, 0.16)

    def test_enqueue_targets_active_shape_only(self) -> None:
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        # Unit EP weight: delivered charge == pending gain*spikes.
        di = DescendingInhibition(lif, gain=0.08, afferent_init_weight=1.0)
        targets = h1_grid_indices()
        self.assertEqual(len(targets), 3)

        di.enqueue_from_population_spikes(("e0",) * 5, targets)
        self.assertAlmostEqual(di.pending_charge, 0.40 * 3)

        fired = di.apply_pending(relay, timestep=1)
        self.assertEqual(len(fired), 6)  # E′ + I per targeted cell
        for pair in relay.pairs:
            if pair.grid_index in targets:
                self.assertEqual(pair.secondary_excitatory.register, RegisterState.ONE)
                self.assertEqual(pair.inhibitory.register, RegisterState.ONE)
            else:
                self.assertEqual(pair.inhibitory.register, RegisterState.Z)
                self.assertAlmostEqual(pair.inhibitory.membrane, 0.0)
                self.assertAlmostEqual(pair.secondary_excitatory.membrane, 0.0)

    def test_subthreshold_charge_accumulates_on_target_cells(self) -> None:
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        di = DescendingInhibition(lif, gain=0.08, afferent_init_weight=1.0)
        target = frozenset({0})

        di.enqueue_from_population_spikes(("e0",), target)
        fired = di.apply_pending(relay, timestep=1)
        self.assertEqual(fired, frozenset())
        self.assertAlmostEqual(
            relay.pairs[0].secondary_excitatory.membrane, 0.08, places=4
        )
        self.assertAlmostEqual(relay.pairs[0].inhibitory.membrane, 0.0)
        self.assertAlmostEqual(relay.pairs[1].secondary_excitatory.membrane, 0.0)

        di.enqueue_from_population_spikes(("e0",), target)
        fired = di.apply_pending(relay, timestep=2)
        self.assertEqual(fired, frozenset())
        self.assertGreater(relay.pairs[0].secondary_excitatory.membrane, 0.08)

    def test_suprathreshold_after_accumulation(self) -> None:
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        di = DescendingInhibition(lif, gain=0.08, afferent_init_weight=1.0)
        target = frozenset({0})

        fired = frozenset()
        for tick in range(1, 6):
            di.enqueue_from_population_spikes(("e0",), target)
            fired = di.apply_pending(relay, timestep=tick)
            if fired:
                break
        self.assertTrue(fired)
        self.assertIn("l1_ep_0", fired)
        self.assertIn("l1_i_0", fired)
        self.assertEqual(relay.pairs[0].inhibitory.register, RegisterState.ONE)

    def test_reset_clears_pending(self) -> None:
        di = DescendingInhibition(LifDynamics(), gain=0.08)
        di.enqueue_from_population_spikes(("e0", "e1"), frozenset({1, 2}))
        di.reset()
        self.assertEqual(di.pending_charge, 0.0)

    def test_protect_grid_indices_skips_shared_cells(self) -> None:
        """Prior-pattern descending must not block relay on current stimulus cells."""
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        di = DescendingInhibition(lif, gain=0.48, afferent_init_weight=1.0)
        h1 = h1_grid_indices()
        v1 = frozenset({1, 4, 7})

        di.enqueue_from_population_spikes(("e0", "e1"), h1)
        fired = di.apply_pending(relay, timestep=1, protect_grid_indices=v1)
        self.assertTrue({"l1_i_3", "l1_i_5"} <= fired)
        self.assertTrue({"l1_ep_3", "l1_ep_5"} <= fired)
        self.assertEqual(relay.pairs[4].inhibitory.register, RegisterState.Z)
        self.assertEqual(relay.pairs[3].inhibitory.register, RegisterState.ONE)
        self.assertEqual(relay.pairs[5].inhibitory.register, RegisterState.ONE)


class DescendingInhibitionEngineTests(unittest.TestCase):
    def test_next_tick_enqueues_then_consumes_pending(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                l2_to_l1_i_gain=0.08,
                pretrained_inhibitor_exclusivity_enabled=False,
            )
        )
        pending_after_spike = 0.0
        for _ in range(12):
            sim.stimulate_pattern(get_line("H1"))
            if sim.nucleus.last_population_spike_ids:
                pending_after_spike = sim._descending.pending_charge
                break
        self.assertGreater(pending_after_spike, 0.0)

        prior = pending_after_spike
        sim._layer1.process_step(
            sim._timestep + 1,
            frozenset(),
            sim._edges,
            descending=sim._descending,
        )
        self.assertEqual(sim._descending.pending_charge, 0.0)
        self.assertGreater(prior, 0.0)

    def test_apply_dynamics_updates_gains(self) -> None:
        sim = BrainSimulator()
        updated = replace(
            sim.dynamics,
            l2_to_l1_i_gain=0.12,
            l1_feedforward_gain=0.50,
        )
        sim.apply_dynamics(updated)
        self.assertAlmostEqual(sim._descending.gain, 0.12)
        for pair in sim.layer1.pairs:
            self.assertAlmostEqual(pair.coupling.feedforward_gain, 0.50)

    def test_reset_clears_engine_pending(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                pretrained_inhibitor_exclusivity_enabled=False,
            )
        )
        for _ in range(40):
            sim.stimulate_pattern(get_line("H1"))
            if sim._descending.pending_charge > 0.0:
                break
        self.assertGreater(sim._descending.pending_charge, 0.0)
        sim.reset()
        self.assertEqual(sim._descending.pending_charge, 0.0)

    def test_pattern_learning_with_descending(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_catalog_line(sim, "H1")
        pattern = get_line("H1")
        owner = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertTrue(str(owner).startswith("nucleus_e_"))

    def test_immediate_l1_i_under_exclusivity(self) -> None:
        """Exclusivity+force: after enough L2E→E′ charge, L1 I force-fires (same tick as E′)."""
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                pretrained_inhibitor_exclusivity_enabled=True,
                descending_mode="force",
                temporal_integration_enabled=False,
                excitatory_flow_rate_enabled=False,
            )
        )
        pattern = get_line("H1")
        saw = False
        for _ in range(120):
            result = sim.stimulate_pattern(pattern)
            if not sim.nucleus.last_population_spike_ids:
                continue
            has_l1_i = any(
                str(event["neuron_id"]).startswith("l1_i_")
                for event in result.step_events
            )
            if has_l1_i:
                saw = True
                break
        self.assertTrue(saw, "expected L1 I after gradual E′ charge under exclusivity")

    def test_population_spike_ids_exposed(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        for _ in range(40):
            sim.stimulate_pattern(get_line("H1"))
            if sim.nucleus.last_population_spike_ids:
                break
        ids = sim.nucleus.last_population_spike_ids
        self.assertTrue(ids)
        central_id = sim.nucleus.central_inhibitor.neuron.id
        self.assertNotIn(central_id, ids)

    def test_l1_inhibitory_fires_under_force_cascade(self) -> None:
        """Labeled force+exclusivity cascade: L1 I fires from descending feedback."""
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                pretrained_inhibitor_exclusivity_enabled=True,
                descending_mode="force",
                temporal_integration_enabled=False,
                excitatory_flow_rate_enabled=False,
            )
        )
        pattern = get_line("H1")
        first_l1_i_tick: int | None = None
        for tick in range(1, 81):
            result = sim.stimulate_pattern(pattern)
            if any(
                str(event["neuron_id"]).startswith("l1_i_")
                for event in result.step_events
            ):
                first_l1_i_tick = tick
                break
        self.assertIsNotNone(
            first_l1_i_tick,
            "L1 I should fire from accumulated L2 descending feedback",
        )
        assert first_l1_i_tick is not None
        self.assertLessEqual(
            first_l1_i_tick,
            80,
            "L1 I should fire within the first 80 Auto-Stim-equivalent steps",
        )

    def test_l1_inhibitory_fires_under_robust_temporal_force_cascade(self) -> None:
        """Full temporal stack under force cascade: L1 I fires within window."""
        from cognative_paradigm.simulation.learning_dynamics import LearningDynamics

        sim = BrainSimulator(
            dynamics=LearningDynamics(
                pretrained_inhibitor_exclusivity_enabled=True,
                descending_mode="force",
            )
        )
        pattern = get_line("H1")
        first_l1_i_tick: int | None = None
        for tick in range(1, 81):
            result = sim.stimulate_pattern(pattern)
            if any(
                str(event["neuron_id"]).startswith("l1_i_")
                for event in result.step_events
            ):
                first_l1_i_tick = tick
                break
        self.assertIsNotNone(
            first_l1_i_tick,
            "L1 I should fire under force+exclusivity temporal dynamics",
        )

    def test_l1_i_does_not_block_l1_e_on_following_pulse(self) -> None:
        """L1 I register must not persist across pulses (would freeze learning)."""
        from cognative_paradigm.simulation.learning_dynamics import LearningDynamics

        sim = BrainSimulator(
            dynamics=LearningDynamics(
                pretrained_inhibitor_exclusivity_enabled=True,
                descending_mode="force",
            )
        )
        pattern = get_line("H1")
        first_l1_i_tick: int | None = None
        relay_after_l1_i: int | None = None
        for tick in range(1, 21):
            result = sim.stimulate_pattern(pattern)
            events = result.step_events
            has_l1_i = any(
                str(event["neuron_id"]).startswith("l1_i_") for event in events
            )
            has_l1_e = any(
                str(event["neuron_id"]).startswith("l1_e_") for event in events
            )
            if has_l1_i and first_l1_i_tick is None:
                first_l1_i_tick = tick
            # Immediate exclusivity may log L1 I after L1 E same pulse; require a
            # later pulse with L1 E to prove I register does not freeze learning.
            if (
                first_l1_i_tick is not None
                and has_l1_e
                and tick > first_l1_i_tick
            ):
                relay_after_l1_i = tick
                break
        self.assertIsNotNone(first_l1_i_tick, "expected L1 I to fire first")
        self.assertIsNotNone(
            relay_after_l1_i,
            "L1 E should relay again on a pulse after L1 I descending inhibition",
        )
        self.assertGreater(
            relay_after_l1_i,
            first_l1_i_tick,
            "relay recovery must be on a later pulse than the first L1 I spike",
        )

    def test_h1_win_does_not_block_v1_center_relay(self) -> None:
        """Rotation H1→V1: shared center cell must relay under V1."""
        from cognative_paradigm.simulation.learning_dynamics import (
            DEFAULT_LEARNING_DYNAMICS,
        )

        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        h1 = get_line("H1")
        v1 = get_line("V1")
        saw_h1_win = False
        for _ in range(40):
            sim.stimulate_pattern(h1)
            if sim.nucleus.last_population_spike_ids:
                saw_h1_win = True
                break
        self.assertTrue(saw_h1_win, "expected H1 nucleus population spike")

        result = sim.stimulate_pattern(v1)
        l1e = [
            str(event["neuron_id"])
            for event in result.step_events
            if str(event.get("neuron_id", "")).startswith("l1_e_")
        ]
        self.assertIn("l1_e_4", l1e)
        self.assertIn("l1_e_1", l1e)
        self.assertIn("l1_e_7", l1e)


if __name__ == "__main__":
    unittest.main()
