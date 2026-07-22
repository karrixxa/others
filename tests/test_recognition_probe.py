import unittest

from fastapi.testclient import TestClient

from cognative_paradigm.api.main import app
from cognative_paradigm.lines import LINE_INDICES


class RecognitionProbeApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.post("/api/reset")

    def _learn_catalog_line(self, line_id: str, max_steps: int = 150) -> None:
        indices = LINE_INDICES[line_id]
        for _ in range(max_steps):
            self.client.post("/api/stimulate", json={"active_indices": indices})
            state = self.client.get("/api/state").json()
            if state["training"]["bound_pattern_count"] > 0:
                probe = self.client.post("/api/probe", json={"line_id": line_id}).json()
                if probe["catalog"]["learned"]:
                    return
        self.fail(f"{line_id} did not bind within {max_steps} steps")

    def test_probe_non_catalog_pattern_not_learned(self) -> None:
        response = self.client.post(
            "/api/probe",
            json={"active_indices": [0, 1, 4]},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["verdict"], "not_learned")
        self.assertTrue(body["catalog"]["valid"])
        self.assertIsNone(body["catalog"]["line_id"])

    def test_probe_not_learned(self) -> None:
        response = self.client.post("/api/probe", json={"line_id": "H1"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["verdict"], "not_learned")
        self.assertTrue(body["catalog"]["valid"])
        self.assertFalse(body["catalog"]["learned"])

    def test_probe_recognizes_learned_line(self) -> None:
        self._learn_catalog_line("H1")

        response = self.client.post("/api/probe", json={"line_id": "H1"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["catalog"]["learned"])
        self.assertEqual(body["verdict"], "recognized")
        self.assertTrue(str(body["neural"]["symbol"]).startswith("sigma_"))
        self.assertIn("sigma_", body["message"])

    def test_probe_by_active_indices(self) -> None:
        self._learn_catalog_line("V1")

        response = self.client.post(
            "/api/probe",
            json={"active_indices": [1, 4, 7]},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["catalog"]["line_id"], "V1")
        self.assertEqual(body["verdict"], "recognized")


if __name__ == "__main__":
    unittest.main()
