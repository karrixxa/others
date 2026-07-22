"""Unit tests for L5 next-line predictor."""

import pytest

from cognative_paradigm.cortical_column.next_line_predictor import NextLinePredictor
from cognative_paradigm.domain.column_signal import EPISODE_END_PREDICTION
from cognative_paradigm.domain.column_state import ColumnState
from cognative_paradigm.domain.sequence_transition_memory import (
    SequenceTransitionMemory,
)
from cognative_paradigm.lines import LINE_IDS


class TestNextLinePredictor:
    def test_unknown_before_evidence_has_zero_confidence(self) -> None:
        predictor = NextLinePredictor()
        state = ColumnState.initial().with_line_observed("H1")
        prediction = predictor.predict(state)
        assert prediction.confidence == 0.0
        assert not prediction.is_episode_end

    def test_learns_h1_to_v1_from_observations(self) -> None:
        predictor = NextLinePredictor()
        for _ in range(5):
            predictor.record_transition("H1", "V1")

        state = ColumnState.initial().with_line_observed("H1")
        prediction = predictor.predict(state)
        assert prediction.predicted_line_id == "V1"
        assert prediction.confidence == 1.0

    def test_learns_full_episode_chain(self) -> None:
        predictor = NextLinePredictor()
        transitions = [
            ("H1", "V1"),
            ("V1", "D0"),
            ("D0", "D1"),
            ("D1", EPISODE_END_PREDICTION),
        ]
        for from_line, to_line in transitions:
            for _ in range(3):
                predictor.record_transition(from_line, to_line)

        expectations = [
            ("H1", "V1", False),
            ("V1", "D0", False),
            ("D0", "D1", False),
            ("D1", EPISODE_END_PREDICTION, True),
        ]
        for prior, expected, is_end in expectations:
            state = ColumnState.initial().with_line_observed(prior)
            prediction = predictor.predict(state)
            assert prediction.predicted_line_id == expected
            assert prediction.is_episode_end is is_end
            assert prediction.confidence == 1.0

    def test_no_hardcoded_lookup_table(self) -> None:
        memory = SequenceTransitionMemory()
        predictor = NextLinePredictor(memory=memory)
        for line_id in LINE_IDS:
            assert not memory.has_evidence_for(line_id)

        state = ColumnState.initial().with_line_observed("D1")
        prediction = predictor.predict(state)
        assert prediction.confidence == 0.0

    def test_record_step_uses_prior_line_only(self) -> None:
        predictor = NextLinePredictor()
        state = ColumnState.initial()
        predictor.record_step(state, "H1")
        assert not predictor.memory.has_evidence_for("H1")

        state = state.with_line_observed("H1")
        predictor.record_step(state, "V1")
        assert predictor.memory.best_successor("H1") == ("V1", 1.0)

    def test_serialize_and_deserialize_round_trip(self) -> None:
        predictor = NextLinePredictor()
        for _ in range(2):
            predictor.record_transition("H1", "V1")
        predictor.record_transition("V1", "D0")

        payload = predictor.serialize()
        restored = NextLinePredictor.deserialize(payload)
        state = ColumnState.initial().with_line_observed("H1")
        assert restored.predict(state) == predictor.predict(state)

    def test_serialize_is_deterministic(self) -> None:
        predictor = NextLinePredictor()
        predictor.record_transition("D0", "D1")
        predictor.record_transition("H1", "V1")
        first = predictor.serialize()
        second = predictor.serialize()
        assert first == second

    def test_competing_successors_use_frequency(self) -> None:
        predictor = NextLinePredictor()
        predictor.record_transition("H1", "V1")
        predictor.record_transition("H1", "V1")
        predictor.record_transition("H1", "D0")

        state = ColumnState.initial().with_line_observed("H1")
        prediction = predictor.predict(state)
        assert prediction.predicted_line_id == "V1"
        assert prediction.confidence == pytest.approx(2.0 / 3.0)

    def test_biological_unknown_has_no_catalog_placeholder(self) -> None:
        from cognative_paradigm.domain.column_profile import ColumnCausalPolicy

        predictor = NextLinePredictor(
            policy=ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        )
        state = ColumnState.initial().with_line_observed("H1")
        prediction = predictor.predict(state)
        assert prediction.is_unknown
        assert prediction.confidence == 0.0
        assert prediction.predicted_line_id == "UNKNOWN"

    def test_biological_never_emits_line_ids_zero_placeholder(self) -> None:
        from cognative_paradigm.cortical_column.context_assembly import ContextAssembly
        from cognative_paradigm.domain.column_profile import ColumnCausalPolicy

        predictor = NextLinePredictor(
            policy=ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        )
        assemblies = tuple(ContextAssembly.unbound_candidate(i) for i in range(2))
        state = ColumnState.initial()
        prediction = predictor.predict(
            state,
            predecessor_representation_id=None,
            assemblies=assemblies,
        )
        assert prediction.is_unknown
        assert prediction.predicted_line_id != LINE_IDS[0]

    def test_biological_plural_recurrent_evidence_is_unknown(self) -> None:
        from cognative_paradigm.cortical_column.context_assembly import ContextAssembly
        from cognative_paradigm.domain.column_profile import ColumnCausalPolicy
        from cognative_paradigm.lines import get_line

        predictor = NextLinePredictor(
            policy=ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        )
        assemblies = tuple(ContextAssembly.unbound_candidate(i) for i in range(3))
        assemblies[0].bind_pattern(get_line("H1"), metadata_label="H1")
        assemblies[1].bind_pattern(get_line("V1"), metadata_label="V1")
        assemblies[2].bind_pattern(get_line("D0"), metadata_label="D0")
        assemblies[1].incoming_recurrent("repr_0").weight = 0.9
        assemblies[2].incoming_recurrent("repr_0").weight = 0.9
        prediction = predictor.predict(
            ColumnState.initial().with_line_observed("H1"),
            predecessor_representation_id="repr_0",
            assemblies=assemblies,
        )
        assert prediction.is_unknown

    def test_legacy_oracle_still_uses_frequency_table(self) -> None:
        """Legacy hybrid_cortical keeps global count authority."""
        predictor = NextLinePredictor()
        predictor.record_transition("H1", "V1")
        predictor.record_transition("H1", "V1")
        predictor.record_transition("H1", "D0")
        state = ColumnState.initial().with_line_observed("H1")
        prediction = predictor.predict(state)
        assert prediction.predicted_line_id == "V1"
        assert prediction.confidence == pytest.approx(2.0 / 3.0)
