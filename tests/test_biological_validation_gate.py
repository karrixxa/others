"""Phase 8 biological validation gate — production integrity + benchmark checks."""

from __future__ import annotations

import unittest

import pytest

from cognative_paradigm.diagnostics.learning_integrity import LearningIntegrityAuditor
from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import LINE_IDS, LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from cognative_paradigm.simulation.stimulus_stream import RotatingStimulusStream
from tests.simulation_helpers import (
    assert_injective_ownership,
    stimulate_until_recognized,
)
from tests.test_model_stress import SimulationInvariantAuditor


@pytest.mark.biological
class BiologicalValidationGateTests(unittest.TestCase):
    """CI gate: exclusivity-ON production must pass audit-grade biology metrics."""

    def test_production_rotation_learns_four_of_four(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        stream = RotatingStimulusStream(
            hold_steps=DEFAULT_LEARNING_DYNAMICS.ecological_stimulus_hold_steps,
        )
        learned: set[str] = set()
        for step in range(500):
            line_id = stream.next_line_id(step)
            sim.stimulate_pattern(get_line(line_id), line_id=line_id)
            for catalog_id in LINE_IDS:
                if sim.nucleus.pattern_ownership.owner_for_pattern(
                    get_line(catalog_id).edge_ids
                ):
                    learned.add(catalog_id)
            if len(learned) == len(LINE_IDS):
                break
        self.assertEqual(len(learned), 4, msg=f"learned {sorted(learned)}")

    def test_zero_ownership_collisions(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        stream = RotatingStimulusStream(
            hold_steps=DEFAULT_LEARNING_DYNAMICS.ecological_stimulus_hold_steps,
        )
        for step in range(200):
            line_id = stream.next_line_id(step)
            sim.stimulate_pattern(get_line(line_id), line_id=line_id)

        collisions = [
            event
            for event in sim.event_log.entries
            if event.get("type") == EventType.OWNERSHIP_COLLISION.name
        ]
        self.assertEqual(collisions, [])

    def test_integrity_probe_clean(self) -> None:
        report = LearningIntegrityAuditor(
            dynamics=DEFAULT_LEARNING_DYNAMICS
        ).run(
            [LINE_INDICES[line_id] for line_id in LINE_IDS],
            max_steps_per_pattern=120,
        )
        self.assertEqual(report.violation_count, 0)

    def test_probe_recall_without_line_id_hint(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        stream = RotatingStimulusStream(
            hold_steps=DEFAULT_LEARNING_DYNAMICS.ecological_stimulus_hold_steps,
        )
        learned: set[str] = set()
        for step in range(500):
            line_id = stream.next_line_id(step)
            sim.stimulate_pattern(get_line(line_id), line_id=line_id)
            for catalog_id in LINE_IDS:
                if sim.nucleus.pattern_ownership.owner_for_pattern(
                    get_line(catalog_id).edge_ids
                ):
                    learned.add(catalog_id)
            if len(learned) == len(LINE_IDS):
                break

        assert_injective_ownership(sim)
        for line_id in LINE_IDS:
            with self.subTest(line_id=line_id):
                stimulate_until_recognized(sim, LINE_INDICES[line_id], max_steps=5)

    def test_production_invariant_audit_no_off_pattern_l1(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        auditor = SimulationInvariantAuditor()
        stream = RotatingStimulusStream(
            hold_steps=DEFAULT_LEARNING_DYNAMICS.ecological_stimulus_hold_steps,
        )
        for step in range(120):
            line_id = stream.next_line_id(step)
            result = sim.stimulate_pattern(get_line(line_id), line_id=line_id)
            violations = auditor.audit_after_step(sim, result)
            off_pattern = [v for v in violations if v.code == "l1_spike_off_pattern"]
            self.assertEqual(off_pattern, [], msg=str(off_pattern))


if __name__ == "__main__":
    unittest.main()
