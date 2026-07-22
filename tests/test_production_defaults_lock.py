"""Hard locks separating production dynamics from biological lab experiments."""

from dataclasses import asdict

from cognative_paradigm.simulation.learning_dynamics import (
    DEFAULT_LEARNING_DYNAMICS,
    LearningDynamics,
    ProductionForceCascadeDefaults,
)


class TestProductionDefaultsLock:
    def test_default_singleton_matches_fresh_production_dynamics(self) -> None:
        assert asdict(DEFAULT_LEARNING_DYNAMICS) == asdict(LearningDynamics())

    def test_biology_stack_remains_lab_only(self) -> None:
        dynamics = DEFAULT_LEARNING_DYNAMICS
        assert dynamics.lab_profile_enabled is False
        assert dynamics.plasticity_mode == "conductance"
        assert dynamics.dual_eligibility_enabled is False
        assert dynamics.plastic_ni_enabled is False
        assert dynamics.inhibitory_stdp_enabled is False
        assert dynamics.scaling_lab_enabled is False
        assert dynamics.offline_replay_enabled is False

    def test_production_force_cascade_stays_locked(self) -> None:
        dynamics = DEFAULT_LEARNING_DYNAMICS
        # Force exclusivity doctrine: NI wipe + same-tick L1I (no soft race).
        assert dynamics.pretrained_inhibitor_exclusivity_enabled is True
        assert dynamics.descending_mode == "force"
        assert dynamics.emergent_autonomy_enabled is False
        assert dynamics.ecological_stimulus_mode == "mastery"
        assert dynamics.scaling_eta == 0.0

    def test_one_shot_l1i_gain_meets_secondary_threshold(self) -> None:
        dynamics = DEFAULT_LEARNING_DYNAMICS
        assert (
            dynamics.l2_to_l1_i_gain
            >= dynamics.l1_secondary_excitatory_threshold
        )
        assert dynamics.l2_to_l1_i_gain == (
            ProductionForceCascadeDefaults.L2_TO_L1_I_GAIN
        )
        assert dynamics.l1_secondary_excitatory_threshold == (
            ProductionForceCascadeDefaults.SECONDARY_EXCITATORY_THRESHOLD
        )

    def test_column_architecture_defaults_to_compatibility(self) -> None:
        dynamics = DEFAULT_LEARNING_DYNAMICS
        assert dynamics.column_architecture_profile == "compatibility"
        assert dynamics.episode_silence_reset_ms == 5000.0
        assert dynamics.uses_hybrid_column() is False
        assert dynamics.uses_biological_hybrid_column() is False

    def test_stage7_multiplicative_stubs_default_off(self) -> None:
        dynamics = DEFAULT_LEARNING_DYNAMICS
        assert dynamics.local_multiplicative_gain_enabled is False
        assert dynamics.local_multiplicative_gain == 1.0
        assert dynamics.multiplicative_metric_hooks_enabled is False

    def test_stage9_dendritic_flags_default_off(self) -> None:
        dynamics = DEFAULT_LEARNING_DYNAMICS
        assert dynamics.dendritic_coincidence_enabled is False
        assert dynamics.nucleus_dendritic_coincidence_enabled is False

    def test_stage14_autonomy_is_labeled_control(self) -> None:
        dynamics = DEFAULT_LEARNING_DYNAMICS
        assert dynamics.emergent_autonomy_enabled is False
        assert dynamics.pretrained_inhibitor_exclusivity_enabled is True
        assert dynamics.descending_mode == "force"

    def test_bio_column_enables_soft_graded_autonomy(self) -> None:
        from cognative_paradigm.learning.lab_profile import BiologicalLabProfileFactory

        dynamics = BiologicalLabProfileFactory.hybrid_biological_dynamics()
        assert dynamics.emergent_autonomy_enabled is True
        assert dynamics.uses_biological_hybrid_column() is True
        assert dynamics.dendritic_coincidence_enabled is True
        assert dynamics.pretrained_inhibitor_exclusivity_enabled is False
        assert dynamics.descending_mode == "graded"
