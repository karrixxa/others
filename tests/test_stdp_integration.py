"""STDP timing integration through nucleus plasticity path."""

from __future__ import annotations

import unittest
from dataclasses import replace

from cognative_paradigm.lines import get_line
from cognative_paradigm.learning.spike_timing_context import (
    build_pulse_timing,
    uses_spike_timing,
)
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS


class SpikeTimingContextTests(unittest.TestCase):
    def test_causal_ordering_within_pulse(self) -> None:
        active = frozenset({"input_r1_c1"})
        relays = frozenset({"l1_e_4"})
        ctx = build_pulse_timing(
            active_ids=active,
            relay_ids=relays,
            pulse_onset_ms=100.0,
            post_spike_ms=140.0,
            stim_duration_ms=40.0,
        )
        self.assertLess(ctx.pre_spike_times_ms["input_r1_c1"], ctx.post_spike_time_ms)
        self.assertLess(ctx.pre_spike_times_ms["l1_e_4"], ctx.post_spike_time_ms)

    def test_mode_gate(self) -> None:
        self.assertFalse(uses_spike_timing("conductance"))
        self.assertTrue(uses_spike_timing("stdp"))
        self.assertTrue(uses_spike_timing("triplet"))


class StdpIntegrationTests(unittest.TestCase):
    def test_stdp_mode_stimulates_without_error(self) -> None:
        dynamics = replace(
            DEFAULT_LEARNING_DYNAMICS,
            plasticity_mode="stdp",
            pretrained_inhibitor_exclusivity_enabled=False,
        )
        sim = BrainSimulator(dynamics=dynamics)
        before = sim.nucleus.ring[0].sensory_conductances.as_dict()
        for _ in range(20):
            sim.stimulate_pattern(get_line("H1"))
        after = sim.nucleus.ring[0].sensory_conductances.as_dict()
        self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
