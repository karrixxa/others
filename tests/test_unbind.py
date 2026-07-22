import unittest

from fastapi.testclient import TestClient

from cognative_paradigm.api.main import app
from cognative_paradigm.lines import LINE_INDICES


class UnbindTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.post("/api/reset")

    def _bind_pattern(self, indices: list[int], max_steps: int = 150) -> None:
        for _ in range(max_steps):
            self.client.post("/api/stimulate", json={"active_indices": indices})
            state = self.client.get("/api/state").json()
            if state["nucleus"]["pattern_owners"]:
                return
        self.fail(f"pattern {indices} did not bind within {max_steps} steps")

    def test_unbind_releases_pattern_and_allows_rebind(self) -> None:
        indices = LINE_INDICES["H1"]
        self._bind_pattern(indices)

        response = self.client.post("/api/unbind", json={"active_indices": indices})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertIn("neuron_id", body)

        state = body["state"]
        self.assertEqual(state["nucleus"]["pattern_owners"], {})
        self.assertEqual(state["training"]["bound_pattern_count"], 0)

        self._bind_pattern(indices)
        state = self.client.get("/api/state").json()
        self.assertEqual(state["training"]["bound_pattern_count"], 1)

    def test_unbind_unbound_pattern_returns_400(self) -> None:
        response = self.client.post(
            "/api/unbind",
            json={"active_indices": LINE_INDICES["H1"]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not bound", response.json()["detail"].lower())

    def test_state_includes_stdp_weights(self) -> None:
        self.client.post(
            "/api/stimulate",
            json={"active_indices": LINE_INDICES["H1"]},
        )
        state = self.client.get("/api/state").json()
        weights = state["stdp_weights"]
        self.assertEqual(len(weights["grid"]), 3)
        self.assertEqual(len(weights["grid"][0]), 3)
        self.assertIn("min_weight", weights)
        self.assertIn("max_weight", weights)


if __name__ == "__main__":
    unittest.main()
