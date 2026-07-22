import unittest

from fastapi.testclient import TestClient

from cognative_paradigm.api.main import app


class UnbindPatternTests(unittest.TestCase):
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

    def test_unbind_pattern_releases_owner(self) -> None:
        indices = [0, 1, 2]
        self._bind_pattern(indices)

        response = self.client.post("/api/unbind", json={"active_indices": indices})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertIn("neuron_id", body)
        self.assertEqual(body["active_indices"], indices)

        state = body["state"]
        self.assertEqual(state["nucleus"]["pattern_owners"], {})

        self._bind_pattern(indices)
        state = self.client.get("/api/state").json()
        self.assertEqual(len(state["nucleus"]["pattern_owners"]), 1)

    def test_unbind_unbound_pattern_returns_400(self) -> None:
        response = self.client.post("/api/unbind", json={"active_indices": [0, 1, 2]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("not bound", response.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
