"""Temporal integration: inter-pulse silence leak and sustained stimulus sub-steps."""

import unittest

from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics
from cognative_paradigm.simulation.simulation_clock import SimulationClock
from cognative_paradigm.lines import get_line


class TemporalIntegrationTests(unittest.TestCase):
    def test_clock_disabled_is_legacy_single_tick(self) -> None:
        clock = SimulationClock.from_dynamics(
            LearningDynamics(temporal_integration_enabled=False)
        )
        self.assertFalse(clock.temporal_integration_enabled)
        self.assertEqual(clock.stim_sub_steps(), 1)
        self.assertEqual(clock.silence_sub_steps(), 0)

    def test_silence_dt_matches_per_ms_stim_integration(self) -> None:
        clock = SimulationClock.from_dynamics(
            LearningDynamics(
                temporal_integration_enabled=True,
                sim_dt_ms=1.0,
                stim_duration_ms=40.0,
                auto_stim_interval_ms=1000,
            )
        )
        self.assertEqual(clock.silence_dt_scale(), clock.stim_dt_scale())
        self.assertEqual(clock.silence_sub_steps(), 960)

    def test_silence_leak_reduces_membrane_between_pulses(self) -> None:
        dynamics = LearningDynamics(
            temporal_integration_enabled=True,
            excitatory_flow_rate_enabled=False,
            inhibitory_flow_rate_enabled=False,
            sim_dt_ms=1.0,
            stim_duration_ms=10.0,
            auto_stim_interval_ms=100,
            membrane_tau=8.5,
            inter_pulse_leak_scale=0.042,
        )
        sim = BrainSimulator(dynamics=dynamics)
        pattern = get_line("H1")

        for _ in range(7):
            sim.step(pattern)

        charged = max(
            competitor.neuron.membrane for competitor in sim.nucleus.ring
        )
        clock = SimulationClock.from_dynamics(dynamics)
        sim._advance_inter_pulse_silence(clock)
        after_leak = max(
            competitor.neuron.membrane for competitor in sim.nucleus.ring
        )

        self.assertGreater(charged, 0.0)
        self.assertLess(after_leak, charged)

    def test_sustained_stim_substeps_increase_charge_faster(self) -> None:
        discrete = BrainSimulator(
            dynamics=LearningDynamics(temporal_integration_enabled=False)
        )
        sustained = BrainSimulator(
            dynamics=LearningDynamics(
                temporal_integration_enabled=True,
                sim_dt_ms=1.0,
                stim_duration_ms=40.0,
                auto_stim_interval_ms=1000,
            )
        )
        pattern = get_line("H1")

        discrete.step(pattern)
        sustained.step(pattern)

        discrete_membrane = sum(
            competitor.neuron.membrane for competitor in discrete.nucleus.ring
        )
        sustained_membrane = sum(
            competitor.neuron.membrane for competitor in sustained.nucleus.ring
        )

        self.assertGreater(sustained_membrane, discrete_membrane)


if __name__ == "__main__":
    unittest.main()
