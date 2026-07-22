#!/usr/bin/env python3
"""CLI: verify every PATTERN_BOUND follows eligibility + weight evidence."""

from __future__ import annotations

import argparse
import sys

from cognative_paradigm.diagnostics.learning_integrity import LearningIntegrityAuditor
from tests.simulation_helpers import biology_dynamics

DEFAULT_PATTERNS = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8],
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit biological learning integrity (no shortcut binds).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=150,
        help="Max timesteps per pattern before giving up (default: 150).",
    )
    parser.add_argument(
        "--patterns",
        nargs="*",
        default=None,
        help="Flat grid indices in groups of three, e.g. 0 1 2 3 4 5",
    )
    args = parser.parse_args(argv)

    if args.patterns:
        flat = [int(value) for value in args.patterns]
        if len(flat) % 3 != 0:
            parser.error("--patterns must contain a multiple of three indices.")
        patterns = [flat[index : index + 3] for index in range(0, len(flat), 3)]
    else:
        patterns = DEFAULT_PATTERNS

    auditor = LearningIntegrityAuditor(dynamics=biology_dynamics())
    report = auditor.run(patterns, max_steps_per_pattern=args.steps)

    print("Learning integrity probe")
    print("=" * 40)
    for line in report.summary_lines():
        print(line)

    if not report.binds:
        print("\nFAIL: no PATTERN_BOUND events observed — increase --steps or check dynamics.")
        return 1

    if report.violation_count:
        print(f"\nFAIL: {report.violation_count} violation(s) detected.")
        return 1

    print("\nPASS: all binds satisfied eligibility + weight evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
