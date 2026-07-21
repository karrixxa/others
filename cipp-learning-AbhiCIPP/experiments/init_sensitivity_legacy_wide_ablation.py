"""Measurement-only initialization sensitivity test for legacy_wide feedforward init.

This writes artifacts outside production source and does not change production defaults.
"""

from __future__ import annotations

import copy
import json
import os
import time
from collections import Counter

import numpy as np

from backend.presets import DASHBOARD_PRESET
from backend.simulation import N_OUT, N_PIX, SimulationEngine
from diagnostic_schedule import CYCLE_ORDER, PRESENTATION_STEPS

WEIGHT_SEED = 1
TOPOLOGY_SEED = 1
CONTROL_MEAN = 125.0
MEAN_CONDITIONS = {
    "mean_125_control": 125.0,
    "mean_250_scaled": 250.0,
    "mean_400_scaled": 400.0,
}
FROZEN_CYCLES = 2
TRAIN_CYCLES = 8


def build_base_engine() -> SimulationEngine:
    kw = dict(DASHBOARD_PRESET)
    kw.update(
        seed=WEIGHT_SEED,
        topology_seed=TOPOLOGY_SEED,
        pos_weight_floor=1,
        l2e_init_mode="legacy_wide",
    )
    return SimulationEngine(**kw)


def get_feedforward_matrix(engine: SimulationEngine) -> np.ndarray:
    return np.array([engine.l2.excitatory_neurons[j].weights.copy() for j in range(N_OUT)], dtype=float)


def set_feedforward_matrix(engine: SimulationEngine, matrix: np.ndarray):
    for j, neuron in enumerate(engine.l2.excitatory_neurons):
        neuron.weights = matrix[j].copy()


def scaled_copy(matrix: np.ndarray, target_mean: float) -> np.ndarray:
    scale = target_mean / float(matrix.mean())
    return matrix * scale


def _effective_rank(weights: np.ndarray) -> float:
    singular = np.linalg.svd(weights, compute_uv=False)
    singular = singular[singular > 1e-12]
    if singular.size == 0:
        return 0.0
    p = singular / singular.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def _modal(values):
    non_none = [v for v in values if v is not None]
    if not non_none:
        return None
    counts = Counter(non_none)
    top = max(counts.values())
    return min(v for v, c in counts.items() if c == top)


def _presentation_run(engine: SimulationEngine, cycles: int, frozen: bool) -> tuple[list[dict], Counter, int, set[str]]:
    engine._set_plasticity_frozen(frozen)
    presentations = []
    first_counts = Counter()
    threshold_crossings = 0
    active = set()
    index = 0
    for _cycle in range(cycles):
        for pattern in CYCLE_ORDER:
            engine.set_pattern(pattern)
            t_start = engine.timestep
            first = None
            same_step_tie = False
            for _step in range(PRESENTATION_STEPS):
                engine.step()
                firers = [f"L2E{j}" for j in range(N_OUT) if engine.spiked[f"L2E{j}"]]
                threshold_crossings += len(firers)
                active.update(firers)
                if first is None and firers:
                    first = firers[0]
                    same_step_tie = len(firers) > 1
            if first is not None:
                first_counts[first] += 1
            presentations.append(dict(
                presentation_index=index,
                pattern=pattern,
                t_start=t_start,
                t_end=engine.timestep,
                first_l2e_spiker=first,
                same_step_tie=same_step_tie,
                response_latency=None if first is None else engine._presentation_first_spike_t - t_start,
            ))
            index += 1
    engine._set_plasticity_frozen(False)
    return presentations, first_counts, threshold_crossings, active


def frozen_metrics(engine: SimulationEngine) -> dict:
    presentations, first_counts, threshold_crossings, active = _presentation_run(engine, FROZEN_CYCLES, frozen=True)
    latencies = [row["response_latency"] for row in presentations if row["response_latency"] is not None]
    return dict(
        cycles=FROZEN_CYCLES,
        active_l2e_count=len(active),
        active_l2e_ids=sorted(active),
        threshold_crossings_total=int(threshold_crossings),
        same_step_ties=int(sum(1 for row in presentations if row["same_step_tie"])),
        same_step_tie_rate=round(float(np.mean([1.0 if row["same_step_tie"] else 0.0 for row in presentations])), 4),
        first_responder_counts=dict(first_counts),
        first_responder_share=(
            {k: round(v / sum(first_counts.values()), 4) for k, v in first_counts.items()}
            if first_counts else {}
        ),
        mean_response_latency=round(float(np.mean(latencies)), 4) if latencies else None,
        presentations=presentations,
    )


