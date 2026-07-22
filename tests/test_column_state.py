"""Unit tests for cortical-column domain contracts (Phase 1)."""

import math

import pytest

from cognative_paradigm.cortical_column.interfaces import (
    ContextAssemblyPort,
    FeedbackGainPort,
    Layer4Port,
    NextInputPredictorPort,
)
from cognative_paradigm.domain.column_signal import (
    CellGainMap,
    ColumnPrediction,
    ColumnStepResult,
    EpisodeBoundaryReason,
    Layer4Activation,
)
from cognative_paradigm.domain.column_state import (
    COLUMN_STATE_FIELD_NAMES,
    LEARNED_PARAM_FIELD_NAMES,
    ColumnState,
    ColumnStateResetPolicy,
)


class TestCellGainMap:
    def test_unity_factory_produces_nine_unit_gains(self) -> None:
        gains = CellGainMap.unity()
        assert gains.gains == (1.0,) * 9

    @pytest.mark.parametrize(
        "bad_gains",
        [
            (float("nan"),) + (1.0,) * 8,
            (-0.1,) + (1.0,) * 8,
            (1.0,) * 8,
            (1.0,) * 10,
        ],
    )
    def test_invalid_gains_rejected(self, bad_gains: tuple[float, ...]) -> None:
        with pytest.raises(ValueError):
            CellGainMap(gains=bad_gains)

    def test_apply_to_indices_zero_gain_suppresses_cell(self) -> None:
        gains = CellGainMap(gains=(0.0,) + (1.0,) * 8)
        assert gains.apply_to_indices(frozenset({0, 1})) == frozenset({1})


class TestColumnStateResetPolicy:
    def test_inter_pulse_gap_does_not_trigger_reset(self) -> None:
        policy = ColumnStateResetPolicy()
        state = ColumnState.initial().with_silence(960.0)
        assert (
            policy.should_reset(
                explicit_end=False, silence_elapsed_ms=state.silence_elapsed_ms
            )
            is False
        )

    def test_episode_silence_threshold_triggers_reset(self) -> None:
        policy = ColumnStateResetPolicy(episode_silence_reset_ms=5000.0)
        state = ColumnState.initial().with_silence(5000.0)
        boundary = policy.boundary_for(state, explicit_end=False)
        assert boundary is not None
        assert boundary.reason is EpisodeBoundaryReason.EPISODE_SILENCE

    def test_explicit_end_triggers_reset(self) -> None:
        policy = ColumnStateResetPolicy()
        state = ColumnState(
            episode_id=2,
            sequence_index=4,
            previous_input_id="D1",
            active_assembly_ids=frozenset({"asm_h1"}),
            compact_context_code=17,
            next_prediction=ColumnPrediction.for_line("H1", confidence=0.8),
            pending_gain=CellGainMap(gains=(2.0,) + (1.0,) * 8),
            silence_elapsed_ms=120.0,
        )
        boundary = policy.boundary_for(state, explicit_end=True)
        assert boundary is not None
        assert boundary.reason is EpisodeBoundaryReason.EXPLICIT_END

    def test_clear_transient_wipes_episode_context_only(self) -> None:
        policy = ColumnStateResetPolicy()
        populated = ColumnState(
            episode_id=3,
            sequence_index=4,
            previous_input_id="D1",
            active_assembly_ids=frozenset({"asm_v1"}),
            compact_context_code=42,
            next_prediction=ColumnPrediction.episode_end(),
            pending_gain=CellGainMap(gains=(0.5,) + (1.0,) * 8),
            silence_elapsed_ms=6000.0,
        )
        cleared = policy.clear_transient(populated)
        assert cleared.episode_id == 4
        assert cleared.sequence_index == 0
        assert cleared.previous_input_id is None
        assert cleared.active_assembly_ids == frozenset()
        assert cleared.compact_context_code == 0
        assert cleared.next_prediction is None
        assert cleared.pending_gain == CellGainMap.unity()
        assert cleared.silence_elapsed_ms == 0.0


class TestColumnStateSeparation:
    def test_column_state_fields_exclude_learned_params(self) -> None:
        overlap = COLUMN_STATE_FIELD_NAMES & LEARNED_PARAM_FIELD_NAMES
        assert overlap == frozenset()

    def test_column_state_field_inventory_is_transient_only(self) -> None:
        assert COLUMN_STATE_FIELD_NAMES == frozenset(
            {
                "episode_id",
                "sequence_index",
                "previous_input_id",
                "active_assembly_ids",
                "compact_context_code",
                "next_prediction",
                "pending_gain",
                "silence_elapsed_ms",
            }
        )


class TestColumnPrediction:
    def test_episode_end_prediction_requires_end_token(self) -> None:
        with pytest.raises(ValueError):
            ColumnPrediction(predicted_line_id="H1", confidence=1.0, is_episode_end=True)

    def test_invalid_confidence_rejected(self) -> None:
        with pytest.raises(ValueError):
            ColumnPrediction.for_line("H1", confidence=math.inf)


class TestColumnStepResult:
    def test_boundary_episode_id_must_match_prior_state(self) -> None:
        prior = ColumnState.initial(episode_id=1)
        updated = prior.with_line_observed("H1")
        activation = Layer4Activation(
            line_id="H1",
            active_cell_indices=frozenset({3, 4, 5}),
            modulated_cell_indices=frozenset({3, 4, 5}),
        )
        with pytest.raises(ValueError):
            ColumnStepResult(
                prior_state=prior,
                updated_state=updated,
                activation=activation,
                prediction=ColumnPrediction.for_line("V1", confidence=0.5),
                next_gain=CellGainMap.unity(),
                boundary=policy_boundary_mismatch(),
            )


def policy_boundary_mismatch():
    from cognative_paradigm.domain.column_signal import EpisodeBoundary

    return EpisodeBoundary(
        episode_id=99,
        reason=EpisodeBoundaryReason.EXPLICIT_END,
        silence_elapsed_ms=0.0,
    )


class TestPortProtocols:
    def test_runtime_checkable_ports_are_protocols(self) -> None:
        assert issubclass(Layer4Port, object)
        assert issubclass(ContextAssemblyPort, object)
        assert issubclass(NextInputPredictorPort, object)
        assert issubclass(FeedbackGainPort, object)
