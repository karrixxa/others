"""Deterministic one-pattern diagnostic for the four-pattern CIPP task.

This script does not change the engine or its learning rules. It holds one input
pattern for a fixed number of steps and reports whether competition is moving
toward one late-window winner, whether L2I remains active, whether feedback is
selective, and whether L2E receptive fields are saturating or collapsing together.

Example:
    PYTHONPATH=. python3 single_pattern_diagnostic.py --pattern "row 1" --seed 1 --steps 8000
"""

from __future__ import annotations

import argparse
from collections import Counter

import numpy as np

from backend.simulation import N_OUT, N_PIX, PATTERNS, SimulationEngine


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(a.dot(b) / denom) if denom else 0.0


def run(pattern: str, seed: int, steps: int, late_fraction: float,
        inhibitory_eta_up: float, inhibitory_eta_down: float,
        allow_subrest_inhibition: bool, l2_gate_eq_frac: float,
        l2e_weight_cap_frac: float, eta_loss: float) -> None:
    if pattern not in PATTERNS:
        raise SystemExit(f"unknown pattern {pattern!r}; choose from {list(PATTERNS)}")
    if steps < 1:
        raise SystemExit("--steps must be positive")

    engine = SimulationEngine(seed=seed,
                              inhibitory_eta_up=inhibitory_eta_up,
                              inhibitory_eta_down=inhibitory_eta_down,
                              allow_subrest_inhibition=allow_subrest_inhibition,
                              l2_gate_eq_frac=l2_gate_eq_frac,
                              l2e_weight_cap_frac=l2e_weight_cap_frac,
                              eta_loss=eta_loss)
    engine.set_pattern(pattern)
    late_start = max(0, int(steps * (1.0 - late_fraction)))

    l2_spikes: list[tuple[int, int]] = []
    l2i_steps: list[int] = []
    l1e_counts = np.zeros(N_PIX, dtype=int)
    l1i_counts = np.zeros(N_PIX, dtype=int)

    for step in range(steps):
        engine.step()
        for i in range(N_PIX):
            l1e_counts[i] += int(engine.spiked[f"L1E{i}"])
            l1i_counts[i] += int(engine.spiked[f"L1I{i}"])
        for j in range(N_OUT):
            if engine.spiked[f"L2E{j}"]:
                l2_spikes.append((step, j))
        if engine.spiked["L2I"]:
            l2i_steps.append(step)

    all_counts = Counter(j for _, j in l2_spikes)
    late_counts = Counter(j for t, j in l2_spikes if t >= late_start)
    ranked = late_counts.most_common()
    winner = ranked[0][0] if ranked else None
    winner_count = ranked[0][1] if ranked else 0
    runner_count = ranked[1][1] if len(ranked) > 1 else 0
    late_total = sum(late_counts.values())
    late_share = winner_count / late_total if late_total else 0.0

    ff = []
    gates = []
    cap_fractions = []
    for j, neuron in enumerate(engine.l2.excitatory_neurons):
        weights = np.asarray(neuron._weights_array, dtype=float)
        ff_j = weights[1:1 + N_PIX]
        ff.append(ff_j)
        gates.append(abs(float(weights[0])))
        cap = float(neuron.weight_cap) or 1.0
        cap_fractions.append(float(np.max(ff_j) / cap))

    pair_cos = [_cosine(ff[a], ff[b]) for a in range(N_OUT) for b in range(a + 1, N_OUT)]
    active_pixels = [i for i, value in enumerate(PATTERNS[pattern]) if value]
    feedback_active = [i for i, count in enumerate(l1i_counts) if count]

    print("=== deterministic one-pattern diagnostic ===")
    print(f"pattern={pattern!r} active_pixels={active_pixels} seed={seed} steps={steps}")
    print(f"inhibitory turnover: eta_up={inhibitory_eta_up} eta_down={inhibitory_eta_down}")
    print(f"allow_subrest_inhibition={allow_subrest_inhibition}")
    print(f"l2_gate_eq_frac={l2_gate_eq_frac or 'baseline'}")
    print(f"l2e_weight_cap_frac={l2e_weight_cap_frac}")
    print(f"loser_depression eta_loss={eta_loss}")
    print(f"late_window={late_start}..{steps - 1} ({late_fraction:.0%} of run)")
    print(f"L2E total spikes: {dict(sorted(all_counts.items()))}")
    print(f"L2E late spikes : {dict(sorted(late_counts.items()))}")
    print(f"late modal winner: {('L2E' + str(winner)) if winner is not None else 'none'}")
    print(f"late winner share: {late_share:.3f}; winner-runner margin: {winner_count - runner_count} spikes")
    print(f"L2I spikes: total={len(l2i_steps)} late={sum(t >= late_start for t in l2i_steps)}")
    print(f"L1E spike counts: {l1e_counts.tolist()}")
    print(f"L1I spike counts: {l1i_counts.tolist()} (active feedback cells={feedback_active})")
    print(f"L2I->L2E gate magnitudes: {[round(v, 3) for v in gates]}")
    print(f"largest L2E feedforward weight/cap: {[round(v, 3) for v in cap_fractions]}")
    if pair_cos:
        print(f"pairwise RF cosine: mean={np.mean(pair_cos):.3f} min={np.min(pair_cos):.3f} max={np.max(pair_cos):.3f}")

    # Require repeated ownership, not a misleading "100%" based on one isolated
    # late spike in a run that was too short to establish a rhythm.
    stable = late_total >= 5 and late_share >= 0.90 and runner_count == 0
    feedback_selective = bool(feedback_active) and set(feedback_active).issubset(active_pixels)
    print(f"stable_single_winner={stable}")
    print(f"feedback_selective_to_active_pixels={feedback_selective}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default="row 1", choices=list(PATTERNS))
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--steps", type=int, default=8000)
    parser.add_argument("--late-fraction", type=float, default=0.25)
    parser.add_argument("--inhibitory-eta-up", type=float, default=0.02)
    parser.add_argument("--inhibitory-eta-down", type=float, default=0.005)
    parser.add_argument("--allow-subrest-inhibition", action="store_true")
    parser.add_argument("--l2-gate-eq-frac", type=float, default=0.0)
    parser.add_argument("--l2e-weight-cap-frac", type=float, default=1.0)
    parser.add_argument("--eta-loss", type=float, default=0.01)
    args = parser.parse_args()
    if not 0 < args.late_fraction <= 1:
        parser.error("--late-fraction must be in (0, 1]")
    run(args.pattern, args.seed, args.steps, args.late_fraction,
        args.inhibitory_eta_up, args.inhibitory_eta_down,
        args.allow_subrest_inhibition, args.l2_gate_eq_frac,
        args.l2e_weight_cap_frac, args.eta_loss)


if __name__ == "__main__":
    main()
