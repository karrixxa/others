import unittest

from cognative_paradigm.api.service import BrainService, ParametersPatch
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS


class ParametersApiTests(unittest.TestCase):
    def test_get_parameters_returns_defaults(self) -> None:
        service = BrainService()
        params = service.get_parameters()
        self.assertEqual(
            params["eligibility_threshold"],
            DEFAULT_LEARNING_DYNAMICS.eligibility_threshold,
        )
        self.assertEqual(
            params["scaling_target_rate"],
            DEFAULT_LEARNING_DYNAMICS.scaling_target_rate,
        )

    def test_update_eligibility_threshold(self) -> None:
        service = BrainService()
        updated = service.update_parameters(ParametersPatch(eligibility_threshold=0.75))
        self.assertEqual(updated["eligibility_threshold"], 0.75)

    def test_update_nucleus_threshold(self) -> None:
        service = BrainService()
        updated = service.update_parameters(ParametersPatch(nucleus_threshold=1.5))
        self.assertEqual(updated["nucleus_threshold"], 1.5)
        self.assertEqual(service.simulator.nucleus.ring[0].neuron.threshold, 1.5)

    def test_update_scaling_parameters(self) -> None:
        service = BrainService()
        updated = service.update_parameters(
            ParametersPatch(
                scaling_target_rate=0.18,
                scaling_eta=0.02,
                scaling_window=25,
            ),
        )
        self.assertAlmostEqual(updated["scaling_target_rate"], 0.18)
        self.assertAlmostEqual(updated["scaling_eta"], 0.02)
        self.assertEqual(updated["scaling_window"], 25)

    def test_homeostasis_aliases_map_to_scaling(self) -> None:
        service = BrainService()
        updated = service.update_parameters(
            ParametersPatch(
                homeostasis_target_rate=0.20,
                homeostasis_eta=0.015,
                homeostasis_window=30,
            ),
        )
        self.assertAlmostEqual(updated["scaling_target_rate"], 0.20)
        self.assertAlmostEqual(updated["homeostasis_target_rate"], 0.20)
        self.assertAlmostEqual(updated["scaling_eta"], 0.015)
        self.assertEqual(updated["scaling_window"], 30)

    def test_rejects_out_of_range_eligibility(self) -> None:
        service = BrainService()
        with self.assertRaises(ValueError):
            service.update_parameters(ParametersPatch(eligibility_threshold=0.0))

    def test_hybrid_profile_activation_is_atomic_and_lab_gated(self) -> None:
        service = BrainService()

        with self.assertRaisesRegex(ValueError, "lab_profile_enabled"):
            service.update_parameters(
                ParametersPatch(column_architecture_profile="hybrid_cortical")
            )

        self.assertEqual(
            service.get_parameters()["column_architecture_profile"],
            "compatibility",
        )
        self.assertIsNone(service.simulator.cortical_column)

        updated = service.update_parameters(
            ParametersPatch(
                column_architecture_profile="hybrid_cortical",
                lab_profile_enabled=True,
                episode_silence_reset_ms=2500.0,
            )
        )
        self.assertEqual(updated["column_architecture_profile"], "hybrid_cortical")
        self.assertTrue(updated["lab_profile_enabled"])
        self.assertEqual(updated["episode_silence_reset_ms"], 2500.0)
        self.assertIsNotNone(service.simulator.cortical_column)

    def test_biological_hybrid_profile_activation_is_lab_gated(self) -> None:
        service = BrainService()

        with self.assertRaisesRegex(ValueError, "lab_profile_enabled"):
            service.update_parameters(
                ParametersPatch(
                    column_architecture_profile="hybrid_cortical_biological"
                )
            )

        updated = service.update_parameters(
            ParametersPatch(
                column_architecture_profile="hybrid_cortical_biological",
                lab_profile_enabled=True,
            )
        )
        self.assertEqual(
            updated["column_architecture_profile"],
            "hybrid_cortical_biological",
        )
        self.assertTrue(updated["lab_profile_enabled"])
        self.assertFalse(updated["pretrained_inhibitor_exclusivity_enabled"])
        self.assertEqual(updated["descending_mode"], "graded")
        self.assertIsNotNone(service.simulator.cortical_column)
        self.assertTrue(
            service.simulator.cortical_column.policy.is_biological
        )

    def test_switching_to_compatibility_removes_column(self) -> None:
        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                column_architecture_profile="hybrid_cortical",
                lab_profile_enabled=True,
            )
        )
        updated = service.update_parameters(
            ParametersPatch(column_architecture_profile="compatibility")
        )
        self.assertEqual(updated["column_architecture_profile"], "compatibility")
        self.assertIsNone(service.simulator.cortical_column)

    def test_rejects_non_finite_episode_silence_without_mutation(self) -> None:
        service = BrainService()
        before = service.get_parameters()["episode_silence_reset_ms"]
        with self.assertRaisesRegex(ValueError, "positive finite"):
            service.update_parameters(
                ParametersPatch(episode_silence_reset_ms=float("nan"))
            )
        self.assertEqual(
            service.get_parameters()["episode_silence_reset_ms"],
            before,
        )

    def test_reset_restores_default_parameters(self) -> None:
        service = BrainService()
        service.update_parameters(
            ParametersPatch(eligibility_threshold=0.5, nucleus_threshold=1.8)
        )
        payload = service.reset()
        params = payload["parameters"]
        self.assertEqual(
            params["eligibility_threshold"],
            DEFAULT_LEARNING_DYNAMICS.eligibility_threshold,
        )
        self.assertEqual(
            params["nucleus_threshold"],
            DEFAULT_LEARNING_DYNAMICS.nucleus_threshold,
        )


if __name__ == "__main__":
    unittest.main()
