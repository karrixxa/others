"""Regression: live parameter patches must not wipe learned structure."""

from __future__ import annotations

import unittest
from dataclasses import replace

from cognative_paradigm.api.service import BrainService, ParametersPatch
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from tests.simulation_helpers import deterministic_dynamics, unguided_ecological_dynamics


class _RingStructureSnapshot:
    """Immutable capture of per-competitor relay/sensory maps and L2 positions."""

    def __init__(self, sim: BrainSimulator) -> None:
        nucleus = sim.nucleus
        self.relay = [
            c.relay_conductances.as_dict() for c in nucleus.ring
        ]
        self.sensory = [
            c.sensory_conductances.as_dict() for c in nucleus.ring
        ]
        self.positions = [
            pos.to_dict() for pos in nucleus.spatial_field.l2_e_positions
        ]

    def assert_same_as(self, other: "_RingStructureSnapshot", case: unittest.TestCase) -> None:
        case.assertEqual(self.relay, other.relay)
        case.assertEqual(self.sensory, other.sensory)
        case.assertEqual(self.positions, other.positions)


class ApplyDynamicsStructurePreserveTests(unittest.TestCase):
    def test_apply_dynamics_preserves_relay_maps_when_learning_rate_changes(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                relay_weight_init_spread=0.25,
                wta_rng_seed=11,
            )
        )
        pattern = get_line("H1")
        for _ in range(25):
            sim.stimulate_pattern(pattern)

        before = _RingStructureSnapshot(sim)
        # Mutate a relay weight away from init so a silent rebuild would be visible.
        ring0 = sim.nucleus.ring[0]
        mutated = dict(ring0.relay_conductances.as_dict())
        first_key = next(iter(mutated))
        mutated[first_key] = mutated[first_key] + 0.05
        ring0.relay_conductances.replace_weights(mutated)
        before = _RingStructureSnapshot(sim)

        sim.apply_dynamics(replace(sim.dynamics, e_learning_rate=0.03))
        after = _RingStructureSnapshot(sim)
        before.assert_same_as(after, self)
        self.assertAlmostEqual(
            after.relay[0][first_key],
            mutated[first_key],
        )

    def test_apply_dynamics_rebuilds_relay_when_seed_changes(self) -> None:
        sim = BrainSimulator(
            dynamics=deterministic_dynamics(
                relay_weight_init_spread=0.25,
                wta_rng_seed=11,
            )
        )
        before = _RingStructureSnapshot(sim)
        sim.apply_dynamics(replace(sim.dynamics, wta_rng_seed=99))
        after = _RingStructureSnapshot(sim)
        self.assertNotEqual(before.relay, after.relay)
        self.assertNotEqual(before.positions, after.positions)

    def test_update_parameters_ecological_mode_preserves_relay_and_sensory(self) -> None:
        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                ecological_stimulus_mode="rotation",
                ecological_stimulus_hold_steps=5,
                wta_rng_seed=7,
            )
        )
        sim = service.simulator
        for _ in range(12):
            service.stimulate_auto()

        # Force a visible learned deviation so reset would fail loudly.
        competitor = sim.nucleus.ring[0]
        relay = dict(competitor.relay_conductances.as_dict())
        sensory = dict(competitor.sensory_conductances.as_dict())
        relay_key = next(iter(relay))
        sensory_key = next(iter(sensory))
        relay[relay_key] = relay[relay_key] + 0.07
        sensory[sensory_key] = sensory[sensory_key] + 0.09
        competitor.relay_conductances.replace_weights(relay)
        competitor.sensory_conductances.replace_weights(sensory)
        before = _RingStructureSnapshot(sim)
        pulse_before = service._ecological_pulse_index

        # Re-patch same mode/hold (UI echo) plus a non-structural slider.
        service.update_parameters(
            ParametersPatch(
                ecological_stimulus_mode="rotation",
                ecological_stimulus_hold_steps=5,
                e_learning_rate=0.025,
            )
        )
        after = _RingStructureSnapshot(sim)
        before.assert_same_as(after, self)
        self.assertEqual(service._ecological_pulse_index, pulse_before)

    def test_rotation_hold_advance_preserves_sensory_grids(self) -> None:
        """Manual sensory mutation survives mode/hold PATCH; learning may still change maps."""
        service = BrainService()
        service.update_parameters(
            ParametersPatch(
                ecological_stimulus_mode="rotation",
                ecological_stimulus_hold_steps=5,
            )
        )
        sim = service.simulator

        # Drive learning through H1 (0–4) and V1 (5–9); pulse 10 starts D0.
        lines: list[str | None] = []
        for _ in range(10):
            payload = service.stimulate_auto()
            lines.append(payload.get("line_id"))

        self.assertEqual(lines[:5], [LINE_IDS[0]] * 5)  # H1
        self.assertEqual(lines[5:10], [LINE_IDS[1]] * 5)  # V1

        # Ensure sensory maps have moved from init before the D0 boundary.
        competitor = sim.nucleus.ring[0]
        sensory = dict(competitor.sensory_conductances.as_dict())
        sensory_key = next(iter(sensory))
        elevated = sensory[sensory_key] + 0.11
        sensory[sensory_key] = elevated
        competitor.sensory_conductances.replace_weights(sensory)
        before_sensory = [
            c.sensory_conductances.as_dict() for c in sim.nucleus.ring
        ]
        before_relay = [
            c.relay_conductances.as_dict() for c in sim.nucleus.ring
        ]

        # Redundant mode/hold PATCH must not wipe structure (no learning tick).
        service.update_parameters(
            ParametersPatch(
                ecological_stimulus_mode="rotation",
                ecological_stimulus_hold_steps=5,
            )
        )
        after_patch_sensory = [
            c.sensory_conductances.as_dict() for c in sim.nucleus.ring
        ]
        after_patch_relay = [
            c.relay_conductances.as_dict() for c in sim.nucleus.ring
        ]
        self.assertEqual(before_sensory, after_patch_sensory)
        self.assertEqual(before_relay, after_patch_relay)
        self.assertAlmostEqual(
            after_patch_sensory[0][sensory_key],
            elevated,
            places=6,
        )

        # Next stim may learn, but must not reset the mutated key to init wipe.
        payload = service.stimulate_auto()
        self.assertEqual(payload.get("line_id"), LINE_IDS[2])  # D0
        after_stim = sim.nucleus.ring[0].sensory_conductances.as_dict()
        self.assertGreater(
            after_stim[sensory_key],
            elevated - 0.05,
            "structure-preserving path must not wipe elevated sensory weight",
        )


class EcologicalDynamicsDefaultSanityTests(unittest.TestCase):
    def test_unguided_defaults_still_construct(self) -> None:
        sim = BrainSimulator(dynamics=unguided_ecological_dynamics())
        self.assertEqual(sim.dynamics.ecological_stimulus_mode, "rotation")


if __name__ == "__main__":
    unittest.main()
