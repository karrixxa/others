r"""Phase 36 predictive-output conductance audit.

Compares four iso-seeded conditions:
  A: prediction OFF
  B: PC learning shadow-only
  C: active PC path with existing instantaneous inhibition
  D: C plus persistent predictive conductance

Schedules:
  - equal-interleaved four-pattern: row1 -> col1 -> diag\ -> diag/ (20 steps)
  - row->column->row: row1 -> col1 -> row1 (20 steps each), repeated

The 30-seed expansion gate is PREREGISTERED here, before running:
run 30 only if D beats C on mean distinct owners over the 5-seed interleaved
batch while not worsening either max first-responder share or no-response rate.
"""

from __future__ import annotations

import json
import math
import os
import time
from collections import Counter

import numpy as np

from backend.presets import DASHBOARD_PRESET
from backend.simulation import N_OUT, N_PIX, SimulationEngine
from diagnostic_schedule import CYCLE_ORDER, PRESENTATION_STEPS
from phase27_l2_ownership_causal_audit import (
    CausalTracer,
    analyze_run,
    find_earliest_modal_collision,
    find_persistent_ownership_collision,
)

TOPOLOGY_SEED = 1
ROW_COL_ROW_ORDER = ["row 1", "col 1", "row 1"]
ROW_COL_ROW_REPEATS = 40
INTERLEAVED_REPEATS = 40
SHARED_PIXEL = 4
ROW_ONLY_PIXELS = [3, 5]
COL_NOVEL_PIXELS = [1, 7]
SEED_STAGES = {"seed_1": [1], "seed_5": [1, 2, 3, 4, 5], "seed_30": list(range(1, 31))}

CONDITIONS = {
    "A_prediction_off": {},
    "B_pc_shadow_only": {
        "prediction_column_enabled": True,
    },
    "C_pc_instantaneous": {
        "prediction_column_enabled": True,
        "prediction_column_to_i_enabled": True,
    },
    "D_pc_persistent": {
        "prediction_column_enabled": True,
        "prediction_column_to_i_enabled": True,
        "prediction_column_persistent_conductance_enabled": True,
    },
}


def build_engine(condition_name: str, weight_seed: int) -> SimulationEngine:
    kw = dict(DASHBOARD_PRESET)
    kw.update(CONDITIONS[condition_name])
    kw["seed"] = weight_seed
    kw["topology_seed"] = TOPOLOGY_SEED
    # Phase 36 requirement: use the existing positive-weight floor so FF
    # weights cannot hit exact zero; do not invent another floor rule.
    kw["pos_weight_floor"] = 1
    return SimulationEngine(**kw)


def _effective_rank(weights: np.ndarray) -> float:
    singular = np.linalg.svd(weights, compute_uv=False)
    singular = singular[singular > 1e-12]
    if singular.size == 0:
        return 0.0
    p = singular / singular.sum()
    return float(np.exp(-(p * np.log(p)).sum()))


def _weight_metrics(engine: SimulationEngine) -> dict:
    matrix = np.array([engine.l2.excitatory_neurons[j]._weights_array.copy() for j in range(N_OUT)])
    return dict(
        exact_zero_count=int(np.count_nonzero(np.isclose(matrix, 0.0, atol=1e-12))),
        minimum_weight=round(float(matrix.min()), 6),
        effective_rank=round(_effective_rank(matrix), 4),
    )


def _stable_distinct_owner_count(per_pattern: dict) -> int:
    stable = [row["modal_owner"] for row in per_pattern.values()
              if row["modal_owner"] is not None and row["consistency"] >= 1.0]
    return len(set(stable))


def _pc_mode_counts(engine: SimulationEngine, counts: Counter):
    if not engine.prediction_column_enabled:
        return
    for i in range(N_PIX):
        if not engine.spiked.get(f"PC{i}"):
            continue
        basal = bool(engine.pcol[i].last_basal_sources)
        apical = bool(engine.pcol[i].last_apical_sources)
        if basal and apical:
            counts["coincidence"] += 1
        elif apical and not basal:
            counts["feedback_only"] += 1
        elif basal and not apical:
            counts["basal_only"] += 1
        else:
            counts["other"] += 1


