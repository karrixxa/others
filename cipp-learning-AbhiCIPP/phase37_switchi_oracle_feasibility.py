"""Phase 37 oracle-feasibility experiment.

This is explicitly an oracle downstream-feasibility check, not evidence that
prediction learning naturally matures. The experiment uses one frozen,
hand-labeled oracle state so the downstream ablations can be compared without a
51,200-step PC pretraining ladder.
"""

from __future__ import annotations

import copy
import json
import os
import time
from collections import Counter

import numpy as np

from backend.presets import DASHBOARD_PRESET
from backend.simulation import N_OUT, N_PIX, PATTERNS, SimulationEngine
from diagnostic_schedule import PRESENTATION_STEPS

TOPOLOGY_SEED = 1
ROW_COL_ROW_ORDER = ["row 1", "col 1", "row 1"]
INTERLEAVED_ORDER = ["row 1", "col 1", "diag \\", "diag /"]
REPEATS = 8
ORACLE_OWNER_BY_PATTERN = {
    "row 1": 0,
    "col 1": 1,
    "diag \\": 2,
    "diag /": 3,
}
ORACLE_LABEL = "oracle_mature_pc_state_v1_manual_mapping"

CONDITIONS = {
    "control": dict(
        prediction_column_to_i_delivery_enabled=False,
        prediction_column_persistent_conductance_enabled=False,
        switchi_paired_shunt_enabled=False,
    ),
    "l1_tail_strong_unnormalized": dict(
        prediction_column_to_i_delivery_enabled=True,
        prediction_column_persistent_conductance_enabled=True,
        inh_trace_normalized=False,
        switchi_paired_shunt_enabled=False,
    ),
    "switchi_paired_l2_shunt": dict(
        prediction_column_to_i_delivery_enabled=False,
        prediction_column_persistent_conductance_enabled=False,
        switchi_paired_shunt_enabled=True,
    ),
}

SEED_STAGES = {
    "seed_1": [1],
    "seed_3": [1, 2, 3],
}


