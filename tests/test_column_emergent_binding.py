"""Stage 4 / Path 1 — emergent binding for biological hybrid column."""

from __future__ import annotations

from dataclasses import replace

from cognative_paradigm.cortical_column.context_assembly_network import (
    ContextAssemblyNetwork,
)
from cognative_paradigm.domain.column_profile import ColumnCausalPolicy
from cognative_paradigm.domain.column_signal import Layer4Activation
from cognative_paradigm.domain.column_state import ColumnState
from cognative_paradigm.domain.pattern import Pattern
from cognative_paradigm.lines import LINE_IDS, LINE_INDICES, edge_id_to_index, get_line


def _relay_activation(indices: frozenset[int], *, line_id: str | None = None) -> Layer4Activation:
    return Layer4Activation(
        line_id=line_id,
        active_cell_indices=indices,
        modulated_cell_indices=indices,
        input_cell_indices=indices,
        gain_gated_input_indices=indices,
        relay_spike_indices=indices,
    )


def _indices_for_pattern(pattern: Pattern) -> frozenset[int]:
    return frozenset(edge_id_to_index(edge_id) for edge_id in pattern.edge_ids)


def _present(
    network: ContextAssemblyNetwork,
    *,
    pattern: Pattern,
    metadata_label: str | None,
) -> ColumnState:
    network.clear_active_state()
    return network.integrate(
        ColumnState.initial(),
        _relay_activation(_indices_for_pattern(pattern), line_id=metadata_label),
        line_id=metadata_label,
        pattern=pattern,
    )


def _bind_with_evidence(
    network: ContextAssemblyNetwork,
    *,
    pattern: Pattern,
    metadata_label: str | None,
    max_trials: int = 8,
) -> str | None:
    """Present until N=2 unique evidence binds (or trials exhausted)."""
    for _ in range(max_trials):
        _present(network, pattern=pattern, metadata_label=metadata_label)
        assert network.ownership_index is not None
        owner = network.ownership_index.owner_for_pattern(pattern)
        if owner is not None:
            return owner
    return None


