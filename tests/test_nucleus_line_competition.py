"""WTA competition phases: learning pool vs equilibrium owner."""

import unittest

from cognative_paradigm.lines import LINE_IDS, LINE_INDICES, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.nucleus_line_competition import (
    COMPETITION_EQUILIBRIUM,
    COMPETITION_LEARNING,
)
from tests.simulation_helpers import (
    deterministic_dynamics,
    learn_catalog_line,
    stimulate_until_pattern_bound,
)


class NucleusLineCompetitionTests(unittest.TestCase):
    def test_unbound_pattern_uses_learning_wta_pool(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        sim.stimulate_pattern(get_line("H1"))
        nucleus = sim.get_state()["nucleus"]
        self.assertEqual(nucleus["competition_phase"], COMPETITION_LEARNING)

        ring_ones = [n for n in nucleus["ring"] if n["register"] == "1"]
        population = list(sim.nucleus.last_population_spike_ids)
        self.assertEqual(
            sorted(n["id"] for n in ring_ones),
            sorted(population),
        )

    def test_learned_pattern_uses_equilibrium_owner_only(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_catalog_line(sim, "H1")
        pattern = get_line("H1")
        owner_id = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        assert owner_id is not None

        result = None
        for _ in range(30):
            result = sim.stimulate_pattern(pattern)
            nucleus = sim.get_state()["nucleus"]
            self.assertEqual(nucleus["competition_phase"], COMPETITION_EQUILIBRIUM)
            if result.output_symbol:
                break

        assert result is not None
        self.assertIsNotNone(result.output_symbol, "owner should recognize matching shape")

    def test_only_one_neuron_owns_each_pattern(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        for line_id in LINE_IDS:
            learn_catalog_line(sim, line_id)

        owners = sim.nucleus.pattern_ownership.as_dict()
        self.assertEqual(len(owners), len(LINE_IDS))
        self.assertEqual(len(set(owners.values())), len(LINE_IDS))

    def test_unbound_neurons_keep_competing_until_they_bind(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        pattern = get_line("H1")
        phases: set[str] = set()
        for _ in range(12):
            sim.stimulate_pattern(pattern)
            phases.add(sim.get_state()["nucleus"]["competition_phase"])
            if sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids):
                break
        self.assertIn(COMPETITION_LEARNING, phases)

    def test_unbind_returns_pattern_to_learning_competition(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_catalog_line(sim, "H1")
        sim.unbind_pattern(LINE_INDICES["H1"])
        sim.stimulate_pattern(get_line("H1"))
        self.assertEqual(
            sim.get_state()["nucleus"]["competition_phase"],
            COMPETITION_LEARNING,
        )


if __name__ == "__main__":
    unittest.main()
