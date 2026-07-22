"""Long-run stress tests and per-tick invariant audits for BrainSimulator."""

from __future__ import annotations

import math
import random
import unittest
from dataclasses import dataclass

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.domain.pattern import Pattern
from cognative_paradigm.domain.register_state import RegisterState
from cognative_paradigm.lines import LINE_IDS, LINE_INDICES, get_line, pattern_from_indices
from cognative_paradigm.simulation.engine import BrainSimulator, SimulationResult
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import (
    catalog_soft_dynamics,
    deterministic_dynamics,
    interleaved_learn_all,
    learn_all_catalog_lines,
    learn_catalog_line,
    stimulate_until_recognized,
    unguided_ecological_dynamics,
)


@dataclass(frozen=True)
class InvariantViolation:
    timestep: int
    code: str
    detail: str


class SimulationInvariantAuditor:
    """Per-tick checks that membranes, registers, and topology stay consistent."""

    MIN_MEMBRANE = -10.0

    def audit_after_step(
        self,
        sim: BrainSimulator,
        result: SimulationResult,
    ) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        t = result.timestep
        state = sim.get_state()

        violations.extend(self._audit_numeric_state(sim, t))
        violations.extend(self._audit_layer1_registers(state, t))
        violations.extend(self._audit_relay_topology(result, t))
        violations.extend(self._audit_spike_events(result, sim, t))
        violations.extend(self._audit_ownership(state, t))
        violations.extend(self._audit_descending_pending(sim, t))
        violations.extend(self._audit_conductance_grid(state, t))
        return violations

    def _audit_numeric_state(
        self,
        sim: BrainSimulator,
        timestep: int,
    ) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []

        for pair in sim.layer1.pairs:
            for neuron in (pair.excitatory, pair.inhibitory):
                if not math.isfinite(neuron.membrane) or neuron.membrane < self.MIN_MEMBRANE:
                    violations.append(
                        InvariantViolation(
                            timestep,
                            "l1_membrane",
                            f"{neuron.id} membrane={neuron.membrane}",
                        )
                    )

        for competitor in sim.nucleus.ring:
            neuron = competitor.neuron
            if not math.isfinite(neuron.membrane) or neuron.membrane < self.MIN_MEMBRANE:
                violations.append(
                    InvariantViolation(
                        timestep,
                        "ring_membrane",
                        f"{neuron.id} membrane={neuron.membrane}",
                    )
                )

        central = sim.nucleus.central_inhibitor.neuron
        if not math.isfinite(central.membrane) or central.membrane < self.MIN_MEMBRANE:
            violations.append(
                InvariantViolation(
                    timestep,
                    "central_membrane",
                    f"{central.id} membrane={central.membrane}",
                )
            )

        return violations

    def _audit_layer1_registers(
        self,
        state: dict,
        timestep: int,
    ) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        for pair in state["layer1"]["pairs"]:
            for key in ("excitatory_register", "inhibitory_register"):
                value = pair[key]
                if value not in ("Z", "1"):
                    violations.append(
                        InvariantViolation(
                            timestep,
                            "l1_register",
                            f"grid {pair['grid_index']} {key}={value!r}",
                        )
                    )
        return violations

    def _audit_relay_topology(
        self,
        result: SimulationResult,
        timestep: int,
    ) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        active = set(result.active_indices)
        for relay_index in result.relay_indices:
            if relay_index not in active:
                violations.append(
                    InvariantViolation(
                        timestep,
                        "relay_off_shape",
                        f"relay l1_e_{relay_index} active={sorted(active)}",
                    )
                )

        # Only pre-nucleus (blocking) L1 I spikes forbid same-tick E relay.
        # Production exclusivity forces I *after* L2 E′ in the same tick —
        # that feedback must not be audited as relay_while_inhibited.
        blocking_inhibited_cells = self._blocking_l1_i_cells(result.step_events)
        for relay_index in result.relay_indices:
            if relay_index in blocking_inhibited_cells:
                violations.append(
                    InvariantViolation(
                        timestep,
                        "relay_while_inhibited",
                        f"l1_e_{relay_index} relayed despite blocking l1_i spike",
                    )
                )
        return violations

    @staticmethod
    def _blocking_l1_i_cells(step_events: list[dict]) -> set[int]:
        """L1 I cells that spiked before the first nucleus E spike this tick."""
        blocked: set[int] = set()
        for event in step_events:
            if event.get("type") != EventType.SPIKE.name:
                continue
            neuron_id = str(event.get("neuron_id", ""))
            if neuron_id.startswith("nucleus_e_"):
                break
            if neuron_id.startswith("l1_i_"):
                blocked.add(int(neuron_id.split("_")[-1]))
        return blocked

    def _audit_spike_events(
        self,
        result: SimulationResult,
        sim: BrainSimulator,
        timestep: int,
    ) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        for event in result.step_events:
            if event["type"] not in EventType.__members__:
                violations.append(
                    InvariantViolation(
                        timestep,
                        "invalid_event_type",
                        str(event),
                    )
                )

        ring_spikes = [
            event["neuron_id"]
            for event in result.step_events
            if event["type"] == EventType.SPIKE.name
            and str(event["neuron_id"]).startswith("nucleus_e_")
        ]
        population = sim.nucleus.last_population_spike_ids
        ring_population = [nid for nid in population if nid.startswith("nucleus_e_")]
        # Multi-spike is authentic competition — no sole-winner force. Demand honesty.
        if sorted(ring_spikes) != sorted(ring_population):
            violations.append(
                InvariantViolation(
                    timestep,
                    "population_spike_log_mismatch",
                    f"events={ring_spikes} population={ring_population}",
                )
            )

        central_id = sim.nucleus.central_inhibitor.neuron.id
        if central_id in population:
            violations.append(
                InvariantViolation(
                    timestep,
                    "central_in_population",
                    f"population={population}",
                )
            )

        if ring_spikes and population and ring_spikes[0] not in population:
            violations.append(
                InvariantViolation(
                    timestep,
                    "logged_ring_not_in_population",
                    f"events={ring_spikes} population={population}",
                )
            )

        return violations

    def _audit_ownership(
        self,
        state: dict,
        timestep: int,
    ) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        owners = state.get("training", {}).get("pattern_owners") or {}
        if not owners:
            return violations

        neuron_ids = list(owners.values())
        if len(neuron_ids) != len(set(neuron_ids)):
            violations.append(
                InvariantViolation(
                    timestep,
                    "duplicate_neuron_owner",
                    str(owners),
                )
            )

        for _pattern_key, neuron_id in owners.items():
            if not str(neuron_id).startswith("nucleus_e_"):
                violations.append(
                    InvariantViolation(
                        timestep,
                        "non_ring_owner",
                        f"{_pattern_key} -> {neuron_id}",
                    )
                )
        return violations

    def _audit_descending_pending(
        self,
        sim: BrainSimulator,
        timestep: int,
    ) -> list[InvariantViolation]:
        pending = sim._descending.pending_charge
        if pending < -1e-12 or not math.isfinite(pending):
            return [
                InvariantViolation(
                    timestep,
                    "invalid_pending_charge",
                    f"pending={pending}",
                )
            ]
        return []

    def _audit_conductance_grid(
        self,
        state: dict,
        timestep: int,
    ) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        grid = state["conductance_weights"]["grid"]
        min_w = state["conductance_weights"]["min_weight"]
        max_w = state["conductance_weights"]["max_weight"]
        for row in grid:
            for weight in row:
                if not math.isfinite(weight):
                    violations.append(
                        InvariantViolation(
                            timestep,
                            "non_finite_weight",
                            f"weight={weight}",
                        )
                    )
                elif weight < min_w - 1e-9 or weight > max_w + 1e-9:
                    violations.append(
                        InvariantViolation(
                            timestep,
                            "weight_out_of_bounds",
                            f"weight={weight} bounds=[{min_w}, {max_w}]",
                        )
                    )
        return violations


