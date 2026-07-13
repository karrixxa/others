"""Deterministic one-pattern diagnostic for the four-pattern CIPP task.

This script does not change the engine or its learning rules. It holds one input
pattern for a fixed number of steps and reports whether competition is moving
toward one late-window winner, whether L2I remains active, whether feedback is
selective, and whether L2E receptive fields are saturating or collapsing together.

CONFIGURATION MODEL (measurement-only patch, 2026-07-13)
----------------------------------------------------------------------------
--preset {constructor,dashboard} selects a NAMED base configuration from
backend/presets.py:
  - "constructor" (default): SimulationEngine's own constructor defaults,
    unmodified -- i.e. no overrides at all.
  - "dashboard": the EXACT override dict backend/api.py uses to build the live
    dashboard engine (backend.presets.DASHBOARD_ENGINE_OVERRIDES). This module
    does NOT import backend.api -- only backend.presets, which defines a plain
    dict and constructs nothing -- so running this script never builds the
    live server engine or has any server-side effect.

Every individual override flag below (--eta-loss, --assembly-flow-credit, ...)
defaults to None, meaning "not specified." Only flags that are explicitly
passed override the selected preset; anything left at None leaves the preset's
value (or the constructor default, under --preset constructor) untouched. This
is what makes "--preset dashboard --eta-loss 2" an honest single-variable
change against the real dashboard configuration, and what makes
"--preset constructor" reproduce plain SimulationEngine() defaults exactly
instead of silently reintroducing this script's old hardcoded flag defaults.

The complete effective configuration (preset name + every resolved override)
is always printed before the run.

Examples:
    PYTHONPATH=. python3 single_pattern_diagnostic.py --pattern "row 1" --seed 1 --steps 8000
    PYTHONPATH=. python3 single_pattern_diagnostic.py --preset constructor --eta-loss 2
    PYTHONPATH=. python3 single_pattern_diagnostic.py --preset dashboard
"""

from __future__ import annotations

import argparse
from collections import Counter

import numpy as np

from backend.presets import PRESETS
from backend.simulation import N_OUT, N_PIX, PATTERNS, SimulationEngine

# Individual CLI override flags -> the SimulationEngine constructor kwarg they
# set. Every one of these defaults to None in argparse (see build_parser) so
# "not specified" can be told apart from an intentional override of whatever
# the selected --preset already set.
_OVERRIDE_ARGS = (
    "inhibitory_eta_up", "inhibitory_eta_down", "allow_subrest_inhibition",
    "l2_gate_eq_frac", "l2e_weight_cap_frac", "eta_loss", "assembly_flow_credit",
)


def _resolve_config(preset_name: str, args: argparse.Namespace) -> dict:
    """Start from the named preset's override dict (copied, never mutated in
    place), then apply only the CLI flags the caller actually passed (not
    None). Returns the fully resolved kwargs dict to hand to SimulationEngine."""
    if preset_name not in PRESETS:
        raise SystemExit(f"unknown --preset {preset_name!r}; choose from {list(PRESETS)}")
    config = dict(PRESETS[preset_name])   # copy -- never mutate the shared preset dict
    for name in _OVERRIDE_ARGS:
        value = getattr(args, name)
        if value is not None:
            config[name] = value
    return config


def _norm(v: np.ndarray) -> float:
    return float(np.linalg.norm(v))


def _cosine_or_undefined(a: np.ndarray, b: np.ndarray):
    """Cosine similarity, or None (reported as 'undefined', never silently 0)
    when either subvector has near-zero norm -- a zero vector has no direction,
    so its cosine with anything is mathematically undefined, not 0."""
    na, nb = _norm(a), _norm(b)
    if na < 1e-9 or nb < 1e-9:
        return None
    return float(a.dot(b) / (na * nb))


def _fmt(x):
    return "undefined" if x is None else f"{x:.3f}"


