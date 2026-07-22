"""Engine-clock spike timing recorder tests."""

import pytest

from cognative_paradigm.simulation.pulse_spike_time_recorder import (
    PulseSpikeTimeRecorder,
)


@pytest.mark.biological_lab
class TestPulseSpikeTimeRecorder:
    def test_recorded_relay_time_overrides_synthetic_fraction(self) -> None:
        recorder = PulseSpikeTimeRecorder()
        recorder.begin_pulse(
            pulse_onset_ms=100.0,
            stim_duration_ms=40.0,
            sensory_spike_ids=frozenset({"input_r1_c1"}),
        )
        recorder.record_presynaptic(
            frozenset({"l1_e_4"}),
            sim_time_ms=117.0,
        )
        recorder.record_postsynaptic(("nucleus_e_0",), sim_time_ms=129.0)

        context = recorder.context_for(
            "nucleus_e_0",
            active_ids=frozenset({"input_r1_c1"}),
            relay_ids=frozenset({"l1_e_4"}),
        )
        assert context.pre_spike_times_ms["input_r1_c1"] == 100.0
        assert context.pre_spike_times_ms["l1_e_4"] == 117.0
        assert context.post_spike_time_ms == 129.0

    def test_missing_recording_uses_synthetic_ablation_fallback(self) -> None:
        recorder = PulseSpikeTimeRecorder()
        recorder.begin_pulse(
            pulse_onset_ms=10.0,
            stim_duration_ms=40.0,
            sensory_spike_ids=frozenset(),
        )
        context = recorder.context_for(
            "nucleus_e_0",
            active_ids=frozenset({"input_r0_c0"}),
            relay_ids=frozenset({"l1_e_0"}),
        )
        assert context.pre_spike_times_ms["input_r0_c0"] == 12.0
        assert context.pre_spike_times_ms["l1_e_0"] == 44.0
        assert context.post_spike_time_ms == 50.0
