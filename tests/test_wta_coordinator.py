"""Neuron-level WTA: no coordinator winner pick, same-tick central inhibition."""

import unittest

from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.simulation.central_inhibitor import CentralInhibitoryNeuron
from cognative_paradigm.simulation.nucleus_ring_competitor import (
    NUCLEUS_RING_SIZE,
    NucleusRingCompetitor,
)
from cognative_paradigm.simulation.wta_coordinator import WtaCoordinator


class WtaCoordinatorTests(unittest.TestCase):
    def test_strongest_membrane_spikes_without_index_tie_break(self) -> None:
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=0.5)
        wta = WtaCoordinator(lif, central, collateral_gain=0.5, membrane_noise_std=0.0)

        ring = [NucleusRingCompetitor(index, relay_weight=0.2) for index in range(NUCLEUS_RING_SIZE)]
        relay_ids = frozenset({"l1_e_0", "l1_e_1", "l1_e_2"})

        for competitor in ring:
            competitor.neuron.membrane = 1.0
        ring[NUCLEUS_RING_SIZE - 1].neuron.membrane = 1.5

        outcome = wta.run(ring, relay_ids, timestep=1, skip_integration=True)
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertEqual(outcome.winner.ring_index, NUCLEUS_RING_SIZE - 1)
        self.assertEqual(
            outcome.population_spike_ids,
            (f"nucleus_e_{NUCLEUS_RING_SIZE - 1}",),
        )

    def test_soft_stagger_strongest_spikes_then_ni_blocks_cofire(self) -> None:
        """Clear-leader soft race: strongest spikes, NI suppress blocks same-tick co-fire."""
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=0.2, inhibition_strength=1.1)
        wta = WtaCoordinator(
            lif,
            central,
            collateral_gain=1.0,
            membrane_noise_std=0.0,
            pretrained_exclusivity=False,
        )
        ring = [NucleusRingCompetitor(index, relay_weight=0.2) for index in range(4)]
        for competitor in ring:
            competitor.neuron.membrane = 1.2
        ring[2].neuron.membrane = 1.8
        central.neuron.membrane = 0.19

        outcome = wta.run(
            ring,
            frozenset({"l1_e_0"}),
            timestep=1,
            skip_integration=True,
        )
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertTrue(outcome.central_fired)
        self.assertEqual(outcome.population_spike_ids, ("nucleus_e_2",))
        self.assertEqual(outcome.winner.ring_index, 2)
        for index, competitor in enumerate(ring):
            if index == 2:
                continue
            self.assertLess(
                competitor.neuron.membrane,
                competitor.neuron.threshold,
                msg=f"loser {index} should be subthreshold after soft NI",
            )

    def test_soft_tight_pack_may_multi_spike_when_ni_quiet(self) -> None:
        """Near-tie pack may multi-spike (no clear-leader mid-loop NI)."""
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=5.0, inhibition_strength=1.1)
        wta = WtaCoordinator(
            lif,
            central,
            collateral_gain=0.1,
            membrane_noise_std=0.0,
            pretrained_exclusivity=False,
        )
        ring = [NucleusRingCompetitor(index, relay_weight=0.2) for index in range(3)]
        for competitor in ring:
            competitor.neuron.membrane = 1.2
        ring[1].neuron.membrane = 1.21  # gap < soft-stagger leader gap

        outcome = wta.run(
            ring,
            frozenset({"l1_e_0"}),
            timestep=1,
            skip_integration=True,
        )
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertGreaterEqual(len(outcome.population_spike_ids), 2)

    def test_central_inhibition_suppresses_losers_same_tick(self) -> None:
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=0.15, inhibition_strength=0.9)
        wta = WtaCoordinator(
            lif,
            central,
            collateral_gain=1.0,
            membrane_noise_std=0.0,
            pretrained_exclusivity=True,
        )

        ring = [NucleusRingCompetitor(index, relay_weight=0.2) for index in range(3)]
        relay_ids = frozenset({"l1_e_0"})

        # Only one authentic candidate above θ; losers stay subthreshold.
        ring[0].neuron.membrane = 1.5
        ring[1].neuron.membrane = 1.0
        ring[2].neuron.membrane = 1.0

        outcome = wta.run(ring, relay_ids, timestep=1, skip_integration=True)
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertTrue(outcome.central_fired)
        self.assertEqual(outcome.population_spike_ids, ("nucleus_e_0",))
        self.assertEqual(ring[1].neuron.membrane, 0.0)
        self.assertEqual(ring[2].neuron.membrane, 0.0)

    def test_central_accumulates_from_ring_before_winner_spike(self) -> None:
        from cognative_paradigm.lines import get_line
        from cognative_paradigm.simulation.engine import BrainSimulator
        from tests.simulation_helpers import deterministic_dynamics

        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                relay_weight_init_spread=0.0,
                central_pool_gain=0.62,
                central_competition_ni_discharge_fraction=1.0,
            ),
        )
        pattern = get_line("H1")
        buildup: list[float] = []
        fire_tick: int | None = None
        for tick in range(1, 80):
            result = sim.stimulate_pattern(pattern)
            state = sim.get_state()["nucleus"]
            buildup.append(state["central_inhibitor_membrane"])
            if state["wta_central_fired"] and fire_tick is None:
                fire_tick = tick
                # Soft race: NI may discharge from competition pool before/without
                # a same-tick ring-E SPIKE; accept NI SPIKE or ring-E SPIKE.
                ni_or_ring = [
                    event["neuron_id"]
                    for event in result.step_events
                    if event.get("type") == "SPIKE"
                    and (
                        str(event["neuron_id"]).startswith("nucleus_e_")
                        or event["neuron_id"] == "nucleus_i"
                    )
                ]
                self.assertGreaterEqual(len(ni_or_ring), 1)
        self.assertGreater(max(buildup[:5]), 0.05, "central I should charge from ring E")
        # With raw I(d) drive scaling, NI charge rises sharply in the first
        # few ticks; later ticks may already reflect post-fire reset.
        self.assertLess(
            buildup[0],
            max(buildup[1:4]),
            "central I membrane should rise while ring E integrate",
        )
        self.assertIsNotNone(fire_tick)

    def test_losers_suppressed_when_central_i_fires(self) -> None:
        from cognative_paradigm.lines import get_line
        from cognative_paradigm.simulation.engine import BrainSimulator
        from tests.simulation_helpers import deterministic_dynamics

        # Explicit strong NI (production defaults are now 1.0 / 0.62).
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                central_competition_ni_discharge_fraction=1.0,
                central_pool_gain=0.62,
            )
        )
        pattern = get_line("H1")
        reductions = 0
        samples = 0
        for _ in range(500):
            pre = [c.neuron.membrane for c in sim.nucleus.ring]
            sim.stimulate_pattern(pattern)
            state = sim.get_state()["nucleus"]
            if not state.get("wta_central_fired"):
                continue
            ring_spikes = [n for n in state["ring"] if n["register"] == "1"]
            if not ring_spikes:
                continue
            samples += 1
            loser_entries = [n for n in state["ring"] if n["register"] != "1"]
            if not loser_entries:
                continue
            # NI-fired channel×scale should reduce at least one non-spiker
            # relative to its pre-pulse membrane (no absolute 0.42 floor).
            reduced = any(
                entry["membrane"] < pre[i]
                for i, entry in enumerate(state["ring"])
                if entry["register"] != "1"
            )
            if reduced:
                reductions += 1
        self.assertGreater(samples, 0, "expected some NI-fired spikes")
        self.assertGreater(
            reductions,
            0,
            "when central I fires, channel suppression should reduce losers",
        )

    def test_all_ring_neurons_enter_wta_when_some_are_bound(self) -> None:
        from cognative_paradigm.lines import get_line
        from cognative_paradigm.simulation.engine import BrainSimulator
        from tests.simulation_helpers import deterministic_dynamics, learn_catalog_line

        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_catalog_line(sim, "H1")
        bound = [c for c in sim.nucleus.ring if c.neuron.memory.is_bound()]
        self.assertGreater(len(bound), 0)

        sim.stimulate_pattern(get_line("H1"))
        registers = [c.neuron.register.name for c in sim.nucleus.ring]
        population = set(sim.nucleus.last_population_spike_ids)
        ones = {
            competitor.neuron.id
            for competitor in sim.nucleus.ring
            if competitor.neuron.register.name == "ONE"
        }
        self.assertEqual(ones, population)
        self.assertLessEqual(registers.count("ONE"), NUCLEUS_RING_SIZE)


if __name__ == "__main__":
    unittest.main()
