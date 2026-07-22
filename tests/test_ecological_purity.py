"""Ecological purity: strict unguided stimulus paths must not read ownership."""

from __future__ import annotations

import unittest

from cognative_paradigm.lines import LINE_IDS
from cognative_paradigm.simulation.stimulus_stream import (
    MasteryAutoStimScheduler,
    ReplayStimulusStream,
    RotatingStimulusStream,
    StochasticStimulusStream,
)


def _module_source(module_name: str) -> str:
    import importlib

    module = importlib.import_module(module_name)
    return open(module.__file__, encoding="utf-8").read()


class EcologicalPurityTests(unittest.TestCase):
    def test_rotation_stream_does_not_import_ownership(self) -> None:
        source = _module_source("cognative_paradigm.simulation.stimulus_stream")
        rotation_block = source.split("class RotatingStimulusStream")[1].split(
            "class StochasticStimulusStream"
        )[0]
        self.assertNotIn("PatternMemorySnapshot", rotation_block)
        self.assertNotIn("owner_for_pattern", rotation_block)

    def test_stochastic_stream_does_not_import_ownership(self) -> None:
        source = _module_source("cognative_paradigm.simulation.stimulus_stream")
        stochastic_block = source.split("class StochasticStimulusStream")[1].split(
            "class MasteryPhase"
        )[0]
        self.assertNotIn("PatternMemorySnapshot", stochastic_block)
        self.assertNotIn("owner_for_pattern", stochastic_block)

    def test_replay_stream_does_not_import_ownership(self) -> None:
        source = _module_source("cognative_paradigm.simulation.stimulus_stream")
        replay_block = source.split("class ReplayStimulusStream")[1].split(
            "class StochasticStimulusStream"
        )[0]
        self.assertNotIn("PatternMemorySnapshot", replay_block)
        self.assertNotIn("owner_for_pattern", replay_block)

    def test_mastery_scheduler_reads_ownership_by_design(self) -> None:
        source = _module_source("cognative_paradigm.simulation.stimulus_stream")
        mastery_block = source.split("class MasteryAutoStimScheduler")[1]
        self.assertIn("owner_for_pattern", mastery_block)

    def test_rotation_hold_is_bind_agnostic(self) -> None:
        stream = RotatingStimulusStream(hold_steps=5)
        first_block = [stream.next_line_id(i) for i in range(5)]
        self.assertEqual(first_block, [LINE_IDS[0]] * 5)
        self.assertEqual(stream.next_line_id(5), LINE_IDS[1])


if __name__ == "__main__":
    unittest.main()