def plastic_metrics(engine: SimulationEngine) -> dict:
    presentations, first_counts, _threshold_crossings, active = _presentation_run(engine, TRAIN_CYCLES, frozen=False)
    by_pattern = {pattern: [row for row in presentations if row["pattern"] == pattern] for pattern in CYCLE_ORDER}
    per_pattern = {}
    for pattern, rows in by_pattern.items():
        firsts = [row["first_l2e_spiker"] for row in rows]
        modal = _modal(firsts)
        per_pattern[pattern] = dict(
            modal_owner=modal,
            n=len(rows),
            no_response_rate=round(sum(1 for row in rows if row["first_l2e_spiker"] is None) / len(rows), 4) if rows else None,
        )
    owners = [row["modal_owner"] for row in per_pattern.values() if row["modal_owner"] is not None]
    collisions = {
        owner: sorted([pattern for pattern, row in per_pattern.items() if row["modal_owner"] == owner])
        for owner in set(owners) if owners.count(owner) > 1
    }
    weights = get_feedforward_matrix(engine)
    statuses = {f"L2E{j}": engine._l2e_status(j)["status"] for j in range(N_OUT)}
    unrecruited = sorted([nid for nid, status in statuses.items() if status == "unrecruited"])
    tyrant_share = round(max(first_counts.values()) / sum(first_counts.values()), 4) if first_counts else 0.0
    return dict(
        cycles=TRAIN_CYCLES,
        distinct_owners=len(set(owners)),
        per_pattern=per_pattern,
        collisions=collisions,
        tyrant_share=tyrant_share,
        first_responder_counts=dict(first_counts),
        effective_rank=round(_effective_rank(weights), 4),
        unrecruited_neurons=unrecruited,
        unrecruited_count=len(unrecruited),
        recruited_l2e_count=len(active),
        final_mean_weight=round(float(weights.mean()), 4),
        final_min_weight=round(float(weights.min()), 4),
        final_max_weight=round(float(weights.max()), 4),
    )


def analyze_condition(base_engine: SimulationEngine, scaled_matrix: np.ndarray, target_mean: float) -> dict:
    condition_base = copy.deepcopy(base_engine)
    set_feedforward_matrix(condition_base, scaled_matrix)
    frozen_engine = copy.deepcopy(condition_base)
    plastic_engine = copy.deepcopy(condition_base)
    return dict(
        target_mean=target_mean,
        actual_initial_mean=round(float(scaled_matrix.mean()), 4),
        actual_initial_min=round(float(scaled_matrix.min()), 4),
        actual_initial_max=round(float(scaled_matrix.max()), 4),
        frozen=frozen_metrics(frozen_engine),
        plastic=plastic_metrics(plastic_engine),
    )


def gate_condition(control: dict, candidate: dict) -> dict:
    frozen_ok = candidate["frozen"]["same_step_ties"] <= control["frozen"]["same_step_ties"]
    recruit_ok = candidate["plastic"]["recruited_l2e_count"] > control["plastic"]["recruited_l2e_count"]
    tyrant_ok = candidate["plastic"]["tyrant_share"] < control["plastic"]["tyrant_share"]
    owners_ok = candidate["plastic"]["distinct_owners"] >= control["plastic"]["distinct_owners"]
    return dict(
        recruits_more_l2e=bool(recruit_ok),
        does_not_increase_same_step_ties=bool(frozen_ok),
        lowers_tyrant_share=bool(tyrant_ok),
        preserves_or_improves_distinct_ownership=bool(owners_ok),
        passes_all=bool(recruit_ok and frozen_ok and tyrant_ok and owners_ok),
    )


def main():
    t0 = time.time()
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "init_sensitivity_legacy_wide_ablation_seed1.json")

    base_engine = build_base_engine()
    base_matrix = get_feedforward_matrix(base_engine)
    results = {}
    for name, target_mean in MEAN_CONDITIONS.items():
        results[name] = analyze_condition(base_engine, scaled_copy(base_matrix, target_mean), target_mean)

    control = results["mean_125_control"]
    gate_250 = gate_condition(control, results["mean_250_scaled"])
    gate_400 = gate_condition(control, results["mean_400_scaled"])

    payload = dict(
        created_at="2026-07-21",
        seed=WEIGHT_SEED,
        topology_seed=TOPOLOGY_SEED,
        note=(
            "Initialization ablation only. This does not claim to solve ownership."
        ),
        base_matrix_mean=round(float(base_matrix.mean()), 4),
        base_matrix_min=round(float(base_matrix.min()), 4),
        base_matrix_max=round(float(base_matrix.max()), 4),
        conditions=results,
        gate=dict(
            mean_250=gate_250,
            mean_400=gate_400,
            retain_mean_250_as_switchi_candidate=bool(gate_250["passes_all"]),
            reject_mean_400_immediately=bool(
                results["mean_400_scaled"]["frozen"]["same_step_ties"] > control["frozen"]["same_step_ties"]
                or results["mean_400_scaled"]["plastic"]["tyrant_share"] > control["plastic"]["tyrant_share"]
            ),
        ),
        runtime_seconds=round(time.time() - t0, 2),
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(dict(runtime_seconds=payload["runtime_seconds"], out_path=out_path), indent=2))


if __name__ == "__main__":
    main()