def run_schedule(engine: SimulationEngine, schedule: list[tuple[str, int]], schedule_patterns: list[str]) -> dict:
    tracer = CausalTracer(engine)
    pc_counts: Counter = Counter()
    presentations: list[dict] = []
    idx = 0
    for cycle_no, (pattern, total_steps) in enumerate(schedule):
        engine.set_pattern(pattern)
        n_windows = total_steps // PRESENTATION_STEPS
        for _window in range(n_windows):
            t_start = engine.timestep
            l1e_counts = np.zeros(N_PIX, dtype=float)
            first = None
            same_step_tie = False
            for _step in range(PRESENTATION_STEPS):
                engine.step()
                _pc_mode_counts(engine, pc_counts)
                l1e_counts += np.array([1.0 if engine.spiked[f"L1E{i}"] else 0.0 for i in range(N_PIX)])
                if first is None:
                    firers = [f"L2E{j}" for j in range(N_OUT) if engine.spiked[f"L2E{j}"]]
                    if firers:
                        first = firers[0]
                        same_step_tie = len(firers) > 1
            presentations.append(dict(
                presentation_index=idx,
                cycle=cycle_no,
                pattern=pattern,
                t_start=t_start,
                t_end=engine.timestep,
                first_l2e_spiker=first,
                same_step_tie=same_step_tie,
                l1e_rates={f"L1E{i}": round(float(l1e_counts[i] / PRESENTATION_STEPS), 4)
                           for i in range(N_PIX)},
            ))
            idx += 1
    analysis = analyze_run(engine, tracer, presentations, schedule_patterns)
    analysis["stable_distinct_owners"] = _stable_distinct_owner_count(analysis["per_pattern"])
    analysis["earliest_modal_collision"] = find_earliest_modal_collision(presentations)
    analysis["persistent_ownership_collision"] = find_persistent_ownership_collision(presentations)
    analysis["max_first_responder_share"] = round(max(analysis["tyrant_share"].values()), 4) if analysis["tyrant_share"] else 0.0
    analysis["pc_fire_modes"] = dict(pc_counts)
    analysis["weight_metrics"] = _weight_metrics(engine)
    return dict(engine=engine, tracer=tracer, presentations=presentations, analysis=analysis)


def interleaved_schedule() -> list[tuple[str, int]]:
    return [(pattern, PRESENTATION_STEPS) for _ in range(INTERLEAVED_REPEATS) for pattern in CYCLE_ORDER]


def row_col_row_schedule() -> list[tuple[str, int]]:
    return [(pattern, PRESENTATION_STEPS) for _ in range(ROW_COL_ROW_REPEATS) for pattern in ROW_COL_ROW_ORDER]


def _row_col_row_metrics(presentations: list[dict]) -> dict:
    shared_rates = []
    novel_rates = []
    row_recovery = []
    row_owner_recovered = []
    for i in range(0, len(presentations), 3):
        first_row, middle_col, return_row = presentations[i:i + 3]
        shared_rates.append(middle_col["l1e_rates"][f"L1E{SHARED_PIXEL}"])
        novel_rates.append(float(np.mean([middle_col["l1e_rates"][f"L1E{pix}"] for pix in COL_NOVEL_PIXELS])))
        initial_row_only = float(np.mean([first_row["l1e_rates"][f"L1E{pix}"] for pix in ROW_ONLY_PIXELS]))
        return_row_only = float(np.mean([return_row["l1e_rates"][f"L1E{pix}"] for pix in ROW_ONLY_PIXELS]))
        if initial_row_only > 1e-9:
            row_recovery.append(return_row_only / initial_row_only)
        row_owner_recovered.append(
            bool(first_row["first_l2e_spiker"] and first_row["first_l2e_spiker"] == return_row["first_l2e_spiker"])
        )
    return dict(
        shared_pixel_mean_rate=round(float(np.mean(shared_rates)), 4) if shared_rates else None,
        novel_pixel_mean_rate=round(float(np.mean(novel_rates)), 4) if novel_rates else None,
        shared_minus_novel_suppression=round(float(np.mean(novel_rates) - np.mean(shared_rates)), 4)
        if shared_rates and novel_rates else None,
        original_pattern_recovery_ratio=round(float(np.mean(row_recovery)), 4) if row_recovery else None,
        original_pattern_owner_recovery_rate=round(float(np.mean(row_owner_recovered)), 4) if row_owner_recovered else None,
    )


def run_condition_seed(condition_name: str, weight_seed: int) -> dict:
    interleaved = run_schedule(build_engine(condition_name, weight_seed), interleaved_schedule(), CYCLE_ORDER)
    row_col_row = run_schedule(build_engine(condition_name, weight_seed), row_col_row_schedule(), ROW_COL_ROW_ORDER)
    row_col_row["analysis"]["switch_metrics"] = _row_col_row_metrics(row_col_row["presentations"])
    return dict(
        condition=condition_name,
        weight_seed=weight_seed,
        topology_seed=TOPOLOGY_SEED,
        interleaved=interleaved["analysis"],
        row_col_row=row_col_row["analysis"],
    )


