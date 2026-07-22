"""Stage 9/11 — dendritic coincidence gate and honest apical eligibility."""

from __future__ import annotations

from dataclasses import replace

import pytest

from cognative_paradigm.cortical_column.apical_context_drive import (
    ApicalContextDrivePolicy,
)
from cognative_paradigm.cortical_column.dendritic_coincidence_gate import (
    DendriticCoincidenceGate,
)
from cognative_paradigm.cortical_column.column_architecture_factory import (
    ColumnArchitectureFactory,
)
from cognative_paradigm.cortical_column.context_assembly import ContextAssembly
from cognative_paradigm.domain.column_profile import ColumnCausalPolicy
from cognative_paradigm.domain.column_signal import ColumnPrediction
from cognative_paradigm.domain.column_state import ColumnState
from cognative_paradigm.learning.lab_profile import BiologicalLabProfileFactory
from cognative_paradigm.learning.prediction_error_modulator import (
    PredictionErrorModulator,
)
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.learning_dynamics import (
    LearningDynamics,
    validate_learning_dynamics,
)


class TestDendriticCoincidenceGate:
    def test_disabled_passes_basal_unchanged(self) -> None:
        gate = DendriticCoincidenceGate.disabled()
        assert gate.effective_basal_drive(0.4, 0.9) == pytest.approx(0.4)
        assert gate.allows_eligibility() is True

    def test_coincidence_amplifies_and_gates_eligibility(self) -> None:
        gate = DendriticCoincidenceGate.from_dynamics_flags(
            enabled=True,
            coincidence_threshold=0.02,
            amp_min=0.5,
            amp_max=2.0,
        )
        driven = gate.effective_basal_drive(0.5, 0.8, membrane=0.4)
        assert driven > 0.5
        assert gate.allows_eligibility() is True
        assert gate.last_coincidence >= 0.02

    def test_basal_only_blocks_eligibility_when_required(self) -> None:
        gate = DendriticCoincidenceGate.from_dynamics_flags(
            enabled=True,
            coincidence_threshold=0.5,
        )
        gate.observe(0.01, 0.0, membrane=0.0)
        assert gate.allows_eligibility() is False


class TestApicalContextDrivePolicy:
    def test_zero_ambient_and_silence_yield_zero_apical(self) -> None:
        policy = ApicalContextDrivePolicy.honest_bio()
        assert policy.ambient == pytest.approx(0.0)
        assembly = ContextAssembly.unbound_candidate(0)
        state = ColumnState.initial()
        assert policy.drive_for(state, assembly) == pytest.approx(0.0)

    def test_self_prior_provides_apical(self) -> None:
        policy = ApicalContextDrivePolicy.honest_bio()
        assembly = ContextAssembly.unbound_candidate(0)
        state = ColumnState.initial().with_line_observed(
            "H1",
            active_assembly_ids=frozenset({assembly.assembly_id}),
        )
        assert policy.drive_for(state, assembly) == pytest.approx(
            policy.self_prior_strength
        )

    def test_prediction_boosts_bound_successor_only(self) -> None:
        policy = ApicalContextDrivePolicy.honest_bio()
        bound = ContextAssembly.unbound_candidate(1)
        bound.bind_pattern(get_line("V1"), metadata_label="V1")
        other = ContextAssembly.unbound_candidate(0)
        state = replace(
            ColumnState.initial(),
            next_prediction=ColumnPrediction.for_line("V1", confidence=0.8),
        )
        assert policy.drive_for(state, bound) == pytest.approx(
            policy.prediction_apical_scale * 0.8
        )
        assert policy.drive_for(state, other) == pytest.approx(0.0)

    def test_unknown_prediction_adds_no_apical(self) -> None:
        policy = ApicalContextDrivePolicy.honest_bio()
        assembly = ContextAssembly.unbound_candidate(0)
        state = replace(
            ColumnState.initial(),
            next_prediction=ColumnPrediction.unknown(),
        )
        assert policy.drive_for(state, assembly) == pytest.approx(0.0)


class TestStage11EligibilitySelectivity:
    def test_basal_plus_zero_apical_not_eligible_under_bio_threshold(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        column = ColumnArchitectureFactory.create(dynamics)
        assert column is not None
        network = column.context_network
        assert network.dendritic_config is not None
        assert network.dendritic_config.coincidence_threshold >= 0.05
        assembly = network.assemblies[0]
        gate = network._gate_for(assembly.assembly_id)
        gate.reset()
        gate.observe(0.4, 0.0, membrane=0.3)
        assert gate.allows_eligibility() is False

    def test_basal_plus_self_prior_is_eligible(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        column = ColumnArchitectureFactory.create(dynamics)
        assert column is not None
        network = column.context_network
        assembly = network.assemblies[0]
        policy = network.apical_policy
        assert policy is not None
        state = ColumnState.initial().with_line_observed(
            "H1",
            active_assembly_ids=frozenset({assembly.assembly_id}),
        )
        apical = network._apical_context_drive(state, assembly)
        assert apical >= policy.self_prior_strength
        gate = network._gate_for(assembly.assembly_id)
        gate.reset()
        gate.observe(0.35, apical, membrane=0.3)
        assert gate.allows_eligibility() is True

    def test_bio_binds_eventually_under_normal_stimulate(self) -> None:
        from cognative_paradigm.api.service import BrainService, ParametersPatch

        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                lab_profile_enabled=True,
                column_architecture_profile="hybrid_cortical_biological",
            )
        )
        for _ in range(6):
            for line_id in LINE_IDS:
                service.stimulate(line_id)
        assemblies = service.simulator.cortical_column._context.assemblies
        bound = [a for a in assemblies if a.is_bound]
        assert len(bound) >= 1
        labels = {a.metadata_label for a in bound if a.metadata_label}
        assert labels  # at least one catalog line bound under honest apical


