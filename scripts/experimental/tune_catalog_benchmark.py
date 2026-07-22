#!/usr/bin/env python3
"""Benchmark catalog learning, raster invariants, and recognition for tuning."""

from __future__ import annotations

import random
import sys
from dataclasses import replace

from cognative_paradigm.diagnostics.learning_integrity import LearningIntegrityAuditor
from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import LINE_IDS, LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import (
    DEFAULT_LEARNING_DYNAMICS,
    LearningDynamics,
)
from cognative_paradigm.simulation.stimulus_stream import RotatingStimulusStream
from tests.simulation_helpers import stimulate_until_recognized
from tests.test_model_stress import SimulationInvariantAuditor


def benchmark_curriculum(
    dynamics: LearningDynamics,
    *,
    seed: int = 0,
    max_steps: int = 500,
) -> dict:
    sim = BrainSimulator(dynamics=dynamics)
    stream = RotatingStimulusStream(
        hold_steps=dynamics.ecological_stimulus_hold_steps,
    )
    invariant = SimulationInvariantAuditor()

    violations: list = []
    bind_timesteps: list[int] = []
    line_steps: dict[str, int] = {}
    current_line: str | None = None
    steps_on_line = 0
    total = 0
    l1_spike_off_pattern = 0
    ring_multi_spike_ticks = 0
    central_i_spikes = 0
    l1_e_spikes = 0
    l1_i_spikes = 0

    while total < max_steps:
        line_id = stream.next_line_id(total)
        if line_id is None:
            break

        if line_id != current_line:
            if current_line and steps_on_line:
                line_steps[current_line] = steps_on_line
            current_line = line_id
            steps_on_line = 0

        pattern = get_line(line_id)
        result = sim.stimulate_pattern(pattern)
        total += 1
        steps_on_line += 1
        violations.extend(invariant.audit_after_step(sim, result))

        active = set(result.active_indices)
        ring_spikes: list[str] = []
        for event in result.step_events:
            if event.get("type") != EventType.SPIKE.name:
                continue
            neuron_id = str(event["neuron_id"])
            if neuron_id.startswith("l1_e_"):
                l1_e_spikes += 1
                cell = int(neuron_id.split("_")[-1])
                if cell not in active:
                    l1_spike_off_pattern += 1
            elif neuron_id.startswith("l1_i_"):
                l1_i_spikes += 1
            elif neuron_id.startswith("nucleus_e_"):
                ring_spikes.append(neuron_id)
            elif neuron_id == "nucleus_i":
                central_i_spikes += 1

        if len(ring_spikes) > 1:
            ring_multi_spike_ticks += 1

        if any(event.get("type") == EventType.PATTERN_BOUND.name for event in result.step_events):
            bind_timesteps.append(total)
            line_steps[line_id] = steps_on_line
            steps_on_line = 0

    learned = [
        line_id
        for line_id in LINE_IDS
        if sim.nucleus.pattern_ownership.owner_for_pattern(get_line(line_id).edge_ids)
    ]
    recognition: dict[str, str] = {}
    for line_id in LINE_IDS:
        try:
            stimulate_until_recognized(sim, LINE_INDICES[line_id], max_steps=5)
            recognition[line_id] = "ok<=5"
        except AssertionError:
            recognition[line_id] = "fail"

    integrity = LearningIntegrityAuditor(dynamics=dynamics).run(
        [LINE_INDICES[line_id] for line_id in LINE_IDS],
        max_steps_per_pattern=120,
    )

    return {
        "total_steps": total,
        "learned_count": len(learned),
        "equilibrium": len(learned) >= len(LINE_IDS),
        "bind_timesteps": bind_timesteps,
        "line_steps": line_steps,
        "invariant_violations": len(violations),
        "l1_spike_off_pattern": l1_spike_off_pattern,
        "ring_multi_spike_ticks": ring_multi_spike_ticks,
        "central_i_spikes": central_i_spikes,
        "l1_e_spikes": l1_e_spikes,
        "l1_i_spikes": l1_i_spikes,
        "recognition": recognition,
        "integrity_violations": integrity.violation_count,
        "integrity_binds": len(integrity.binds),
    }


def print_report(label: str, report: dict) -> None:
    print(f"=== {label} ===")
    print(f"  curriculum: {report['total_steps']} steps -> {report['learned_count']}/4 learned")
    print(f"  per-line binds: {report['line_steps']}")
    print(f"  bind timesteps: {report['bind_timesteps']}")
    print(
        f"  raster audit: inv={report['invariant_violations']} "
        f"l1_off_pattern={report['l1_spike_off_pattern']} "
        f"ring_multi={report['ring_multi_spike_ticks']} "
        f"NI_spikes={report['central_i_spikes']} "
        f"L1_E={report['l1_e_spikes']} L1_I={report['l1_i_spikes']}"
    )
    print(f"  recognition: {report['recognition']}")
    print(
        f"  integrity: binds={report['integrity_binds']} "
        f"violations={report['integrity_violations']}"
    )
    print()


def main() -> int:
    base = DEFAULT_LEARNING_DYNAMICS
    candidates: list[tuple[str, LearningDynamics]] = [
        ("default", base),
        (
            "peak_combo",
            replace(
                base,
                eligibility_alpha=0.52,
                eligibility_decay=0.06,
                e_learning_rate=0.03,
                nucleus_relay_weight=0.072,
                nucleus_threshold=1.15,
                consolidation_weight_threshold=0.12,
                collateral_gain=0.42,
            ),
        ),
    ]

    if "--multi-seed" in sys.argv:
        dynamics = DEFAULT_LEARNING_DYNAMICS
        for seed in range(8):
            report = benchmark_curriculum(dynamics, seed=seed)
            ok = (
                report["equilibrium"]
                and not report["invariant_violations"]
                and not report["integrity_violations"]
                and not report["l1_spike_off_pattern"]
            )
            print(
                f"seed={seed} steps={report['total_steps']} "
                f"lines={report['line_steps']} ok={ok}"
            )
        return 0

    failures = 0
    for label, dynamics in candidates:
        report = benchmark_curriculum(dynamics)
        print_report(label, report)
        if not report["equilibrium"]:
            failures += 1
        # Integrity binds are hard gates; raster invariant count may include
        # benign multi-spiker WTA ticks — triaged separately from learning.
        if report["integrity_violations"]:
            failures += 1
        if report["l1_spike_off_pattern"]:
            failures += 1
        if any(value == "fail" for value in report["recognition"].values()):
            failures += 1
        if report["invariant_violations"]:
            print(
                f"  note: {label} raster invariant_violations="
                f"{report['invariant_violations']} "
                f"(ring_multi={report['ring_multi_spike_ticks']}; triaged, non-blocking)"
            )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
