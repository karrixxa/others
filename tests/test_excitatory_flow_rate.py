"""Excitatory flow-rate trace and inhibitory turnover plasticity."""

import unittest
from dataclasses import replace

from cognative_paradigm.domain.excitatory_flow_trace import ExcitatoryFlowTrace
from cognative_paradigm.domain.neuron import Neuron
from cognative_paradigm.learning.inhibitory_turnover import (
    InhibitoryTurnoverConfig,
    InhibitoryTurnoverPlasticity,
)
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics
from cognative_paradigm.lines import get_line


class ExcitatoryFlowTraceTests(unittest.TestCase):
    def test_lazy_advance_matches_dense_steps(self) -> None:
        decay = 0.8
        drive = 1.0
        lazy_neuron = Neuron(id="lazy", threshold=99.0)
        lazy_trace = ExcitatoryFlowTrace(decay=decay, normalized=True)
        lazy_trace.receive_drive(lazy_neuron, drive, t=1)

        lazy_trace.advance_to(lazy_neuron, t=5)

        dense_voltage = drive * (1.0 - decay)
        dense_current = drive * (1.0 - decay) * decay
        for _ in range(4):
            dense_voltage += dense_current
            dense_current *= decay

        self.assertAlmostEqual(lazy_neuron.membrane, dense_voltage, places=6)

    def test_residual_current_crosses_threshold_without_new_input(self) -> None:
        neuron = Neuron(id="flow", threshold=0.5)
        trace = ExcitatoryFlowTrace(decay=0.8, normalized=True)
        trace.receive_drive(neuron, drive=1.0, t=1)
        neuron.membrane = 0.0
        trace.advance_to(neuron, t=6)
        self.assertGreaterEqual(neuron.membrane, neuron.threshold)

    def test_spike_discharge_clears_trace(self) -> None:
        trace = ExcitatoryFlowTrace(decay=0.8)
        neuron = Neuron(id="n", threshold=2.0)
        trace.receive_drive(neuron, 1.0, t=1)
        trace.discharge()
        self.assertEqual(trace.trace, 0.0)


class InhibitoryTurnoverTests(unittest.TestCase):
    def test_high_charge_target_strengthens_more_than_weak_target(self) -> None:
        turnover = InhibitoryTurnoverPlasticity(
            InhibitoryTurnoverConfig(i_max_weight=1.21)
        )
        theta = 1.0
        weak = turnover.update_channel(0.5, v_pre=0.2, theta=theta)
        strong = turnover.update_channel(0.5, v_pre=0.9, theta=theta)
        self.assertGreater(strong, weak)

    def test_turnover_spreads_channels_under_repeated_inhibition(self) -> None:
        turnover = InhibitoryTurnoverPlasticity(
            InhibitoryTurnoverConfig(i_max_weight=1.21)
        )
        theta = 1.27
        weak_channel = 0.5
        strong_channel = 0.5
        for _ in range(30):
            weak_channel = turnover.update_channel(weak_channel, v_pre=0.15, theta=theta)
            strong_channel = turnover.update_channel(
                strong_channel, v_pre=1.1, theta=theta
            )
        spread = strong_channel - weak_channel
        self.assertGreater(spread, 0.05)


class FlowRateIntegrationTests(unittest.TestCase):
    def test_flow_controller_enabled_by_default(self) -> None:
        sim = BrainSimulator()
        self.assertTrue(sim.nucleus.exc_flow.enabled)

    def test_temporal_plus_flow_builds_subthreshold_charge_without_runaway(self) -> None:
        base_dynamics = LearningDynamics(
            temporal_integration_enabled=True,
            sim_dt_ms=1.0,
            stim_duration_ms=40.0,
            auto_stim_interval_ms=1000,
            membrane_noise_std=0.0,
            wta_rng_seed=7,
            relay_weight_init_spread=0.0,
            sensory_weight_init_spread=0.0,
        )
        temporal_only = BrainSimulator(
            dynamics=replace(base_dynamics, excitatory_flow_rate_enabled=False)
        )
        temporal_flow = BrainSimulator(
            dynamics=replace(base_dynamics, excitatory_flow_rate_enabled=True)
        )
        pattern = get_line("H1")

        temporal_only.step(pattern)
        temporal_flow.step(pattern)

        only_membrane = max(c.neuron.membrane for c in temporal_only.nucleus.ring)
        flow_membrane = max(c.neuron.membrane for c in temporal_flow.nucleus.ring)
        self.assertGreater(only_membrane, 0.05)
        self.assertGreater(flow_membrane, 0.05)
        self.assertLess(flow_membrane, temporal_only.nucleus.ring[0].neuron.threshold * 1.5)


if __name__ == "__main__":
    unittest.main()
