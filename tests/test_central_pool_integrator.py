"""Central I (NI) gradual pool integration — Abhi-aligned."""

import unittest

from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.central_inhibitor import CentralInhibitoryNeuron
from cognative_paradigm.simulation.central_pool_integrator import (
    CentralPoolConfig,
    CentralPoolIntegrator,
)
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import LearningDynamics
from cognative_paradigm.simulation.nucleus_ring_competitor import (
    NUCLEUS_RING_SIZE,
    NucleusRingCompetitor,
)
from tests.simulation_helpers import deterministic_dynamics, robustness_dynamics


class CentralPoolIntegratorTests(unittest.TestCase):
    def test_structural_cap_blocks_single_source_threshold_crossing(self) -> None:
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=1.2)
        config = CentralPoolConfig(
            collateral_gain=0.45,
            pool_gain=0.45,
            nucleus_threshold=1.27,
            central_threshold=1.2,
            central_membrane_tau=1.2,
            max_afferent_weight=1.5,
        )
        integrator = CentralPoolIntegrator(lif, central, config)
        ring = [
            NucleusRingCompetitor(index, relay_weight=0.2, threshold=1.27)
            for index in range(NUCLEUS_RING_SIZE)
        ]
        for competitor in ring:
            competitor.neuron.membrane = 2.0

        integrator.integrate_pool(ring, timestep=1, drive_mode="absolute")
        self.assertLess(
            central.neuron.membrane,
            central.neuron.threshold,
            "one collateral event must not cross θ alone",
        )
        integrator.add_collateral(
            5.0,
            timestep=1,
            winner_ring_index=0,
            assembly_credit_enabled=False,
        )
        self.assertLess(
            central.neuron.membrane,
            central.neuron.threshold,
            "single-winner collateral must stay below θ",
        )

    def test_faster_leak_than_ring_e(self) -> None:
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=1.2)
        ring_tau = 8.5
        ni_tau = ring_tau / 7.0
        integrator = CentralPoolIntegrator(
            lif,
            central,
            CentralPoolConfig(
                pool_gain=0.45,
                collateral_gain=0.45,
                nucleus_threshold=1.27,
                central_threshold=1.2,
                central_membrane_tau=ni_tau,
            ),
        )
        central.neuron.membrane = 0.5
        ring = [NucleusRingCompetitor(0, relay_weight=0.2)]
        ring[0].neuron.membrane = 0.5

        lif.leak(ring[0].neuron, dt_scale=1.0, membrane_tau=ring_tau)
        ring_after = ring[0].neuron.membrane
        integrator.leak_central(1, dt_scale=1.0, fast=True)
        ni_fast = central.neuron.membrane
        self.assertLess(ni_fast, ring_after, "NI fast volley leak should exceed ring E leak")

    def test_delta_mode_ignores_precharged_baseline(self) -> None:
        lif = LifDynamics()
        central = CentralInhibitoryNeuron(threshold=1.2)
        integrator = CentralPoolIntegrator(
            lif,
            central,
            CentralPoolConfig(
                pool_gain=0.45,
                collateral_gain=0.45,
                nucleus_threshold=1.27,
                central_threshold=1.2,
                central_membrane_tau=1.2,
            ),
        )
        ring = [NucleusRingCompetitor(index, relay_weight=0.2) for index in range(2)]
        baselines = [0.8, 0.8]
        for competitor in ring:
            competitor.neuron.membrane = 0.8

        integrator.integrate_pool(
            ring,
            timestep=1,
            drive_mode="delta",
            baselines=baselines,
        )
        self.assertAlmostEqual(central.neuron.membrane, 0.0, places=6)

        ring[0].neuron.membrane = 1.0
        integrator.integrate_pool(
            ring,
            timestep=1,
            drive_mode="delta",
            baselines=baselines,
        )
        self.assertGreater(central.neuron.membrane, 0.0)


class CentralInhibitorGradualRampTests(unittest.TestCase):
    def test_effective_threshold_higher_with_temporal_integration(self) -> None:
        dynamics = LearningDynamics(
            temporal_integration_enabled=True,
            central_inhibitor_threshold=0.8,
            central_inhibitor_threshold_temporal=1.1,
        )
        self.assertEqual(dynamics.effective_central_threshold(), 1.1)

    def test_ni_does_not_fire_every_pulse_during_early_volley(self) -> None:
        sim = BrainSimulator(dynamics=robustness_dynamics(membrane_noise_std=0.0))
        pattern = get_line("H1")
        central_fires = 0
        pulses = 15
        for _ in range(pulses):
            sim.stimulate_pattern(pattern)
            if sim.get_state()["nucleus"]["wta_central_fired"]:
                central_fires += 1
        self.assertLess(
            central_fires,
            pulses // 2,
            "NI should ramp gradually, not fire on most pulses",
        )

    def test_substep_integration_charges_central_before_wta(self) -> None:
        sim = BrainSimulator(
            dynamics=robustness_dynamics(
                membrane_noise_std=0.0,
                assembly_flow_credit_enabled=False,
            )
        )
        pattern = get_line("H1")
        sim.stimulate_pattern(pattern)
        membrane = sim.get_state()["nucleus"]["central_inhibitor_membrane"]
        self.assertGreater(
            membrane,
            0.0,
            "substep pool integration should charge NI before WTA",
        )


if __name__ == "__main__":
    unittest.main()
