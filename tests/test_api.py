import unittest

from fastapi.testclient import TestClient

from cognative_paradigm.api.main import app
from cognative_paradigm.lines import LINE_IDS, LINE_INDICES


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.post("/api/reset")

    def test_health_endpoint(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["service"], "BrainService")

    def test_learn_all_catalog_patterns_via_api(self) -> None:
        for line_id in LINE_IDS:
            indices = LINE_INDICES[line_id]
            for _ in range(150):
                self.client.post("/api/stimulate", json={"active_indices": indices})
                state = self.client.get("/api/state").json()
                pattern_key = ",".join(
                    sorted(
                        f"input_r{i // 3}_c{i % 3}" for i in sorted(indices)
                    )
                )
                if pattern_key in state["nucleus"]["pattern_owners"]:
                    break
            else:
                self.fail(f"{line_id} did not bind via API within 150 steps")

        training = self.client.get("/api/training").json()
        self.assertTrue(training["equilibrium"])
        self.assertEqual(training["progress"], f"{len(LINE_IDS)}/{len(LINE_IDS)}")

    def test_list_lines_returns_catalog(self) -> None:
        response = self.client.get("/api/lines")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), len(LINE_IDS))

    def test_stimulate_h1_indices(self) -> None:
        response = self.client.post(
            "/api/stimulate",
            json={"active_indices": LINE_INDICES["H1"]},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["active_indices"], [3, 4, 5])
        self.assertIn("state", body)
        self.assertEqual(body["state"]["timestep"], body["timestep"])
        self.assertIn("training", body["state"])

    def test_reset_clears_pattern_owners(self) -> None:
        for _ in range(5):
            self.client.post(
                "/api/stimulate",
                json={"active_indices": LINE_INDICES["H1"]},
            )
        self.client.post("/api/reset")
        state = self.client.get("/api/state").json()
        self.assertEqual(state["nucleus"]["pattern_owners"], {})
        self.assertEqual(state["timestep"], 0)

    def test_reset_restores_default_parameters_in_payload(self) -> None:
        self.client.patch("/api/parameters", json={"eligibility_threshold": 0.5})
        response = self.client.post("/api/reset")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("parameters", body)
        self.assertAlmostEqual(body["parameters"]["eligibility_threshold"], 0.80)
        self.assertEqual(body["state"]["timestep"], 0)

    def test_patch_homeostasis_parameters(self) -> None:
        response = self.client.patch(
            "/api/parameters",
            json={
                "homeostasis_target_rate": 0.18,
                "homeostasis_eta": 0.02,
                "homeostasis_window": 25,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertAlmostEqual(body["homeostasis_target_rate"], 0.18)
        self.assertAlmostEqual(body["homeostasis_eta"], 0.02)
        self.assertEqual(body["homeostasis_window"], 25)

    def test_patch_hybrid_profile_requires_lab_and_applies_atomically(self) -> None:
        rejected = self.client.patch(
            "/api/parameters",
            json={"column_architecture_profile": "hybrid_cortical"},
        )
        self.assertEqual(rejected.status_code, 400)
        unchanged = self.client.get("/api/parameters").json()
        self.assertEqual(
            unchanged["column_architecture_profile"],
            "compatibility",
        )

        activated = self.client.patch(
            "/api/parameters",
            json={
                "column_architecture_profile": "hybrid_cortical",
                "lab_profile_enabled": True,
                "episode_silence_reset_ms": 2400.0,
            },
        )
        self.assertEqual(activated.status_code, 200)
        params = activated.json()
        self.assertEqual(params["column_architecture_profile"], "hybrid_cortical")
        self.assertTrue(params["lab_profile_enabled"])
        self.assertEqual(params["episode_silence_reset_ms"], 2400.0)
        self.assertIn("cortical_column", self.client.get("/api/state").json())

    def test_patch_biological_hybrid_requires_lab_and_soft_force_gates(self) -> None:
        rejected = self.client.patch(
            "/api/parameters",
            json={"column_architecture_profile": "hybrid_cortical_biological"},
        )
        self.assertEqual(rejected.status_code, 400)

        activated = self.client.patch(
            "/api/parameters",
            json={
                "column_architecture_profile": "hybrid_cortical_biological",
                "lab_profile_enabled": True,
            },
        )
        self.assertEqual(activated.status_code, 200)
        params = activated.json()
        self.assertEqual(
            params["column_architecture_profile"],
            "hybrid_cortical_biological",
        )
        self.assertTrue(params["lab_profile_enabled"])
        self.assertFalse(params["pretrained_inhibitor_exclusivity_enabled"])
        self.assertEqual(params["descending_mode"], "graded")
        self.assertIn("cortical_column", self.client.get("/api/state").json())

    def test_switching_back_to_compatibility_removes_column_state(self) -> None:
        self.client.patch(
            "/api/parameters",
            json={
                "column_architecture_profile": "hybrid_cortical",
                "lab_profile_enabled": True,
            },
        )
        response = self.client.patch(
            "/api/parameters",
            json={"column_architecture_profile": "compatibility"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["column_architecture_profile"],
            "compatibility",
        )
        self.assertNotIn("cortical_column", self.client.get("/api/state").json())

    def test_end_column_episode_requires_hybrid_profile(self) -> None:
        response = self.client.post("/api/column/end-episode")
        self.assertEqual(response.status_code, 409)
        self.assertIn("inactive", response.json()["detail"])

    def test_end_column_episode_learns_d1_to_end_and_returns_state(self) -> None:
        self.client.patch(
            "/api/parameters",
            json={
                "column_architecture_profile": "hybrid_cortical",
                "lab_profile_enabled": True,
            },
        )
        for _ in range(2):
            for line_id in LINE_IDS:
                response = self.client.post(
                    "/api/stimulate",
                    json={"line_id": line_id},
                )
                self.assertEqual(response.status_code, 200)
            ended = self.client.post("/api/column/end-episode")
            self.assertEqual(ended.status_code, 200)

        body = ended.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["boundary"]["reason"], "explicit_end")
        column = body["state"]["cortical_column"]
        self.assertEqual(column["sequence_index"], 0)
        self.assertIn(
            {"from": "D1", "to": "END", "count": 2},
            column["predictor"]["transitions"],
        )
        self.assertEqual(column["last_activation"]["line_id"], "D1")

    def test_learn_and_recognize_via_api(self) -> None:
        indices = LINE_INDICES["H1"]
        for _ in range(150):
            self.client.post("/api/stimulate", json={"active_indices": indices})
            state = self.client.get("/api/state").json()
            if state["training"]["bound_pattern_count"] > 0:
                break
        else:
            self.fail("H1 pattern did not bind via API within 150 steps")

        state = self.client.get("/api/state").json()
        self.assertTrue(state["bound"])

        for _ in range(80):
            result = self.client.post(
                "/api/stimulate",
                json={"active_indices": indices},
            ).json()
            if result["output_symbol"]:
                break
        else:
            self.fail("H1 not recognized via API")

        self.assertTrue(str(result["output_symbol"]).startswith("sigma_"))


    def test_raster_feed_records_stimulation_steps(self) -> None:
        empty = self.client.get("/api/raster-feed").json()
        self.assertEqual(empty["seq"], 0)
        self.assertEqual(empty["steps"], [])

        self.client.post(
            "/api/stimulate",
            json={"active_indices": LINE_INDICES["H1"]},
        )
        feed = self.client.get("/api/raster-feed").json()
        self.assertEqual(feed["seq"], 1)
        self.assertEqual(len(feed["steps"]), 1)
        step = feed["steps"][0]["step"]
        self.assertEqual(step["timestep"], 1)
        self.assertIn("step_events", step)
        self.assertIn("state", feed["steps"][0])

    def test_raster_feed_incremental_since_seq(self) -> None:
        for _ in range(3):
            self.client.post(
                "/api/stimulate",
                json={"active_indices": LINE_INDICES["H1"]},
            )
        partial = self.client.get("/api/raster-feed?since_seq=2").json()
        self.assertEqual(len(partial["steps"]), 1)
        self.assertEqual(partial["steps"][0]["seq"], 3)

    def test_raster_feed_reset_generation(self) -> None:
        self.client.post(
            "/api/stimulate",
            json={"active_indices": LINE_INDICES["H1"]},
        )
        before = self.client.get("/api/raster-feed").json()
        self.client.post("/api/reset")
        after = self.client.get(
            f"/api/raster-feed?generation={before['generation']}"
        ).json()
        self.assertTrue(after["reset"])
        self.assertEqual(after["seq"], 0)
        self.assertEqual(after["steps"], [])


if __name__ == "__main__":
    unittest.main()
