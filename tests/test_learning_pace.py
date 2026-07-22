"""Learning pace: binds should not appear instantly on the raster timeline."""

from __future__ import annotations

import unittest

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import LINE_IDS, get_line, pattern_from_indices
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import (
    interleaved_learn_all,
    ownership_owner_ids,
    unguided_ecological_dynamics,
)


class LearningPaceTests(unittest.TestCase):
    def test_ecological_first_bind_not_instant(self) -> None:
        """First PATTERN_BOUND should appear after sustained rotation."""
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        first_bind: int | None = None

        for round_index in range(200):
            line_id = LINE_IDS[round_index % len(LINE_IDS)]
            result = sim.stimulate_pattern(get_line(line_id))
            if any(
                event.get("type") == EventType.PATTERN_BOUND.name
                for event in result.step_events
            ):
                first_bind = round_index + 1
                break

        self.assertIsNotNone(first_bind)
        self.assertGreaterEqual(
            first_bind,
            18,
            "first bind too early for gradual raster-visible learning",
        )

    def test_ecological_equilibrium_requires_many_rotations(self) -> None:
        sim = BrainSimulator(
            dynamics=unguided_ecological_dynamics()
        )
        steps = interleaved_learn_all(sim, max_rounds=120)
        self.assertGreaterEqual(steps, 28)
        self.assertLessEqual(steps, 80)
        self.assertEqual(len(ownership_owner_ids(sim)), len(LINE_IDS))

    def test_single_pattern_hold_bind_is_gradual(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        pattern = pattern_from_indices([0, 1, 2])
        bind_pulse: int | None = None

        for pulse in range(80):
            result = sim.stimulate_pattern(pattern)
            if any(
                event.get("type") == EventType.PATTERN_BOUND.name
                for event in result.step_events
            ):
                bind_pulse = pulse + 1
                break

        self.assertIsNotNone(bind_pulse)
        self.assertGreaterEqual(bind_pulse, 12)
        self.assertLessEqual(bind_pulse, 80)


if __name__ == "__main__":
    unittest.main()
