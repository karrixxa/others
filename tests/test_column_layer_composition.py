"""Composed column-layer tests (no engine wiring)."""

from cognative_paradigm.cortical_column.context_assembly_network import (
    ContextAssemblyNetwork,
)
from cognative_paradigm.cortical_column.feedback_gain_controller import (
    FeedbackGainController,
)
from cognative_paradigm.cortical_column.layer4_adapter import Layer4Adapter
from cognative_paradigm.cortical_column.next_line_predictor import NextLinePredictor
from cognative_paradigm.domain.column_signal import CellGainMap, EPISODE_END_PREDICTION
from cognative_paradigm.domain.column_state import ColumnState
from cognative_paradigm.domain.input_edge import InputEdge
from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.lines import LINE_IDS, index_to_edge_id
from cognative_paradigm.simulation.layer1_network import Layer1Relay
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics


def _build_edges(baseline: float = 2.0) -> dict[str, InputEdge]:
    edges: dict[str, InputEdge] = {}
    for index in range(9):
        key = index_to_edge_id(index)
        row, col = divmod(index, 3)
        edges[key] = InputEdge(id=key, row=row, col=col, weight=baseline)
    return edges


class TestColumnLayerComposition:
    def test_full_episode_step_chain_without_engine(self) -> None:
        dynamics = LearningDynamics(scaling_eta=0.0)
        lif = LifDynamics(dynamics.lif_parameters())
        relay = Layer1Relay(lif, dynamics=dynamics)
        persistent_edges = _build_edges(dynamics.sensory_baseline_weight)

        l4 = Layer4Adapter(relay, persistent_edges, dynamics=dynamics)
        l23 = ContextAssemblyNetwork()
        l5 = NextLinePredictor()
        l6 = FeedbackGainController()

        for from_line, to_line in zip(
            LINE_IDS,
            list(LINE_IDS[1:]) + [EPISODE_END_PREDICTION],
        ):
            for _ in range(3):
                l5.record_transition(from_line, to_line)

        state = ColumnState.initial()
        for step_index, line_id in enumerate(LINE_IDS):
            activation = l4.process(
                line_id,
                Layer4Adapter.line_indices(line_id),
                pending_gain=state.pending_gain,
            )
            state = l6.consume_pending_gain(state)
            assert state.pending_gain == CellGainMap.unity()
            state = l23.integrate(state, activation, line_id=line_id)
            prediction = l5.predict(state)
            state = l6.apply_to_state(state, prediction)
            assert state.sequence_index == step_index + 1

        end_state = ColumnState.initial().with_line_observed("D1")
        end_prediction = l5.predict(end_state)
        assert end_prediction.is_episode_end
        assert l6.compute_gain_from_prediction(end_prediction) == CellGainMap.unity()
