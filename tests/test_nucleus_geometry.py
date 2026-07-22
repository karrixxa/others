"""Nucleus spatial layout and L1→L2 distance influence on plasticity."""

from __future__ import annotations

import unittest

from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.domain.nucleus_geometry import (
    INFLUENCE_EPSILON,
    NeuronPosition,
    NucleusSpatialField,
    PlasticityInfluenceNormalizer,
    RingLayoutInitializer,
)
from cognative_paradigm.domain.relay_conductance_map import RelayConductanceMap
from cognative_paradigm.learning.conductance_plasticity import (
    ConductancePlasticityConfig,
    ConductancePlasticityLearner,
)
from cognative_paradigm.lines import edge_id
from cognative_paradigm.persistence.brain_checkpoint import BrainCheckpoint
from cognative_paradigm.simulation.central_inhibitor import CentralInhibitoryNeuron
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.l1_relay_broadcast import L1RelayBroadcastIntegrator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from cognative_paradigm.simulation.nucleus_ring_competitor import NucleusRingCompetitor
from cognative_paradigm.simulation.wta_coordinator import WtaCoordinator
from tests.simulation_helpers import deterministic_dynamics


class NucleusGeometryTests(unittest.TestCase):
    def test_l2_i_at_origin_and_l1_center_aligned(self) -> None:
        field = NucleusSpatialField(seed=0)
        self.assertEqual(field.l2_i_position.as_tuple(), (0.0, 0.0, 0.0))
        self.assertEqual(field.l1_position(4).as_tuple(), (0.0, 0.0, 0.0))

    def test_layout_inside_sphere_with_separation(self) -> None:
        field = NucleusSpatialField(seed=7, disk_radius=1.0, min_separation=0.28)
        origin = field.l2_i_position
        positions = field.l2_e_positions
        self.assertEqual(len(positions), 4)
        for position in positions:
            self.assertLessEqual(position.distance_to(origin), 1.0 + 1e-9)
            self.assertGreaterEqual(position.distance_to(origin), 0.28 - 1e-9)
        # At least one neuron has nonzero z — 3D placement, not flat disk.
        self.assertTrue(any(abs(pos.z) > 1e-6 for pos in positions))
        for index, left in enumerate(positions):
            for right in positions[index + 1 :]:
                self.assertGreaterEqual(left.distance_to(right), 0.28 - 1e-9)

    def test_layout_deterministic_under_seed(self) -> None:
        first = NucleusSpatialField(seed=42).l2_e_positions
        second = NucleusSpatialField(seed=42).l2_e_positions
        self.assertEqual(
            [pos.as_tuple() for pos in first],
            [pos.as_tuple() for pos in second],
        )

    def test_influence_uses_3d_distance(self) -> None:
        field = NucleusSpatialField(
            l2_e_positions=[
                NeuronPosition(0.0, 0.0, 0.1),
                NeuronPosition(0.0, 0.0, 0.9),
                NeuronPosition(0.0, 0.5, 0.0),
                NeuronPosition(-0.5, 0.0, 0.0),
            ]
        )
        near = field.influence(4, 0)  # L1 center → E at z=0.1
        far = field.influence(4, 1)  # L1 center → E at z=0.9
        self.assertGreater(near, far)
        self.assertAlmostEqual(near, 1.0 / (0.1**2 + INFLUENCE_EPSILON))

    def test_influence_finite_when_colocated(self) -> None:
        field = NucleusSpatialField(
            l2_e_positions=[
                NeuronPosition(0.0, 0.0, 0.0),
                NeuronPosition(0.5, 0.0, 0.0),
                NeuronPosition(0.0, 0.5, 0.0),
                NeuronPosition(-0.5, 0.0, 0.0),
            ],
            min_separation=0.0,
        )
        influence = field.influence(4, 0)
        self.assertAlmostEqual(influence, 1.0 / INFLUENCE_EPSILON)