def run(pattern: str, seed: int, steps: int, late_fraction: float, config: dict) -> None:
    if pattern not in PATTERNS:
        raise SystemExit(f"unknown pattern {pattern!r}; choose from {list(PATTERNS)}")
    if steps < 1:
        raise SystemExit("--steps must be positive")

    print("=== effective configuration ===")
    print(f"pattern={pattern!r} seed={seed} steps={steps} late_fraction={late_fraction}")
    for k in sorted(config):
        print(f"  {k}={config[k]!r}")
    print()

    engine = SimulationEngine(seed=seed, **config)
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

    active_pixels = [i for i, value in enumerate(PATTERNS[pattern]) if value]
    active_mask = np.zeros(N_PIX, dtype=bool)
    active_mask[active_pixels] = True
    inactive_mask = ~active_mask

    ff, gates, cap_fractions = [], [], []
    floor_counts, cap_counts = [], []
    for j, neuron in enumerate(engine.l2.excitatory_neurons):
        weights = np.asarray(neuron._weights_array, dtype=float)
        ff_j = weights[1:1 + N_PIX]
        ff.append(ff_j)
        gates.append(abs(float(weights[0])))
        cap = float(neuron.weight_cap) or 1.0
        cap_fractions.append(float(np.max(ff_j) / cap))
        floor = float(neuron.min_positive_weight) if neuron.min_positive_weight is not None else 0.0
        floor_counts.append(int(np.sum(np.abs(ff_j - floor) < 1e-6)))
        cap_counts.append(int(np.sum(np.abs(ff_j - cap) < 1e-6)))

    feedback_active = [i for i, count in enumerate(l1i_counts) if count]

    print("=== deterministic one-pattern diagnostic ===")
    print(f"active_pixels={active_pixels}")
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

    # Require repeated ownership, not a misleading "100%" based on one isolated
    # late spike in a run that was too short to establish a rhythm.
    stable = late_total >= 5 and late_share >= 0.90 and runner_count == 0
    feedback_selective = bool(feedback_active) and set(feedback_active).issubset(active_pixels)
    print(f"stable_single_winner={stable}")
    print(f"feedback_selective_to_active_pixels={feedback_selective}")

    # ---- extended per-neuron receptive-field metrics -----------------------
    print("\n=== per-L2E receptive-field detail ===")
    for j in range(N_OUT):
        label = "WINNER" if j == winner else "loser"
        act = ff[j][active_mask]
        inact = ff[j][inactive_mask]
        print(f"L2E{j} [{label}]: full_norm={_norm(ff[j]):.3f}  "
              f"active(mean/min/max)={act.mean():.3f}/{act.min():.3f}/{act.max():.3f}  "
              f"inactive(mean/min/max)={inact.mean():.3f}/{inact.min():.3f}/{inact.max():.3f}  "
              f"at_floor={floor_counts[j]}/{N_PIX}  at_cap={cap_counts[j]}/{N_PIX}")

    print("\n=== pairwise receptive-field comparisons ===")
    full_cos, active_cos, inactive_cos, euclid = [], [], [], []
    for a in range(N_OUT):
        for b in range(a + 1, N_OUT):
            fc = _cosine_or_undefined(ff[a], ff[b])
            ac = _cosine_or_undefined(ff[a][active_mask], ff[b][active_mask])
            ic = _cosine_or_undefined(ff[a][inactive_mask], ff[b][inactive_mask])
            ed = float(np.linalg.norm(ff[a] - ff[b]))
            full_cos.append(fc); active_cos.append(ac); inactive_cos.append(ic); euclid.append(ed)
            print(f"  L2E{a} vs L2E{b}: full_cos={_fmt(fc)}  active_cos={_fmt(ac)}  "
                  f"inactive_cos={_fmt(ic)}  euclid_dist={ed:.3f}")

    def _summ(name, values):
        defined = [v for v in values if v is not None]
        undefined_n = len(values) - len(defined)
        if defined:
            print(f"  {name}: mean={np.mean(defined):.3f} min={np.min(defined):.3f} "
                  f"max={np.max(defined):.3f}" + (f"  ({undefined_n} undefined)" if undefined_n else ""))
        else:
            print(f"  {name}: all undefined (every pair had a near-zero-norm subvector)")

    print("summary across all pairs:")
    _summ("full-vector cosine", full_cos)
    _summ("active-input cosine", active_cos)
    _summ("inactive-input cosine", inactive_cos)
    print(f"  euclidean distance: mean={np.mean(euclid):.3f} min={np.min(euclid):.3f} max={np.max(euclid):.3f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default="row 1", choices=list(PATTERNS))
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--steps", type=int, default=8000)
    parser.add_argument("--late-fraction", type=float, default=0.25)
    parser.add_argument("--preset", default="constructor", choices=list(PRESETS),
                        help="Named base configuration (backend/presets.py). "
                             "'constructor' = plain SimulationEngine defaults, "
                             "no overrides. 'dashboard' = the exact overrides "
                             "backend/api.py uses.")

    # Every override below defaults to None ("not specified" -- leaves the
    # selected preset's value, or the constructor default, untouched). This is
    # requirement 6/5 of the measurement patch: explicit CLI args override the
    # preset, and argparse defaults must not silently override it themselves.
    parser.add_argument("--inhibitory-eta-up", dest="inhibitory_eta_up", type=float, default=None)
    parser.add_argument("--inhibitory-eta-down", dest="inhibitory_eta_down", type=float, default=None)
    subrest = parser.add_mutually_exclusive_group()
    subrest.add_argument("--allow-subrest-inhibition", dest="allow_subrest_inhibition",
                         action="store_true", default=None)
    subrest.add_argument("--no-allow-subrest-inhibition", dest="allow_subrest_inhibition",
                         action="store_false", default=None)
    parser.add_argument("--l2-gate-eq-frac", dest="l2_gate_eq_frac", type=float, default=None)
    parser.add_argument("--l2e-weight-cap-frac", dest="l2e_weight_cap_frac", type=float, default=None)
    parser.add_argument("--eta-loss", dest="eta_loss", type=float, default=None)
    afc = parser.add_mutually_exclusive_group()
    afc.add_argument("--assembly-flow-credit", dest="assembly_flow_credit",
                     action="store_true", default=None)
    afc.add_argument("--no-assembly-flow-credit", dest="assembly_flow_credit",
                     action="store_false", default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not 0 < args.late_fraction <= 1:
        parser.error("--late-fraction must be in (0, 1]")
    config = _resolve_config(args.preset, args)
    print(f"preset={args.preset!r}")
    run(args.pattern, args.seed, args.steps, args.late_fraction, config)


if __name__ == "__main__":
    main()
