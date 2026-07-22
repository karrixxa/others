"""Smoke tests for hybrid cortical column engine wiring."""

import pytest

from cognative_paradigm.cortical_column.cortical_column import HybridCorticalColumn
from cognative_paradigm.cortical_column.episode_stream import OrderedColumnEpisodeStream
from cognative_paradigm.diagnostics.column_metric_pack import ColumnMetricPack
from cognative_paradigm.domain.column_signal import EPISODE_END_PREDICTION
from cognative_paradigm.learning.lab_profile import BiologicalLabProfileFactory
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import (
    LearningDynamics,
    validate_learning_dynamics,
)


@pytest.mark.cortical_column_lab
class TestHybridCorticalColumn:
    def test_episode_stream_yields_canonical_order_then_end(self) -> None:
        stream = OrderedColumnEpisodeStream()
        assert list(stream) == [*LINE_IDS, EPISODE_END_PREDICTION]

    def test_learns_transitions_and_predicts_next_line(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)

        for _ in range(3):
            prior: str | None = None
            for line_id in OrderedColumnEpisodeStream(include_end=True):
                if line_id == EPISODE_END_PREDICTION:
                    column.end_episode()
                    break
                if prior is not None:
                    prediction = column.predictor.predict(column.state)
                    if prediction.confidence > 0.0:
                        assert prediction.predicted_line_id == line_id
                column.process_pattern(line_id)
                prior = line_id

        state = column.state.with_line_observed("H1")
        prediction = column.predictor.predict(state)
        assert prediction.predicted_line_id == "V1"
        assert prediction.confidence == 1.0

    def test_metric_pack_reports_perfect_accuracy_after_training(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)
        snapshot = ColumnMetricPack().evaluate_column(column, training_episodes=4)
        assert snapshot.predictions_made > 0
        assert snapshot.accuracy == 1.0

    def test_hybrid_rejected_without_lab_profile(self) -> None:
        dynamics = LearningDynamics(
            column_architecture_profile="hybrid_cortical",
            lab_profile_enabled=False,
        )
        with pytest.raises(ValueError, match="lab_profile_enabled"):
            validate_learning_dynamics(dynamics)

    def test_brain_simulator_wires_column_when_hybrid_lab_active(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        sim = BrainSimulator(dynamics=dynamics)
        assert sim.cortical_column is not None
        sim.stimulate_pattern(get_line("H1"), line_id="H1")
        assert sim.cortical_column.state.sequence_index == 1
        state = sim.get_state()
        assert "cortical_column" in state

    def test_serialize_restore_round_trip_preserves_predictor(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)
        column.process_pattern("H1")
        column.process_pattern("V1")
        payload = column.serialize_state()

        restored = HybridCorticalColumn(dynamics)
        restored.restore_state(payload)
        assert restored.predictor.predict(
            restored.state.with_line_observed("H1")
        ) == column.predictor.predict(column.state.with_line_observed("H1"))

    def test_serialized_state_exposes_prediction_and_last_l4_activation(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)
        column.process_pattern("H1")
        payload = column.serialize_state()

        assert payload["next_prediction"] == {
            "predicted_line_id": "H1",
            "confidence": 0.0,
            "is_episode_end": False,
        }
        assert payload["last_activation"] == {
            "line_id": "H1",
            "active_cell_indices": [3, 4, 5],
            "modulated_cell_indices": [3, 4, 5],
        }

        restored = HybridCorticalColumn(dynamics)
        restored.restore_state(payload)
        restored_payload = restored.serialize_state()
        assert restored_payload["next_prediction"] == payload["next_prediction"]
        assert restored_payload["last_activation"] == payload["last_activation"]

    def test_restore_accepts_legacy_payload_without_live_signals(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)
        column.restore_state({"episode_id": 2, "sequence_index": 1})
        payload = column.serialize_state()
        assert payload["next_prediction"] is None
        assert payload["last_activation"] is None

    def test_natural_episode_learns_all_transitions_including_d1_to_end(
        self,
    ) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)

        for _ in range(4):
            for line_id in LINE_IDS:
                column.process_pattern(line_id)
            column.end_episode()

        memory = column.predictor.memory
        assert memory.best_successor("H1") == ("V1", 1.0)
        assert memory.best_successor("V1") == ("D0", 1.0)
        assert memory.best_successor("D0") == ("D1", 1.0)
        assert memory.best_successor("D1") == (EPISODE_END_PREDICTION, 1.0)

        d1_state = column.state.with_line_observed("D1")
        end_prediction = column.predictor.predict(d1_state)
        assert end_prediction.is_episode_end
        assert end_prediction.confidence > 0.0

    def test_biological_rejects_hybrid_without_soft_graded_gates(self) -> None:
        dynamics = LearningDynamics(
            column_architecture_profile="hybrid_cortical_biological",
            lab_profile_enabled=True,
            pretrained_inhibitor_exclusivity_enabled=True,
            descending_mode="force",
        )
        with pytest.raises(ValueError, match="pretrained_inhibitor_exclusivity"):
            validate_learning_dynamics(dynamics)

    def test_biological_column_processes_pattern_without_line_id(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        sim = BrainSimulator(dynamics=dynamics)
        assert sim.cortical_column is not None
        result = sim.stimulate_pattern(get_line("H1"), line_id=None)
        assert result.relay_indices == [3, 4, 5]
        assert sim.cortical_column.state.sequence_index == 1

    def test_biological_abstention_yields_unknown_and_unity_gain(self) -> None:
        from cognative_paradigm.domain.pattern import Pattern

        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        column = HybridCorticalColumn(dynamics)
        # Empty pattern → no sensory drive → abstention.
        outcome = column.process_pattern("H1", Pattern(edge_ids=frozenset()))
        assert outcome.step.competition is not None
        assert not outcome.step.competition.has_unique_representation
        assert outcome.step.prediction.is_unknown
        assert list(outcome.step.next_gain.gains) == [1.0] * 9
        assert column.state.compact_context_code == 0
