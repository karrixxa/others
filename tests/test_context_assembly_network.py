"""Unit tests for L2/3 context assembly network."""

from cognative_paradigm.cortical_column.context_assembly import assembly_id_for_line
from cognative_paradigm.cortical_column.context_assembly_network import (
    ContextAssemblyNetwork,
)
from cognative_paradigm.cortical_column.layer4_adapter import Layer4Adapter
from cognative_paradigm.domain.column_signal import Layer4Activation
from cognative_paradigm.domain.column_state import ColumnState
from cognative_paradigm.domain.context_transition_map import ContextTransitionMap
from cognative_paradigm.lines import LINE_IDS


def _activation(line_id: str) -> Layer4Activation:
    indices = Layer4Adapter.line_indices(line_id)
    return Layer4Activation(
        line_id=line_id,
        active_cell_indices=indices,
        modulated_cell_indices=indices,
    )


class TestContextAssemblyNetwork:
    def test_matching_line_wins_competition(self) -> None:
        network = ContextAssemblyNetwork()
        state = ColumnState.initial()
        updated = network.integrate(state, _activation("H1"), line_id="H1")
        assert updated.active_assembly_ids == frozenset({assembly_id_for_line("H1")})
        assert updated.compact_context_code == 1

    def test_catalog_sequence_advances_active_assembly_each_line(self) -> None:
        """Residual Vm after fire must not lock the first catalog winner forever."""
        network = ContextAssemblyNetwork()
        state = ColumnState.initial()
        expected = []
        for line_id in LINE_IDS:
            state = network.integrate(state, _activation(line_id), line_id=line_id)
            expected_id = assembly_id_for_line(line_id)
            assert state.active_assembly_ids == frozenset({expected_id}), (
                f"{line_id} should activate {expected_id}, "
                f"got {sorted(state.active_assembly_ids)}"
            )
            expected.append(expected_id)
        assert expected == [assembly_id_for_line(line_id) for line_id in LINE_IDS]

    def test_prior_active_assembly_biases_competition(self) -> None:
        transition_map = ContextTransitionMap()
        network = ContextAssemblyNetwork(transition_map=transition_map)
        state = ColumnState.initial()
        state = network.integrate(state, _activation("H1"), line_id="H1")
        ambiguous = Layer4Activation(
            line_id="V1",
            active_cell_indices=frozenset({4}),
            modulated_cell_indices=frozenset({4}),
        )
        updated = network.integrate(state, ambiguous, line_id="V1")
        assert assembly_id_for_line("H1") in updated.active_assembly_ids or (
            assembly_id_for_line("V1") in updated.active_assembly_ids
        )

    def test_transition_map_learns_and_persists_across_reset(self) -> None:
        network = ContextAssemblyNetwork()
        state = ColumnState.initial()
        for line_id in LINE_IDS:
            state = network.integrate(state, _activation(line_id), line_id=line_id)

        learned_weight = max(
            network.learned_transition_map.bias_for(
                "H1",
                "V1",
                assembly_id_for_line(line_id),
            )
            for line_id in LINE_IDS
        )
        assert learned_weight > 0.0

        network.clear_active_state()
        assert max(
            network.learned_transition_map.bias_for(
                "H1",
                "V1",
                assembly_id_for_line(line_id),
            )
            for line_id in LINE_IDS
        ) == learned_weight

    def test_clear_active_state_wipes_assembly_membranes_not_weights(self) -> None:
        network = ContextAssemblyNetwork()
        state = ColumnState.initial()
        state = network.integrate(state, _activation("D0"), line_id="D0")
        network.clear_active_state()
        cleared = network.integrate(ColumnState.initial(), _activation("D0"), line_id="D0")
        assert cleared.active_assembly_ids == frozenset({assembly_id_for_line("D0")})

    def test_transition_map_serializes_deterministically(self) -> None:
        transition_map = ContextTransitionMap()
        transition_map.observe(None, "H1", assembly_id_for_line("H1"))
        transition_map.observe("H1", "V1", assembly_id_for_line("V1"))
        payload = transition_map.serialize()
        restored = ContextTransitionMap.deserialize(payload)
        assert restored.bias_for(None, "H1", assembly_id_for_line("H1")) > 0.0
        assert restored.bias_for("H1", "V1", assembly_id_for_line("V1")) > 0.0

    def test_integrate_advances_sequence_index(self) -> None:
        network = ContextAssemblyNetwork()
        state = ColumnState.initial()
        updated = network.integrate(state, _activation("H1"), line_id="H1")
        assert updated.sequence_index == 1
        assert updated.previous_input_id == "H1"

    def test_four_assemblies_cover_catalog(self) -> None:
        network = ContextAssemblyNetwork()
        assert network.assemblies is not None
        assert len(network.assemblies) == 4
        assert {assembly.line_id for assembly in network.assemblies} == set(LINE_IDS)

    def test_biological_below_threshold_abstains(self) -> None:
        from cognative_paradigm.domain.column_profile import ColumnCausalPolicy

        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        silent = Layer4Activation(
            line_id="H1",
            active_cell_indices=frozenset({3, 4, 5}),
            modulated_cell_indices=frozenset(),
            input_cell_indices=frozenset({3, 4, 5}),
            gain_gated_input_indices=frozenset({3, 4, 5}),
            relay_spike_indices=frozenset(),
        )
        updated = network.integrate(ColumnState.initial(), silent, line_id="H1")
        assert updated.active_assembly_ids == frozenset()
        assert updated.compact_context_code == 0
        assert network.last_competition is not None
        assert not network.last_competition.has_unique_representation