class TestBiologicalDendriticWiring:
    def test_bio_factory_enables_column_coincidence(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        assert dynamics.dendritic_coincidence_enabled is True
        assert dynamics.nucleus_dendritic_coincidence_enabled is False
        assert dynamics.dendritic_coincidence_threshold == pytest.approx(0.05)
        column = ColumnArchitectureFactory.create(dynamics)
        assert column is not None
        assert column.context_network.dendritic_coincidence_enabled is True
        payload = column.serialize_state()
        assert "dendritic_coincidence" in payload
        assert payload["dendritic_coincidence"]["enabled"] is True
        assert len(payload["dendritic_coincidence"]["assemblies"]) == 4

    def test_bio_profile_forbids_disabling_column_coincidence(self) -> None:
        from cognative_paradigm.api.service import BrainService, ParametersPatch

        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                lab_profile_enabled=True,
                column_architecture_profile="hybrid_cortical_biological",
            )
        )
        try:
            service.update_parameters(
                ParametersPatch(dendritic_coincidence_enabled=False)
            )
        except ValueError as exc:
            assert "dendritic_coincidence_enabled=True" in str(exc)
        else:
            raise AssertionError("bio profile must keep dendritic coincidence ON")

    def test_eligible_targets_drive_full_population_under_bio_coincidence(
        self,
    ) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        column = ColumnArchitectureFactory.create(dynamics)
        assert column is not None
        network = column.context_network
        pattern = get_line("H1")
        assemblies = list(network.assemblies)
        assemblies[0].bind_pattern(pattern, metadata_label="H1")
        network.ownership_index.rebuild(network.assemblies)
        targets = network._eligible_drive_targets(pattern)
        assert targets == frozenset(a.assembly_id for a in network.assemblies)

        novel = get_line("V1")
        assert network._eligible_drive_targets(novel) == frozenset(
            a.assembly_id for a in network.assemblies
        )
        assert (
            network.inhibitory_network is not None
            and network.inhibitory_network.coupling.inhibition_strength >= 0.85
        )

    def test_bind_evidence_requires_coincidence_when_enabled(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        column = ColumnArchitectureFactory.create(dynamics)
        assert column is not None
        network = column.context_network
        assembly = network.assemblies[0]
        gate = network._gate_for(assembly.assembly_id)
        gate.reset()
        assert gate.allows_eligibility() is False
        gate.observe(0.5, 0.5, membrane=0.4)
        assert gate.allows_eligibility() is True

    def test_nucleus_coincidence_bypasses_bound_match_soft_gates(self) -> None:
        dynamics = replace(
            BiologicalLabProfileFactory.hybrid_biological_dynamics(),
            nucleus_dendritic_coincidence_enabled=True,
        )
        validate_learning_dynamics(dynamics)
        modulator = PredictionErrorModulator(dynamics)
        assert modulator.soft_gates_active is False

    def test_orphaned_ownership_claim_apis_are_retired(self) -> None:
        from cognative_paradigm.domain.abstract_code_ownership import (
            AbstractCodeOwnership,
        )
        from cognative_paradigm.domain.feature_code_ownership import (
            FeatureCodeOwnership,
        )

        feature = FeatureCodeOwnership()
        abstract = AbstractCodeOwnership()
        with pytest.raises(RuntimeError, match="retired"):
            feature.claim("code", "n0")
        with pytest.raises(RuntimeError, match="retired"):
            feature.can_bind("code", "n0")
        with pytest.raises(RuntimeError, match="retired"):
            abstract.claim("code", "n0")
        assert feature.owner_for_code("code") is None
        assert abstract.as_dict() == {}

    def test_causal_regression_still_forbids_force(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        with pytest.raises(ValueError, match="forbids"):
            validate_learning_dynamics(
                replace(dynamics, pretrained_inhibitor_exclusivity_enabled=True)
            )


class TestNucleusDendriticSoftGateBypass:
    def test_nucleus_flag_requires_soft_and_graded(self) -> None:
        with pytest.raises(ValueError, match="nucleus_dendritic"):
            validate_learning_dynamics(
                LearningDynamics(
                    lab_profile_enabled=True,
                    pretrained_inhibitor_exclusivity_enabled=True,
                    descending_mode="force",
                    nucleus_dendritic_coincidence_enabled=True,
                )
            )

    def test_modulator_bypasses_spike_eligible_when_coincidence_on(self) -> None:
        dynamics = replace(
            BiologicalLabProfileFactory.hybrid_biological_dynamics(),
            nucleus_dendritic_coincidence_enabled=True,
        )
        validate_learning_dynamics(dynamics)
        modulator = PredictionErrorModulator(dynamics)
        assert modulator.soft_gates_active is False

        class _Stub:
            id = "n0"

            @property
            def memory(self):
                class M:
                    def is_bound(self_inner):
                        return False

                return M()

            @property
            def prediction(self):
                class P:
                    def matches(self_inner, _code):
                        return False

                return P()

        assert modulator.spike_eligible(
            _Stub(), frozenset({"e0"}), pattern_has_binder=True
        )


@pytest.mark.cortical_column_lab
class TestStage9CausalLocks:
    def test_policy_remains_biological(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        assert policy.is_biological is True
        assert policy.force_modes_reachable is False
