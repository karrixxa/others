"""Pulse energy frames and competition-gated NI (channel×scale)."""

import unittest
from dataclasses import replace

from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.central_inhibitor import CentralInhibitoryNeuron
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from cognative_paradigm.simulation.nucleus_ring_competitor import NucleusRingCompetitor
from cognative_paradigm.simulation.wta_coordinator import WtaCoordinator


class CompetitionGatedNiTests(unittest.TestCase):
    def test_ni_channel_scale_depletes_losers_without_pool_boost(self) -> None:
        """Pure channel×scale loser drop when NI fires; no competition_pool_boost."""
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=0.15, inhibition_strength=0.9)
        wta = WtaCoordinator(lif, central, collateral_gain=1.0, membrane_noise_std=0.0)

        ring = [NucleusRingCompetitor(index, relay_weight=0.2) for index in range(3)]
        relay_ids = frozenset({"l1_e_0"})
        ring[0].neuron.membrane = 1.5
        ring[1].neuron.membrane = 1.0
        ring[2].neuron.membrane = 1.0
        pre_losers = (ring[1].neuron.membrane, ring[2].neuron.membrane)

        outcome = wta.run(ring, relay_ids, timestep=1, skip_integration=True)
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertTrue(outcome.central_fired)
        self.assertEqual(outcome.population_spike_ids, ("nucleus_e_0",))
        self.assertLess(ring[1].neuron.membrane, pre_losers[0])
        self.assertLess(ring[2].neuron.membrane, pre_losers[1])
        self.assertEqual(set(outcome.inhibited_ring_indices), {1, 2})

    def test_functional_ni_spares_empty_set(self) -> None:
        """Functional NI applies channel×scale to all targets (spared=∅)."""
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=0.2, inhibition_strength=1.0)
        wta = WtaCoordinator(lif, central, collateral_gain=0.5, membrane_noise_std=0.0)

        ring = [NucleusRingCompetitor(index, relay_weight=0.2) for index in range(3)]
        relay_ids = frozenset({"l1_e_0"})
        # Parallel pack below θ_E but hot enough to trigger functional NI.
        for competitor in ring:
            competitor.neuron.membrane = 0.98
        central.neuron.membrane = 1.2

        outcome = wta.run(
            ring,
            relay_ids,
            timestep=1,
            skip_integration=True,
            competition_hot_fraction=0.88,
            competition_ni_discharge_fraction=0.5,
        )
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertTrue(outcome.central_fired)
        self.assertEqual(outcome.population_spike_ids, ())
        self.assertEqual(set(outcome.inhibited_ring_indices), {0, 1, 2})

    def test_gradual_ni_without_forced_boost(self) -> None:
        """Without pool boost, NI must not fire on nearly every pulse."""
        sim = BrainSimulator(
            dynamics=replace(
                DEFAULT_LEARNING_DYNAMICS,
                central_competition_ni_discharge_fraction=1.0,
                membrane_noise_std=0.0,
            )
        )
        fires = 0
        for _ in range(15):
            sim.stimulate_pattern(get_line("H1"))
            if sim.get_state()["nucleus"].get("wta_central_fired"):
                fires += 1
        self.assertLess(fires, 8, "without pool boost NI should not fire most pulses")


class PulseEnergyRecorderTests(unittest.TestCase):
    def test_stimulate_emits_fractional_energy_frames(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        result = sim.stimulate_pattern(get_line("H1"))
        frames = result.energy_frames
        self.assertGreater(len(frames), 1)
        fractions = [frame["t_frac"] for frame in frames]
        self.assertGreater(len(frames), 1)
        self.assertLess(len(frames), 16)
        self.assertAlmostEqual(fractions[-1], 1.0, places=4)
        self.assertIn("ring", frames[-1]["nucleus"])
        self.assertIn("central_inhibitor_raster_charge", frames[-1]["nucleus"])

    def test_final_l2_charge_uses_stim_dt_not_full_tick(self) -> None:
        """Within-pulse Σ dt_scale must equal 1.0 (no final-step 40× dump)."""
        dynamics = replace(
            DEFAULT_LEARNING_DYNAMICS,
            excitatory_flow_rate_enabled=False,
            relay_weight_init_spread=0.0,
            membrane_noise_std=0.0,
        )
        sim = BrainSimulator(dynamics=dynamics)
        broadcast = sim.nucleus._relay_broadcast
        original = broadcast.apply_ring_charge
        dt_scales: list[float] = []

        def spy(ring, relay_ids, timestep, **kwargs):
            dt_scales.append(float(kwargs.get("dt_scale", 1.0)))
            return original(ring, relay_ids, timestep, **kwargs)

        broadcast.apply_ring_charge = spy  # type: ignore[method-assign]
        sim.stimulate_pattern(get_line("H1"))

        self.assertGreaterEqual(len(dt_scales), 2)
        self.assertAlmostEqual(sum(dt_scales), 1.0, places=6)
        self.assertAlmostEqual(dt_scales[-1], dt_scales[0], places=6)
        # One legacy tick of charge ≈ D·1 with mild leak — not ~2× from a final dt=1 dump.
        self.assertLess(sim.nucleus.ring[0].neuron.membrane, 0.30)
        self.assertGreater(sim.nucleus.ring[0].neuron.membrane, 0.15)


if __name__ == "__main__":
    unittest.main()
