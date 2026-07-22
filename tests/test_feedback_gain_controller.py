"""Unit tests for L6 feedback gain controller."""

import pytest

from cognative_paradigm.cortical_column.feedback_gain_controller import (
    FeedbackGainController,
)
from cognative_paradigm.domain.column_signal import CellGainMap, ColumnPrediction
from cognative_paradigm.domain.column_state import ColumnState
from cognative_paradigm.lines import LINE_INDICES


class TestFeedbackGainController:
    def test_unknown_prediction_yields_unity_gain(self) -> None:
        controller = FeedbackGainController()
        state = ColumnState.initial().with_line_observed(
            "H1",
            next_prediction=ColumnPrediction.for_line("V1", confidence=0.0),
        )
        assert controller.compute_gain(state) == CellGainMap.unity()

    def test_episode_end_prediction_yields_unity_gain(self) -> None:
        controller = FeedbackGainController()
        state = ColumnState.initial().with_line_observed(
            "D1",
            next_prediction=ColumnPrediction.episode_end(confidence=1.0),
        )
        assert controller.compute_gain(state) == CellGainMap.unity()

    def test_boosts_predicted_line_cells(self) -> None:
        controller = FeedbackGainController(
            predicted_boost=2.5,
            non_predicted_gain=0.25,
        )
        prediction = ColumnPrediction.for_line("H1", confidence=0.9)
        gain = controller.compute_gain_from_prediction(prediction)

        for index in range(9):
            expected = 2.5 if index in LINE_INDICES["H1"] else 0.25
            assert gain.gain_at(index) == expected

    def test_apply_to_state_sets_pending_gain(self) -> None:
        controller = FeedbackGainController()
        state = ColumnState.initial()
        prediction = ColumnPrediction.for_line("V1", confidence=0.8)
        updated = controller.apply_to_state(state, prediction)
        assert updated.next_prediction == prediction
        assert updated.pending_gain != CellGainMap.unity()
        for index in LINE_INDICES["V1"]:
            assert updated.pending_gain.gain_at(index) > 1.0

    def test_consume_pending_gain_resets_to_unity(self) -> None:
        controller = FeedbackGainController()
        state = ColumnState.initial().with_line_observed(
            "H1",
            pending_gain=CellGainMap(gains=(2.0,) * 9),
        )
        consumed = controller.consume_pending_gain(state)
        assert consumed.pending_gain == CellGainMap.unity()

    def test_pending_gain_consumed_once_per_step(self) -> None:
        controller = FeedbackGainController()
        prediction = ColumnPrediction.for_line("D0", confidence=1.0)
        state = controller.apply_to_state(ColumnState.initial(), prediction)
        assert state.pending_gain != CellGainMap.unity()

        consumed = controller.consume_pending_gain(state)
        assert consumed.pending_gain == CellGainMap.unity()

    def test_no_prediction_yields_unity(self) -> None:
        controller = FeedbackGainController()
        assert controller.compute_gain(ColumnState.initial()) == CellGainMap.unity()

    def test_invalid_boost_rejected(self) -> None:
        with pytest.raises(ValueError):
            FeedbackGainController(predicted_boost=-1.0)

    def test_biological_policy_always_unity_gain(self) -> None:
        from cognative_paradigm.domain.column_profile import ColumnCausalPolicy

        controller = FeedbackGainController(
            policy=ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        )
        prediction = ColumnPrediction.for_line("H1", confidence=1.0)
        assert controller.compute_gain_from_prediction(prediction) == CellGainMap.unity()
        assert (
            controller.compute_gain_from_prediction(ColumnPrediction.unknown())
            == CellGainMap.unity()
        )
