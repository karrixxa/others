"""Stage 6 — graded explicit E/I for biological hybrid column."""

import pytest

from cognative_paradigm.cortical_column.context_assembly_network import (
    ContextAssemblyNetwork,
)
from cognative_paradigm.cortical_column.context_inhibitory_network import (
    ContextInhibitoryNetwork,
)
from cognative_paradigm.domain.column_profile import ColumnCausalPolicy
from cognative_paradigm.domain.column_signal import Layer4Activation
from cognative_paradigm.domain.column_state import ColumnState
from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.learning.lab_profile import BiologicalLabProfileFactory
from cognative_paradigm.lines import LINE_INDICES, get_line
from cognative_paradigm.simulation.learning_dynamics import (
    LearningDynamics,
    validate_learning_dynamics,
)


def _relay(indices: frozenset[int]) -> Layer4Activation:
    return Layer4Activation(
        line_id=None,
        active_cell_indices=indices,
        modulated_cell_indices=indices,
        input_cell_indices=indices,
        gain_gated_input_indices=indices,
        relay_spike_indices=indices,
    )


class TestColumnGradedInhibition:
    def test_inhibitory_network_uses_try_spike(self) -> None:
        network = ContextInhibitoryNetwork()
        lif = LifDynamics()
        spikes = network.apply_e_to_i(
            lif,
            excitatory_spiker_ids=frozenset({"repr_0"}),
            all_assembly_ids=("repr_0", "repr_1"),
            timestep=1,
        )
        # Peer I for repr_1 may spike from collateral drive.
        assert isinstance(spikes, frozenset)
        from cognative_paradigm.domain.register_state import RegisterState

        for assembly_id in spikes:
            neuron = network.inhibitory_neurons[assembly_id]
            assert neuron.register == RegisterState.ONE

    def test_suppression_never_assigns_identity(self) -> None:
        network = ContextInhibitoryNetwork()
        suppression = network.suppression_for_targets(
            inhibitory_spike_ids=frozenset({"repr_0"}),
            target_assembly_ids=("repr_0", "repr_1"),
        )
        assert suppression["repr_0"] == 0.0
        assert suppression["repr_1"] > 0.0

    def test_biological_column_has_explicit_ei_circuit(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        assert policy.inhibitory_circuit == "explicit_ei"
        assert policy.force_modes_reachable is False
        assert policy.allow_direct_membrane_wipe is False
        network = ContextAssemblyNetwork(policy=policy)
        assert network.inhibitory_network is not None
        network.integrate(
            ColumnState.initial(),
            _relay(frozenset(LINE_INDICES["H1"])),
            line_id="H1",
            pattern=get_line("H1"),
        )
        # No direct half-membrane wipe path on biological assemblies.
        assert network.last_competition is not None

    def test_legacy_still_uses_half_membrane_wipe(self) -> None:
        network = ContextAssemblyNetwork()
        assert network.policy is not None
        assert network.policy.inhibitory_circuit == "scalar_half_membrane"
        assert network.inhibitory_network is None

    def test_force_exclusivity_unreachable_from_biological(self) -> None:
        dynamics = LearningDynamics(
            lab_profile_enabled=True,
            column_architecture_profile="hybrid_cortical_biological",
            pretrained_inhibitor_exclusivity_enabled=True,
            descending_mode="graded",
        )
        with pytest.raises(ValueError, match="pretrained_inhibitor_exclusivity"):
            validate_learning_dynamics(dynamics)

    def test_force_descending_unreachable_from_biological(self) -> None:
        dynamics = LearningDynamics(
            lab_profile_enabled=True,
            column_architecture_profile="hybrid_cortical_biological",
            pretrained_inhibitor_exclusivity_enabled=False,
            descending_mode="force",
        )
        with pytest.raises(ValueError, match="descending_mode"):
            validate_learning_dynamics(dynamics)

    def test_hybrid_biological_factory_locks_soft_graded(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        assert dynamics.pretrained_inhibitor_exclusivity_enabled is False
        assert dynamics.descending_mode == "graded"
        validate_learning_dynamics(dynamics)

    def test_production_force_cascade_keeps_soft_modes_as_control(self) -> None:
        # Force exclusivity is production doctrine; soft/graded remain labeled control.
        production = LearningDynamics()
        assert production.pretrained_inhibitor_exclusivity_enabled is True
        assert production.descending_mode == "force"
        assert production.emergent_autonomy_enabled is False
        control = LearningDynamics(
            pretrained_inhibitor_exclusivity_enabled=False,
            descending_mode="graded",
            emergent_autonomy_enabled=True,
        )
        assert control.pretrained_inhibitor_exclusivity_enabled is False
        assert control.descending_mode == "graded"
        assert control.emergent_autonomy_enabled is True
