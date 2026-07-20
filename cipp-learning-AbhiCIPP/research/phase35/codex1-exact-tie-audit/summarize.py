#!/usr/bin/env python3
"""Offline aggregation of the passive physical scan."""
import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
d = json.loads((ROOT / "results.json").read_text())
rows = d["tied_seed_records"]
pairs = [p for row in rows for p in row["pair_details"]]
overshoots = [v for p in pairs for v in p["first_coactive_crossing"]["threshold_overshoot"].values()]
weight_diffs = [p["first_coactive_crossing"]["feedforward_weight_linf_difference"] for p in pairs]
first_coactive_steps = [p["first_coactive_crossing"]["step"] for p in pairs]
first_to_rival = [row["first_distinct_rival_step"] - row["earliest_physical_response_step"]
                  for row in rows if len(row["earliest_physical_response_set"]) == 1]
coactive = sum(p["coactive_spike_count"] for p in pairs)
union = sum(p["distinct_spike_step_count"] for p in pairs)

summary = {
    "verdict": "FAST_FIRST_SPIKE_PATH_CAN_RESOLVE_MOST_TIES",
    "reproduction": {"clean": d["clean_seed_count"], "tied": d["tied_seed_count"]},
    "tie_cardinality_counts": d["tie_cardinality_counts"],
    "classifications": d["classification_counts"],
    "earliest_response_set_size_counts": dict(Counter(
        len(row["earliest_physical_response_set"]) for row in rows)),
    "first_spike_path_could_precede_all_rivals": sum(
        row["hypothetical_first_spike_inhibition_could_arrive_before_rival"] for row in rows),
    "first_spike_path_cannot_precede_same_step_rival": sum(
        not row["hypothetical_first_spike_inhibition_could_arrive_before_rival"] for row in rows),
    "singleton_first_to_rival_delay": {
        "count": len(first_to_rival), "min": min(first_to_rival),
        "median": statistics.median(first_to_rival), "max": max(first_to_rival),
        "histogram": dict(Counter(first_to_rival)),
    },
    "pairwise_coactivity": {
        "coactive_steps": coactive, "union_spike_steps": union,
        "fraction": coactive / union,
    },
    "first_coactive_step": {
        "min": min(first_coactive_steps), "median": statistics.median(first_coactive_steps),
        "max": max(first_coactive_steps),
    },
    "first_coactive_threshold_overshoot": {
        "count": len(overshoots), "min": min(overshoots),
        "median": statistics.median(overshoots), "max": max(overshoots),
    },
    "feedforward_weight_linf_difference_at_first_coactivity": {
        "count": len(weight_diffs), "min": min(weight_diffs),
        "median": statistics.median(weight_diffs), "max": max(weight_diffs),
    },
    "shared_l2i_received_both_before_firing": sum(
        p["shared_l2i_received_both_before_firing"] for p in pairs),
    "pair_count": len(pairs),
    "weight_identical_pairs": sum(p["first_weight_identical_step"] is not None for p in pairs),
    "ties_present_at_initialization": sum(row["tie_at_initialization"] for row in rows),
    "runtime_seconds": d["runtime_seconds"],
}
(ROOT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps(summary, indent=2, sort_keys=True))
