"""Regression: biology-mode scaling must not silence the sensory path."""

import unittest

from cognative_paradigm.lines import pattern_from_indices
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import biology_dynamics, deterministic_dynamics


class BiologyScalingBalanceTests(unittest.TestCase):
    def test_input_weights_do_not_collapse_under_repeated_pattern(self) -> None:
        sim = BrainSimulator(
            dynamics=biology_dynamics(consolidation_weight_threshold=0.15),
        )
        pattern = pattern_from_indices([0, 1, 2])
        for _ in range(60):
            sim.stimulate_pattern(pattern)

        weights = sim.get_state()["stdp_weights"]["grid"][0]
        self.assertGreater(
            min(weights),
            0.45,
            "pattern edge weights should not be crushed by homeostasis",
        )

    def test_relay_and_winner_rate_stays_viable(self) -> None:
        bio = BrainSimulator(
            dynamics=biology_dynamics(consolidation_weight_threshold=0.15),
        )
        baseline = BrainSimulator(
            dynamics=deterministic_dynamics(consolidation_weight_threshold=0.15),
        )
        pattern = pattern_from_indices([0, 1, 2])

        def rates(sim: BrainSimulator) -> tuple[float, float]:
            winners = 0
            relay_steps = 0
            for _ in range(60):
                result = sim.stimulate_pattern(pattern)
                if result.winner_neuron_id:
                    winners += 1
                state = sim.get_state()
                if any(
                    pair["excitatory_register"] == "1"
                    for pair in state["layer1"]["pairs"]
                ):
                    relay_steps += 1
            return winners / 60, relay_steps / 60

        bio_w, bio_r = rates(bio)
        base_w, base_r = rates(baseline)
        self.assertGreaterEqual(bio_r, 0.70, "L1 relays should fire most steps")
        self.assertGreaterEqual(
            bio_w,
            0.12,
            "nucleus should produce winners on a steady fraction of steps",
        )
        self.assertGreaterEqual(bio_w, base_w * 0.45, "biology winners within 45% of fast-test baseline")


if __name__ == "__main__":
    unittest.main()
