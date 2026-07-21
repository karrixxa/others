"""Phase 36.1 measurement-first conformance audit.

Protocol:
  - keep the Phase 36 mechanism unchanged;
  - measure whether PCs naturally mature and fire in shadow mode first;
  - fork one identical mature shadow state into:
      S: paired topology, physical PC->L1I delivery OFF
      I: same state, delivery ON, instantaneous inhibition only
      P: same state, delivery ON, persistent conductance enabled
  - run 30 seeds only if P beneficially differs from I on the 5-seed gate.

The preregistered maturity criterion is intentionally simple and local:
training continues in shadow mode until every PC0..PC8 has emitted at least one
physical spike during equal-interleaved training, or until the fixed checkpoint
ladder is exhausted. Decoder learning is spike-triggered only, so a PC that
never fires has not yet entered causal learning at all.
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
SEED_STAGES = {
    "seed_5": [1, 2, 3, 4, 5],
    "seed_30": list(range(1, 31)),
}
PRETRAIN_CHECKPOINT_STEPS = [3200, 6400, 12800, 25600, 51200]
MATURITY_CRITERION = (
    "all nine PCs must emit at least one physical spike during shadow-mode "
    "equal-interleaved training"
)

FORK_CONDITIONS = {
    "S_shadow_delivery_off": dict(delivery=False, persistent=False),
    "I_pc_instantaneous": dict(delivery=True, persistent=False),
    "P_pc_persistent": dict(delivery=True, persistent=True),
}


def build_engine(weight_seed: int, **overrides) -> SimulationEngine:
    kw = dict(DASHBOARD_PRESET)
    kw.update(
        seed=weight_seed,
        topology_seed=TOPOLOGY_SEED,
        pos_weight_floor=1,
        prediction_column_enabled=True,
        **overrides,
    )
    return SimulationEngine(**kw)


def build_shadow_engine(weight_seed: int) -> SimulationEngine:
    return build_engine(
        weight_seed,
        prediction_column_to_i_enabled=True,
        prediction_column_to_i_delivery_enabled=False,
        prediction_column_persistent_conductance_enabled=False,
    )


def build_global_route_engine(weight_seed: int) -> SimulationEngine:
    return build_engine(weight_seed, prediction_column_to_i_enabled=False)


def interleaved_schedule() -> list[tuple[str, int]]:
    return [(pattern, PRESENTATION_STEPS) for _ in range(INTERLEAVED_REPEATS) for pattern in CYCLE_ORDER]


def row_col_row_schedule() -> list[tuple[str, int]]:
    return [(pattern, PRESENTATION_STEPS) for _ in range(ROW_COL_ROW_REPEATS) for pattern in ROW_COL_ROW_ORDER]


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
        original_pattern_owner_recovery_rate=round(float(np.mean(row_owner_recovered)), 4)
        if row_owner_recovered else None,
    )


def _init_measurement() -> dict:
    return dict(
        delivery_modes=Counter(),
        pc_spikes=Counter(),
        pc_fire_modes=Counter(),
        l1i_spikes=Counter(),
        paired_inhibition_targets=Counter(),
        paired_inhibition_total_charge=0.0,
        l1i_input_active_sources=Counter(),
        l1i_input_charge_total=Counter(),
        conductance_tail_seed_total=0.0,
        conductance_tail_seed_events=0,
        conductance_tail_delivery_total=0.0,
        conductance_tail_delivery_events=0,
        conductance_decay_ratios=[],
        best_coincident_gap=[float("inf")] * N_PIX,
        best_basal_only_gap=[float("inf")] * N_PIX,
        best_apical_only_gap=[float("inf")] * N_PIX,
    )


def _observe_step(engine: SimulationEngine, measurement: dict):
    for i in range(N_PIX):
        pc = engine.pcol[i]
        basal = bool(pc.last_basal_sources)
        apical = bool(pc.last_apical_sources)
        total_charge = float(pc.last_basal_charge + pc.last_apical_charge)
        gap = float(engine.prediction_threshold - total_charge)
        if basal and apical:
            measurement["delivery_modes"]["coincident"] += 1
            measurement["best_coincident_gap"][i] = min(measurement["best_coincident_gap"][i], gap)
        elif basal:
            measurement["delivery_modes"]["basal_only"] += 1
            measurement["best_basal_only_gap"][i] = min(measurement["best_basal_only_gap"][i], gap)
        elif apical:
            measurement["delivery_modes"]["apical_only"] += 1
            measurement["best_apical_only_gap"][i] = min(measurement["best_apical_only_gap"][i], gap)
        else:
            measurement["delivery_modes"]["silent"] += 1
        if engine.spiked.get(f"PC{i}"):
            measurement["pc_spikes"][f"PC{i}"] += 1
            if basal and apical:
                measurement["pc_fire_modes"]["coincidence"] += 1
            elif apical:
                measurement["pc_fire_modes"]["feedback_only"] += 1
            elif basal:
                measurement["pc_fire_modes"]["basal_only"] += 1
            else:
                measurement["pc_fire_modes"]["other"] += 1

    for i, inh in enumerate(engine.l1.inhibitory_neurons):
        if engine.spiked.get(f"L1I{i}"):
            measurement["l1i_spikes"][f"L1I{i}"] += 1
        active_sources = int(np.count_nonzero(np.asarray(inh._last_input_spikes) > 0.5))
        measurement["l1i_input_active_sources"][f"L1I{i}"] += active_sources
        measurement["l1i_input_charge_total"][f"L1I{i}"] += float(
            np.dot(np.asarray(inh.weights), np.asarray(inh._last_input_spikes))
        )

    for nid, ev in engine._inh_events:
        measurement["paired_inhibition_targets"][nid] += 1
        measurement["paired_inhibition_total_charge"] += float(ev.get("w_delivered", 0.0))
        tail_seed = float(ev.get("tail_seeded", 0.0))
        if tail_seed > 0.0:
            measurement["conductance_tail_seed_total"] += tail_seed
            measurement["conductance_tail_seed_events"] += 1

    for rec in engine._prediction_column_last_conductance:
        delivered_tail = float(rec["delivered_tail"])
        if delivered_tail > 0.0:
            measurement["conductance_tail_delivery_total"] += delivered_tail
            measurement["conductance_tail_delivery_events"] += 1
            before = float(rec["tail_before"])
            if before > 0.0:
                measurement["conductance_decay_ratios"].append(float(rec["tail_after"]) / before)


def _measurement_summary(engine: SimulationEngine, measurement: dict) -> dict:
    decoder_weights = {
        f"PC{i}": [round(float(w), 4) for w in engine.pcol[i].decoder_weights]
        for i in range(N_PIX)
    }
    max_apical = {
        f"PC{i}": round(float(max(engine.pcol[i].decoder_weights)), 4)
        for i in range(N_PIX)
    }
    best_single_source_gap = {
        f"PC{i}": round(float(engine.prediction_threshold
                             - (engine.prediction_lateral_weight + max(engine.pcol[i].decoder_weights))), 4)
        for i in range(N_PIX)
    }
    return dict(
        delivery_modes=dict(measurement["delivery_modes"]),
        pc_spike_total=int(sum(measurement["pc_spikes"].values())),
        pc_spikes_by_pc={k: int(v) for k, v in measurement["pc_spikes"].items()},
        pc_fire_modes=dict(measurement["pc_fire_modes"]),
        l1i_spikes_by_pc={k: int(v) for k, v in measurement["l1i_spikes"].items()},
        paired_inhibition_targets={k: int(v) for k, v in measurement["paired_inhibition_targets"].items()},
        paired_inhibition_total_charge=round(float(measurement["paired_inhibition_total_charge"]), 4),
        l1i_input_dimension=int(len(engine.l1.inhibitory_neurons[0].weights)),
        l1i_input_active_sources_total={k: int(v) for k, v in measurement["l1i_input_active_sources"].items()},
        l1i_input_charge_total={k: round(float(v), 4) for k, v in measurement["l1i_input_charge_total"].items()},
        conductance_tail_seed_total=round(float(measurement["conductance_tail_seed_total"]), 4),
        conductance_tail_seed_events=int(measurement["conductance_tail_seed_events"]),
        conductance_tail_delivery_total=round(float(measurement["conductance_tail_delivery_total"]), 4),
        conductance_tail_delivery_events=int(measurement["conductance_tail_delivery_events"]),
        conductance_decay_mean=round(float(np.mean(measurement["conductance_decay_ratios"])), 6)
        if measurement["conductance_decay_ratios"] else None,
        decoder_weights=decoder_weights,
        max_apical_weight_by_pc=max_apical,
        best_single_source_gap_by_pc=best_single_source_gap,
        best_coincident_gap_by_pc={
            f"PC{i}": None if not np.isfinite(measurement["best_coincident_gap"][i])
            else round(float(measurement["best_coincident_gap"][i]), 4)
            for i in range(N_PIX)
        },
        best_basal_only_gap_by_pc={
            f"PC{i}": None if not np.isfinite(measurement["best_basal_only_gap"][i])
            else round(float(measurement["best_basal_only_gap"][i]), 4)
            for i in range(N_PIX)
        },
        best_apical_only_gap_by_pc={
            f"PC{i}": None if not np.isfinite(measurement["best_apical_only_gap"][i])
            else round(float(measurement["best_apical_only_gap"][i]), 4)
            for i in range(N_PIX)
        },
    )


def _run_schedule(engine: SimulationEngine, schedule: list[tuple[str, int]], schedule_patterns: list[str]) -> dict:
    tracer = CausalTracer(engine)
    measurement = _init_measurement()
    presentations = []
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
                _observe_step(engine, measurement)
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
    analysis["max_first_responder_share"] = (
        round(max(analysis["tyrant_share"].values()), 4) if analysis["tyrant_share"] else 0.0
    )
    analysis["weight_metrics"] = _weight_metrics(engine)
    analysis["measurement"] = _measurement_summary(engine, measurement)
    return dict(engine=engine, tracer=tracer, presentations=presentations, analysis=analysis)


def _run_measurement_only(engine: SimulationEngine, schedule: list[tuple[str, int]]) -> dict:
    measurement = _init_measurement()
    for pattern, total_steps in schedule:
        engine.set_pattern(pattern)
        for _ in range(total_steps):
            engine.step()
            _observe_step(engine, measurement)
    return _measurement_summary(engine, measurement)


def _run_pretrain_block(engine: SimulationEngine, total_steps: int) -> dict:
    measurement = _init_measurement()
    start_step = engine.timestep
    steps_remaining = total_steps
    order_idx = 0
    while steps_remaining > 0:
        pattern = CYCLE_ORDER[order_idx % len(CYCLE_ORDER)]
        order_idx += 1
        engine.set_pattern(pattern)
        for _ in range(PRESENTATION_STEPS):
            engine.step()
            _observe_step(engine, measurement)
            steps_remaining -= 1
            if steps_remaining <= 0:
                break
    summary = _measurement_summary(engine, measurement)
    summary["steps"] = int(engine.timestep - start_step)
    return summary


def _pretrain_shadow_to_maturity(weight_seed: int) -> dict:
    engine = build_shadow_engine(weight_seed)
    checkpoints = []
    previous = 0
    pc_spiked_ever = Counter()
    for target in PRETRAIN_CHECKPOINT_STEPS:
        block = _run_pretrain_block(engine, target - previous)
        previous = target
        for pc_id, count in block["pc_spikes_by_pc"].items():
            pc_spiked_ever[pc_id] += count
        matured = all(pc_spiked_ever.get(f"PC{i}", 0) > 0 for i in range(N_PIX))
        checkpoints.append(dict(
            step=target,
            matured=bool(matured),
            pc_spiked_ever={f"PC{i}": int(pc_spiked_ever.get(f"PC{i}", 0)) for i in range(N_PIX)},
            measurement=block,
        ))
        if matured:
            break
    return dict(
        engine=engine,
        matured=bool(checkpoints[-1]["matured"]),
        steps_reached=int(checkpoints[-1]["step"]),
        checkpoints=checkpoints,
    )


def _configure_fork(engine: SimulationEngine, *, delivery: bool, persistent: bool):
    engine.prediction_column_to_i_delivery_enabled = bool(delivery)
    engine.params["prediction_column_to_i_delivery_enabled"] = bool(delivery)
    engine.prediction_column_persistent_conductance_enabled = bool(persistent)
    engine.params["prediction_column_persistent_conductance_enabled"] = bool(persistent)
    for e in engine.l1.excitatory_neurons:
        e.inhibitory_flow_rate = bool(persistent)
        e.inhibitory_persistent_after_discharge = bool(persistent)
        if not persistent:
            e.inh_trace = 0.0
            e.inh_trace_pending = 0.0


def _fork_conditions(shadow_engine: SimulationEngine) -> dict:
    forks = {}
    for name, cfg in FORK_CONDITIONS.items():
        fork = copy.deepcopy(shadow_engine)
        _configure_fork(fork, **cfg)
        forks[name] = fork
    return forks


def _run_seed(weight_seed: int) -> dict:
    pretrain = _pretrain_shadow_to_maturity(weight_seed)
    forks = _fork_conditions(pretrain["engine"])
    schedules = {}
    for condition_name, fork_base in forks.items():
        interleaved = _run_schedule(copy.deepcopy(fork_base), interleaved_schedule(), CYCLE_ORDER)
        row_col_row = _run_schedule(copy.deepcopy(fork_base), row_col_row_schedule(), ROW_COL_ROW_ORDER)
        row_col_row["analysis"]["switch_metrics"] = _row_col_row_metrics(row_col_row["presentations"])
        schedules[condition_name] = dict(
            interleaved=interleaved["analysis"],
            row_col_row=row_col_row["analysis"],
        )

    global_engine = build_global_route_engine(weight_seed)
    _run_pretrain_block(global_engine, pretrain["steps_reached"])
    global_interleaved = _run_measurement_only(copy.deepcopy(global_engine), interleaved_schedule())
    global_row_col_row = _run_measurement_only(copy.deepcopy(global_engine), row_col_row_schedule())

    return dict(
        weight_seed=weight_seed,
        topology_seed=TOPOLOGY_SEED,
        pretrain=dict(
            matured=pretrain["matured"],
            steps_reached=pretrain["steps_reached"],
            maturity_criterion=MATURITY_CRITERION,
            checkpoints=pretrain["checkpoints"],
        ),
        fork_runs=schedules,
        confound_compare=dict(
            global_route_interleaved=global_interleaved,
            shadow_route_interleaved=schedules["S_shadow_delivery_off"]["interleaved"]["measurement"],
            global_route_row_col_row=global_row_col_row,
            shadow_route_row_col_row=schedules["S_shadow_delivery_off"]["row_col_row"]["measurement"],
        ),
    )


def _aggregate_condition(runs: list[dict], condition_name: str) -> dict:
    inter = [run["fork_runs"][condition_name]["interleaved"] for run in runs]
    row = [run["fork_runs"][condition_name]["row_col_row"] for run in runs]
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
        pc_fire_modes_total=dict(sum((Counter(r["measurement"]["pc_fire_modes"]) for r in inter), Counter())),
        mean_pc_spikes=round(float(np.mean([r["measurement"]["pc_spike_total"] for r in inter])), 4),
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


def _aggregate_pretrain(runs: list[dict]) -> dict:
    matured = [1.0 if run["pretrain"]["matured"] else 0.0 for run in runs]
    steps = [run["pretrain"]["steps_reached"] for run in runs]
    return dict(
        maturity_rate=round(float(np.mean(matured)), 4),
        mean_steps_reached=round(float(np.mean(steps)), 4),
        matured_seeds=[run["weight_seed"] for run in runs if run["pretrain"]["matured"]],
    )


def _aggregate_confound(runs: list[dict]) -> dict:
    def _mean_charge(kind: str, schedule_key: str) -> float:
        vals = []
        for run in runs:
            rec = run["confound_compare"][schedule_key]
            vals.append(sum(rec["l1i_input_charge_total"].values()))
        return round(float(np.mean(vals)), 4)

    def _mean_spikes(kind: str, schedule_key: str) -> float:
        vals = []
        for run in runs:
            rec = run["confound_compare"][schedule_key]
            vals.append(sum(rec["l1i_spikes_by_pc"].values()))
        return round(float(np.mean(vals)), 4)

    return dict(
        interleaved=dict(
            global_fan_in=8,
            silent_paired_fan_in=1,
            mean_global_l1i_input_charge=_mean_charge("global", "global_route_interleaved"),
            mean_silent_l1i_input_charge=_mean_charge("silent", "shadow_route_interleaved"),
            mean_global_l1i_spikes=_mean_spikes("global", "global_route_interleaved"),
            mean_silent_l1i_spikes=_mean_spikes("silent", "shadow_route_interleaved"),
        ),
        row_col_row=dict(
            global_fan_in=8,
            silent_paired_fan_in=1,
            mean_global_l1i_input_charge=_mean_charge("global", "global_route_row_col_row"),
            mean_silent_l1i_input_charge=_mean_charge("silent", "shadow_route_row_col_row"),
            mean_global_l1i_spikes=_mean_spikes("global", "global_route_row_col_row"),
            mean_silent_l1i_spikes=_mean_spikes("silent", "shadow_route_row_col_row"),
        ),
    )


def _should_run_30(runs: list[dict]) -> dict:
    i_summary = _aggregate_condition(runs, "I_pc_instantaneous")
    p_summary = _aggregate_condition(runs, "P_pc_persistent")
    improves = p_summary["mean_distinct_owners"] > i_summary["mean_distinct_owners"]
    no_tyranny = p_summary["mean_max_first_responder_share"] <= i_summary["mean_max_first_responder_share"]
    no_global_suppression = p_summary["mean_no_response_rate"] <= i_summary["mean_no_response_rate"]
    return dict(
        run_30=bool(improves and no_tyranny and no_global_suppression),
        improves_distinct_owners=bool(improves),
        avoids_first_responder_tyranny=bool(no_tyranny),
        avoids_global_suppression=bool(no_global_suppression),
        compare_I=i_summary,
        compare_P=p_summary,
    )


def _run_stage(seeds: list[int]) -> list[dict]:
    return [_run_seed(seed) for seed in seeds]


def main():
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "phase36_1_conformance_audit_results.json",
    )
    t0 = time.time()

    stage5 = _run_stage(SEED_STAGES["seed_5"])
    gate30 = _should_run_30(stage5)
    results = {
        "seed_5": dict(seeds=SEED_STAGES["seed_5"], runs=stage5, gate_to_30=gate30),
    }

    if gate30["run_30"]:
        stage30 = _run_stage(SEED_STAGES["seed_30"])
        results["seed_30"] = dict(seeds=SEED_STAGES["seed_30"], runs=stage30)
    else:
        results["seed_30"] = dict(seeds=SEED_STAGES["seed_30"], skipped=True, gate_to_30=gate30)

    summary = {
        "seed_5": dict(
            pretrain=_aggregate_pretrain(stage5),
            confound=_aggregate_confound(stage5),
            conditions={name: _aggregate_condition(stage5, name) for name in FORK_CONDITIONS},
        )
    }
    if results["seed_30"].get("runs"):
        summary["seed_30"] = dict(
            pretrain=_aggregate_pretrain(results["seed_30"]["runs"]),
            confound=_aggregate_confound(results["seed_30"]["runs"]),
            conditions={name: _aggregate_condition(results["seed_30"]["runs"], name)
                        for name in FORK_CONDITIONS},
        )

    payload = dict(
        created_at="2026-07-21",
        topology_seed=TOPOLOGY_SEED,
        presentation_steps=PRESENTATION_STEPS,
        interleaved_repeats=INTERLEAVED_REPEATS,
        row_col_row_repeats=ROW_COL_ROW_REPEATS,
        pretrain_checkpoints=PRETRAIN_CHECKPOINT_STEPS,
        maturity_criterion=MATURITY_CRITERION,
        fork_conditions=FORK_CONDITIONS,
        runtime_seconds=round(time.time() - t0, 2),
        summary=summary,
        stages=results,
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(dict(runtime_seconds=payload["runtime_seconds"], out_path=out_path), indent=2))


if __name__ == "__main__":
    main()
