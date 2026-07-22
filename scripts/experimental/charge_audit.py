#!/usr/bin/env python3
"""Trace membrane drive per timestep: L1 relay → L2 ring (no double integration)."""

from __future__ import annotations

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS


def main() -> None:
    pattern = get_line("H1")
    sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
    d = DEFAULT_LEARNING_DYNAMICS

    print("=== Charge audit (H1, first 15 timesteps) ===")
    print(
        f"dynamics: relay_w={d.nucleus_relay_weight} theta_L2={d.nucleus_threshold} "
        f"tau={d.membrane_tau} elig_alpha={d.eligibility_alpha} "
        f"consolidation_w={d.consolidation_weight_threshold}"
    )
    print(
        "tick | L1 relays | drive_N0 | mem_N0 | winner | trace_N0 | sensory_w(3,4,5)"
    )

    for tick in range(1, 16):
        pre_ring = sim.nucleus.ring[0]
        pre_mem = pre_ring.neuron.membrane
        pre_trace = pre_ring.eligibility_trace.trace

        result = sim.stimulate_pattern(pattern)
        state = sim.get_state()

        relay_ids = result.relay_indices
        ring0 = state["nucleus"]["ring"][0]
        mem = ring0["membrane"]
        trace = ring0.get("eligibility_trace", ring0.get("bind_progress", 0))
        sensory = ring0.get("sensory_conductances", {})
        w345 = (
            sensory.get("input_r1_c0"),
            sensory.get("input_r1_c1"),
            sensory.get("input_r1_c2"),
        )

        drive_est = pre_ring.compute_drive(sim._last_relay_ids)
        binds = [e for e in result.step_events if e.get("type") == EventType.PATTERN_BOUND.name]

        print(
            f"{tick:4d} | {sorted(relay_ids)} | {drive_est:8.4f} | "
            f"{mem:6.3f} | {result.winner_neuron_id or '-':10} | "
            f"{trace:5.2f} | {w345}"
            + (" BIND" if binds else "")
        )

        if binds:
            break

    print("\n=== Steady-state estimate (3 relays @ nucleus_relay_weight) ===")
    w = d.nucleus_relay_weight
    drive = 3 * w
    leak = 1.0 - 1.0 / d.membrane_tau
    steady = drive / (1.0 - leak) if leak < 1.0 else float("inf")
    ticks_to_theta = 0
    mem = 0.0
    while mem < d.nucleus_threshold and ticks_to_theta < 50:
        mem = mem * (1.0 - 1.0 / d.membrane_tau) + drive
        ticks_to_theta += 1
    print(f"per-tick drive (uniform 3x{w:.3f}) = {drive:.4f}")
    print(f"leak factor per tick = {1.0 - 1.0/d.membrane_tau:.3f}")
    print(f"steady-state membrane = {steady:.4f}")
    print(f"ticks to reach theta={d.nucleus_threshold}: {ticks_to_theta}")


if __name__ == "__main__":
    main()
