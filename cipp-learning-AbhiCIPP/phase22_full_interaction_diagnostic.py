"""
Phase 22 -- full interaction: pretrained_l2i_recruitment (Phase 17) x
prediction_column_to_i_enabled (Phase 21), 2x2 factorial, across short/long
hold-switch schedules, equal interleaving, and a genuine novel-pattern
spare-capacity challenge.

Conditions:
  A: neither (baseline)
  B: pretrained_l2i_recruitment only        (Phase 17's own narrow negative
                                              result -- tyrant_share=1.0 in
                                              every long-hold seed)
  C: prediction_column_to_i_enabled only    (Phase 21's own positive result
                                              -- exact per-pixel selectivity,
                                              weaker overall suppression)
  D: BOTH together                          (the new interaction under test)

Reports SEPARATELY (per the explicit instruction -- never conflate these):
  - physical WTA metrics: distinct_owners, consistency, tyrant_share
    (reused from diagnostic_schedule.py's established summarize()).
  - allocation metrics: how many of the 8 L2E are ever recruited across
    the 4 patterns.
  - prediction reconstruction metrics: PCi firing precision (Phase 19/21's
    own metric) under condition C/D only (PC doesn't exist under A/B).
  - capacity metrics: does a genuinely novel 5th pattern (held-out PROBES
    'row 0', introduced with LIVE plasticity -- never present_probe(), which
    freezes) recruit a previously-spare L2E, or get absorbed by an existing
    tyrant?

Explicitly: clean one-hot firing is NOT interpreted as successful one-to-one
representation (a known false-positive risk carried over from Phase 17).
"""

import copy
import json

import numpy as np

import diagnostic_schedule as ds
from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS, PROBES
from backend.presets import DASHBOARD_PRESET

SEEDS = (1, 2)
SCHEDULES = {'short': 5, 'equal': 20, 'long': 100}
CYCLES = 3


def _kwargs(condition):
    kw = dict(DASHBOARD_PRESET)
    if condition in ('B', 'D'):
        kw['pretrained_l2i_recruitment'] = True
    if condition in ('C', 'D'):
        kw['prediction_column_enabled'] = True
        kw['prediction_column_to_i_enabled'] = True
    return kw


def _wta_and_allocation(condition, schedule_name, steps, seed):
    run = ds.run_diagnostic(seed=seed, engine_kwargs=_kwargs(condition),
                            cycles=CYCLES, presentation_steps=steps)
    return ds.summarize(run)


def _prediction_precision(condition, seed):
    """PCi precision (Phase 19/21's metric) -- only meaningful under C/D."""
    if condition not in ('C', 'D'):
        return None
    e = SimulationEngine(seed=seed, **_kwargs(condition))
    e.set_pattern('row 1')
    spikes = np.zeros(N_PIX)
    for _ in range(1500):
        e.step()
        for i in range(N_PIX):
            if e.spiked.get(f'PC{i}'):
                spikes[i] += 1
    fired = set(np.nonzero(spikes)[0].tolist())
    active = set(i for i, v in enumerate(PATTERNS['row 1']) if v)
    tp, fp = len(fired & active), len(fired - active)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    return dict(precision=round(precision, 3), fired=sorted(fired))


def _spare_capacity_challenge(condition, seed):
    """Train 4 patterns, freeze+record owners, introduce a genuinely novel
    pattern (PROBES['row 0']) with LIVE plasticity (never present_probe()),
    observe the eventual responder and whether it was previously spare."""
    e = SimulationEngine(seed=seed, **_kwargs(condition))
    for _c in range(CYCLES):
        for pattern in ds.CYCLE_ORDER:
            e.set_pattern(pattern)
            for _ in range(20):
                e.step()

    pre_novel_owners = {}
    for pattern in ds.CYCLE_ORDER:
        counts = np.zeros(N_OUT)
        e2 = copy.deepcopy(e)
        e2._set_plasticity_frozen(True)
        e2.set_pattern(pattern)
        for _ in range(20):
            e2.step()
            for j in range(N_OUT):
                if e2.spiked.get(f'L2E{j}'):
                    counts[j] += 1
        pre_novel_owners[pattern] = int(np.argmax(counts)) if counts.sum() else None
    ever_used = set(v for v in pre_novel_owners.values() if v is not None)
    spare_before = [j for j in range(N_OUT) if j not in ever_used]

    # Introduce the novel pattern with LIVE plasticity.
    e.input_vec = np.array(PROBES['row 0'], dtype=float)
    e._start_presentation('row 0', 'train')
    novel_counts = np.zeros(N_OUT)
    for _ in range(100):
        e.step()
        for j in range(N_OUT):
            if e.spiked.get(f'L2E{j}'):
                novel_counts[j] += 1
    novel_owner = int(np.argmax(novel_counts)) if novel_counts.sum() else None
    return dict(
        pre_novel_owners=pre_novel_owners,
        spare_before=spare_before,
        novel_owner=novel_owner,
        novel_owner_was_spare=(novel_owner in spare_before) if novel_owner is not None else None,
        novel_owner_was_tyrant=(novel_owner in ever_used) if novel_owner is not None else None,
    )


def main():
    results = {}
    for condition in ('A', 'B', 'C', 'D'):
        results[condition] = {'wta': {}, 'prediction': {}, 'capacity': {}}
        for sched_name, steps in SCHEDULES.items():
            per_seed = []
            for seed in SEEDS:
                summary = _wta_and_allocation(condition, sched_name, steps, seed)
                per_seed.append(summary)
            results[condition]['wta'][sched_name] = per_seed
        results[condition]['prediction'] = {
            seed: _prediction_precision(condition, seed) for seed in SEEDS}
        results[condition]['capacity'] = {
            seed: _spare_capacity_challenge(condition, seed) for seed in SEEDS}
        print(f"\n=== condition {condition} ===")
        print(json.dumps(results[condition], indent=2, default=str))

    with open('phase22_full_interaction_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("\nWritten to phase22_full_interaction_results.json")


if __name__ == "__main__":
    main()
