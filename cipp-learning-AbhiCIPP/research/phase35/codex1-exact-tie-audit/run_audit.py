#!/usr/bin/env python3
"""Passive exact-tie audit against the frozen Phase 35 checkpoint."""
import json
import os
import time
from collections import Counter, defaultdict
from itertools import combinations

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, PATTERNS

STAGE1_KW = dict(
    prediction_column_enabled=True,
    prediction_column_to_i_enabled=False,
    prediction_leak_diagnostic_disable=True,
    loser_depression=False,
    l2e_budget=False,
)
PATTERN = "row 1"
STEPS = 6000
TOL = 1e-12


def active_pixels():
    return [i for i, value in enumerate(PATTERNS[PATTERN]) if value]


def decoder_totals(engine, active):
    return np.array([
        sum(engine.pcol[i].decoder_weights[j] for i in active)
        for j in range(N_OUT)
    ], dtype=float)


def main():
    started = time.time()
    seed_rows = []
    tied_rows = []
    clean_seeds = []
    active = active_pixels()

    for seed in range(1, 41):
        engine = SimulationEngine(seed=seed, **STAGE1_KW)
        engine.set_pattern(PATTERN)
        initial_weights = np.array([n._weights_array.copy() for n in engine.l2.excitatory_neurons])
        initial_membranes = np.array([n.potential for n in engine.l2.excitatory_neurons])
        spike_steps = defaultdict(list)
        coactive_steps = defaultdict(list)
        first_coactive = {}
        first_weight_equal = {}
        first_membrane_equal = {}
        checkpoints = []
        l2i_fires = {}

        for outer_step in range(STEPS):
            t = engine.timestep
            pre_mem = np.array([n.potential for n in engine.l2.excitatory_neurons])
            pre_weights = np.array([n._weights_array.copy() for n in engine.l2.excitatory_neurons])
            engine.step()
            spikers = [j for j in range(N_OUT) if engine.spiked[f"L2E{j}"]]
            crossing_mem = np.array([engine.l2_drive[f"L2E{j}"] for j in range(N_OUT)])

            for j in spikers:
                spike_steps[j].append(t)
            for a, b in combinations(spikers, 2):
                pair = (a, b)
                coactive_steps[pair].append(t)
                if pair not in first_coactive:
                    first_coactive[pair] = dict(
                        step=t,
                        response_set=[f"L2E{x}" for x in spikers],
                        membrane_step_start={f"L2E{x}": float(pre_mem[x]) for x in (a, b)},
                        membrane_at_threshold_evaluation={f"L2E{x}": float(crossing_mem[x]) for x in (a, b)},
                        threshold={f"L2E{x}": float(engine.l2.excitatory_neurons[x].threshold) for x in (a, b)},
                        threshold_overshoot={f"L2E{x}": float(crossing_mem[x] - engine.l2.excitatory_neurons[x].threshold) for x in (a, b)},
                        feedforward_weight_difference=(pre_weights[a] - pre_weights[b]).tolist(),
                        feedforward_weight_linf_difference=float(np.max(np.abs(pre_weights[a] - pre_weights[b]))),
                    )

            for a, b in combinations(range(N_OUT), 2):
                pair = (a, b)
                if pair not in first_weight_equal and np.array_equal(pre_weights[a], pre_weights[b]):
                    first_weight_equal[pair] = t
                if pair not in first_membrane_equal and pre_mem[a] == pre_mem[b]:
                    first_membrane_equal[pair] = t

            if engine.spiked["L2I"]:
                new_records = [rec for rec in engine._l2i_pending if rec["fire_t"] == t]
                # A fire always schedules exactly one record on this path.
                if new_records:
                    rec = new_records[-1]
                    l2i_fires[t] = dict(
                        threshold_crossing_step=t,
                        contributors=[dict(step=int(ct), source=cid) for ct, cid in rec["contributors"]],
                        schedule_step=t,
                        delivery_step=int(rec["deliver_at"]),
                        threshold_causing_source=(rec["contributors"][-1][1] if rec["contributors"] else None),
                        v_pre=float(rec["l2i_v_pre"]),
                        v_post=float(rec["l2i_v_post"]),
                    )

            if (outer_step + 1) % 1000 == 0:
                checkpoints.append(dict(step=outer_step + 1, totals=decoder_totals(engine, active).tolist()))

        totals = decoder_totals(engine, active)
        max_total = float(np.max(totals))
        leaders = [j for j, value in enumerate(totals) if abs(float(value) - max_total) <= 1e-6]
        counts = {f"L2E{j}": len(spike_steps[j]) for j in range(N_OUT)}
        seed_row = dict(seed=seed, leaders=[f"L2E{j}" for j in leaders], final_totals=totals.tolist(),
                        spike_counts=counts,
                        first_spike_steps={f"L2E{j}": (spike_steps[j][0] if spike_steps[j] else None)
                                           for j in range(N_OUT)},
                        checkpoints=checkpoints)
        seed_rows.append(seed_row)
        if len(leaders) < 2:
            clean_seeds.append(seed)
            continue

        # Report every member of the exact top set; Claude called these two-way,
        # but this deliberately preserves any higher-order tie found physically.
        leader_pairs = list(combinations(leaders, 2))
        earliest_spike = min(step for j in leaders for step in spike_steps[j])
        earliest_set = [j for j in leaders if earliest_spike in spike_steps[j]]
        pair_details = []
        any_same_step = False
        all_pair_spikes_coactive = True
        for pair in leader_pairs:
            a, b = pair
            common = sorted(set(spike_steps[a]) & set(spike_steps[b]))
            union = sorted(set(spike_steps[a]) | set(spike_steps[b]))
            any_same_step |= bool(common)
            all_pair_spikes_coactive &= (common == union)
            first = first_coactive.get(pair)
            inhibition = None
            if first:
                for fire_step in sorted(l2i_fires):
                    candidate = l2i_fires[fire_step]
                    contributor_keys = {(c["step"], c["source"]) for c in candidate["contributors"]}
                    if all((first["step"], f"L2E{x}") in contributor_keys for x in pair):
                        inhibition = candidate
                        break
            contributors = inhibition["contributors"] if inhibition else []
            both_before_fire = bool(first and inhibition and all(
                any(c["step"] == first["step"] and c["source"] == f"L2E{x}" for c in contributors)
                for x in pair))
            hypothetical_arrival = (first["step"] + engine.l2_inhibition_delay) if first else None
            second_physical_step = first["step"] if first else None
            pair_details.append(dict(
                neurons=[f"L2E{a}", f"L2E{b}"],
                first_coactive_crossing=first,
                coactive_spike_count=len(common),
                distinct_spike_step_count=len(union),
                all_spikes_coactive=(common == union),
                first_weight_identical_step=first_weight_equal.get(pair),
                first_membrane_identical_step=first_membrane_equal.get(pair),
                weights_identical_at_initialization=bool(np.array_equal(initial_weights[a], initial_weights[b])),
                membranes_identical_at_initialization=bool(initial_membranes[a] == initial_membranes[b]),
                shared_l2i_received_both_before_firing=both_before_fire,
                l2i_event_at_first_coactive=inhibition,
                hypothetical_first_spike_inhibition_arrival_step=hypothetical_arrival,
                second_physical_spike_step=second_physical_step,
                hypothetical_inhibition_could_arrive_before_second=bool(
                    hypothetical_arrival is not None and second_physical_step is not None
                    and hypothetical_arrival < second_physical_step),
            ))

        if all_pair_spikes_coactive:
            classification = "TRUE_SAME_STEP_CROSSING"
        elif not any_same_step and len({counts[f"L2E{j}"] for j in leaders}) == 1:
            classification = "MODAL_COUNT_TIE_ONLY"
        elif not any_same_step:
            classification = "REPEATED_ALTERNATION"
        elif all(p["first_weight_identical_step"] is not None for p in pair_details):
            classification = "LEARNED_TRAJECTORY_SYMMETRY"
        else:
            classification = "MIXED_TIE"

        tied_rows.append(dict(
            seed=seed,
            classification=classification,
            tied_neurons=[f"L2E{j}" for j in leaders],
            tie_cardinality=len(leaders),
            earliest_physical_response_step=earliest_spike,
            earliest_physical_response_set=[f"L2E{j}" for j in earliest_set],
            first_physical_spike_by_tied_neuron={f"L2E{j}": spike_steps[j][0] for j in leaders},
            first_distinct_rival_step=min((spike_steps[j][0] for j in leaders
                                           if j not in earliest_set), default=earliest_spike),
            hypothetical_first_spike_inhibition_arrival_step=earliest_spike + engine.l2_inhibition_delay,
            hypothetical_first_spike_inhibition_could_arrive_before_rival=bool(
                len(earliest_set) == 1 and earliest_spike + engine.l2_inhibition_delay <=
                min((spike_steps[j][0] for j in leaders if j not in earliest_set), default=earliest_spike)),
            tie_at_initialization=all(p["weights_identical_at_initialization"] and
                                      p["membranes_identical_at_initialization"] for p in pair_details),
            pair_details=pair_details,
            final_totals={f"L2E{j}": float(totals[j]) for j in leaders},
            final_spike_counts={f"L2E{j}": counts[f"L2E{j}"] for j in leaders},
        ))

    classification_counts = Counter(row["classification"] for row in tied_rows)
    resolvable = sum(row["hypothetical_first_spike_inhibition_could_arrive_before_rival"]
                     for row in tied_rows)
    verdict = ("FAST_FIRST_SPIKE_PATH_CAN_RESOLVE_MOST_TIES"
               if tied_rows and resolvable > len(tied_rows) / 2
               else "SAME_STEP_SYMMETRY_LIMITS_FIRST_SPIKE_PATH")
    result = dict(
        schema_version=1,
        checkpoint="db30ceadbe18cf90e01f6d54dee0203f342b24a8",
        configuration=dict(pattern=PATTERN, steps=STEPS, seeds=list(range(1, 41)), **STAGE1_KW),
        clean_seed_count=len(clean_seeds), clean_seeds=clean_seeds,
        tied_seed_count=len(tied_rows), tied_seeds=[row["seed"] for row in tied_rows],
        tie_cardinality_counts=dict(Counter(row["tie_cardinality"] for row in tied_rows)),
        classification_counts=dict(classification_counts),
        verdict=verdict,
        tied_seed_records=tied_rows,
        all_seed_summary=seed_rows,
        runtime_seconds=time.time() - started,
        production_modified=False, committed=False, pushed=False,
    )
    out = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({k: result[k] for k in (
        "clean_seed_count", "tied_seed_count", "tie_cardinality_counts",
        "classification_counts", "verdict", "runtime_seconds")}, indent=2))


if __name__ == "__main__":
    main()