class TestColumnEmergentBinding:
    def test_biological_assemblies_are_neutral_unbound(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        assert network.assemblies is not None
        assert len(network.assemblies) == policy.representation_capacity
        for assembly in network.assemblies:
            assert assembly.representation_id is not None
            assert assembly.line_id is None
            assert assembly.is_unbound
            assert not assembly.assembly_id.startswith("asm_")

    def test_novel_pattern_recruits_unbound_owner_after_evidence(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        pattern = get_line("H1")
        _present(network, pattern=pattern, metadata_label="H1")
        assert network.last_competition is not None
        assert network.last_competition.has_unique_representation
        assert all(a.is_unbound for a in network.assemblies)

        winner = _bind_with_evidence(
            network, pattern=pattern, metadata_label="H1"
        )
        assert winner is not None
        owner = next(a for a in network.assemblies if a.assembly_id == winner)
        assert owner.is_bound
        assert owner.bound_pattern == pattern
        assert owner.metadata_label == "H1"

    def test_single_presentation_does_not_bind(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        _present(network, pattern=get_line("H1"), metadata_label="H1")
        assert all(a.is_unbound for a in network.assemblies)
        assert network.last_competition is not None
        assert network.last_competition.has_unique_representation

    def test_introduction_order_does_not_force_lexicographic_ownership(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        orders = [
            list(LINE_IDS),
            list(reversed(LINE_IDS)),
            ["V1", "H1", "D1", "D0"],
            ["D0", "D1", "H1", "V1"],
        ]
        mappings: list[dict[str, str]] = []
        for order in orders:
            network = ContextAssemblyNetwork(policy=policy)
            mapping: dict[str, str] = {}
            for line_id in order:
                owner = _bind_with_evidence(
                    network,
                    pattern=get_line(line_id),
                    metadata_label=line_id,
                )
                assert owner is not None, f"failed to bind {line_id} in order {order}"
                mapping[line_id] = owner
            mappings.append(mapping)

        lex = {line_id: f"repr_{index}" for index, line_id in enumerate(LINE_IDS)}
        assert mappings[0] != lex

    def test_binds_actual_pattern_not_line_metadata(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        pattern = get_line("V1")
        owner = _bind_with_evidence(
            network, pattern=pattern, metadata_label="H1"
        )
        assert owner is not None
        bound = next(a for a in network.assemblies if a.is_bound)
        assert bound.bound_pattern == pattern
        assert bound.bound_pattern.edge_ids != get_line("H1").edge_ids

    def test_owned_pattern_routes_only_to_owner(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        pattern = get_line("D0")
        owner_id = _bind_with_evidence(
            network, pattern=pattern, metadata_label="D0"
        )
        assert owner_id is not None
        updated = _present(network, pattern=pattern, metadata_label="D0")
        assert updated.active_assembly_ids == frozenset({owner_id})

    def test_capacity_exhausted_abstains_novel(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        tight = replace(policy, representation_capacity=1)
        network = ContextAssemblyNetwork(policy=tight)
        first = get_line("H1")
        assert (
            _bind_with_evidence(network, pattern=first, metadata_label="H1")
            is not None
        )
        assert network.assemblies is not None
        assert all(a.is_bound for a in network.assemblies)
        second = get_line("V1")
        updated = _present(network, pattern=second, metadata_label="V1")
        assert updated.compact_context_code == 0
        assert not network.last_competition.has_unique_representation

    def test_transition_map_not_mutated_on_biological(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        before = network.learned_transition_map.serialize()
        _present(network, pattern=get_line("H1"), metadata_label="H1")
        assert network.learned_transition_map.serialize() == before

    def test_ownership_collision_index_readonly(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        pattern = get_line("H1")
        assert (
            _bind_with_evidence(network, pattern=pattern, metadata_label="H1")
            is not None
        )
        assert network.ownership_index is not None
        assert not network.ownership_index.has_collision
        owner = network.ownership_index.owner_for_pattern(pattern)
        assert owner is not None

    def test_novel_drives_all_unbound_slots(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        targets = network._eligible_drive_targets(get_line("H1"))
        assert targets == frozenset(a.assembly_id for a in network.assemblies)

    def test_legacy_catalog_assemblies_unchanged(self) -> None:
        network = ContextAssemblyNetwork()
        assert network.assemblies is not None
        assert {a.line_id for a in network.assemblies} == {"H1", "V1", "D0", "D1"}
        assert all(a.assembly_id.startswith("asm_") for a in network.assemblies)

    def test_emergent_evidence_matures_before_optional_latch(self) -> None:
        """Hybrid C: unique-win evidence is observed; latch remains optional readout."""
        from cognative_paradigm.cortical_column.emergent_ownership_evidence import (
            EmergentOwnershipEvidence,
        )

        evidence = EmergentOwnershipEvidence(rf_concentration_threshold=0.01)
        pattern = get_line("H1")
        weights = {i: 0.05 for i in range(9)}
        for edge_id in pattern.edge_ids:
            weights[edge_id_to_index(edge_id)] = 1.0
        assert not evidence.is_mature(pattern, weights)
        evidence.observe_unique_win(pattern)
        assert evidence.unique_wins_for(pattern) == 1
        assert evidence.record_unique_spike(pattern) is True
        assert evidence.unique_wins_for(pattern) >= 2
        assert evidence.is_mature(pattern, weights)

    def test_mismatch_attenuation_prefers_rf_over_latch(self) -> None:
        from cognative_paradigm.cortical_column.emergent_ownership_evidence import (
            EmergentOwnershipEvidence,
        )

        evidence = EmergentOwnershipEvidence(required_unique_wins=2)
        h1 = get_line("H1")
        v1 = get_line("V1")
        weights = {i: 0.05 for i in range(9)}
        for edge_id in h1.edge_ids:
            weights[edge_id_to_index(edge_id)] = 1.0
        evidence.observe_unique_win(h1)
        evidence.observe_unique_win(h1)
        scale = evidence.basal_mismatch_scale(v1, weights, bound_pattern=None)
        assert scale < 0.5
        assert scale >= evidence.mismatch_attenuation - 1e-9

    def test_latch_revisable_on_sustained_mismatch(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        pattern = get_line("H1")
        owner_id = _bind_with_evidence(
            network, pattern=pattern, metadata_label="H1"
        )
        assert owner_id is not None
        owner = next(a for a in network.assemblies if a.assembly_id == owner_id)
        assert owner.is_bound
        other = get_line("V1")
        cleared = False
        for _ in range(8):
            if owner.revise_latch_on_mismatch(other):
                cleared = True
                break
        assert cleared
        assert owner.is_unbound

    def test_column_learned_prefers_emergent_evidence(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        pattern = get_line("D0")
        assert network.column_pattern_is_learned(pattern) is False
        owner_id = _bind_with_evidence(
            network, pattern=pattern, metadata_label="D0"
        )
        assert owner_id is not None
        assert network.column_pattern_is_learned(pattern) is True
