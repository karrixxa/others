"""Ensure compatibility profile leaves production engine path isolated."""

from dataclasses import asdict

import pytest

from cognative_paradigm.domain.column_profile import ColumnCausalPolicy
from cognative_paradigm.learning.lab_profile import BiologicalLabProfileFactory
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import (
    DEFAULT_LEARNING_DYNAMICS,
    LearningDynamics,
)


@pytest.mark.cortical_column_lab
class TestColumnProfileIsolation:
    def test_default_simulator_has_no_cortical_column(self) -> None:
        sim = BrainSimulator()
        assert sim.cortical_column is None
        assert "cortical_column" not in sim.get_state()

    def test_compatibility_stimulate_pattern_unchanged(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        result = sim.stimulate_pattern(get_line("H1"), line_id="H1")
        assert result.relay_indices == [3, 4, 5]
        assert sim.cortical_column is None

    def test_hybrid_off_lab_preset_stays_compatibility(self) -> None:
        p3 = BiologicalLabProfileFactory.dynamics("P3")
        assert p3.column_architecture_profile == "compatibility"
        sim = BrainSimulator(dynamics=p3)
        assert sim.cortical_column is None

    def test_production_dynamics_dict_unchanged_except_new_safe_defaults(self) -> None:
        fresh = asdict(LearningDynamics())
        defaults = asdict(DEFAULT_LEARNING_DYNAMICS)
        assert fresh == defaults
        assert defaults["column_architecture_profile"] == "compatibility"

    def test_legacy_and_biological_hybrids_are_isolated(self) -> None:
        legacy = BiologicalLabProfileFactory.hybrid_column_dynamics()
        biological = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        assert legacy.column_architecture_profile == "hybrid_cortical"
        assert biological.column_architecture_profile == "hybrid_cortical_biological"
        assert legacy.uses_hybrid_column() is True
        assert biological.uses_hybrid_column() is True
        assert legacy.uses_biological_hybrid_column() is False
        assert biological.uses_biological_hybrid_column() is True

        legacy_policy = ColumnCausalPolicy.for_profile("hybrid_cortical")
        bio_policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        assert legacy_policy.schema_version == 1
        assert bio_policy.schema_version == 2
        assert legacy_policy.allow_l4_input_fallback is True
        assert bio_policy.allow_l4_input_fallback is False

        legacy_sim = BrainSimulator(dynamics=legacy)
        bio_sim = BrainSimulator(dynamics=biological)
        assert legacy_sim.cortical_column is not None
        assert bio_sim.cortical_column is not None
        assert legacy_sim.cortical_column.policy.schema_version == 1
        assert bio_sim.cortical_column.policy.schema_version == 2
