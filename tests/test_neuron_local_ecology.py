"""NeuronLocalEcologyProbe — measurement-only diagnostics."""

import unittest

from cognative_paradigm.diagnostics.neuron_local_ecology import NeuronLocalEcologyProbe
from tests.simulation_helpers import deterministic_dynamics


class NeuronLocalEcologyProbeTests(unittest.TestCase):
    def test_probe_reports_counts_without_ui(self) -> None:
        probe = NeuronLocalEcologyProbe(dynamics=deterministic_dynamics())
        report = probe.run(n_stimuli=12)
        self.assertEqual(report.stimuli_run, 12)
        self.assertGreaterEqual(report.multi_spike_ticks, 0)
        self.assertGreaterEqual(report.prediction_error_count, 0)
        self.assertGreaterEqual(report.ownership_collision_count, 0)
        self.assertIn("H1", report.binds_by_line)
        self.assertTrue(any("stimuli_run=" in line for line in report.summary_lines()))


if __name__ == "__main__":
    unittest.main()
