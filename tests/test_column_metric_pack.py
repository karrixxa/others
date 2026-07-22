"""Tests for cortical-column diagnostic metrics."""

import pytest

from cognative_paradigm.cortical_column.cortical_column import HybridCorticalColumn
from cognative_paradigm.diagnostics.column_metric_pack import ColumnMetricPack
from cognative_paradigm.learning.lab_profile import BiologicalLabProfileFactory


@pytest.mark.cortical_column_lab
class TestColumnMetricPack:
    def test_untrained_column_scores_end_opportunity_as_incorrect(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)
        snapshot = ColumnMetricPack().evaluate_column(column, training_episodes=0)
        assert snapshot.predictions_made == 1
        assert snapshot.correct_predictions == 0
        assert snapshot.accuracy == 0.0

    def test_missing_end_episode_skips_d1_to_end_learning(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)
        for line_id in ("H1", "V1", "D0", "D1"):
            column.process_pattern(line_id)
        prediction = column.predictor.predict(column.state)
        assert not (prediction.is_episode_end and prediction.confidence > 0.0)
        assert column.predictor.memory.best_successor("D1")[0] is None

    def test_trained_column_reaches_full_chain_accuracy(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)
        snapshot = ColumnMetricPack().evaluate_column(column, training_episodes=5)
        assert snapshot.correct_predictions == snapshot.predictions_made
        assert snapshot.accuracy == ColumnMetricPack().expected_chain_accuracy()

    def test_catalog_size_matches_four_lines(self) -> None:
        assert ColumnMetricPack().catalog_size() == 4


@pytest.mark.cortical_column_lab
class TestCausalSafetyMetricPack:
    def test_biological_column_passes_exact_zero_causal_safety(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        column = HybridCorticalColumn(dynamics)
        snapshot = ColumnMetricPack().evaluate_causal_safety(column, episodes=3)
        assert snapshot.steps_observed >= 1
        assert snapshot.abstention_count >= 1
        assert snapshot.passes_exact_zero()

    def test_evaluate_causal_safety_rejects_non_biological(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        column = HybridCorticalColumn(dynamics)
        with pytest.raises(ValueError, match="is_biological"):
            ColumnMetricPack().evaluate_causal_safety(column, episodes=1)
