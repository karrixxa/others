"""Phase 6: interleaved catalog stress — rotate patterns until 4/4 ownership."""

from __future__ import annotations

import unittest

from cognative_paradigm.lines import LINE_IDS, LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import (
    SOFT_CATALOG_COMPETITION,
    assert_injective_ownership,
    assert_unique_owners,
    deterministic_dynamics,
    interleaved_learn_all,
    ownership_owner_ids,
    robustness_dynamics,
    stimulate_until_recognized,
)
from tests.test_model_stress import ModelStressHarness


def _soft_robustness(**overrides):
    """Phases 1–5 robustness with soft NI required for interleaved 4/4."""
    soft = dict(SOFT_CATALOG_COMPETITION)
    soft.update(overrides)
    return robustness_dynamics(**soft)


class InterleavedRobustnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = ModelStressHarness()

    def test_interleaved_rotation_robustness_reaches_equilibrium(self) -> None:
        """Robust stack (Phases 1–5) binds all four lines under true rotation."""
        sim = BrainSimulator(dynamics=_soft_robustness())
        steps = interleaved_learn_all(sim, max_rounds=400)

        training = sim.get_state()["training"]
        self.assertTrue(training["equilibrium"])
        self.assertEqual(training["progress"], f"{len(LINE_IDS)}/{len(LINE_IDS)}")
        self.assertLessEqual(steps, 400)
        assert_injective_ownership(sim)

    def test_interleaved_default_discrete_stays_single_owner(self) -> None:
        """
        Soft independent race under rotation reaches full catalog ownership.
        """
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        for round_index in range(500):
            line_id = LINE_IDS[round_index % len(LINE_IDS)]
            sim.stimulate_pattern(get_line(line_id))

        owners = ownership_owner_ids(sim)
        self.assertEqual(len(owners), len(LINE_IDS))
        assert_unique_owners(sim)

    def test_interleaved_seeds_under_robustness(self) -> None:
        for seed in (0, 7, 42):
            with self.subTest(seed=seed):
                sim = BrainSimulator(
                    dynamics=_soft_robustness(wta_rng_seed=seed),
                )
                violations: list = []
                catalog = LINE_IDS
                learned: set[str] = set()

                for round_index in range(200):
                    line_id = catalog[round_index % len(catalog)]
                    result = sim.stimulate_pattern(get_line(line_id))
                    violations.extend(
                        self.harness._auditor.audit_after_step(sim, result)
                    )
                    if violations:
                        break
                    if sim.nucleus.pattern_ownership.owner_for_pattern(
                        get_line(line_id).edge_ids
                    ):
                        learned.add(line_id)
                    if len(learned) == len(catalog):
                        break
                else:
                    self.fail(f"seed {seed}: did not reach 4/4 within 200 rounds")

                self.harness.assert_clean(violations, f"robust interleaved seed {seed}")
                assert_injective_ownership(sim)

    def test_interleaved_invariants_hold_under_robustness(self) -> None:
        sim = BrainSimulator(dynamics=_soft_robustness())
        violations: list = []
        learned: set[str] = set()

        for round_index in range(200):
            line_id = LINE_IDS[round_index % len(LINE_IDS)]
            result = sim.stimulate_pattern(get_line(line_id))
            violations.extend(self.harness._auditor.audit_after_step(sim, result))
            if violations:
                break
            if sim.nucleus.pattern_ownership.owner_for_pattern(
                get_line(line_id).edge_ids
            ):
                learned.add(line_id)
            if len(learned) == len(LINE_IDS):
                break
        else:
            self.fail("robust interleaved invariants run did not finish 4/4")

        self.harness.assert_clean(violations, "robust interleaved invariants")
        assert_injective_ownership(sim)

    def test_interleaved_invariants_hold_under_default_rotation(self) -> None:
        """Per-tick audits stay clean even when discrete dynamics binds 1/4."""
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        violations: list = []

        for round_index in range(300):
            line_id = LINE_IDS[round_index % len(LINE_IDS)]
            result = sim.stimulate_pattern(get_line(line_id))
            violations.extend(self.harness._auditor.audit_after_step(sim, result))
            if violations:
                break

        self.harness.assert_clean(violations, "default interleaved invariants")
        assert_unique_owners(sim)

    def test_post_interleaved_recognition(self) -> None:
        sim = BrainSimulator(dynamics=_soft_robustness())
        interleaved_learn_all(sim, max_rounds=400)

        owners_before = ownership_owner_ids(sim)
        for line_id in LINE_IDS:
            result = stimulate_until_recognized(
                sim, LINE_INDICES[line_id], max_steps=40
            )
            self.assertIsNotNone(result.output_symbol)
            owner = sim.nucleus.pattern_ownership.owner_for_pattern(
                get_line(line_id).edge_ids
            )
            self.assertIsNotNone(owner)
            self.assertEqual(owners_before, ownership_owner_ids(sim))

    def test_interleaved_no_owner_collision_during_robust_learning(self) -> None:
        """Ownership map stays injective as each new pattern binds."""
        sim = BrainSimulator(dynamics=_soft_robustness())
        bound_count = 0

        for round_index in range(200):
            line_id = LINE_IDS[round_index % len(LINE_IDS)]
            sim.stimulate_pattern(get_line(line_id))
            owners = ownership_owner_ids(sim)
            if len(owners) > bound_count:
                assert_unique_owners(sim)
                bound_count = len(owners)
            if bound_count >= len(LINE_IDS):
                break
        else:
            self.fail("robust interleaved did not reach full catalog ownership")


if __name__ == "__main__":
    unittest.main()