class ModelStressHarness:
    """Runs extended simulations and fails on the first invariant breach."""

    def __init__(self) -> None:
        self._auditor = SimulationInvariantAuditor()

    def run_steps(
        self,
        sim: BrainSimulator,
        *,
        steps: int,
        pattern_picker,
    ) -> list[InvariantViolation]:
        violations: list[InvariantViolation] = []
        for _ in range(steps):
            pattern = pattern_picker(sim)
            result = sim.stimulate_pattern(pattern)
            violations.extend(self._auditor.audit_after_step(sim, result))
            if violations:
                return violations
        return violations

    def assert_clean(self, violations: list[InvariantViolation], label: str) -> None:
        if violations:
            first = violations[0]
            raise AssertionError(
                f"{label}: {first.code} at t={first.timestep} — {first.detail} "
                f"(+{len(violations) - 1} more)"
            )


class ModelStressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = ModelStressHarness()

    def test_deterministic_full_catalog_invariants(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        for line_id in LINE_IDS:
            result = learn_catalog_line(sim, line_id)
            violations = self.harness._auditor.audit_after_step(sim, result)
            self.harness.assert_clean(violations, f"learn {line_id}")

        training = sim.get_state()["training"]
        self.assertTrue(training["equilibrium"])
        self.assertEqual(training["progress"], f"{len(LINE_IDS)}/{len(LINE_IDS)}")

    def test_noisy_cycling_two_thousand_steps(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        rng = random.Random(0)
        line_ids = list(LINE_IDS)

        violations: list[InvariantViolation] = []
        for _ in range(2000):
            line_id = rng.choice(line_ids)
            pattern = get_line(line_id)
            result = sim.stimulate_pattern(pattern)
            violations.extend(self.harness._auditor.audit_after_step(sim, result))
            if violations:
                break

        self.harness.assert_clean(violations, "noisy cycling 2000")

    def test_interleaved_seeds_learn_all_patterns(self) -> None:
        """Soft-NI interleaved rotation reaches 4/4 under multiple seeds."""
        for seed in (0, 7, 42):
            with self.subTest(seed=seed):
                sim = BrainSimulator(
                    dynamics=unguided_ecological_dynamics(wta_rng_seed=seed),
                )
                violations: list[InvariantViolation] = []
                steps = interleaved_learn_all(sim, max_rounds=400)
                # Re-run a short audited pass after learning for honesty.
                for line_id in LINE_IDS:
                    result = sim.stimulate_pattern(get_line(line_id))
                    violations.extend(
                        self.harness._auditor.audit_after_step(sim, result)
                    )
                self.harness.assert_clean(violations, f"interleaved seed {seed}")
                self.assertEqual(
                    sim.get_state()["training"]["progress"],
                    f"{len(LINE_IDS)}/{len(LINE_IDS)}",
                )
                self.assertLessEqual(steps, 400)

    def test_post_equilibrium_random_probe_stress(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_all_catalog_lines(sim)
        rng = random.Random(17)

        violations = self.harness.run_steps(
            sim,
            steps=800,
            pattern_picker=lambda _: get_line(rng.choice(LINE_IDS)),
        )
        self.harness.assert_clean(violations, "post-equilibrium random 800")

        for line_id in LINE_IDS:
            result = stimulate_until_recognized(
                sim, LINE_INDICES[line_id], max_steps=30
            )
            self.assertIsNotNone(result.output_symbol)
            violations = self.harness._auditor.audit_after_step(sim, result)
            self.harness.assert_clean(violations, f"recognize {line_id}")

    def test_unbind_relearn_cycles(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_all_catalog_lines(sim)

        for cycle in range(3):
            with self.subTest(cycle=cycle):
                line_id = LINE_IDS[cycle % len(LINE_IDS)]
                indices = LINE_INDICES[line_id]
                pattern = get_line(line_id)
                released = sim.unbind_pattern(indices)
                self.assertIsNotNone(released)

                violations: list[InvariantViolation] = []
                for _ in range(150):
                    result = sim.stimulate_pattern(pattern)
                    violations.extend(
                        self.harness._auditor.audit_after_step(sim, result)
                    )
                    if sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids):
                        break
                else:
                    self.fail(f"{line_id} did not rebind in cycle {cycle}")

                self.harness.assert_clean(violations, f"rebind {line_id} cycle {cycle}")
                recognize = stimulate_until_recognized(
                    sim, indices, max_steps=30
                )
                self.assertIsNotNone(recognize.output_symbol)

    def test_l1_stimulus_never_directly_fires_inhibitory(self) -> None:
        """Stimulus must not fire L1 I; exclusivity may force I only after L2 E′."""
        sim = BrainSimulator(dynamics=deterministic_dynamics(l1_feedforward_gain=0.0))
        saw_nucleus_e = False
        for _ in range(60):
            result = sim.stimulate_pattern(get_line("H1"))
            nucleus_e_ids = [
                event["neuron_id"]
                for event in result.step_events
                if event["type"] == EventType.SPIKE.name
                and str(event["neuron_id"]).startswith("nucleus_e_")
            ]
            l1_i_before_nucleus = SimulationInvariantAuditor._blocking_l1_i_cells(
                result.step_events
            )
            self.assertEqual(
                l1_i_before_nucleus,
                set(),
                "L1 I must not spike from stimulus before nucleus E′ cascade",
            )
            if nucleus_e_ids:
                saw_nucleus_e = True
                # After L2, exclusivity may force I — that is descending feedback.
                break
            for pair in sim.layer1.pairs:
                self.assertEqual(
                    pair.inhibitory.register,
                    RegisterState.Z,
                    "I must stay Z until first nucleus E′ / descending cascade",
                )
        if not saw_nucleus_e:
            self.skipTest("no L2 winner spike in sample window")

    def test_descending_pending_consumed_next_tick(self) -> None:
        # Graded (non-exclusivity) path enqueues pending; exclusivity delivers immediately.
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                l2_to_l1_i_gain=0.10,
                pretrained_inhibitor_exclusivity_enabled=False,
            )
        )
        pending_after_enqueue = 0.0
        for _ in range(30):
            sim.stimulate_pattern(get_line("H1"))
            if sim._descending.pending_charge > 0:
                pending_after_enqueue = sim._descending.pending_charge
                break
        self.assertGreater(pending_after_enqueue, 0.0)

        sim._layer1.process_step(
            sim._timestep + 1,
            frozenset(),
            sim._edges,
            descending=sim._descending,
        )
        self.assertEqual(sim._descending.pending_charge, 0.0)

    def test_learn_all_helper_reaches_equilibrium(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_all_catalog_lines(sim)
        training = sim.get_state()["training"]
        self.assertTrue(training["equilibrium"])
        owners = sim.nucleus.pattern_ownership.as_dict()
        self.assertEqual(len(owners), len(LINE_IDS))


if __name__ == "__main__":
    unittest.main()
