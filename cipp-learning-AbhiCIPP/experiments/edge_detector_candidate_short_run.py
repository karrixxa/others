"""Bounded simulator-side comparison of the legacy control vs the measured
edge_detector_candidate developmental start.

This is a short delivery check, not a claim that stable 4/4 ownership is solved.
Artifacts stay under experiments/results.
"""

from __future__ import annotations

import json
import os
import time

from init_sensitivity_legacy_wide_ablation import (
    TRAIN_CYCLES,
    build_base_engine,
    frozen_metrics,
    gate_condition,
    get_feedforward_matrix,
    plastic_metrics,
    scaled_copy,
    set_feedforward_matrix,
)

SEEDS = [1, 2, 3]
CONDITIONS = {
    "legacy_125_control": 125.0,
    "edge_detector_candidate_250": 250.0,
}


def run_condition(seed: int, target_mean: float) -> dict:
    engine = build_base_engine()
    engine.params["seed"] = seed
    engine._build()
    base = get_feedforward_matrix(engine)
    matrix = scaled_copy(base, target_mean)
    frozen_engine = build_base_engine()
    frozen_engine.params["seed"] = seed
    frozen_engine._build()
    set_feedforward_matrix(frozen_engine, matrix)
    plastic_engine = build_base_engine()
    plastic_engine.params["seed"] = seed
    plastic_engine._build()
    set_feedforward_matrix(plastic_engine, matrix)
    return dict(
        seed=seed,
        target_mean=target_mean,
        initial_mean=round(float(matrix.mean()), 4),
        frozen=frozen_metrics(frozen_engine),
        plastic=plastic_metrics(plastic_engine),
    )


def summarize(rows: list[dict]) -> dict:
    return dict(
        seeds=[row["seed"] for row in rows],
        mean_distinct_owners=round(sum(row["plastic"]["distinct_owners"] for row in rows) / len(rows), 4),
        mean_tyrant_share=round(sum(row["plastic"]["tyrant_share"] for row in rows) / len(rows), 4),
        mean_same_step_ties=round(sum(row["frozen"]["same_step_ties"] for row in rows) / len(rows), 4),
        mean_recruited=round(sum(row["plastic"]["recruited_l2e_count"] for row in rows) / len(rows), 4),
    )


def main():
    t0 = time.time()
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "edge_detector_candidate_short_run.json")

    payload = {
        "created_at": "2026-07-21",
        "note": (
            "Delivery-time bounded comparison only. This keeps legacy mean-125 as "
            "control and tests the measured mean-250 candidate over three seeds."
        ),
        "train_cycles": TRAIN_CYCLES,
        "conditions": {},
    }
    for name, target_mean in CONDITIONS.items():
        rows = [run_condition(seed, target_mean) for seed in SEEDS]
        payload["conditions"][name] = {
            "per_seed": rows,
            "summary": summarize(rows),
        }

    payload["gate"] = gate_condition(
        payload["conditions"]["legacy_125_control"]["per_seed"][0],
        payload["conditions"]["edge_detector_candidate_250"]["per_seed"][0],
    )
    payload["runtime_seconds"] = round(time.time() - t0, 2)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps({"out_path": out_path, "runtime_seconds": payload["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
