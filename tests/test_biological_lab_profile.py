"""Composition tests for cumulative biological lab presets."""

import pytest

from cognative_paradigm.learning.lab_profile import (
    BiologicalLabPreset,
    BiologicalLabProfile,
    BiologicalLabProfileFactory,
)
from cognative_paradigm.simulation.learning_dynamics import (
    DEFAULT_LEARNING_DYNAMICS,
)


@pytest.mark.biological_lab
class TestBiologicalLabProfile:
    def test_apply_to_copies_without_mutating_production(self) -> None:
        lab = BiologicalLabProfileFactory.dynamics(BiologicalLabPreset.P2)

        assert lab is not DEFAULT_LEARNING_DYNAMICS
        assert lab.lab_profile_enabled is True
        assert lab.plasticity_mode == "triplet"
        assert DEFAULT_LEARNING_DYNAMICS.plasticity_mode == "conductance"
        assert DEFAULT_LEARNING_DYNAMICS.lab_profile_enabled is False

    @pytest.mark.parametrize(
        ("preset", "expected"),
        [
            ("P3", {"dual_eligibility_enabled": True}),
            (
                "P4",
                {
                    "plastic_ni_enabled": True,
                    "inhibitory_stdp_enabled": True,
                    "inhibitory_turnover_enabled": False,
                    "pretrained_inhibitor_exclusivity_enabled": False,
                },
            ),
            ("P5", {"scaling_lab_enabled": True}),
            (
                "P6",
                {
                    "descending_mode": "graded",
                    "pretrained_inhibitor_exclusivity_enabled": False,
                },
            ),
            ("P7", {"offline_replay_enabled": True}),
            ("FULL", {"offline_replay_enabled": True}),
        ],
    )
    def test_named_presets_compose_cumulatively(
        self,
        preset: str,
        expected: dict[str, object],
    ) -> None:
        dynamics = BiologicalLabProfileFactory.dynamics(preset)
        assert dynamics.plasticity_mode == "triplet"
        for field, value in expected.items():
            assert getattr(dynamics, field) == value

    def test_invalid_graded_hard_exclusivity_is_rejected(self) -> None:
        profile = BiologicalLabProfile(
            descending_mode="graded",
            pretrained_inhibitor_exclusivity_enabled=True,
        )
        with pytest.raises(ValueError, match="soft inhibitor"):
            profile.to_dynamics()

    def test_hybrid_column_preset_enables_lab_column_path(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_column_dynamics()
        assert dynamics.lab_profile_enabled is True
        assert dynamics.column_architecture_profile == "hybrid_cortical"
        assert dynamics.uses_hybrid_column() is True
        assert dynamics.uses_biological_hybrid_column() is False
        assert dynamics.episode_silence_reset_ms == 5000.0
        assert dynamics.plasticity_mode == "conductance"

    def test_hybrid_biological_preset_enables_strict_lab_path(self) -> None:
        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        assert dynamics.lab_profile_enabled is True
        assert dynamics.column_architecture_profile == "hybrid_cortical_biological"
        assert dynamics.uses_hybrid_column() is True
        assert dynamics.uses_biological_hybrid_column() is True
        assert dynamics.pretrained_inhibitor_exclusivity_enabled is False
        assert dynamics.descending_mode == "graded"

    def test_hybrid_column_does_not_mutate_p7_preset(self) -> None:
        p7 = BiologicalLabProfileFactory.dynamics(BiologicalLabPreset.P7)
        hybrid = BiologicalLabProfileFactory.hybrid_column_dynamics()
        assert p7.column_architecture_profile == "compatibility"
        assert hybrid.offline_replay_enabled is False
        assert p7.offline_replay_enabled is True
