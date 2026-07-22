"""Inhibitory flow-rate: sustained suppression via decaying current J."""

import unittest

from cognative_paradigm.domain.inhibitory_flow_trace import InhibitoryFlowTrace
from cognative_paradigm.domain.neuron import Neuron
from cognative_paradigm.domain.spike_drive import SpikeDrive
from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.simulation.inhibitory_flow_controller import InhibitoryFlowController
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics


class InhibitoryFlowTraceTests(unittest.TestCase):
    def test_normalized_injection_totals_to_single_step_subtraction(self) -> None:
        decay = 0.8
        inhibition = 0.5
        trace = InhibitoryFlowTrace(decay=decay, normalized=True)
        trace.inject(inhibition)

        membrane = 1.0
        total_removed = 0.0
        for _ in range(50):
            before = membrane
            membrane = trace.drain(membrane, resting_potential=0.0)
            total_removed += before - membrane
            if trace.trace <= 1e-9:
                break

        self.assertAlmostEqual(total_removed, inhibition, places=2)

    def test_sustained_drain_across_multiple_steps(self) -> None:
        neuron = Neuron(id="target", threshold=2.0, membrane=1.0)
        controller = InhibitoryFlowController(
            LearningDynamics(inhibitory_flow_rate_enabled=True, inh_trace_decay=0.8)
        )
        controller.inject(neuron.id, 0.6)

        controller.drain(neuron, refractory=False)
        first = neuron.membrane
        controller.drain(neuron, refractory=False)
        second = neuron.membrane

        self.assertLess(first, 1.0)
        self.assertLess(second, first)


class SpikeDriveInhibitoryFlowTests(unittest.TestCase):
    def test_apply_inhibitory_defers_membrane_change_when_flow_enabled(self) -> None:
        lif = LifDynamics()
        controller = InhibitoryFlowController(
            LearningDynamics(inhibitory_flow_rate_enabled=True)
        )
        drive = SpikeDrive(lif, inhibitory_flow=controller)
        neuron = Neuron(id="n", threshold=2.0, membrane=1.0)

        drive.apply_inhibitory(neuron, 0.4)
        self.assertAlmostEqual(neuron.membrane, 1.0)

        controller.drain(neuron, refractory=False)
        self.assertLess(neuron.membrane, 1.0)

    def test_legacy_one_shot_when_flow_disabled(self) -> None:
        lif = LifDynamics()
        controller = InhibitoryFlowController(
            LearningDynamics(inhibitory_flow_rate_enabled=False)
        )
        drive = SpikeDrive(lif, inhibitory_flow=controller)
        neuron = Neuron(id="n", threshold=2.0, membrane=1.0)

        drive.apply_inhibitory(neuron, 0.4)
        self.assertAlmostEqual(neuron.membrane, 0.6)


if __name__ == "__main__":
    unittest.main()
