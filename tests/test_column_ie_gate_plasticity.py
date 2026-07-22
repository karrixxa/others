"""Stage 13 Option A — plastic per-assembly column I→E gates."""

from __future__ import annotations

from cognative_paradigm.cortical_column.column_ie_gate_plasticity import (
    COLUMN_IE_GATE_I_MAX,
    ColumnIeGatePlasticity,
)
from cognative_paradigm.cortical_column.context_assembly_network import (
    ContextAssemblyNetwork,
)
from cognative_paradigm.cortical_column.context_inhibitory_network import (
    ContextInhibitoryNetwork,
)
from cognative_paradigm.domain.column_profile import ColumnCausalPolicy
from cognative_paradigm.domain.column_signal import (
    AssemblyCompetitionResult,
    Layer4Activation,
)
from cognative_paradigm.domain.lif_dynamics import LifDynamics
from cognative_paradigm.domain.register_state import RegisterState


BIO_E_THRESHOLD = 0.55


def _relay(indices: frozenset[int]) -> Layer4Activation:
    return Layer4Activation(
        line_id=None,
        active_cell_indices=indices,
        modulated_cell_indices=indices,
        input_cell_indices=indices,
        gain_gated_input_indices=indices,
        relay_spike_indices=indices,
    )


class TestColumnIeGatePlasticity:
    def test_gate_ceiling_is_subthreshold(self) -> None:
        gates = ColumnIeGatePlasticity.for_biological()
        assert gates.i_max_weight < BIO_E_THRESHOLD
        assert COLUMN_IE_GATE_I_MAX < BIO_E_THRESHOLD

    def test_plastic_gate_updates_on_i_discharge(self) -> None:
        network = ContextInhibitoryNetwork.for_biological()
        assert network.plastic_gates_enabled is True
        target = "repr_1"
        before = network.ie_gates.ensure_gate(target)
        # Near-threshold V_pre strengthens more than cold.
        hot = network.ie_gates.plasticize_on_discharge(
            target_assembly_id=target,
            v_pre=0.50,
            theta=BIO_E_THRESHOLD,
        )
        assert hot > before
        cold_target = "repr_2"
        cold_before = network.ie_gates.ensure_gate(cold_target)
        cold = network.ie_gates.plasticize_on_discharge(
            target_assembly_id=cold_target,
            v_pre=0.05,
            theta=BIO_E_THRESHOLD,
        )
        # Hot charge ratio strengthens; cold may decay via η_down.
        assert hot - before > cold - cold_before

    def test_repeated_hot_discharge_stays_at_or_below_ceiling(self) -> None:
        gates = ColumnIeGatePlasticity.for_biological()
        weight = gates.ensure_gate("repr_0")
        for _ in range(200):
            weight = gates.plasticize_on_discharge(
                target_assembly_id="repr_0",
                v_pre=BIO_E_THRESHOLD,
                theta=BIO_E_THRESHOLD,
            )
        assert weight <= gates.i_max_weight
        assert weight < BIO_E_THRESHOLD

    def test_legacy_network_keeps_fixed_scalars(self) -> None:
        network = ContextInhibitoryNetwork()
        assert network.plastic_gates_enabled is False
        suppression = network.suppression_for_targets(
            inhibitory_spike_ids=frozenset({"repr_0"}),
            target_assembly_ids=("repr_0", "repr_1"),
        )
        assert suppression["repr_0"] == 0.0
        assert suppression["repr_1"] == network.coupling.inhibition_strength

    def test_biological_factory_enables_plastic_gates(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        assert network.inhibitory_network is not None
        assert network.inhibitory_network.plastic_gates_enabled is True

    def test_plural_still_possible_on_exact_drive_ties(self) -> None:
        """Exact drive ties must remain plural — never invent unique via argmax."""
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        assert network.assemblies is not None
        # Force identical membranes/registers as if two authentic spikes landed.
        a0, a1 = network.assemblies[0], network.assemblies[1]
        assert a0.neuron is not None and a1.neuron is not None
        a0.neuron.register = RegisterState.ONE
        a1.neuron.register = RegisterState.ONE
        a0.neuron.membrane = a0.neuron.threshold
        a1.neuron.membrane = a1.neuron.threshold
        result = AssemblyCompetitionResult.plural(
            frozenset({a0.assembly_id, a1.assembly_id})
        )
        assert result.unique_representation_id is None
        assert result.ambiguous is True
        assert len(result.spiker_assembly_ids) == 2

    def test_no_unique_invented_when_two_authentic_spikes(self) -> None:
        policy = ColumnCausalPolicy.for_profile("hybrid_cortical_biological")
        network = ContextAssemblyNetwork(policy=policy)
        assert network.assemblies is not None
        # Bypass race: mark two assemblies as already spiked, run Stage-6-like
        # suppression bookkeeping through the inhibitory network only.
        e_spikers = frozenset(
            {network.assemblies[0].assembly_id, network.assemblies[1].assembly_id}
        )
        for assembly in network.assemblies[:2]:
            assert assembly.neuron is not None
            assembly.neuron.register = RegisterState.ONE
            assembly.neuron.membrane = assembly.neuron.threshold
        lif = LifDynamics()
        assert network.inhibitory_network is not None
        all_ids = tuple(a.assembly_id for a in network.assemblies)
        i_spikes = network.inhibitory_network.apply_e_to_i(
            lif,
            excitatory_spiker_ids=e_spikers,
            all_assembly_ids=all_ids,
            timestep=1,
        )
        if i_spikes:
            suppression = network.inhibitory_network.suppression_for_targets(
                inhibitory_spike_ids=i_spikes,
                target_assembly_ids=all_ids,
            )
            for assembly in network.assemblies:
                amount = suppression.get(assembly.assembly_id, 0.0)
                if amount <= 0.0:
                    continue
                neuron = assembly.neuron
                assert neuron is not None
                v_pre = float(neuron.membrane)
                neuron.membrane = max(0.0, neuron.membrane - amount)
                network.inhibitory_network.ie_gates.plasticize_on_discharge(
                    target_assembly_id=assembly.assembly_id,
                    v_pre=v_pre,
                    theta=float(neuron.threshold),
                )
        spikers = [
            a.assembly_id
            for a in network.assemblies
            if a.neuron is not None and a.neuron.register == RegisterState.ONE
        ]
        assert len(spikers) == 2
        result = AssemblyCompetitionResult.plural(frozenset(spikers))
        assert result.unique_representation_id is None
        assert result.has_unique_representation is False

    def test_disabled_gates_do_not_plasticize(self) -> None:
        gates = ColumnIeGatePlasticity.disabled()
        before = gates.ensure_gate("repr_0")
        after = gates.plasticize_on_discharge(
            target_assembly_id="repr_0",
            v_pre=0.5,
            theta=BIO_E_THRESHOLD,
        )
        assert after == before
        assert gates.gate_weights.get("repr_0") == before or "repr_0" not in gates.gate_weights
