"""Offline replay and consolidation tests (Phase 7)."""

from __future__ import annotations

import importlib
import unittest
from dataclasses import replace

import pytest

from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from cognative_paradigm.simulation.stimulus_stream import ReplayStimulusStream
from tests.simulation_helpers import (
    interleaved_learn_all_with_offline_replay,
    unguided_ecological_dynamics,
)


def _module_source(module_name: str) -> str:
    module = importlib.import_module(module_name)
    return open(module.__file__, encoding="utf-8").read()


def _count_rotation_steps(
    sim: BrainSimulator,
    *,
    max_rounds: int,
    replay_interval: int = 0,
    offline_steps: int = 0,
) -> int | None:
    catalog = LINE_IDS

    def all_learned() -> bool:
        return all(
            sim.nucleus.pattern_ownership.owner_for_pattern(get_line(line_id).edge_ids)
            for line_id in catalog
        )

    steps = 0
    for round_index in range(max_rounds):
        if all_learned():
            return steps
        line_id = catalog[round_index % len(catalog)]
        pattern = get_line(line_id)
        sim.stimulate_pattern(pattern, line_id=line_id)
        steps += 1
        if replay_interval > 0 and steps % replay_interval == 0:
            sim.offline_consolidation_steps(offline_steps)
    return None if not all_learned() else steps


def _offline_lab_dynamics(**overrides):
    return replace(
        unguided_ecological_dynamics(),
        offline_replay_enabled=True,
        offline_replay_eligibility_boost=1.75,
        offline_replay_plasticity_scale=1.4,
        quiescence_eligibility_decay_scale=0.30,
        **overrides,
    )


class ReplayStreamPurityTests(unittest.TestCase):
    def test_replay_stream_does_not_import_ownership(self) -> None:
        source = _module_source("cognative_paradigm.simulation.stimulus_stream")
        replay_block = source.split("class ReplayStimulusStream")[1].split(
            "class StochasticStimulusStream"
        )[0]
        self.assertNotIn("PatternMemorySnapshot", replay_block)
        self.assertNotIn("owner_for_pattern", replay_block)

    def test_replay_stream_cycles_buffer(self) -> None:
        stream = ReplayStimulusStream(line_ids=("H1", "V1"))
        self.assertEqual(stream.next_line_id(0), "H1")
        self.assertEqual(stream.next_line_id(1), "V1")
        self.assertEqual(stream.next_line_id(2), "H1")


class OfflineConsolidationUnitTests(unittest.TestCase):
    def test_disabled_by_default(self) -> None:
        self.assertFalse(DEFAULT_LEARNING_DYNAMICS.offline_replay_enabled)
        sim = BrainSimulator()
        self.assertEqual(sim.offline_consolidation_steps(3), [])

    def test_quiescence_preserves_eligibility_longer_than_online_decay(self) -> None:
        dynamics = _offline_lab_dynamics()
        sim = BrainSimulator(dynamics=dynamics)
        competitor = sim.nucleus.ring[0]
        trace = competitor.eligibility_trace
        trace.on_matching_spike(get_line("H1").edge_ids, dynamics.eligibility_alpha)
        before = trace.trace

        sim.quiescence_step()
        after_quiescence = trace.trace

        sim.stimulate_pattern(get_line("H1"), line_id="H1")
        after_online = trace.trace

        quiescence_retained = before - after_quiescence
        online_lost = after_quiescence - after_online
        self.assertLess(quiescence_retained, online_lost)


@pytest.mark.biological_lab
class OfflineConsolidationEcologyTests(unittest.TestCase):
    def test_rotation_with_replay_reaches_four_of_four(self) -> None:
        sim = BrainSimulator(dynamics=_offline_lab_dynamics())
        steps = interleaved_learn_all_with_offline_replay(
            sim,
            max_rounds=250,
            replay_interval=3,
            offline_steps=2,
        )
        self.assertGreater(steps, 0)
        owners = {
            line_id
            for line_id in LINE_IDS
            if sim.nucleus.pattern_ownership.owner_for_pattern(
                get_line(line_id).edge_ids
            )
        }
        self.assertEqual(len(owners), 4)

    def test_replay_improves_rotation_sample_efficiency(self) -> None:
        baseline_steps: list[int] = []
        replay_steps: list[int] = []
        # Deterministic WTA — all seeds reliably reach 4/4 under soft ecology.
        seeds = tuple(range(10))
        max_rounds = 600

        for seed in seeds:
            base_sim = BrainSimulator(
                dynamics=unguided_ecological_dynamics(
                    wta_rng_seed=seed,
                    membrane_noise_std=0.0,
                    wta_fair_ties=False,
                )
            )
            base_count = _count_rotation_steps(base_sim, max_rounds=max_rounds)
            replay_sim = BrainSimulator(
                dynamics=_offline_lab_dynamics(
                    wta_rng_seed=seed,
                    membrane_noise_std=0.0,
                    wta_fair_ties=False,
                )
            )
            replay_count = _count_rotation_steps(
                replay_sim,
                max_rounds=max_rounds,
                replay_interval=5,
                offline_steps=2,
            )
            if base_count is None:
                continue
            self.assertIsNotNone(
                replay_count,
                msg=f"replay seed {seed} must reach 4/4 within {max_rounds}",
            )
            baseline_steps.append(base_count)
            replay_steps.append(replay_count)

        self.assertGreaterEqual(
            len(baseline_steps),
            8,
            msg="expected at least 8/10 deterministic seeds to reach 4/4 baseline",
        )

        paired_improvements = [
            (base - replay) / max(base, 1)
            for base, replay in zip(baseline_steps, replay_steps, strict=True)
        ]
        mean_improvement = sum(paired_improvements) / len(paired_improvements)
        self.assertGreaterEqual(
            mean_improvement,
            0.15,
            msg=(
                f"expected ≥15% paired improvement; baseline={baseline_steps} "
                f"replay={replay_steps} mean={mean_improvement:.1%}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
