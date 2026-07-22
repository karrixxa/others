"""Ecological rotation ablation: interleaved ownership without curriculum oracle."""

from __future__ import annotations

import unittest

from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import (
    interleaved_learn_all,
    ownership_owner_ids,
    unguided_ecological_dynamics,
)


def _owner_count(sim: BrainSimulator) -> int:
    return len(ownership_owner_ids(sim))


class EcologicalAblationTests(unittest.TestCase):
    def test_discrete_rotation_without_curriculum(self) -> None:
        sim = BrainSimulator(
            dynamics=unguided_ecological_dynamics(
                temporal_integration_enabled=False,
                excitatory_flow_rate_enabled=False,
                inhibitory_turnover_enabled=False,
                assembly_flow_credit_enabled=False,
                inhibitory_flow_rate_enabled=False,
            ),
        )
        for round_index in range(500):
            line_id = LINE_IDS[round_index % len(LINE_IDS)]
            sim.stimulate_pattern(get_line(line_id))

        self.assertGreaterEqual(_owner_count(sim), 1)
        self.assertLessEqual(_owner_count(sim), len(LINE_IDS))

    def test_robust_rotation_reaches_four_of_four(self) -> None:
        sim = BrainSimulator(dynamics=unguided_ecological_dynamics())
        interleaved_learn_all(sim, max_rounds=200)
        self.assertEqual(_owner_count(sim), len(LINE_IDS))

    def test_robustness_stack_matches_ecological_defaults(self) -> None:
        sim = BrainSimulator(dynamics=unguided_ecological_dynamics())
        interleaved_learn_all(sim, max_rounds=200)
        self.assertEqual(_owner_count(sim), len(LINE_IDS))


if __name__ == "__main__":
    unittest.main()
