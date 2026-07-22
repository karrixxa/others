"""Raster spike biology during ecological catalog rotation."""

from __future__ import annotations

import unittest

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.stimulus_stream import RotatingStimulusStream
from tests.simulation_helpers import unguided_ecological_dynamics
from tests.test_model_stress import SimulationInvariantAuditor


class RasterBiologyTests(unittest.TestCase):
    def test_ecological_rotation_spikes_match_active_pattern(self) -> None:
        sim = BrainSimulator(dynamics=unguided_ecological_dynamics())
        stream = RotatingStimulusStream(hold_steps=5)
        invariant = SimulationInvariantAuditor()

        l1_off_pattern = 0
        ring_multi = 0
        relay_off_shape = 0
        total_steps = 0

        while total_steps < 200:
            line_id = stream.next_line_id(total_steps)
            pattern = get_line(line_id)
            result = sim.stimulate_pattern(pattern)
            total_steps += 1
            active = set(result.active_indices)

            for violation in invariant.audit_after_step(sim, result):
                if violation.code == "relay_off_shape":
                    relay_off_shape += 1
                elif violation.code == "population_spike_log_mismatch":
                    ring_multi += 1

            ring_spikes: list[str] = []
            for event in result.step_events:
                if event.get("type") != EventType.SPIKE.name:
                    continue
                neuron_id = str(event["neuron_id"])
                if neuron_id.startswith("l1_e_"):
                    cell = int(neuron_id.split("_")[-1])
                    if cell not in active:
                        l1_off_pattern += 1
                elif neuron_id.startswith("nucleus_e_"):
                    ring_spikes.append(neuron_id)

            population = list(sim.nucleus.last_population_spike_ids)
            if sorted(ring_spikes) != sorted(population):
                ring_multi += 1

            learned = [
                line
                for line in LINE_IDS
                if sim.nucleus.pattern_ownership.owner_for_pattern(get_line(line).edge_ids)
            ]
            if len(learned) == len(LINE_IDS):
                break

        # Ecology bind count may fail honestly without force assists — keep assert.
        self.assertEqual(len(learned), len(LINE_IDS), f"expected 4/4, got {learned}")
        self.assertEqual(l1_off_pattern, 0, "L1 E spiked off active pattern cells")
        self.assertEqual(ring_multi, 0, "event log must match population_spike_ids")
        self.assertEqual(relay_off_shape, 0, "L1 relay fired off active stimulus")


if __name__ == "__main__":
    unittest.main()
