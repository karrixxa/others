"""Path 5 — column_only_stimulate lab flag."""

from __future__ import annotations

from unittest.mock import MagicMock

from cognative_paradigm.api.service import BrainService, ParametersPatch
from cognative_paradigm.diagnostics.column_metric_pack import ColumnMetricPack
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics
from cognative_paradigm.learning.lab_profile import BiologicalLabProfileFactory


class TestColumnOnlyStimulate:
    def test_flag_off_runs_nucleus_step(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        assert dynamics.column_only_stimulate is False
        sim = BrainSimulator(dynamics=dynamics)
        sim.step = MagicMock(wraps=sim.step)
        sim.stimulate_pattern(get_line("H1"), line_id="H1")
        assert sim.step.called

    def test_flag_on_bio_skips_nucleus_step(self) -> None:
        from dataclasses import replace

        dynamics = replace(
            BiologicalLabProfileFactory.hybrid_biological_dynamics(),
            column_only_stimulate=True,
        )
        sim = BrainSimulator(dynamics=dynamics)
        sim.step = MagicMock(wraps=sim.step)
        result = sim.stimulate_pattern(get_line("H1"), line_id="H1")
        assert not sim.step.called
        assert result.winner_neuron_id is None
        assert result.timestep == 1
        assert result.step_events == []
        assert sim.cortical_column is not None
        assert sim.cortical_column._last_competition is not None

    def test_column_only_clears_stale_nucleus_winner_highlight(self) -> None:
        from dataclasses import replace

        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        sim = BrainSimulator(dynamics=dynamics)
        sim.stimulate_pattern(get_line("H1"), line_id="H1")
        if sim.get_state().get("winner_neuron_id") is None:
            # Seed a display winner so the clear path is deterministic.
            ring = sim.nucleus.ring
            assert ring
            sim.nucleus._last_winner = ring[0]
            sim.nucleus._last_winner_latency_ms = 1.0
        assert sim.get_state()["winner_neuron_id"] is not None

        owners_before = dict(sim.get_state()["nucleus"]["pattern_owners"])
        sim.apply_dynamics(replace(sim._dynamics, column_only_stimulate=True))
        result = sim.stimulate_pattern(get_line("V1"), line_id="V1")

        assert result.winner_neuron_id is None
        assert sim.get_state()["winner_neuron_id"] is None
        assert sim.get_state()["winner_latency_ms"] is None
        assert sim.get_state()["nucleus"]["competition_resolved"] is False
        assert sim.get_state()["nucleus"]["pattern_owners"] == owners_before

    def test_column_only_advances_monotonic_stimulation_clock(self) -> None:
        from dataclasses import replace

        dynamics = replace(
            BiologicalLabProfileFactory.hybrid_biological_dynamics(),
            column_only_stimulate=True,
        )
        sim = BrainSimulator(dynamics=dynamics)
        first = sim.stimulate_pattern(get_line("H1"), line_id="H1")
        second = sim.stimulate_pattern(get_line("V1"), line_id="V1")
        assert first.timestep == 1
        assert second.timestep == 2
        assert first.timestep < second.timestep
        assert sim.get_state()["timestep"] == 2

    def test_column_only_raster_feed_grows_from_cold_start(self) -> None:
        from dataclasses import replace

        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                lab_profile_enabled=True,
                column_architecture_profile="hybrid_cortical_biological",
                column_only_stimulate=True,
            )
        )
        cold = service.get_raster_feed()
        assert cold["seq"] == 0
        assert cold["steps"] == []

        service.stimulate("H1")
        service.stimulate("V1")
        feed = service.get_raster_feed()
        assert feed["seq"] == 2
        assert len(feed["steps"]) == 2
        assert feed["steps"][0]["step"]["timestep"] == 1
        assert feed["steps"][1]["step"]["timestep"] == 2
        assert feed["steps"][0]["step"]["step_events"] == []
        assert feed["steps"][1]["step"]["step_events"] == []

    def test_flag_on_compatibility_still_steps_nucleus(self) -> None:
        from dataclasses import replace

        dynamics = replace(
            LearningDynamics(),
            column_only_stimulate=True,
        )
        sim = BrainSimulator(dynamics=dynamics)
        sim.step = MagicMock(wraps=sim.step)
        sim.stimulate_pattern(get_line("H1"), line_id="H1")
        assert sim.step.called

    def test_service_patch_and_causal_pack(self) -> None:
        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                lab_profile_enabled=True,
                column_architecture_profile="hybrid_cortical_biological",
                column_only_stimulate=True,
            )
        )
        params = service.get_parameters()
        assert params["column_only_stimulate"] is True
        column = service.simulator.cortical_column
        assert column is not None
        snapshot = ColumnMetricPack().evaluate_causal_safety(column, episodes=1)
        assert snapshot.passes_exact_zero()
