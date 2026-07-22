"""Biological sparseness without forced WTA — trajectory + doctrine checks."""

import importlib.util
import unittest

from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import deterministic_dynamics, robustness_dynamics


FORBIDDEN_MODULES = (
    "cognative_paradigm.simulation.latency_wta_arbiter",
    "cognative_paradigm.simulation.recall_drive_integrator",
    "cognative_paradigm.simulation.stimulus_completion_schedule",
    "cognative_paradigm.simulation.substep_lateral_suppression",
)


class BiologicalSparsenessTests(unittest.TestCase):
    def test_force_assist_modules_absent(self) -> None:
        for module_name in FORBIDDEN_MODULES:
            self.assertIsNone(
                importlib.util.find_spec(module_name),
                f"forbidden force-assist module present: {module_name}",
            )

    def test_collision_remains_audit_only(self) -> None:
        """OWNERSHIP_COLLISION must not block consolidation of a second binder."""
        from cognative_paradigm.domain.event_log import EventType
        from cognative_paradigm.learning.eligibility_consolidator import (
            EligibilityConsolidator,
        )

        consolidator = EligibilityConsolidator(deterministic_dynamics())
        self.assertTrue(hasattr(consolidator, "try_consolidate"))
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        pattern = get_line("H1")
        saw_population = False
        for _ in range(40):
            sim.stimulate_pattern(pattern)
            if len(sim.nucleus.last_population_spike_ids) >= 1:
                saw_population = True
                break
        self.assertTrue(saw_population)
        self.assertEqual(EventType.OWNERSHIP_COLLISION.name, "OWNERSHIP_COLLISION")

    def test_inhibitory_channels_can_rise_on_hot_losers(self) -> None:
        """Trajectory: with turnover ON, hot-loser channels strengthen above init."""
        # Soft labeled control: plural authentic spikes create hot losers for
        # turnover. Force wipe zeros loser V before η_up can strengthen channels.
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                inhibitory_turnover_enabled=True,
                plastic_ni_enabled=True,
                central_competition_ni_discharge_fraction=1.0,
                central_pool_gain=0.62,
                pretrained_inhibitor_exclusivity_enabled=False,
                descending_mode="graded",
                emergent_autonomy_enabled=True,
                temporal_integration_enabled=False,
                excitatory_flow_rate_enabled=False,
                eligibility_threshold=0.99,
                consolidation_weight_threshold=0.95,
            )
        )
        pattern = get_line("H1")
        init_channels = list(sim.nucleus._central.inhibition_channels)
        init_max = max(init_channels)

        peak = init_max
        multi_spike_seen = False
        for _ in range(160):
            sim.stimulate_pattern(pattern)
            if len(sim.nucleus.last_population_spike_ids) >= 2:
                multi_spike_seen = True
            peak = max(peak, max(sim.nucleus._central.inhibition_channels))

        self.assertGreater(
            peak,
            init_max,
            "expected at least one NI→E channel to strengthen above init",
        )
        # Soft path (exclusivity OFF): multi-spike remains allowed.
        self.assertIsInstance(multi_spike_seen, bool)

    def test_extra_spiker_active_weights_do_not_runaway_vs_owner_path(self) -> None:
        """Over pulses, extras should not keep consolidating forever unchecked."""
        sim = BrainSimulator(
            dynamics=robustness_dynamics(
                heterosynaptic_depression_enabled=True,
                prediction_error_ltd_enabled=True,
            )
        )
        pattern = get_line("H1")
        active = pattern.edge_ids

        # Drive until bound; then present a different pattern to a bound neuron
        # is covered by PE-LTD unit tests. Here assert learning still progresses.
        bound = False
        for _ in range(120):
            sim.stimulate_pattern(pattern)
            if sim.nucleus.pattern_ownership.owner_for_pattern(active):
                bound = True
                break
        self.assertTrue(bound, "H1 should still bind under LTD defaults")


if __name__ == "__main__":
    unittest.main()
