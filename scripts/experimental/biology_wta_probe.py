"""Probe central-I WTA dynamics for the biological flat workspace."""

from cognative_paradigm.lines import pattern_from_indices
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from tests.simulation_helpers import biology_dynamics


def probe(label: str, dynamics) -> None:
    pattern = pattern_from_indices([0, 1, 2])
    sim = BrainSimulator(dynamics=dynamics)
    winners = central = relays = no_above = 0
    mem_trace: list[tuple[float, float, float]] = []

    for step in range(80):
        result = sim.stimulate_pattern(pattern)
        state = sim.get_state()
        ring = state["nucleus"]["ring"]
        max_mem = max(entry["membrane"] for entry in ring)
        min_mem = min(entry["membrane"] for entry in ring)
        central_mem = state["nucleus"]["central_inhibitor_membrane"]

        if result.winner_neuron_id:
            winners += 1
        else:
            no_above += 1
        if state["nucleus"].get("wta_central_fired"):
            central += 1
        if any(pair["excitatory_register"] == "1" for pair in state["layer1"]["pairs"]):
            relays += 1
        mem_trace.append((max_mem, min_mem, central_mem))

    last = state
    print(f"=== {label} ===")
    print(f"  winners: {winners}/80  no_wta_winner: {no_above}/80")
    print(f"  central_fired: {central}/80  l1_relays: {relays}/80")
    print(
        f"  ring membrane last tick: max={mem_trace[-1][0]:.3f} "
        f"min={mem_trace[-1][1]:.3f} central_I={mem_trace[-1][2]:.3f}"
    )
    print(f"  inhibitory_channels: {last['nucleus']['inhibitory_channels']}")
    print(
        f"  dynamics: relay={dynamics.nucleus_relay_weight} "
        f"theta={dynamics.nucleus_threshold} "
        f"central_I={dynamics.central_inhibition_strength} "
        f"collateral={dynamics.collateral_gain} "
        f"consolidation_w={dynamics.consolidation_weight_threshold} "
        f"noise={dynamics.membrane_noise_std}"
    )
    print()


if __name__ == "__main__":
    probe("DEFAULT_LEARNING_DYNAMICS", DEFAULT_LEARNING_DYNAMICS)
    probe(
        "biology_dynamics() test helper",
        biology_dynamics(consolidation_weight_threshold=0.15),
    )
