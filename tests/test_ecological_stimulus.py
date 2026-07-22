"""Mastery auto-stim: hold until bind, advance, then random probe."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from cognative_paradigm.api.main import app
from cognative_paradigm.domain.pattern_memory_snapshot import PatternMemorySnapshot
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.stimulus_stream import (
    MasteryAutoStimScheduler,
    MasteryPhase,
    RotatingStimulusStream,
    StochasticStimulusStream,
    create_stimulus_stream,
)
from tests.simulation_helpers import biology_dynamics


class StimulusStreamUnitTests(unittest.TestCase):
    def test_rotation_cycles_catalog(self) -> None:
        stream = RotatingStimulusStream()
        seen = [stream.next_line_id(index) for index in range(8)]
        self.assertEqual(seen[:4], list(LINE_IDS))
        self.assertEqual(seen[4], LINE_IDS[0])

    def test_rotation_holds_shape_for_multiple_pulses(self) -> None:
        stream = RotatingStimulusStream(hold_steps=5)
        seen = [stream.next_line_id(index) for index in range(12)]
        self.assertEqual(seen[:5], [LINE_IDS[0]] * 5)
        self.assertEqual(seen[5:10], [LINE_IDS[1]] * 5)
        self.assertEqual(seen[10], LINE_IDS[2])

    def test_stochastic_does_not_import_ownership(self) -> None:
        import cognative_paradigm.simulation.stimulus_stream as module

        source = open(module.__file__, encoding="utf-8").read()
        self.assertNotIn("PatternOwnership", source)

    def test_create_stimulus_stream_modes(self) -> None:
        self.assertIsInstance(
            create_stimulus_stream("rotation"),
            RotatingStimulusStream,
        )
        self.assertIsInstance(
            create_stimulus_stream("stochastic"),
            StochasticStimulusStream,
        )
        self.assertIsInstance(
            create_stimulus_stream("mastery"),
            MasteryAutoStimScheduler,
        )


class MasterySchedulerTests(unittest.TestCase):
    def test_hold_until_learned_then_advance(self) -> None:
        sim = BrainSimulator(
            dynamics=biology_dynamics(
                eligibility_threshold=0.75,
                consolidation_weight_threshold=0.15,
            ),
        )
        scheduler = MasteryAutoStimScheduler()
        ownership = sim.nucleus.pattern_ownership
        self.assertIsInstance(ownership, PatternMemorySnapshot)

        learning_lines: list[str] = []
        while not ownership.owner_for_pattern(get_line(LINE_IDS[0]).edge_ids):
            line_id = scheduler.resolve_line_id(ownership)
            self.assertIsNotNone(line_id)
            learning_lines.append(line_id)
            sim.stimulate_pattern(get_line(line_id))

        self.assertGreater(len(learning_lines), 0)
        self.assertTrue(all(line == LINE_IDS[0] for line in learning_lines))

        next_line = scheduler.resolve_line_id(ownership)
        self.assertEqual(next_line, LINE_IDS[1])
        self.assertEqual(scheduler.phase, MasteryPhase.LEARNING)

    def test_enters_random_probe_after_catalog(self) -> None:
        sim = BrainSimulator(
            dynamics=biology_dynamics(
                eligibility_threshold=0.75,
                consolidation_weight_threshold=0.15,
            ),
        )
        scheduler = MasteryAutoStimScheduler(rng=__import__("random").Random(0))
        ownership = sim.nucleus.pattern_ownership

        for _ in range(800):
            line_id = scheduler.resolve_line_id(ownership)
            self.assertIsNotNone(line_id)
            sim.stimulate_pattern(get_line(line_id))
            if scheduler.phase is MasteryPhase.PROBE:
                break

        self.assertEqual(scheduler.phase, MasteryPhase.PROBE)
        self.assertEqual(len(ownership.as_dict()), len(LINE_IDS))

        probe_lines = [scheduler.resolve_line_id(ownership) for _ in range(20)]
        self.assertTrue(all(line in LINE_IDS for line in probe_lines))
        self.assertGreater(len(set(probe_lines)), 1)

    def test_legacy_complete_checkpoint_maps_to_probe(self) -> None:
        scheduler = MasteryAutoStimScheduler(rng=__import__("random").Random(1))
        scheduler.restore(
            {
                "catalog_index": 3,
                "phase": "complete",
                "current_line_id": None,
            }
        )
        self.assertEqual(scheduler.phase, MasteryPhase.PROBE)
        line_id = scheduler.resolve_line_id(PatternMemorySnapshot(lambda: []))
        self.assertIn(line_id, LINE_IDS)


class AutoStimApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_default_mastery_holds_same_line_until_learned(self) -> None:
        self.client.post("/api/reset")
        params = self.client.get("/api/parameters").json()
        self.assertEqual(params.get("ecological_stimulus_mode"), "mastery")
        self.assertNotIn("auto_stim_post_bind_pulses", params)

        lines: list[str | None] = []
        for _ in range(30):
            response = self.client.post("/api/stimulate", json={})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            lines.append(body.get("line_id"))
            training = body.get("training") or {}
            if training.get("learned_line_ids"):
                break

        first = lines[0]
        self.assertIsNotNone(first)
        self.assertTrue(all(line == first for line in lines))

    def test_rotation_mode_hold_then_rotates(self) -> None:
        self.client.post("/api/reset")
        self.client.patch(
            "/api/parameters",
            json={"ecological_stimulus_mode": "rotation"},
        )

        lines: list[str | None] = []
        for _ in range(12):
            response = self.client.post("/api/stimulate", json={})
            self.assertEqual(response.status_code, 200)
            lines.append(response.json().get("line_id"))

        self.assertEqual(lines[:5], [LINE_IDS[0]] * 5)
        self.assertEqual(lines[5:10], [LINE_IDS[1]] * 5)
        self.assertEqual(lines[10], LINE_IDS[2])


if __name__ == "__main__":
    unittest.main()
