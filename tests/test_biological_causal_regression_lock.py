"""Path 0 — regression lock for biological causal gates (Stages 0–3).

These locks must remain green while Stage 8+ emergent remediation proceeds.
Known PARTIAL gaps are documented in comments; they are not claimed PASS.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from cognative_paradigm.cortical_column.column_architecture_factory import (
    ColumnArchitectureFactory,
)
from cognative_paradigm.cortical_column.feedback_gain_controller import (
    FeedbackGainController,
)
from cognative_paradigm.cortical_column.layer4_adapter import Layer4Adapter
from cognative_paradigm.diagnostics.column_metric_pack import ColumnMetricPack
from cognative_paradigm.domain.column_profile import ColumnCausalPolicy
from cognative_paradigm.domain.column_signal import CellGainMap, ColumnPrediction
from cognative_paradigm.domain.input_edge import InputEdge
from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.learning.lab_profile import BiologicalLabProfileFactory
from cognative_paradigm.lines import LINE_INDICES, get_line, index_to_edge_id
from cognative_paradigm.simulation.layer1_network import Layer1Relay
from cognative_paradigm.simulation.learning_dynamics import validate_learning_dynamics


@pytest.mark.cortical_column_lab
class TestBiologicalCausalRegressionLock:
    """Must-stay-locked causal safety for hybrid_cortical_biological."""

    def test_policy_forbids_forced_win_levers(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        assert policy.is_biological is True
        assert policy.allow_l4_input_fallback is False
        assert policy.require_authentic_l4_spikes is True
        assert policy.force_modes_reachable is False
        assert policy.unknown_prediction_emits_catalog_placeholder is False
        assert policy.gain_mode == "unity_unless_local_connected"
        assert policy.competition_mode == "authentic_spike_only"
        assert policy.learn_without_unique_representation is False

    def test_lab_factory_forbids_exclusivity_and_force_descending(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        assert dynamics.pretrained_inhibitor_exclusivity_enabled is False
        assert dynamics.descending_mode == "graded"
        assert dynamics.dendritic_coincidence_enabled is True
        with pytest.raises(ValueError, match="forbids"):
            validate_learning_dynamics(
                replace(dynamics, pretrained_inhibitor_exclusivity_enabled=True)
            )
        with pytest.raises(ValueError, match="forbids"):
            validate_learning_dynamics(replace(dynamics, descending_mode="force"))

    def test_l4_empty_relay_does_not_fallback_to_input(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        lif = LifDynamics(dynamics.lif_parameters())
        relay = Layer1Relay(lif, dynamics=dynamics)
        edges: dict[str, InputEdge] = {}
        for index in range(9):
            key = index_to_edge_id(index)
            row, col = divmod(index, 3)
            edges[key] = InputEdge(
                id=key,
                row=row,
                col=col,
                weight=dynamics.sensory_baseline_weight,
            )
        adapter = Layer4Adapter(
            relay,
            edges,
            dynamics=dynamics,
            policy=ColumnCausalPolicy.for_profile("hybrid_cortical_biological"),
        )
        indices = frozenset(LINE_INDICES["H1"])
        silent_gain = CellGainMap(gains=tuple(0.0 for _ in range(9)))
        activation = adapter.process("H1", indices, pending_gain=silent_gain)
        assert activation.relay_spike_indices == frozenset()
        assert activation.input_cell_indices == indices
        assert activation.modulated_cell_indices == frozenset()

    def test_unknown_prediction_is_not_catalog_placeholder(self) -> None:
        column = ColumnArchitectureFactory.create(
            BiologicalLabProfileFactory.hybrid_biological_dynamics()
        )
        assert column is not None
        result = column.process_pattern("H1", get_line("H1"))
        prediction = result.step.prediction
        assert prediction is not None
        assert prediction.is_unknown is True
        assert prediction.predicted_line_id == "UNKNOWN"
        assert prediction.confidence == 0.0

    def test_abstention_keeps_unity_gain(self) -> None:
        controller = FeedbackGainController(
            policy=ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        )
        gain = controller.compute_gain_from_prediction(ColumnPrediction.unknown())
        assert list(gain.gains) == [1.0] * 9

    def test_causal_safety_pack_exact_zeros(self) -> None:
        column = ColumnArchitectureFactory.create(
            BiologicalLabProfileFactory.hybrid_biological_dynamics()
        )
        assert column is not None
        snapshot = ColumnMetricPack().evaluate_causal_safety(column, episodes=2)
        assert snapshot.passes_exact_zero()
        assert snapshot.false_winner_count == 0
        assert snapshot.l4_fabrication_count == 0

    def test_legacy_hybrid_still_allows_forced_win_levers(self) -> None:
        legacy = ColumnCausalPolicy.for_profile("hybrid_cortical")
        assert legacy.allow_l4_input_fallback is True
        assert legacy.force_modes_reachable is True
        assert legacy.competition_mode == "max_vm_catalog_tiebreak"

    # Stage 8+ paths 1–5 remediate: recruitment, N=2 bind, local END,
    # prior_active_bias retirement, predictive spikes, column_only_stimulate.
