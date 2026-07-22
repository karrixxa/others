"""Unit tests for L4 Layer4Adapter."""

from dataclasses import replace

import pytest

from cognative_paradigm.cortical_column.layer4_adapter import Layer4Adapter
from cognative_paradigm.domain.column_signal import CellGainMap
from cognative_paradigm.domain.input_edge import InputEdge
from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.lines import LINE_INDICES, index_to_edge_id
from cognative_paradigm.simulation.layer1_network import Layer1Relay
from cognative_paradigm.simulation.layer1_relay import parse_l1_relay_index
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics


def _build_edges(baseline: float = 2.0) -> dict[str, InputEdge]:
    edges: dict[str, InputEdge] = {}
    for index in range(9):
        key = index_to_edge_id(index)
        row, col = divmod(index, 3)
        edges[key] = InputEdge(id=key, row=row, col=col, weight=baseline)
    return edges


def _relay_indices(
    relay: Layer1Relay,
    edges: dict[str, InputEdge],
    active_indices: frozenset[int],
    timestep: int,
) -> frozenset[int]:
    active_edge_ids = frozenset(index_to_edge_id(i) for i in active_indices)
    ephemeral = {
        key: replace(edge, last_event_t=None) for key, edge in edges.items()
    }
    for edge_key in active_edge_ids:
        ephemeral[edge_key].register_event(timestep)
    firing = relay.process_step(timestep, active_edge_ids, ephemeral, descending=None)
    return frozenset(
        index
        for relay_id in firing.excitatory
        for index in [parse_l1_relay_index(relay_id)]
        if index is not None
    )


class TestLayer4Adapter:
    def test_unity_gain_matches_direct_relay_behavior(self) -> None:
        dynamics = LearningDynamics(scaling_eta=0.0)
        lif = LifDynamics(dynamics.lif_parameters())
        relay = Layer1Relay(lif, dynamics=dynamics)
        persistent_edges = _build_edges(dynamics.sensory_baseline_weight)
        adapter = Layer4Adapter(relay, persistent_edges, dynamics=dynamics)

        line_id = "H1"
        indices = Layer4Adapter.line_indices(line_id)

        direct = _relay_indices(relay, persistent_edges, indices, timestep=1)
        relay.reset()
        adapter.reset()
        activation = adapter.process(
            line_id,
            indices,
            pending_gain=CellGainMap.unity(),
        )

        assert activation.modulated_cell_indices == direct
        assert activation.active_cell_indices == indices

    def test_ephemeral_gain_does_not_mutate_persistent_weights(self) -> None:
        dynamics = LearningDynamics(scaling_eta=0.0)
        lif = LifDynamics(dynamics.lif_parameters())
        relay = Layer1Relay(lif, dynamics=dynamics)
        persistent_edges = _build_edges(dynamics.sensory_baseline_weight)
        baseline_snapshot = {key: edge.weight for key, edge in persistent_edges.items()}
        adapter = Layer4Adapter(relay, persistent_edges, dynamics=dynamics)

        gains = CellGainMap(gains=(0.0, 0.0, 0.0, 2.0, 2.0, 2.0, 0.0, 0.0, 0.0))
        adapter.process(
            "H1",
            Layer4Adapter.line_indices("H1"),
            pending_gain=gains,
        )

        for key, edge in persistent_edges.items():
            assert edge.weight == baseline_snapshot[key]

    def test_zero_gain_suppresses_cells(self) -> None:
        dynamics = LearningDynamics(scaling_eta=0.0)
        lif = LifDynamics(dynamics.lif_parameters())
        relay = Layer1Relay(lif, dynamics=dynamics)
        persistent_edges = _build_edges(dynamics.sensory_baseline_weight)
        adapter = Layer4Adapter(relay, persistent_edges, dynamics=dynamics)

        gains = CellGainMap(gains=(0.0,) * 9)
        activation = adapter.process(
            "H1",
            Layer4Adapter.line_indices("H1"),
            pending_gain=gains,
        )

        assert activation.modulated_cell_indices == frozenset()

    def test_boosted_gain_can_change_firing_set(self) -> None:
        dynamics = LearningDynamics(
            scaling_eta=0.0,
            sensory_baseline_weight=0.2,
            l1_excitatory_threshold=0.45,
        )
        lif = LifDynamics(dynamics.lif_parameters())
        relay = Layer1Relay(lif, dynamics=dynamics)
        persistent_edges = _build_edges(dynamics.sensory_baseline_weight)
        adapter = Layer4Adapter(relay, persistent_edges, dynamics=dynamics)

        unity = adapter.process(
            "H1",
            Layer4Adapter.line_indices("H1"),
            pending_gain=CellGainMap.unity(),
        )
        relay.reset()
        adapter.reset()
        boosted = adapter.process(
            "H1",
            Layer4Adapter.line_indices("H1"),
            pending_gain=CellGainMap(gains=(3.0,) * 9),
        )

        assert len(boosted.modulated_cell_indices) >= len(unity.modulated_cell_indices)

    def test_line_indices_match_catalog(self) -> None:
        assert Layer4Adapter.line_indices("V1") == frozenset(LINE_INDICES["V1"])

    def test_biological_policy_keeps_relay_silence_empty(self) -> None:
        from cognative_paradigm.domain.column_profile import ColumnCausalPolicy

        dynamics = LearningDynamics(
            scaling_eta=0.0,
            sensory_baseline_weight=0.01,
            l1_excitatory_threshold=10.0,
            column_architecture_profile="hybrid_cortical_biological",
            lab_profile_enabled=True,
            pretrained_inhibitor_exclusivity_enabled=False,
            descending_mode="graded",
        )
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        lif = LifDynamics(dynamics.lif_parameters())
        relay = Layer1Relay(lif, dynamics=dynamics)
        persistent_edges = _build_edges(dynamics.sensory_baseline_weight)
        adapter = Layer4Adapter(
            relay, persistent_edges, dynamics=dynamics, policy=policy
        )

        indices = Layer4Adapter.line_indices("H1")
        activation = adapter.process(
            "H1",
            indices,
            pending_gain=CellGainMap.unity(),
        )

        assert activation.input_cell_indices == indices
        assert activation.gain_gated_input_indices == indices
        assert activation.relay_spike_indices == frozenset()
        assert activation.modulated_cell_indices == frozenset()
