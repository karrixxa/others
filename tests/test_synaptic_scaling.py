import unittest

from cognative_paradigm.domain.inhibitory_coupling import (
    DEFAULT_INHIBITION_STRENGTH,
    InhibitoryCoupling,
    default_inhibitory_coupling,
)
from cognative_paradigm.domain.input_edge import InputEdge
from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.learning.assembly_flow_credit import (
    AssemblyFlowCreditConfig,
    AssemblyFlowCreditLearner,
)
from cognative_paradigm.learning.synaptic_scaling import SynapticScalingHomeostasis
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.descending_inhibition import DescendingInhibition
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.layer1_network import Layer1Relay
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import deterministic_dynamics, learn_catalog_line


class SynapticScalingHomeostasisTests(unittest.TestCase):
    def _homeostasis(self, **overrides) -> SynapticScalingHomeostasis:
        defaults = dict(
            target_rate=0.15,
            eta=0.05,
            window=5,
            i_min=0.1,
            i_max=0.5,
        )
        defaults.update(overrides)
        return SynapticScalingHomeostasis(**defaults)

    def _update(self, homeostasis, coupling, *, e_fired: bool) -> InhibitoryCoupling:
        edge = InputEdge(id="input_r0_c0", row=0, col=0)
        updated_coupling, _edge = homeostasis.update(
            coupling,
            grid_index=0,
            e_fired=e_fired,
            input_edge=edge,
        )
        return updated_coupling

    def test_coupling_frozen_when_e_overfires(self) -> None:
        """L1 I coupling is saturated/frozen — scaling never mutates strength."""
        homeostasis = self._homeostasis(target_rate=0.1, eta=0.1)
        coupling = default_inhibitory_coupling()
        strength = coupling.inhibition_strength

        for _ in range(30):
            coupling = self._update(homeostasis, coupling, e_fired=True)

        self.assertAlmostEqual(coupling.inhibition_strength, strength)

    def test_coupling_frozen_when_e_silent(self) -> None:
        homeostasis = self._homeostasis(target_rate=0.2, eta=0.1)
        coupling = InhibitoryCoupling(
            feedforward_gain=0.40,
            inhibition_strength=0.35,
            e_collateral=0.4,
        )

        for _ in range(40):
            coupling = self._update(homeostasis, coupling, e_fired=False)

        self.assertAlmostEqual(coupling.inhibition_strength, 0.35)

    def test_default_coupling_is_saturated_max(self) -> None:
        self.assertAlmostEqual(
            DEFAULT_INHIBITION_STRENGTH,
            DEFAULT_LEARNING_DYNAMICS.homeostasis_i_max,
        )
        self.assertAlmostEqual(default_inhibitory_coupling().inhibition_strength, 0.5)

    def test_scaling_does_not_modify_input_edge_weight(self) -> None:
        homeostasis = self._homeostasis()
        coupling = default_inhibitory_coupling()
        edge = InputEdge(id="input_r0_c0", row=0, col=0, weight=0.5)

        _coupling, updated_edge = homeostasis.update(
            coupling,
            grid_index=0,
            e_fired=True,
            input_edge=edge,
        )

        self.assertEqual(updated_edge.weight, 0.5)

    def test_coupling_serialized_in_layer1_state(self) -> None:
        sim = BrainSimulator()
        sim.stimulate_pattern(get_line("H1"))
        pair = sim.get_state()["layer1"]["pairs"][0]
        self.assertIn("inhibitory_coupling", pair)
        self.assertAlmostEqual(
            pair["inhibitory_coupling"]["inhibition_strength"],
            DEFAULT_INHIBITION_STRENGTH,
            places=2,
        )

    def test_engine_coupling_unchanged_under_scaling(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        before = [
            pair.coupling.inhibition_strength for pair in sim.layer1.pairs
        ]
        for _ in range(40):
            sim.stimulate_pattern(get_line("H1"))
        after = [
            pair.coupling.inhibition_strength for pair in sim.layer1.pairs
        ]
        self.assertEqual(before, after)
        self.assertTrue(all(abs(s - 0.5) < 1e-9 for s in after))

    def test_l1_input_edges_saturated_after_create_and_reset(self) -> None:
        sim = BrainSimulator()
        baseline = sim.dynamics.sensory_baseline_weight
        # L1 InputEdge baseline is membrane-scale and deliberately not tied to e_max.
        self.assertAlmostEqual(baseline, 2.0)
        self.assertAlmostEqual(sim.dynamics.e_max_weight, 1000.0)
        for edge in sim._edges.values():
            self.assertAlmostEqual(edge.weight, baseline)
        sim.stimulate_pattern(get_line("H1"))
        for edge in sim._edges.values():
            self.assertAlmostEqual(edge.weight, baseline)
        sim.reset()
        for edge in sim._edges.values():
            self.assertAlmostEqual(edge.weight, baseline)

    def test_pattern_learning_with_scaling(self) -> None:
        sim = BrainSimulator(dynamics=deterministic_dynamics())
        learn_catalog_line(sim, "H1")
        pattern = get_line("H1")
        owner = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        self.assertTrue(str(owner).startswith("nucleus_e_"))


class EpAfferentPlasticityTests(unittest.TestCase):
    def test_delivered_charge_scales_by_ep_weight(self) -> None:
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        di = DescendingInhibition(lif, gain=0.20, afferent_init_weight=0.5)
        di.enqueue_from_population_spikes(("nucleus_e_0",), frozenset({4}))
        di.apply_pending(relay, timestep=1)
        # pending 0.20 * w=0.5 → 0.10 on E′
        self.assertAlmostEqual(
            relay.pairs[4].secondary_excitatory.membrane, 0.10, places=4
        )

    def test_immature_needs_multiple_hits_mature_one_hit(self) -> None:
        lif = LifDynamics()
        # Immature below production default: 0.18*0.75=0.135 < θ=0.26 → needs ≥2 hits
        relay = Layer1Relay(lif)
        di = DescendingInhibition(lif, gain=0.18, afferent_init_weight=0.75)
        di.enqueue_from_population_spikes(("e0",), frozenset({0}))
        fired = di.apply_pending(relay, timestep=1)
        self.assertEqual(fired, frozenset())
        di.enqueue_from_population_spikes(("e0",), frozenset({0}))
        fired = di.apply_pending(relay, timestep=2)
        self.assertIn("l1_ep_0", fired)

        # Mature (post-credit max): 0.18*1.5=0.27 ≥ θ → one hit
        relay2 = Layer1Relay(lif)
        di2 = DescendingInhibition(lif, gain=0.18, afferent_init_weight=1.5)
        di2.enqueue_from_population_spikes(("e0",), frozenset({0}))
        fired2 = di2.apply_pending(relay2, timestep=1)
        self.assertIn("l1_ep_0", fired2)

    def test_ep_weight_increases_on_force_i_fire(self) -> None:
        lif = LifDynamics()
        relay = Layer1Relay(lif)
        di = DescendingInhibition(
            lif,
            gain=0.40,
            afferent_init_weight=0.75,
            assembly_credit_enabled=True,
            assembly_learner=AssemblyFlowCreditLearner(
                AssemblyFlowCreditConfig(learning_rate=0.05, decay_frac=0.5)
            ),
        )
        before = di.assembly_afferents.weights[1]
        di.enqueue_from_population_spikes(("e0",), frozenset({1}))
        fired = di.apply_pending(relay, timestep=1, learn_assembly=True)
        self.assertIn("l1_i_1", fired)
        self.assertGreater(di.assembly_afferents.weights[1], before)

    def test_ep_weights_serialized_in_state(self) -> None:
        sim = BrainSimulator()
        state = sim.get_state()
        self.assertIn("descending", state)
        weights = state["descending"]["assembly_afferents"]["weights"]
        self.assertEqual(len(weights), 9)
        self.assertAlmostEqual(
            weights[0], DEFAULT_LEARNING_DYNAMICS.assembly_afferent_init_weight
        )


if __name__ == "__main__":
    unittest.main()
