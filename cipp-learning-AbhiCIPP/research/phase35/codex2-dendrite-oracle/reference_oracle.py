#!/usr/bin/env python3
"""Standalone reference oracle for basal/apical dendritic coincidence.

No production modules are imported.  Run this file to regenerate golden_cases.json
and results.json next to the script.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from itertools import product
import json
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Config:
    name: str
    coincidence_charge: float
    soma_threshold: float
    d_init: float
    maturity: float
    d_max: float
    eta: float
    expected_feedback_source: str


@dataclass(frozen=True)
class Event:
    event_id: str
    branch: str                 # basal | apical
    source: str
    target: str
    scheduled_timestep: int
    delivered_timestep: int
    magnitude: float
    origin_pattern: str
    current_pattern: str
    origin_pixel: str
    current_pixel: str
    delivery_role: str = "active"  # active | shadow
    deferred: bool = False


def origin_class(events: Iterable[Event]) -> str:
    events = tuple(events)
    stale = [e for e in events if e.origin_pattern != e.current_pattern]
    if not stale:
        return "current-correct"
    labels = {"stale-same-pixel" if e.origin_pixel == e.current_pixel else
              "stale-wrong-pixel" for e in stale}
    if len(stale) != len(events) or len(labels) != 1:
        return "mixed"
    return next(iter(labels))


def simulate(events: Iterable[Event], cfg: Config,
             weights: dict[str, float] | None = None) -> dict[str, Any]:
    """Evaluate deliveries by timestep; traces are deliberately non-causal."""
    events = tuple(events)
    if len({e.event_id for e in events}) != len(events):
        raise ValueError("event_id must be delivered at most once")
    weights = dict(weights or {})
    records: list[dict[str, Any]] = []
    decoder_updates: list[dict[str, Any]] = []
    spikes: list[dict[str, Any]] = []
    active = [e for e in events if e.delivery_role == "active"]
    timesteps = sorted({e.delivered_timestep for e in events})
    for timestep in timesteps:
        delivered_all = [e for e in events if e.delivered_timestep == timestep]
        delivered = [e for e in active if e.delivered_timestep == timestep]
        targets = sorted({e.target for e in delivered})
        coincidences: list[dict[str, Any]] = []
        for target in targets:
            basal = [e for e in delivered if e.target == target and e.branch == "basal"]
            apical = [e for e in delivered if e.target == target and e.branch == "apical"
                      and e.source == cfg.expected_feedback_source]
            if not basal or not apical:
                continue
            paired = basal + apical
            associations = []
            for b in basal:
                key = f"{b.source}->{target}"
                before = weights.get(key, cfg.d_init)
                mature_before = before >= cfg.maturity
                delta = cfg.eta * sum(a.magnitude for a in apical)
                after = min(cfg.d_max, before + delta)
                weights[key] = after
                update = {"key": key, "before": before, "delta": after - before,
                          "after": after, "mature_before": mature_before}
                decoder_updates.append({"timestep": timestep, **update})
                associations.append(update)
                if mature_before and cfg.coincidence_charge >= cfg.soma_threshold:
                    spikes.append({"timestep": timestep, "target": target, "key": key})
            coincidences.append({
                "target": target,
                "charge": cfg.coincidence_charge,
                "origin_class": origin_class(paired),
                "event_ids": sorted(e.event_id for e in paired),
                "associations": associations,
            })
        records.append({
            "timestep": timestep,
            "delivered_event_ids": sorted(e.event_id for e in delivered_all),
            "active_event_ids": sorted(e.event_id for e in delivered),
            "coincidences": coincidences,
            "end_state": {"basal_events": [], "apical_events": []},
        })
    return {"records": records, "decoder_updates": decoder_updates,
            "spikes": spikes, "final_weights": weights,
            "delivery_counts": {e.event_id: 1 for e in events}}


CANDIDATE = Config("legacy_candidate_only", 500, 500, 50, 350, 1200, 0.15, "feedback")
TEST = Config("oracle_test", 7, 7, 2, 5, 11, 1, "feedback")


def ev(event_id: str, branch: str, *, source: str | None = None,
       target: str = "t0", scheduled: int = 0, delivered: int = 0,
       magnitude: float = 1, origin_pattern: str = "A",
       current_pattern: str = "A", origin_pixel: str = "p0",
       current_pixel: str = "p0", role: str = "active", deferred: bool = False) -> Event:
    return Event(event_id, branch, source or ("input" if branch == "basal" else "feedback"),
                 target, scheduled, delivered, magnitude, origin_pattern,
                 current_pattern, origin_pixel, current_pixel, role, deferred)


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    coincidences = [c for r in result["records"] for c in r["coincidences"]]
    return {
        "coincidence_count": len(coincidences),
        "coincidence_targets": [c["target"] for c in coincidences],
        "origin_classes": [c["origin_class"] for c in coincidences],
        "spike_count": len(result["spikes"]),
        "decoder_update_keys": [u["key"] for u in result["decoder_updates"]],
        "delivery_counts": result["delivery_counts"],
        "end_states_clear": all(not r["end_state"]["basal_events"] and
                                not r["end_state"]["apical_events"]
                                for r in result["records"]),
    }


def golden_cases() -> list[dict[str, Any]]:
    cases: list[tuple[str, str, list[Event], dict[str, float] | None]] = []
    add = cases.append
    add(("neither_input", "No deliveries.", [], None))
    add(("basal_only", "One basal delivery.", [ev("b", "basal")], None))
    add(("apical_only_max_weight", "Apical alone, even with a max decoder.",
         [ev("a", "apical")], {"input->t0": TEST.d_max}))
    add(("same_step_coincidence", "Matching target and delivered timestep.",
         [ev("b", "basal"), ev("a", "apical")], None))
    add(("offset_minus_one", "Apical delivered one timestep before basal.",
         [ev("a", "apical", delivered=0), ev("b", "basal", delivered=1)], None))
    add(("offset_plus_one", "Apical delivered one timestep after basal.",
         [ev("b", "basal", delivered=0), ev("a", "apical", delivered=1)], None))
    add(("same_schedule_different_delivery", "Scheduled together, delivered apart.",
         [ev("b", "basal", scheduled=0, delivered=0),
          ev("a", "apical", scheduled=0, delivered=1)], None))
    add(("different_schedule_same_delivery", "Scheduled apart, delivered together.",
         [ev("b", "basal", scheduled=0, delivered=2),
          ev("a", "apical", scheduled=1, delivered=2)], None))
    add(("wrong_target", "Branches arrive at different targets.",
         [ev("b", "basal", target="t0"), ev("a", "apical", target="t1")], None))
    add(("wrong_feedback_source", "Apical source is not configured feedback.",
         [ev("b", "basal"), ev("a", "apical", source="other")], None))
    add(("repeated_single_branch", "Repeated basal deliveries do not form a pair.",
         [ev("b0", "basal", delivered=0), ev("b1", "basal", delivered=1)], None))
    add(("timestep_clearing", "A prior basal cannot pair with later apical.",
         [ev("b", "basal", delivered=0), ev("a", "apical", delivered=1)], None))
    add(("decoder_threshold_crossing", "Pre-update maturity controls firing.",
         [ev("b0", "basal", delivered=0), ev("a0", "apical", delivered=0, magnitude=1),
          ev("b1", "basal", delivered=1), ev("a1", "apical", delivered=1, magnitude=1)],
         {"input->t0": TEST.maturity - TEST.eta}))
    nine = [ev(f"a{i}", "apical", target=f"t{i}") for i in range(9)]
    three = [ev(f"b{i}", "basal", source=f"in{i}", target=f"t{i}") for i in (1, 4, 7)]
    add(("three_active_targets_of_nine", "Nine feedback targets, three basal targets.",
         nine + three, None))
    add(("queue_carryover_switch_same_pixel", "Queued stale event survives switch.",
         [ev("b", "basal", scheduled=0, delivered=2, origin_pattern="A",
             current_pattern="B", origin_pixel="p0", current_pixel="p0"),
          ev("a", "apical", scheduled=0, delivered=2, origin_pattern="A",
             current_pattern="B", origin_pixel="p0", current_pixel="p0")], None))
    add(("queue_carryover_switch_wrong_pixel", "Stale wrong-pixel classification.",
         [ev("b", "basal", scheduled=0, delivered=2, origin_pattern="A",
             current_pattern="B", origin_pixel="p9", current_pixel="p0"),
          ev("a", "apical", scheduled=0, delivered=2, origin_pattern="A",
             current_pattern="B", origin_pixel="p9", current_pixel="p0")], None))
    add(("queue_carryover_mixed_origin", "Current and stale deliveries coincide.",
         [ev("b", "basal", scheduled=0, delivered=2, origin_pattern="A",
             current_pattern="B", origin_pixel="p0", current_pixel="p0"),
          ev("a", "apical", scheduled=2, delivered=2, origin_pattern="B",
             current_pattern="B")], None))
    add(("one_time_refractory_deferral", "Deferred event arrives exactly once.",
         [ev("b", "basal", scheduled=0, delivered=1, deferred=True),
          ev("a", "apical", scheduled=1, delivered=1)], None))
    add(("active_versus_shadow", "Shadow apical is recorded but causally inert.",
         [ev("b", "basal"), ev("shadow_a", "apical", role="shadow")], None))
    output = []
    for name, purpose, events, weights in cases:
        result = simulate(events, TEST, weights)
        output.append({"name": name, "purpose": purpose,
                       "events": [asdict(e) for e in events],
                       "initial_weights": weights or {}, "expected": summarize(result)})
    return output


def exhaustive_check() -> dict[str, Any]:
    """Enumerate all ordered two-event records in a compact semantic domain."""
    domains = {
        "branch": ["basal", "apical"], "source": ["input", "feedback", "other"],
        "target": ["t0", "t1"], "scheduled_timestep": [0, 1],
        "delivered_timestep": [0, 1], "magnitude": [1, 2],
        "origin_pattern": ["A", "B"], "current_pattern": ["B"],
        "origin_pixel": ["p0", "p1"], "current_pixel": ["p0"],
        "delivery_role": ["active", "shadow"],
    }
    tuples = list(product(*domains.values()))
    keys = list(domains)
    counterexamples: list[dict[str, Any]] = []
    checked_pairs = 0
    for left in tuples:
        e0 = Event("e0", **dict(zip(keys, left)), deferred=False)
        for right in tuples:
            e1 = Event("e1", **dict(zip(keys, right)), deferred=False)
            result = simulate([e0, e1], TEST)
            coins = [c for r in result["records"] for c in r["coincidences"]]
            expected = (e0.delivery_role == e1.delivery_role == "active" and
                        e0.delivered_timestep == e1.delivered_timestep and
                        e0.target == e1.target and {e0.branch, e1.branch} == {"basal", "apical"} and
                        next(e.source for e in (e0, e1) if e.branch == "apical") == TEST.expected_feedback_source)
            violations = []
            if bool(coins) != expected: violations.append("physical_gate_equivalence")
            if (not coins) and (result["spikes"] or result["decoder_updates"]):
                violations.append("no_effect_without_coincidence")
            if any(u["key"].split("->")[1] not in {c["target"] for c in coins}
                   for u in result["decoder_updates"]):
                violations.append("target_locality")
            if any(count != 1 for count in result["delivery_counts"].values()):
                violations.append("exactly_once_delivery")
            if not summarize(result)["end_states_clear"]: violations.append("clearing")
            if violations and len(counterexamples) < 100:
                counterexamples.append({"events": [asdict(e0), asdict(e1)],
                                        "violations": violations, "result": summarize(result)})
            checked_pairs += 1
    # Separate maturity boundary check, including a threshold-crossing update.
    before_values = [TEST.maturity - TEST.eta, TEST.maturity, TEST.maturity + TEST.eta]
    maturity_failures = []
    pair = [ev("mb", "basal"), ev("ma", "apical")]
    for before in before_values:
        r = simulate(pair, TEST, {"input->t0": before})
        if bool(r["spikes"]) != (before >= TEST.maturity):
            maturity_failures.append({"before": before, "result": summarize(r)})
    counterexamples.extend({"violations": ["pre_update_maturity"], **x}
                           for x in maturity_failures)
    return {
        "space": {"record_length": 2, "ordered": True, "domains": domains,
                  "single_event_domain_size": len(tuples),
                  "two_event_records": checked_pairs,
                  "additional_maturity_boundary_runs": len(before_values),
                  "total_simulations": checked_pairs + len(before_values)},
        "counterexample_count": len(counterexamples),
        "counterexamples": counterexamples,
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    goldens = golden_cases()
    exhaustive = exhaustive_check()
    verdict = "SEMANTIC_CONTRACT_CONSISTENT" if not exhaustive["counterexamples"] else "COUNTEREXAMPLE_FOUND"
    (root / "golden_cases.json").write_text(json.dumps({
        "schema_version": 1, "config": asdict(TEST), "cases": goldens}, indent=2) + "\n")
    (root / "results.json").write_text(json.dumps({
        "schema_version": 1, "verdict": verdict,
        "parameter_sets": {"oracle_test": asdict(TEST),
                           "legacy_candidate_only": asdict(CANDIDATE)},
        "golden_case_count": len(goldens), "exhaustive": exhaustive}, indent=2) + "\n")
    print(verdict)
    print(f"golden_cases={len(goldens)} simulations={exhaustive['space']['total_simulations']} "
          f"counterexamples={exhaustive['counterexample_count']}")


if __name__ == "__main__":
    main()
