#!/usr/bin/env python3
"""CLI: neuron-local ecology after N catalog stimuli (no UI)."""

from __future__ import annotations

import argparse
import sys

from cognative_paradigm.diagnostics.neuron_local_ecology import NeuronLocalEcologyProbe
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure binds-by-line, dual owners, multi-spike ticks, "
            "and PREDICTION_ERROR / OWNERSHIP_COLLISION counts."
        ),
    )
    parser.add_argument(
        "--stimuli",
        type=int,
        default=80,
        help="Number of catalog stimuli to present (default: 80).",
    )
    args = parser.parse_args(argv)

    probe = NeuronLocalEcologyProbe(dynamics=DEFAULT_LEARNING_DYNAMICS)
    report = probe.run(n_stimuli=args.stimuli)

    print("Neuron-local ecology probe")
    print("=" * 40)
    for line in report.summary_lines():
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