class DistancePlasticityTests(unittest.TestCase):
    def test_nearer_synapse_gets_larger_delta(self) -> None:
        learner = ConductancePlasticityLearner(
            ConductancePlasticityConfig(
                e_learning_rate=0.05,
                sensory_plasticity_scale=1.0,
                sensory_plasticity_threshold=3.0,
                min_weight=0.01,
                e_max_weight=2.0,
            )
        )
        near_edge = edge_id(1, 1)
        far_edge = edge_id(0, 0)
        weights = {near_edge: 0.4, far_edge: 0.4}
        learner.apply_sensory_postsynaptic_spike(
            weights,
            frozenset({near_edge, far_edge}),
            influence_by_edge_id={near_edge: 4.0, far_edge: 1.0},
        )
        self.assertGreater(weights[near_edge], weights[far_edge])

    def test_default_influence_is_identity(self) -> None:
        learner = ConductancePlasticityLearner(
            ConductancePlasticityConfig(
                e_learning_rate=0.05,
                sensory_plasticity_scale=1.0,
                sensory_plasticity_threshold=2.0,
                min_weight=0.01,
                e_max_weight=2.0,
            )
        )
        edge = edge_id(1, 0)
        with_default = {edge: 0.5}
        with_one = {edge: 0.5}
        learner.apply_sensory_postsynaptic_spike(with_default, frozenset({edge}))
        learner.apply_sensory_postsynaptic_spike(
            with_one, frozenset({edge}), influence_by_edge_id={edge: 1.0}
        )
        self.assertAlmostEqual(with_default[edge], with_one[edge])


class IdentityDriveTests(unittest.TestCase):
    """Forward L1→L2 E drive is Σ w only; I(d) does not scale charge."""

    def _field_near_far(self) -> NucleusSpatialField:
        return NucleusSpatialField(
            l2_e_positions=[
                NeuronPosition(0.0, 0.0, 0.1),
                NeuronPosition(0.0, 0.0, 0.9),
                NeuronPosition(0.0, 0.5, 0.0),
                NeuronPosition(-0.5, 0.0, 0.0),
            ]
        )

    def test_drive_for_sums_weights_only(self) -> None:
        conductances = RelayConductanceMap(0.5)
        relay_ids = frozenset({"l1_e_0", "l1_e_1"})
        self.assertAlmostEqual(conductances.drive_for(relay_ids), 1.0)

    def test_broadcast_equal_weights_equal_drive_despite_geometry(self) -> None:
        field = self._field_near_far()
        self.assertGreater(field.influence(4, 0), field.influence(4, 1))
        lif = LifDynamics()
        broadcast = L1RelayBroadcastIntegrator(lif, DEFAULT_LEARNING_DYNAMICS)
        ring = [
            NucleusRingCompetitor(index, relay_weight=0.25)
            for index in range(4)
        ]
        relay_ids = frozenset({"l1_e_4"})
        drives = broadcast.apply_ring_charge(ring, relay_ids, timestep=1)
        self.assertAlmostEqual(drives["nucleus_e_0"], 0.25)
        self.assertAlmostEqual(drives["nucleus_e_1"], 0.25)
        self.assertAlmostEqual(drives["nucleus_e_0"], drives["nucleus_e_1"])

    def test_compute_drive_identity(self) -> None:
        competitor = NucleusRingCompetitor(ring_index=0, relay_weight=0.2)
        weights = competitor.relay_conductances.as_dict()
        weights["l1_e_0"] = 0.5
        weights["l1_e_1"] = 0.1
        competitor.relay_conductances.replace_weights(weights)
        relay_ids = frozenset({"l1_e_0", "l1_e_1"})
        self.assertAlmostEqual(competitor.compute_drive(relay_ids), 0.6)

    def test_wta_relay_drive_matches_identity_compute_drive(self) -> None:
        competitor = NucleusRingCompetitor(ring_index=0, relay_weight=0.3)
        relay_ids = frozenset({"l1_e_4"})
        expected = competitor.compute_drive(relay_ids)
        wta = WtaCoordinator(LifDynamics(), CentralInhibitoryNeuron())
        self.assertAlmostEqual(wta._relay_drive(competitor, relay_ids), expected)
        self.assertAlmostEqual(expected, 0.3)

    def test_raw_influence_map_unchanged_for_diagnostics(self) -> None:
        field = self._field_near_far()
        relay_ids = frozenset({"l1_e_4"})
        raw = field.influence_map(relay_ids, 0)
        self.assertAlmostEqual(raw["l1_e_4"], field.influence(4, 0))
        self.assertGreater(raw["l1_e_4"], field.influence(4, 1))

    def test_plasticity_influence_map_max_normalizes(self) -> None:
        field = self._field_near_far()
        near_edge = edge_id(1, 1)  # L1 index 4 — near ring 0
        far_edge = edge_id(0, 0)  # L1 index 0 — farther from ring 0
        active = frozenset({near_edge, far_edge})
        normalized = field.plasticity_influence_map(active, 0)
        raw = field.influence_map(active, 0)
        peak = max(raw.values())
        self.assertAlmostEqual(normalized[near_edge], raw[near_edge] / peak)
        self.assertAlmostEqual(max(normalized.values()), 1.0)
        self.assertLess(normalized[far_edge], normalized[near_edge])
        self.assertAlmostEqual(
            normalized[near_edge] / normalized[far_edge],
            raw[near_edge] / raw[far_edge],
        )

    def test_plasticity_influence_map_empty(self) -> None:
        field = self._field_near_far()
        self.assertEqual(field.plasticity_influence_map(frozenset(), 0), {})
        self.assertEqual(PlasticityInfluenceNormalizer.normalize({}), {})

    def test_single_spike_colocated_cannot_hit_e_max(self) -> None:
        """Near/colocated geometry: one sensory plasticity spike stays below e_max."""
        field = NucleusSpatialField(
            l2_e_positions=[
                NeuronPosition(0.0, 0.0, 0.0),  # colocated with L1 center
                NeuronPosition(0.0, 0.0, 0.9),
                NeuronPosition(0.0, 0.5, 0.0),
                NeuronPosition(-0.5, 0.0, 0.0),
            ],
            min_separation=0.0,
        )
        e_max = 2.0
        init_w = 0.48
        learner = ConductancePlasticityLearner(
            ConductancePlasticityConfig(
                e_learning_rate=0.05,
                sensory_plasticity_scale=1.0,
                sensory_plasticity_threshold=3.2,
                min_weight=0.01,
                e_max_weight=e_max,
            )
        )
        near_edge = edge_id(1, 1)  # L1 center (index 4)
        far_edge = edge_id(0, 0)  # L1 corner (index 0)
        weights = {near_edge: init_w, far_edge: init_w}
        active = frozenset({near_edge, far_edge})
        influence = field.plasticity_influence_map(active, 0)
        self.assertAlmostEqual(influence[near_edge], 1.0)
        self.assertLess(influence[far_edge], 1.0)

        learner.apply_sensory_postsynaptic_spike(
            weights,
            active,
            influence_by_edge_id=influence,
        )
        self.assertLess(weights[near_edge], e_max)
        self.assertLess(weights[far_edge], e_max)
        self.assertLess(weights[near_edge], init_w + 0.5)
        self.assertGreater(weights[near_edge] - init_w, weights[far_edge] - init_w)

        # Control: raw colocated I(d) would still slam to e_max in one spike.
        raw_slammed = {near_edge: init_w}
        learner.apply_sensory_postsynaptic_spike(
            raw_slammed,
            frozenset({near_edge}),
            influence_by_edge_id={near_edge: field.influence(4, 0)},
        )
        self.assertAlmostEqual(raw_slammed[near_edge], e_max)