def _aggregate_runs(runs: list[dict]) -> dict:
    if not runs:
        return {}
    inter = [run["interleaved"] for run in runs]
    row = [run["row_col_row"] for run in runs]
    return dict(
        mean_distinct_owners=round(float(np.mean([r["distinct_owners"] for r in inter])), 4),
        mean_stable_distinct_owners=round(float(np.mean([r["stable_distinct_owners"] for r in inter])), 4),
        persistent_collision_rate=round(float(np.mean([1.0 if r["persistent_ownership_collision"] else 0.0 for r in inter])), 4),
        mean_max_first_responder_share=round(float(np.mean([r["max_first_responder_share"] for r in inter])), 4),
        mean_no_response_rate=round(float(np.mean([
            np.mean([row["no_response_rate"] for row in r["per_pattern"].values()])
            for r in inter
        ])), 4),
        mean_exact_zero_count=round(float(np.mean([r["weight_metrics"]["exact_zero_count"] for r in inter])), 4),
        mean_minimum_weight=round(float(np.mean([r["weight_metrics"]["minimum_weight"] for r in inter])), 6),
        mean_effective_rank=round(float(np.mean([r["weight_metrics"]["effective_rank"] for r in inter])), 4),
        pc_fire_modes_total=dict(sum((Counter(r["pc_fire_modes"]) for r in inter), Counter())),
        mean_shared_minus_novel_suppression=round(float(np.mean([
            r["switch_metrics"]["shared_minus_novel_suppression"] for r in row
        ])), 4),
        mean_original_pattern_recovery_ratio=round(float(np.mean([
            r["switch_metrics"]["original_pattern_recovery_ratio"] for r in row
        ])), 4),
        mean_original_pattern_owner_recovery_rate=round(float(np.mean([
            r["switch_metrics"]["original_pattern_owner_recovery_rate"] for r in row
        ])), 4),
    )


def should_run_30(stage_runs: list[dict]) -> dict:
    by_condition = {name: [run for run in stage_runs if run["condition"] == name] for name in CONDITIONS}
    c = _aggregate_runs(by_condition["C_pc_instantaneous"])
    d = _aggregate_runs(by_condition["D_pc_persistent"])
    improves = d["mean_distinct_owners"] > c["mean_distinct_owners"]
    no_tyranny = d["mean_max_first_responder_share"] <= c["mean_max_first_responder_share"]
    no_global_suppression = d["mean_no_response_rate"] <= c["mean_no_response_rate"]
    return dict(
        run_30=bool(improves and no_tyranny and no_global_suppression),
        improves_distinct_owners=improves,
        avoids_first_responder_tyranny=no_tyranny,
        avoids_global_suppression=no_global_suppression,
        compare_C=c,
        compare_D=d,
    )


def run_stage(seeds: list[int]) -> list[dict]:
    rows = []
    for seed in seeds:
        for condition_name in CONDITIONS:
            rows.append(run_condition_seed(condition_name, seed))
    return rows


def main():
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "phase36_predictive_conductance_results.json")
    t0 = time.time()
    results = {}

    stage1 = run_stage(SEED_STAGES["seed_1"])
    results["seed_1"] = dict(seeds=SEED_STAGES["seed_1"], runs=stage1)

    stage5 = run_stage(SEED_STAGES["seed_5"])
    gate30 = should_run_30(stage5)
    results["seed_5"] = dict(seeds=SEED_STAGES["seed_5"], runs=stage5, gate_to_30=gate30)

    if gate30["run_30"]:
        stage30 = run_stage(SEED_STAGES["seed_30"])
        results["seed_30"] = dict(seeds=SEED_STAGES["seed_30"], runs=stage30)
    else:
        results["seed_30"] = dict(seeds=SEED_STAGES["seed_30"], skipped=True, gate_to_30=gate30)

    summary = {}
    for stage_name, stage in results.items():
        if stage.get("skipped"):
            continue
        summary[stage_name] = {
            condition: _aggregate_runs([run for run in stage["runs"] if run["condition"] == condition])
            for condition in CONDITIONS
        }

    payload = dict(
        created_at="2026-07-21",
        topology_seed=TOPOLOGY_SEED,
        presentation_steps=PRESENTATION_STEPS,
        interleaved_repeats=INTERLEAVED_REPEATS,
        row_col_row_repeats=ROW_COL_ROW_REPEATS,
        conditions=CONDITIONS,
        runtime_seconds=round(time.time() - t0, 2),
        summary=summary,
        stages=results,
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(dict(runtime_seconds=payload["runtime_seconds"], out_path=out_path), indent=2))


if __name__ == "__main__":
    main()
