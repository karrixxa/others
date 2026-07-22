"""Simulation time engine tests."""

import unittest

from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics
from cognative_paradigm.simulation.simulation_clock import SimulationClock
from cognative_paradigm.simulation.simulation_time_engine import SimulationTimeEngine


class SimulationTimeEngineTests(unittest.TestCase):
    def test_advances_on_silence_and_stim_steps(self) -> None:
        dynamics = LearningDynamics(
            temporal_integration_enabled=True,
            sim_dt_ms=1.0,
            stim_duration_ms=10.0,
            auto_stim_interval_ms=100.0,
        )
        engine = SimulationTimeEngine.from_dynamics(dynamics)
        clock = SimulationClock.from_dynamics(dynamics)

        for _ in range(90):
            engine.advance_silence_step(clock)
        self.assertAlmostEqual(engine.sim_time_ms, 90.0)

        onset = engine.mark_pulse_onset()
        self.assertEqual(onset, 90.0)
        for _ in range(10):
            engine.advance_stim_step(clock)
        self.assertAlmostEqual(engine.sim_time_ms, 100.0)
        self.assertAlmostEqual(engine.pulse_elapsed_ms(), 10.0)

    def test_brain_simulator_exposes_sim_time_in_state(self) -> None:
        dynamics = LearningDynamics(
            temporal_integration_enabled=True,
            sim_dt_ms=1.0,
            stim_duration_ms=5.0,
            auto_stim_interval_ms=50.0,
            excitatory_flow_rate_enabled=False,
            inhibitory_flow_rate_enabled=False,
        )
        sim = BrainSimulator(dynamics=dynamics)
        result = sim.step(get_line("H1"))
        state = sim.get_state()

        self.assertGreater(result.sim_time_ms, 0.0)
        self.assertIn("time", state)
        self.assertAlmostEqual(state["time"]["sim_time_ms"], result.sim_time_ms)


if __name__ == "__main__":
    unittest.main()
