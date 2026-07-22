#!/usr/bin/env python3
"""Benchmark ecological rotation learning pace and raster-friendly bind spacing.

Mode matrix
-----------
- Production exclusivity ON: ``DEFAULT_LEARNING_DYNAMICS`` (force NI / wipe /
  same-tick L1I) — recognition path; optional comparison print only.
- Ecology lab soft: ``unguided_ecological_dynamics()`` / ``SOFT_CATALOG``
  (exclusivity OFF soft NI) — default path for ecological 4/4.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from cognative_paradigm.diagnostics.learning_integrity import LearningIntegrityAuditor
from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import LINE_IDS, LINE_INDICES, get_line, pattern_from_indices
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import (
    DEFAULT_LEARNING_DYNAMICS,
    LearningDynamics,
)
from tests.simulation_helpers import ownership_owner_ids, unguided_ecological_dynamics
from tests.test_model_stress import SimulationInvariantAuditor


def ecological_benchmark(
    dynamics: LearningDynamics,
    *,
    max_rounds: int = 500,
    seed: int | None = None,
) -> dict:
    active = dynamics if seed is None else replace(dynamics, wta_rng_seed=seed)
    sim = BrainSimulator(dynamics=active)
    invariant = SimulationInvariantAuditor()

    bind_events: list[tuple[int, str]] = []
    violations = 0
    spike_counts: list[int] = []
    eligibility_peaks: list[float] = []

    for round_index in range(max_rounds):
        line_id = LINE_IDS[round_index % len(LINE_IDS)]
        pattern = get_line(line_id)
        before = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        result = sim.stimulate_pattern(pattern)
        after = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)

        violations += len(invariant.audit_after_step(sim, result))
        spike_counts.append(
            sum(1 for event in result.step_events if event.get("type") == EventType.SPIKE.name)
        )
        eligibility_peaks.append(
            max(competitor.eligibility_trace.trace for competitor in sim.nucleus.ring)
        )

        if before is None and after is not None:
            bind_events.append((round_index + 1, line_id))

        if len(ownership_owner_ids(sim)) >= len(LINE_IDS):
            break

    owners = ownership_owner_ids(sim)
    gaps = [
        bind_events[index + 1][0] - bind_events[index][0]
        for index in range(len(bind_events) - 1)
    ]

    hold_sim = BrainSimulator(dynamics=active)
    hold_bind: int | None = None
    hold_pattern = pattern_from_indices(LINE_INDICES["H1"])
    for pulse in range(120):
        result = hold_sim.stimulate_pattern(hold_pattern)
        if any(
            event.get("type") == EventType.PATTERN_BOUND.name
            for event in result.step_events
        ):
            hold_bind = pulse + 1
            break

    integrity = LearningIntegrityAuditor(dynamics=active).run(
        [LINE_INDICES[line_id] for line_id in LINE_IDS],
        max_steps_per_pattern=250,
    )

    return {
        "rounds": round_index + 1,
        "owners": len(owners),
        "equilibrium": len(owners) >= len(LINE_IDS),
        "bind_events": bind_events,
        "bind_gaps": gaps,
        "first_bind": bind_events[0][0] if bind_events else None,
        "hold_bind_pulses": hold_bind,
        "avg_spikes_per_pulse": sum(spike_counts) / max(len(spike_counts), 1),
        "max_eligibility": max(eligibility_peaks) if eligibility_peaks else 0.0,
        "invariant_violations": violations,
        "integrity_violations": integrity.violation_count,
    }


def print_report(label: str, report: dict) -> None:
    print(f"=== {label} ===")
    print(f"  ecological 4/4: {report['owners']}/4 in {report['rounds']} pulses")
    print(f"  bind events:    {report['bind_events']}")
    print(f"  bind gaps:      {report['bind_gaps']}")
    print(f"  first bind:     pulse {report['first_bind']}")
    print(f"  H1 hold bind:   pulse {report['hold_bind_pulses']}")
    print(
        f"  raster:         avg_spikes={report['avg_spikes_per_pulse']:.1f} "
        f"max_eligibility={report['max_eligibility']:.3f}"
    )
    print(
        f"  audit:          invariant={report['invariant_violations']} "
        f"integrity={report['integrity_violations']}"
    )
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=0, help="Run N seeds (0 = single run)")
    args = parser.parse_args()

    # Default: ecology lab soft NI (SOFT_CATALOG / exclusivity OFF).
    dynamics = unguided_ecological_dynamics()
    failures = 0

    if args.seeds > 0:
        for seed in range(args.seeds):
            report = ecological_benchmark(dynamics, seed=seed)
            ok = report["equilibrium"] and not report["integrity_violations"]
            print(
                f"seed={seed} rounds={report['rounds']} "
                f"first_bind={report['first_bind']} hold={report['hold_bind_pulses']} ok={ok}"
            )
            failures += 0 if ok else 1
        return 1 if failures else 0

    report = ecological_benchmark(dynamics)
    print_report("ecology lab soft (SOFT_CATALOG)", report)

    if not report["equilibrium"]:
        failures += 1
    if report["integrity_violations"] or report["invariant_violations"]:
        failures += 1
    if report["first_bind"] is not None and report["first_bind"] < 20:
        print("WARN: first bind very early — learning may look instant on raster")
        failures += 1

    # Always print production exclusivity ON comparison (not scored for exit).
    production = ecological_benchmark(DEFAULT_LEARNING_DYNAMICS)
    print_report("production exclusivity ON (comparison)", production)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
