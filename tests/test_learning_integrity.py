"""Learning integrity auditor — every bind must follow biological evidence rules."""

import unittest

from cognative_paradigm.diagnostics.learning_integrity import LearningIntegrityAuditor
from cognative_paradigm.lines import LINE_IDS, LINE_INDICES
from tests.simulation_helpers import biology_dynamics, unguided_ecological_dynamics


class LearningIntegrityTests(unittest.TestCase):
    def test_single_pattern_bind_has_no_violations(self) -> None:
        auditor = LearningIntegrityAuditor(dynamics=biology_dynamics())
        report = auditor.run([[0, 1, 2]], max_steps_per_pattern=150)

        self.assertEqual(len(report.binds), 1)
        self.assertEqual(report.violation_count, 0)
        self.assertTrue(report.binds[0].symbol.startswith("sigma_"))

    def test_two_patterns_bind_with_distinct_owners(self) -> None:
        auditor = LearningIntegrityAuditor(dynamics=biology_dynamics())
        report = auditor.run([[0, 1, 2], [6, 7, 8]], max_steps_per_pattern=150)

        self.assertEqual(len(report.binds), 2)
        self.assertEqual(report.violation_count, 0)
        owners = {record.neuron_id for record in report.binds}
        self.assertEqual(len(owners), 2)

    def test_soft_ecological_catalog_bind_integrity(self) -> None:
        """Soft NI co-spikers may bind without being diagnostic WTA winner."""
        auditor = LearningIntegrityAuditor(dynamics=unguided_ecological_dynamics())
        report = auditor.run(
            [LINE_INDICES[line_id] for line_id in LINE_IDS],
            max_steps_per_pattern=250,
        )

        self.assertEqual(len(report.binds), 4)
        self.assertEqual(report.violation_count, 0)
        self.assertTrue(report.passed)


if __name__ == "__main__":
    unittest.main()
