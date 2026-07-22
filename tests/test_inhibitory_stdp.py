"""Inhibitory STDP and plastic NI channel tests (Phase 4)."""

from __future__ import annotations

import unittest
from dataclasses import replace

import pytest

from cognative_paradigm.learning.inhibitory_stdp import (
    InhibitorySTDP,
    InhibitorySTDPConfig,
    VogelsInhibitorySTDP,
)
from cognative_paradigm.learning.lab_profile import BiologicalLabProfileFactory
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics
from tests.simulation_helpers import deterministic_dynamics, unguided_ecological_dynamics


class InhibitorySTDPUnitTests(unittest.TestCase):
    def test_vogels_i_spike_uses_post_trace_minus_alpha(self) -> None:
        stdp = VogelsInhibitorySTDP(
            InhibitorySTDPConfig(eta=0.01, alpha=0.1)
        )
        weight = stdp.on_excitatory_spike(0, 1.0, time_ms=0.0)
        updated = stdp.on_inhibitory_spike(0, weight, time_ms=1.0)
        self.assertGreater(updated, weight)

    def test_vogels_e_spike_uses_pre_trace(self) -> None:
        stdp = VogelsInhibitorySTDP(InhibitorySTDPConfig(eta=0.01))
        weight = stdp.on_inhibitory_spike(0, 1.0, time_ms=0.0)
        updated = stdp.on_excitatory_spike(0, weight, time_ms=1.0)
        self.assertGreater(updated, weight)

    def test_i_after_e_potentiates(self) -> None:
        stdp = InhibitorySTDP(InhibitorySTDPConfig(w_max=2.0, w_min=0.1))
        updated = stdp.update_channel(
            1.0,
            delta_t_ms=5.0,
            v_pre=1.2,
            theta=1.0,
        )
        self.assertGreater(updated, 1.0)

    def test_cold_loser_unchanged(self) -> None:
        stdp = InhibitorySTDP()
        updated = stdp.update_channel(
            1.0,
            delta_t_ms=5.0,
            v_pre=0.01,
            theta=1.0,
        )
        self.assertEqual(updated, 1.0)


class PlasticNIIntegrationTests(unittest.TestCase):
    def test_production_exclusivity_keeps_channels_frozen(self) -> None:
        dynamics = deterministic_dynamics(
            pretrained_inhibitor_exclusivity_enabled=True,
            inhibitory_turnover_enabled=True,
            plastic_ni_enabled=False,
        )
        sim = BrainSimulator(dynamics=dynamics)
        before = list(sim.nucleus.central_inhibitor.inhibition_channels)
        for _ in range(25):
            sim.stimulate_pattern(get_line("H1"))
        after = list(sim.nucleus.central_inhibitor.inhibition_channels)
        self.assertEqual(before, after)

    def test_plastic_ni_lab_channels_can_change(self) -> None:
        dynamics = replace(
            unguided_ecological_dynamics(),
            plastic_ni_enabled=True,
            inhibitory_stdp_enabled=True,
            inhibitory_turnover_enabled=True,
            pretrained_inhibitor_exclusivity_enabled=False,
        )
        sim = BrainSimulator(dynamics=dynamics)
        before = list(sim.nucleus.central_inhibitor.inhibition_channels)
        self.assertTrue(all(w < dynamics.i_max_weight for w in before))
        peak = max(before)
        for _ in range(40):
            sim.stimulate_pattern(get_line("H1"))
            peak = max(peak, max(sim.nucleus.central_inhibitor.inhibition_channels))
        self.assertGreater(peak, before[0])

    @pytest.mark.biological_lab
    def test_soft_full_lab_stack_reaches_three_of_four(self) -> None:
        dynamics = BiologicalLabProfileFactory.dynamics("FULL")
        sim = BrainSimulator(dynamics=dynamics)
        for pulse in range(240):
            sim.stimulate_pattern(get_line(LINE_IDS[pulse % len(LINE_IDS)]))
            learned = sum(
                bool(
                    sim.nucleus.pattern_ownership.owner_for_pattern(
                        get_line(line_id).edge_ids
                    )
                )
                for line_id in LINE_IDS
            )
            if learned >= 3:
                break
        self.assertGreaterEqual(learned, 3)


if __name__ == "__main__":
    unittest.main()
