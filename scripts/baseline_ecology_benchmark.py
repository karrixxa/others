#!/usr/bin/env python3
"""Phase 1 baseline: rotation vs mastery under production dynamics."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from cognative_paradigm.diagnostics.bio_metric_pack import (
    BiologicalMetricPack,
    BiologicalMetricSnapshot,
)
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from cognative_paradigm.simulation.stimulus_stream import (
    MasteryAutoStimScheduler,
    RotatingStimulusStream,
)


class BaselineEcologyBenchmark:
    """Run rotation/mastery ablations and emit the normative metric pack."""

    def __init__(self, metric_pack: BiologicalMetricPack | None = None) -> None:
        self._metrics = metric_pack or BiologicalMetricPack()

    @staticmethod
    def _owner_count(sim: BrainSimulator) -> int:
        ownership = sim.nucleus.pattern_ownership
        return sum(
            1
            for line_id in LINE_IDS
            if ownership.owner_for_pattern(get_line(line_id).edge_ids)
        )

    def run_rotation(
        self,
        *,
        hold_steps: int,
        max_pulses: int,
        seed: int,
    ) -> BiologicalMetricSnapshot:
        dynamics = replace(
            DEFAULT_LEARNING_DYNAMICS,
            ecological_stimulus_mode="rotation",
            ecological_stimulus_hold_steps=hold_steps,
            wta_rng_seed=seed,
        )
        sim = BrainSimulator(dynamics=dynamics)
        stream = RotatingStimulusStream(hold_steps=hold_steps)
        pulses = 0
        for pulse_index in range(max_pulses):
            line_id = stream.next_line_id(pulse_index)
            sim.stimulate_pattern(get_line(line_id))
            pulses = pulse_index + 1
            if self._owner_count(sim) == len(LINE_IDS):
                break
        return self._metrics.capture(sim, pulses=pulses)

    def run_mastery(
        self,
        *,
        max_pulses: int,
        seed: int,
    ) -> BiologicalMetricSnapshot:
        dynamics = replace(
            DEFAULT_LEARNING_DYNAMICS,
            ecological_stimulus_mode="mastery",
            wta_rng_seed=seed,
        )
        sim = BrainSimulator(dynamics=dynamics)
        scheduler = MasteryAutoStimScheduler()
        ownership = sim.nucleus.pattern_ownership
        pulses = 0
        for _ in range(max_pulses):
            line_id = scheduler.resolve_line_id(ownership)
            if line_id is None:
                break
            sim.stimulate_pattern(get_line(line_id))
            pulses += 1
            if (
                self._owner_count(sim) == len(LINE_IDS)
                and scheduler.phase.value == "probe"
            ):
                break
        return self._metrics.capture(sim, pulses=pulses)

    def guide_dependence_passes(
        self,
        *,
        rotation_passes: int,
        mastery_passes: int,
    ) -> bool:
        return self._metrics.guide_dependence_passes(
            rotation_passes=rotation_passes,
            mastery_passes=mastery_passes,
        )

    def rotation_passes(self, snapshot: BiologicalMetricSnapshot) -> bool:
        return self._metrics.rotation_passes(snapshot)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hold-steps", type=int, default=5)
    parser.add_argument("--max-pulses", type=int, default=300)
    parser.add_argument("--seeds", type=str, default="0,7,42")
    args = parser.parse_args()
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    print("=== Baseline ecology benchmark (production dynamics) ===")
    print(f"hold_steps={args.hold_steps} max_pulses={args.max_pulses} seeds={seeds}")
    rotation_ok = 0
    mastery_ok = 0
    benchmark = BaselineEcologyBenchmark()

    for seed in seeds:
        rotation = benchmark.run_rotation(
            hold_steps=args.hold_steps,
            max_pulses=args.max_pulses,
            seed=seed,
        )
        mastery = benchmark.run_mastery(
            max_pulses=args.max_pulses * 3,
            seed=seed,
        )
        rot_pass = benchmark.rotation_passes(rotation)
        mas_pass = mastery.complete
        rotation_ok += int(rot_pass)
        mastery_ok += int(mas_pass)
        print(
            f"seed={seed}: rotation {rotation.owner_count}/{len(LINE_IDS)} "
            f"in {rotation.pulses} pulses {'PASS' if rot_pass else 'FAIL'} "
            f"(collisions={rotation.ownership_collisions}, "
            f"integrity={rotation.integrity_ratio:.2f}, "
            f"spike_rate={rotation.excitatory_spike_rate:.3f}) | "
            f"mastery {mastery.owner_count}/{len(LINE_IDS)} "
            f"in {mastery.pulses} pulses {'PASS' if mas_pass else 'FAIL'}"
        )

    ratio = rotation_ok / max(mastery_ok, 1)
    print(f"guide_dependence_ratio={ratio:.2f} (target >= 0.95)")
    if rotation_ok < len(seeds):
        return 1
    if not benchmark.guide_dependence_passes(
        rotation_passes=rotation_ok,
        mastery_passes=mastery_ok,
    ):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
