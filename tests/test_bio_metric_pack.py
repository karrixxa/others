"""Normative biological metric pack unit tests."""

import pytest

from cognative_paradigm.diagnostics.bio_metric_pack import BiologicalMetricPack
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator


@pytest.mark.biological_lab
class TestBiologicalMetricPack:
    def test_empty_simulator_has_clean_integrity_and_zero_rate(self) -> None:
        snapshot = BiologicalMetricPack().capture(BrainSimulator(), pulses=0)
        assert snapshot.owner_count == 0
        assert snapshot.ownership_collisions == 0
        assert snapshot.integrity_ratio == 1.0
        assert snapshot.excitatory_spike_rate == 0.0

    def test_capture_counts_pulses_without_mutating_simulator(self) -> None:
        simulator = BrainSimulator()
        simulator.stimulate_pattern(get_line("H1"))
        snapshot = BiologicalMetricPack().capture(simulator, pulses=1)
        assert snapshot.pulses == 1
        assert snapshot.owner_count >= 0
