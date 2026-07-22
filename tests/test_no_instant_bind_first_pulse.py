"""No PATTERN_BOUND on the first pulse (Phase 3 acceptance)."""

from __future__ import annotations

import unittest
from dataclasses import replace

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS


def _first_pulse_bound(sim: BrainSimulator) -> bool:
    sim.stimulate_pattern(get_line(LINE_IDS[0]))
    return any(
        entry["type"] == EventType.PATTERN_BOUND.name
        for entry in sim.event_log.entries
    )


class NoInstantBindTests(unittest.TestCase):
    def test_production_never_binds_first_pulse(self) -> None:
        for seed in (0, 7, 42):
            dynamics = replace(DEFAULT_LEARNING_DYNAMICS, wta_rng_seed=seed)
            sim = BrainSimulator(dynamics=dynamics)
            self.assertFalse(_first_pulse_bound(sim), f"seed={seed}")

    def test_dual_eligibility_never_binds_first_pulse(self) -> None:
        for seed in (0, 7, 42):
            dynamics = replace(
                DEFAULT_LEARNING_DYNAMICS,
                dual_eligibility_enabled=True,
                wta_rng_seed=seed,
                pretrained_inhibitor_exclusivity_enabled=False,
            )
            sim = BrainSimulator(dynamics=dynamics)
            self.assertFalse(_first_pulse_bound(sim), f"seed={seed}")


if __name__ == "__main__":
    unittest.main()
