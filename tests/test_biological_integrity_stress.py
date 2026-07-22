"""Full-stack biological integrity stress: no injected binds, API + simulator."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from cognative_paradigm.api.main import app, service
from cognative_paradigm.diagnostics.learning_integrity import LearningIntegrityAuditor
from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.domain.pattern_memory_snapshot import PatternMemorySnapshot
from cognative_paradigm.learning.weight_consolidation import pattern_weight_score
from cognative_paradigm.lines import LINE_IDS, LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import biology_dynamics
from tests.test_model_stress import ModelStressHarness


class ApiBindIntegrityAuditor:
    """Audit PATTERN_BOUND events from API responses using pre-step state snapshots."""

    def __init__(
        self,
        *,
        eligibility_threshold: float,
        consolidation_threshold: float,
        eligibility_alpha: float,
        eligibility_decay: float,
    ) -> None:
        self._eligibility_threshold = eligibility_threshold
        self._consolidation_threshold = consolidation_threshold
        self._eligibility_alpha = eligibility_alpha
        self._eligibility_decay = eligibility_decay
        self.violations: list[str] = []
        self.binds: list[dict] = []

    def audit_step(self, pre_state: dict, response: dict, sim: BrainSimulator) -> None:
        bind_events = [
            event
            for event in response.get("step_events") or []
            if event.get("type") == EventType.PATTERN_BOUND.name
        ]
        if not bind_events:
            return

        active_indices = sorted(response.get("active_indices") or [])
        edge_ids = frozenset(
            f"input_r{index // 3}_c{index % 3}" for index in active_indices
        )
        pattern_key = PatternMemorySnapshot.pattern_key(edge_ids)
        pre_owners = pre_state.get("nucleus", {}).get("pattern_owners") or {}
        pre_traces = {
            neuron["id"]: float(neuron.get("eligibility_trace") or neuron.get("bind_progress") or 0.0)
            for neuron in pre_state.get("nucleus", {}).get("ring") or []
        }

        for event in bind_events:
            neuron_id = str(event["neuron_id"])
            symbol = str(event.get("symbol") or "")
            record = {
                "neuron_id": neuron_id,
                "symbol": symbol,
                "pattern": active_indices,
                "timestep": response.get("timestep"),
            }
            self.binds.append(record)

            if not symbol.startswith("sigma_"):
                self.violations.append(f"t={record['timestep']}: non-emergent symbol {symbol!r}")

            if response.get("winner_neuron_id") != neuron_id:
                # Soft independent race: winner_neuron_id is diagnostic among
                # plural authentic spikers; consolidator may bind any eligible
                # spiker. Only enforce sole-winner identity under wipe exclusivity.
                if getattr(sim.dynamics, "pretrained_inhibitor_exclusivity_enabled", False):
                    self.violations.append(
                        f"t={record['timestep']}: bind {neuron_id} != winner "
                        f"{response.get('winner_neuron_id')}"
                    )

            prior_owner = pre_owners.get(pattern_key)
            if prior_owner is not None and prior_owner != neuron_id:
                self.violations.append(
                    f"t={record['timestep']}: pattern already owned by {prior_owner}"
                )

            eligibility = self._project_eligibility(pre_traces.get(neuron_id, 0.0))
            if eligibility < self._eligibility_threshold:
                self.violations.append(
                    f"t={record['timestep']}: eligibility {eligibility:.4f} "
                    f"< {self._eligibility_threshold}"
                )

            competitor = sim.nucleus.competitor_by_id(neuron_id)
            sensory = (
                competitor.sensory_conductances
                if competitor is not None
                else {}
            )
            weight_score = pattern_weight_score(sensory, edge_ids)
            if weight_score < self._consolidation_threshold:
                self.violations.append(
                    f"t={record['timestep']}: weight {weight_score:.4f} "
                    f"< {self._consolidation_threshold}"
                )

    def _project_eligibility(self, trace: float) -> float:
        decayed = trace * max(0.0, 1.0 - self._eligibility_decay)
        return min(1.0, decayed + self._eligibility_alpha)


class BiologicalIntegrityStressTests(unittest.TestCase):
    def test_full_catalog_simulator_integrity(self) -> None:
        patterns = [LINE_INDICES[line_id] for line_id in LINE_IDS]
        auditor = LearningIntegrityAuditor(dynamics=biology_dynamics())
        report = auditor.run(patterns, max_steps_per_pattern=200)

        self.assertEqual(report.violation_count, 0, report.summary_lines())
        self.assertEqual(len(report.binds), len(LINE_IDS))

        owners = {record.neuron_id for record in report.binds}
        self.assertEqual(len(owners), len(LINE_IDS), "each bind should claim a distinct neuron")

    def test_api_auto_stim_reaches_equilibrium_with_clean_binds(self) -> None:
        client = TestClient(app)
        client.post("/api/reset")

        dynamics = service._dynamics
        bind_auditor = ApiBindIntegrityAuditor(
            eligibility_threshold=dynamics.eligibility_threshold,
            consolidation_threshold=dynamics.consolidation_weight_threshold or 0.0,
            eligibility_alpha=dynamics.eligibility_alpha,
            eligibility_decay=dynamics.eligibility_decay,
        )

        for step in range(3000):
            pre = client.get("/api/state").json()
            response = client.post("/api/stimulate", json={})
            self.assertEqual(response.status_code, 200)
            body = response.json()

            bind_auditor.audit_step(pre, body, service._simulator)

            relay = set(body.get("relay_indices") or [])
            active = set(body.get("active_indices") or [])
            self.assertTrue(relay.issubset(active), f"relay {relay} not subset of {active}")

            if body["training"].get("equilibrium"):
                break
        else:
            self.fail("API auto-stim did not reach 4/4 equilibrium within 3000 steps")

        self.assertEqual([], bind_auditor.violations)
        self.assertGreaterEqual(len(bind_auditor.binds), len(LINE_IDS))

        training = client.get("/api/training").json()
        observed = set(training.get("observed_line_ids") or training.get("learned_line_ids") or [])
        self.assertEqual(observed, set(LINE_IDS))

    def test_single_pulse_never_binds(self) -> None:
        sim = BrainSimulator(dynamics=biology_dynamics())
        pattern = get_line("H1")
        result = sim.stimulate_pattern(pattern)

        bind_events = [
            event
            for event in result.step_events
            if event.get("type") == EventType.PATTERN_BOUND.name
        ]
        self.assertEqual(bind_events, [])
        self.assertIsNone(sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids))

    def test_population_spikes_stay_honest_under_stress(self) -> None:
        """Multi-spike allowed; event log must match population_spike_ids."""
        sim = BrainSimulator(dynamics=biology_dynamics())
        harness = ModelStressHarness()
        violations = harness.run_steps(
            sim,
            steps=500,
            pattern_picker=lambda _: get_line(LINE_IDS[0]),
        )
        harness.assert_clean(violations, "single-pattern 500-step population honesty")

    def test_manual_line_id_still_requires_biological_bind(self) -> None:
        client = TestClient(app)
        client.post("/api/reset")

        response = client.post("/api/stimulate", json={"line_id": "V1"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        bind_events = [
            event
            for event in body.get("step_events") or []
            if event.get("type") == EventType.PATTERN_BOUND.name
        ]
        self.assertEqual(bind_events, [])
        self.assertNotIn("V1", body["training"].get("learned_line_ids") or [])


if __name__ == "__main__":
    unittest.main()
