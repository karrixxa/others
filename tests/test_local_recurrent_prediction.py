"""Stage 5 — local recurrent prediction for biological hybrid column."""

from cognative_paradigm.cortical_column.context_assembly import ContextAssembly
from cognative_paradigm.cortical_column.next_line_predictor import NextLinePredictor
from cognative_paradigm.cortical_column.recurrent_prediction_network import (
    RecurrentPredictionNetwork,
)
from cognative_paradigm.domain.column_profile import ColumnCausalPolicy
from cognative_paradigm.domain.column_state import ColumnState
from cognative_paradigm.domain.local_synapse import LocalRecurrentSynapse
from cognative_paradigm.lines import get_line


class TestLocalRecurrentPrediction:
    def test_pair_stdp_updates_receiver_owned_synapse(self) -> None:
        synapse = LocalRecurrentSynapse(
            source_representation_id="repr_0",
            receiver_id="repr_1",
            weight=0.10,
        )
        before = synapse.weight
        provenance = synapse.try_pair_stdp(pre_timestep=1, post_timestep=2)
        assert provenance is not None
        assert provenance.rule == "pair_stdp_recurrent"
        assert synapse.weight > before
        assert provenance.receiver_id == "repr_1"
        assert provenance.source_id == "repr_0"

    def test_no_predecessor_yields_unknown(self) -> None:
        assemblies = tuple(ContextAssembly.unbound_candidate(i) for i in range(4))
        network = RecurrentPredictionNetwork()
        prediction = network.predict(assemblies, predecessor_id=None)
        assert prediction.is_unknown

    def test_equal_recurrent_evidence_abstains(self) -> None:
        assemblies = tuple(ContextAssembly.unbound_candidate(i) for i in range(3))
        a0, a1, a2 = assemblies
        a0.bind_pattern(get_line("H1"), metadata_label="H1")
        a1.bind_pattern(get_line("V1"), metadata_label="V1")
        a2.bind_pattern(get_line("D0"), metadata_label="D0")
        # Equal predictive drives — must not insertion-order top-1.
        a1.incoming_recurrent("repr_0").weight = 0.5
        a2.incoming_recurrent("repr_0").weight = 0.5
        network = RecurrentPredictionNetwork(prediction_threshold=0.10)
        prediction = network.predict(assemblies, predecessor_id="repr_0")
        assert prediction.is_unknown
        assert network.last_diagnostic is not None
        assert network.last_diagnostic.plural

    def test_unique_recurrent_drive_predicts_metadata_label(self) -> None:
        assemblies = tuple(ContextAssembly.unbound_candidate(i) for i in range(2))
        a0, a1 = assemblies
        a0.bind_pattern(get_line("H1"), metadata_label="H1")
        a1.bind_pattern(get_line("V1"), metadata_label="V1")
        a1.incoming_recurrent("repr_0").weight = 0.8
        network = RecurrentPredictionNetwork(prediction_threshold=0.10)
        prediction = network.predict(assemblies, predecessor_id="repr_0")
        assert not prediction.is_unknown
        assert prediction.predicted_line_id == "V1"
        assert prediction.confidence > 0.0

    def test_biological_predictor_ignores_global_table_mutation(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        predictor = NextLinePredictor(policy=policy)
        assemblies = tuple(ContextAssembly.unbound_candidate(i) for i in range(2))
        assemblies[0].bind_pattern(get_line("H1"), metadata_label="H1")
        assemblies[1].bind_pattern(get_line("V1"), metadata_label="V1")
        predictor.bind_assemblies(assemblies)
        predictor.record_transition("H1", "V1")
        assert not predictor.memory.has_evidence_for("H1")
        state = ColumnState.initial().with_line_observed("H1")
        prediction = predictor.predict(
            state,
            predecessor_representation_id="repr_0",
            assemblies=assemblies,
        )
        assert prediction.is_unknown

    def test_stdp_sequence_enables_prediction(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        predictor = NextLinePredictor(policy=policy)
        assemblies = tuple(ContextAssembly.unbound_candidate(i) for i in range(2))
        assemblies[0].bind_pattern(get_line("H1"), metadata_label="H1")
        assemblies[1].bind_pattern(get_line("V1"), metadata_label="V1")
        for tick in range(1, 6):
            predictor.record_biological_representation(
                representation_id="repr_0",
                timestep=tick * 2 - 1,
                assemblies=assemblies,
            )
            predictor.record_biological_representation(
                representation_id="repr_1",
                timestep=tick * 2,
                assemblies=assemblies,
            )
        state = ColumnState.initial().with_line_observed("H1")
        prediction = predictor.predict(
            state,
            predecessor_representation_id="repr_0",
            assemblies=assemblies,
        )
        assert prediction.predicted_line_id == "V1"

    def test_silence_does_not_invent_end(self) -> None:
        network = RecurrentPredictionNetwork()
        network.observe_unique_representation(
            tuple(ContextAssembly.unbound_candidate(i) for i in range(1)),
            representation_id="repr_0",
            timestep=1,
        )
        network.clear_episode_transient()
        assert "repr_0" not in network.end_evidence_by_predecessor

    def test_explicit_end_records_evidence(self) -> None:
        assemblies = tuple(ContextAssembly.unbound_candidate(i) for i in range(1))
        assemblies[0].bind_pattern(get_line("D1"), metadata_label="D1")
        network = RecurrentPredictionNetwork(prediction_threshold=0.10)
        network.observe_explicit_end(assemblies, predecessor_id="repr_0")
        assert assemblies[0].boundary_end_evidence >= 0.15
        prediction = network.predict(assemblies, predecessor_id="repr_0")
        assert prediction.is_episode_end

    def test_explicit_end_on_any_prior_is_local(self) -> None:
        assemblies = tuple(ContextAssembly.unbound_candidate(i) for i in range(2))
        assemblies[0].bind_pattern(get_line("H1"), metadata_label="H1")
        assemblies[1].bind_pattern(get_line("V1"), metadata_label="V1")
        assemblies[1].incoming_recurrent("repr_0").weight = 0.8
        network = RecurrentPredictionNetwork(prediction_threshold=0.10)
        network.observe_explicit_end(assemblies, predecessor_id="repr_0")
        assert assemblies[0].boundary_end_evidence > 0.0
        # Stronger successor spike drive beats one END deposit.
        prediction = network.predict(assemblies, predecessor_id="repr_0")
        assert prediction.predicted_line_id == "V1"
        assert not prediction.is_episode_end