class SpatialCheckpointTests(unittest.TestCase):
    def test_checkpoint_restores_l2_positions(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        original = [
            pos.as_tuple() for pos in sim.nucleus.spatial_field.l2_e_positions
        ]
        payload = BrainCheckpoint().export(sim)

        fresh = BrainSimulator(dynamics=deterministic_dynamics(wta_rng_seed=99))
        BrainCheckpoint().restore(fresh, payload)
        restored = [
            pos.as_tuple() for pos in fresh.nucleus.spatial_field.l2_e_positions
        ]
        self.assertEqual(original, restored)

    def test_state_exposes_ring_positions(self) -> None:
        sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
        state = sim.get_state()["nucleus"]
        self.assertIn("spatial", state)
        self.assertEqual(state["spatial"]["l2_i"], {"x": 0.0, "y": 0.0, "z": 0.0})
        for entry in state["ring"]:
            self.assertIn("position", entry)
            self.assertIn("x", entry["position"])
            self.assertIn("y", entry["position"])
            self.assertIn("z", entry["position"])


class RingLayoutInitializerTests(unittest.TestCase):
    def test_rejects_impossible_packing(self) -> None:
        initializer = RingLayoutInitializer(
            disk_radius=0.2,
            min_separation=0.5,
            max_attempts=50,
        )
        with self.assertRaises(RuntimeError):
            initializer.create(4, seed=0)


if __name__ == "__main__":
    unittest.main()
