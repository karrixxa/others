"""Brain checkpoint export/restore roundtrip."""

import unittest

from fastapi.testclient import TestClient

from cognative_paradigm.api.main import app
from cognative_paradigm.lines import LINE_INDICES, LINE_IDS
from cognative_paradigm.persistence.brain_checkpoint import BrainCheckpoint
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import deterministic_dynamics, learn_all_catalog_lines


class BrainCheckpointTests(unittest.TestCase):
    def test_export_restore_preserves_bindings(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_all_catalog_lines(sim)
        owners_before = dict(sim.nucleus.pattern_ownership.as_dict())

        checkpoint = BrainCheckpoint()
        payload = checkpoint.export(sim)

        fresh = BrainSimulator(dynamics=deterministic_dynamics())
        checkpoint.restore(fresh, payload)

        self.assertEqual(fresh.nucleus.pattern_ownership.as_dict(), owners_before)
        self.assertEqual(
            fresh.get_state()["training"]["bound_pattern_count"],
            len(owners_before),
        )

    def test_api_checkpoint_roundtrip(self) -> None:
        client = TestClient(app)
        client.post("/api/reset")

        for _ in range(1200):
            response = client.post("/api/stimulate", json={})
            if response.json()["training"].get("equilibrium"):
                break
        else:
            self.fail("did not reach equilibrium before checkpoint export")

        export = client.get("/api/checkpoint")
        self.assertEqual(export.status_code, 200)
        payload = export.json()
        self.assertEqual(payload["version"], 1)
        self.assertEqual(len(payload.get("ring") or []), len(LINE_IDS))

        client.post("/api/reset")
        self.assertEqual(client.get("/api/training").json()["bound_pattern_count"], 0)

        loaded = client.post("/api/checkpoint", json=payload)
        self.assertEqual(loaded.status_code, 200)
        training = client.get("/api/training").json()
        self.assertTrue(training["equilibrium"])

        probe = client.post("/api/probe", json={"active_indices": LINE_INDICES["H1"]})
        self.assertEqual(probe.json().get("verdict"), "recognized")


if __name__ == "__main__":
    unittest.main()