def _modal(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    counts = Counter(vals)
    top = max(counts.values())
    return min(v for v, c in counts.items() if c == top)


def build_base_engine(weight_seed: int) -> SimulationEngine:
    kw = dict(DASHBOARD_PRESET)
    kw.update(
        seed=weight_seed,
        topology_seed=TOPOLOGY_SEED,
        pos_weight_floor=1,
        prediction_column_enabled=True,
        prediction_column_to_i_enabled=True,
        prediction_column_to_i_delivery_enabled=False,
        prediction_column_persistent_conductance_enabled=False,
        pretrained_l1i_regulation=True,
        prediction_learning_rate=0.0,
        switchi_paired_shunt_enabled=False,
    )
    engine = SimulationEngine(**kw)
    apply_oracle_state(engine)
    engine._set_plasticity_frozen(True)
    return engine


def apply_oracle_state(engine: SimulationEngine):
    floor = float(engine.params["pos_weight_floor"] or 1)
    cap = float(engine.l2.excitatory_neurons[0].weight_cap)
    for j, neuron in enumerate(engine.l2.excitatory_neurons):
        neuron.learning_rate = 0.0
        neuron.weights = np.full(N_PIX, floor)
        if j in ORACLE_OWNER_BY_PATTERN.values():
            pattern = next(name for name, idx in ORACLE_OWNER_BY_PATTERN.items() if idx == j)
            weights = np.full(N_PIX, floor)
            for i, active in enumerate(PATTERNS[pattern]):
                if active:
                    weights[i] = cap
            neuron.weights = weights
    for i, pc in enumerate(engine.pcol):
        for conn in pc.apical_connections:
            conn.weight = 0.0
        for pattern, owner_idx in ORACLE_OWNER_BY_PATTERN.items():
            if PATTERNS[pattern][i]:
                pc.apical_connections[owner_idx].weight = 400.0
    engine.oracle_state_label = ORACLE_LABEL


def configure_condition(engine: SimulationEngine, condition_name: str):
    cfg = CONDITIONS[condition_name]
    engine.prediction_column_to_i_delivery_enabled = bool(cfg["prediction_column_to_i_delivery_enabled"])
    engine.params["prediction_column_to_i_delivery_enabled"] = bool(cfg["prediction_column_to_i_delivery_enabled"])
    engine.prediction_column_persistent_conductance_enabled = bool(
        cfg["prediction_column_persistent_conductance_enabled"])
    engine.params["prediction_column_persistent_conductance_enabled"] = bool(
        cfg["prediction_column_persistent_conductance_enabled"])
    engine.switchi_paired_shunt_enabled = bool(cfg["switchi_paired_shunt_enabled"])
    engine.params["switchi_paired_shunt_enabled"] = bool(cfg["switchi_paired_shunt_enabled"])
    if "inh_trace_normalized" in cfg:
        engine.params["inh_trace_normalized"] = bool(cfg["inh_trace_normalized"])
    for e in engine.l1.excitatory_neurons:
        e.inhibitory_flow_rate = bool(engine.prediction_column_persistent_conductance_enabled)
        e.inhibitory_persistent_after_discharge = bool(engine.prediction_column_persistent_conductance_enabled)
        e.inh_trace_decay = engine.params["inh_trace_decay"]
        e.inh_trace_normalized = bool(engine.params["inh_trace_normalized"])
        if not engine.prediction_column_persistent_conductance_enabled:
            e.inh_trace = 0.0
            e.inh_trace_pending = 0.0
    if not engine.switchi_paired_shunt_enabled:
        engine.switchi_recent_spike_trace[:] = 0.0


def interleaved_schedule():
    return [(pattern, PRESENTATION_STEPS) for _ in range(REPEATS) for pattern in INTERLEAVED_ORDER]


def row_col_row_schedule():
    return [(pattern, PRESENTATION_STEPS) for _ in range(REPEATS) for pattern in ROW_COL_ROW_ORDER]


def run_schedule(engine: SimulationEngine, schedule: list[tuple[str, int]], schedule_patterns: list[str]) -> dict:
    presentations = []
    first_counts = Counter()
    switchi_fires = 0
    switchi_delta = 0.0
    pred_tail = 0.0
    for index, (pattern, total_steps) in enumerate(schedule):
        engine.set_pattern(pattern)
        t_start = engine.timestep
        first = None
        same_step_tie = False
        peak_drive = {f"L2E{j}": float("-inf") for j in range(N_OUT)}
        incumbent_delta = {}
        for _step in range(total_steps):
            engine.step()
            for j in range(N_OUT):
                peak_drive[f"L2E{j}"] = max(peak_drive[f"L2E{j}"], float(engine.l2_drive.get(f"L2E{j}", 0.0)))
            if first is None:
                firers = [f"L2E{j}" for j in range(N_OUT) if engine.spiked[f"L2E{j}"]]
                if firers:
                    first = firers[0]
                    same_step_tie = len(firers) > 1
            switchi_fires += sum(1 for row in engine._switchi_last_events if row["fired"])
            switchi_delta += sum(float(row["delta"]) for row in engine._switchi_last_events if row["fired"])
            pred_tail += sum(float(row["delivered_tail"]) for row in engine._prediction_column_last_conductance)
        ordered = sorted(peak_drive.items(), key=lambda kv: kv[1], reverse=True)
        top1 = ordered[0]
        top2 = ordered[1]
        winner = first
        if winner:
            first_counts[winner] += 1
        presentations.append(dict(
            presentation_index=index,
            pattern=pattern,
            t_start=t_start,
            t_end=engine.timestep,
            first_l2e_spiker=winner,
            same_step_tie=same_step_tie,
            peak_drive=peak_drive,
            top_drive_neuron=top1[0],
            top_drive=round(float(top1[1]), 4),
            runner_up=top2[0],
            runner_up_margin=round(float(top1[1] - top2[1]), 4),
        ))
    by_pattern = {p: [r for r in presentations if r["pattern"] == p] for p in schedule_patterns}
    per_pattern = {}
    for pattern, recs in by_pattern.items():
        firsts = [r["first_l2e_spiker"] for r in recs]
        n = len(firsts)
        modal = _modal(firsts)
        non_none = [v for v in firsts if v is not None]
        per_pattern[pattern] = dict(
            modal_owner=modal,
            consistency=round((non_none.count(modal) / n), 4) if modal is not None and n else 0.0,
            no_response_rate=round(sum(1 for v in firsts if v is None) / n, 4) if n else 0.0,
        )
    distinct_owners = len(set(v["modal_owner"] for v in per_pattern.values() if v["modal_owner"] is not None))
    total_first = sum(first_counts.values())
    first_responder_share = round(max(first_counts.values()) / total_first, 4) if total_first else 0.0
    return dict(
        presentations=presentations,
        per_pattern=per_pattern,
        distinct_owners=distinct_owners,
        first_responder_share=first_responder_share,
        global_silence_rate=round(sum(1 for r in presentations if r["first_l2e_spiker"] is None) / len(presentations), 4),
        switchi_fire_count=int(switchi_fires),
        switchi_total_delta=round(float(switchi_delta), 4),
        predictive_tail_total=round(float(pred_tail), 4),
    )


def analyze_row_col_row(schedule_result: dict) -> dict:
    presentations = schedule_result["presentations"]
    incumbent_changes = []
    middle_margins = []
    transitions = []
    recoveries = []
    incumbents = []
    return_winners = []
    for i in range(0, len(presentations), 3):
        first_row, middle_col, return_row = presentations[i:i + 3]
        incumbent = first_row["first_l2e_spiker"]
        incumbents.append(incumbent)
        return_winners.append(return_row["first_l2e_spiker"])
        if incumbent is not None:
            start_peak = float(first_row["peak_drive"].get(incumbent, 0.0))
            middle_peak = float(middle_col["peak_drive"].get(incumbent, 0.0))
            incumbent_changes.append(middle_peak - start_peak)
        middle_margins.append(float(middle_col["runner_up_margin"]))
        transitions.append(bool(middle_col["first_l2e_spiker"] is not None and middle_col["first_l2e_spiker"] != incumbent))
        recoveries.append(bool(return_row["first_l2e_spiker"] is not None and return_row["first_l2e_spiker"] == incumbent))
    permanent_lockout = False
    initial = incumbents[0] if incumbents else None
    if initial is not None:
        lost = False
        recovered_after_loss = False
        for winner in return_winners:
            if winner != initial:
                lost = True
            elif lost:
                recovered_after_loss = True
                break
        permanent_lockout = bool(lost and not recovered_after_loss)
    return dict(
        incumbent_specific_membrane_change=round(float(np.mean(incumbent_changes)), 4) if incumbent_changes else 0.0,
        runner_up_margin=round(float(np.mean(middle_margins)), 4) if middle_margins else 0.0,
        winner_transition_rate=round(float(np.mean(transitions)), 4) if transitions else 0.0,
        original_owner_recovery_rate=round(float(np.mean(recoveries)), 4) if recoveries else 0.0,
        permanent_lockout=permanent_lockout,
    )


def run_condition_seed(condition_name: str, seed: int) -> dict:
    base = build_base_engine(seed)
    configure_condition(base, condition_name)
    inter = run_schedule(copy.deepcopy(base), interleaved_schedule(), INTERLEAVED_ORDER)
    row = run_schedule(copy.deepcopy(base), row_col_row_schedule(), ROW_COL_ROW_ORDER)
    row["row_col_row_metrics"] = analyze_row_col_row(row)
    return dict(
        condition=condition_name,
        seed=seed,
        oracle_state_label=ORACLE_LABEL,
        interleaved=inter,
        row_col_row=row,
    )


def summarize_condition(runs: list[dict], condition_name: str) -> dict:
    selected = [r for r in runs if r["condition"] == condition_name]
    return dict(
        mean_distinct_owners=round(float(np.mean([r["interleaved"]["distinct_owners"] for r in selected])), 4),
        mean_first_responder_share=round(float(np.mean([r["interleaved"]["first_responder_share"] for r in selected])), 4),
        mean_global_silence=round(float(np.mean([r["interleaved"]["global_silence_rate"] for r in selected])), 4),
        mean_incumbent_specific_membrane_change=round(float(np.mean([
            r["row_col_row"]["row_col_row_metrics"]["incumbent_specific_membrane_change"] for r in selected
        ])), 4),
        mean_runner_up_margin=round(float(np.mean([
            r["row_col_row"]["row_col_row_metrics"]["runner_up_margin"] for r in selected
        ])), 4),
        mean_winner_transition_rate=round(float(np.mean([
            r["row_col_row"]["row_col_row_metrics"]["winner_transition_rate"] for r in selected
        ])), 4),
        mean_original_owner_recovery_rate=round(float(np.mean([
            r["row_col_row"]["row_col_row_metrics"]["original_owner_recovery_rate"] for r in selected
        ])), 4),
        permanent_lockout_rate=round(float(np.mean([
            1.0 if r["row_col_row"]["row_col_row_metrics"]["permanent_lockout"] else 0.0 for r in selected
        ])), 4),
        mean_switchi_fire_count=round(float(np.mean([r["interleaved"]["switchi_fire_count"] for r in selected])), 4),
        mean_predictive_tail_total=round(float(np.mean([r["interleaved"]["predictive_tail_total"] for r in selected])), 4),
    )


def should_run_seed3(seed1_runs: list[dict]) -> dict:
    by_name = {row["condition"]: row for row in seed1_runs}
    control = by_name["control"]
    tail = by_name["l1_tail_strong_unnormalized"]
    shunt = by_name["switchi_paired_l2_shunt"]
    selective_transition = (
        shunt["row_col_row"]["row_col_row_metrics"]["winner_transition_rate"] > 0.0
        and shunt["row_col_row"]["row_col_row_metrics"]["original_owner_recovery_rate"] > 0.0
    )
    tail_does_not = tail["row_col_row"]["row_col_row_metrics"]["winner_transition_rate"] <= 0.0
    no_silence = shunt["interleaved"]["global_silence_rate"] <= control["interleaved"]["global_silence_rate"]
    return dict(
        run_seed_3=bool(selective_transition and tail_does_not and no_silence),
        selective_transition=bool(selective_transition),
        stronger_l1_tail_does_not_transition=bool(tail_does_not),
        avoids_extra_global_silence=bool(no_silence),
    )


def run_stage(seeds: list[int]) -> list[dict]:
    rows = []
    for seed in seeds:
        for condition_name in CONDITIONS:
            rows.append(run_condition_seed(condition_name, seed))
    return rows


def main():
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "phase37_switchi_oracle_feasibility_results.json",
    )
    t0 = time.time()
    seed1 = run_stage(SEED_STAGES["seed_1"])
    gate = should_run_seed3(seed1)
    results = {
        "seed_1": dict(seeds=SEED_STAGES["seed_1"], runs=seed1, gate_to_seed_3=gate),
    }
    if gate["run_seed_3"]:
        seed3 = run_stage(SEED_STAGES["seed_3"])
        results["seed_3"] = dict(seeds=SEED_STAGES["seed_3"], runs=seed3)
    else:
        results["seed_3"] = dict(seeds=SEED_STAGES["seed_3"], skipped=True, gate_to_seed_3=gate)
    summary = {}
    for stage_name, stage in results.items():
        if stage.get("skipped"):
            continue
        summary[stage_name] = {
            name: summarize_condition(stage["runs"], name)
            for name in CONDITIONS
        }
    payload = dict(
        created_at="2026-07-21",
        oracle_state_label=ORACLE_LABEL,
        repeats=REPEATS,
        conditions=CONDITIONS,
        runtime_seconds=round(time.time() - t0, 2),
        summary=summary,
        stages=results,
        note=(
            "Oracle downstream feasibility only. This file does not claim that PC "
            "prediction learning naturally matures."
        ),
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(dict(runtime_seconds=payload["runtime_seconds"], out_path=out_path), indent=2))


if __name__ == "__main__":
    main()
