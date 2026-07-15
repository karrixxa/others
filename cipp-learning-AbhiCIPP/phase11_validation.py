"""
Phase 11 -- controlled multi-seed validation (July14 Phases 6-12 corrected
prompt file, july14-integration). MEASUREMENT ONLY: no neural parameter is
tuned here; every condition uses Phase 7-10's documented, as-shipped
defaults except for the dimensions explicitly under test.

Every run is based on DASHBOARD_PRESET (the live dashboard's exact config) --
NOT the raw SimulationEngine constructor defaults, which differ from it in
several canonical values (structural_free_energy, loser_depression,
l2i_hard_reset_losers, distance_ref, l2e_init_mode, etc.). Only the
dimensions explicitly under test are overridden per condition.

Crosses:
  - 4 GEOMETRY conditions, (symmetric_geometry, influence) in
        (True,  False)  "current symmetric geometry, influence off"
        (False, False)  "jittered geometry, influence off"
        (True,  True)   "current symmetric geometry, influence on"
        (False, True)   "jittered geometry, influence on"
    "influence" here is the ORIGINAL L1E->L2E distance-weighting pathway
    (distance_weighting on/off, legacy_distance_compat off/on to match) -- a
    judgment call, documented in CLAUDE_HANDOFF.md: Phase 4's four SEPARATE
    experimental pathways (infl_l2e_l2i/infl_l2i_l2e/infl_l2e_l1i/infl_l1i_l1e)
    stay OFF throughout, per the standing "do not enable every pathway
    together" rule -- this phase does not relitigate that. NOTE:
    DASHBOARD_PRESET's own default is symmetric_geometry=False,
    distance_weighting=True, legacy_distance_compat=True (jittered layout,
    but delivery pinned to the legacy reference distances) -- i.e. the
    dashboard's actual shipped default sits INSIDE the "jittered, influence
    off" cell of this 2x2, not outside it.
  - adaptive_threshold in (False, True) -- Phase 10.
  - WEIGHT_SEEDS x TOPOLOGY_SEEDS (topology_seed is a documented no-op under
    symmetric_geometry=True; looped uniformly anyway for a simple, uniform
    protocol across all 4 geometry conditions).
  - SHORT-INTERLEAVED schedule (brief's own equal cycle, via
    diagnostic_schedule.py's already-tested recording function) vs
    LONG-SATURATION schedule (train interleaved, then hold each pattern for
    many cycles, recording the per-cycle winner -- same honest protocol as
    sustained_dominance.py/ablation_harness.py, scaled down for this
    combinatorial sweep's runtime budget).

N_OUT is never modified (always 8, the architecture invariant).

Reports, per run: first-responder consistency, same-step ambiguity rate,
mean latency margin, retention/forgetting, receptive-field cosine
similarity, silent/recruitable cells, L2I causal timing (schedule
delay/magnitude + observed activity), L1I selectivity (all-nine-sync rate),
distance/influence distribution (min/median/max, via
pathway_influence_report), and the final adaptive-threshold state
distribution across L2E. Every number here is a raw OBSERVATION; conclusions
are drawn separately in the written report, not computed by this script.

Usage:
    PYTHONPATH=. python phase11_validation.py [--quick] [--out FILE.json]
"""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import statistics as stats
from collections import Counter

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS
from backend.presets import DASHBOARD_PRESET
from diagnostic_schedule import (CYCLE_ORDER, _present_and_record, summarize,
                                 PRESENTATION_STEPS)

GEOMETRY_CONDITIONS = [
    dict(name='symmetric_influence_off', symmetric_geometry=True, influence=False),
    dict(name='jittered_influence_off', symmetric_geometry=False, influence=False),
    dict(name='symmetric_influence_on', symmetric_geometry=True, influence=True),
    dict(name='jittered_influence_on', symmetric_geometry=False, influence=True),
]

WEIGHT_SEEDS = [1, 2, 3]
TOPOLOGY_SEEDS = [1, 2]

SHORT_CYCLES = 10             # short-interleaved: rotations of the 4-pattern cycle
SHORT_STEPS = PRESENTATION_STEPS
SHORT_CONSISTENCY_REPS = 4

LONG_TRAIN_EPOCHS = 12        # long-saturation: interleaved warm-up before holding
LONG_HOLD_CYCLES = 12         # cycles held per pattern during measurement
LONG_STEPS_PER_CYCLE = 20


def _engine_kwargs(geometry, adaptive_threshold, weight_seed, topology_seed):
    """Base every run on DASHBOARD_PRESET (the live dashboard's exact config)
    -- NOT the raw SimulationEngine constructor defaults, which differ from
    it substantially (e.g. structural_free_energy, loser_depression,
    l2i_hard_reset_losers, distance_ref, l2e_init_mode all have different
    canonical values). Only the dimensions explicitly under test in this
    phase are overridden: seed, topology_seed, symmetric_geometry,
    adaptive_threshold, and the L1E->L2E influence toggle (distance_weighting
    + legacy_distance_compat, explicit in BOTH the on and off direction --
    DASHBOARD_PRESET's own base already sets distance_weighting=True, so
    "influence off" must explicitly override it, not just inherit the base)."""
    kw = dict(DASHBOARD_PRESET)
    kw.update(seed=weight_seed, topology_seed=topology_seed,
             symmetric_geometry=geometry['symmetric_geometry'],
             adaptive_threshold=adaptive_threshold,
             distance_weighting=bool(geometry['influence']),
             legacy_distance_compat=not geometry['influence'])
    return kw


def _cosine(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _rf_similarity(receptive_fields: dict) -> dict:
    """Mean pairwise cosine similarity across all C(N_OUT,2) L2E receptive-field
    pairs -- lower means sharper/more distinct receptive fields."""
    vals = list(receptive_fields.values())
    sims = [_cosine(vals[i], vals[j])
           for i in range(len(vals)) for j in range(i + 1, len(vals))]
    return dict(mean=round(float(np.mean(sims)), 4) if sims else None,
               max=round(float(np.max(sims)), 4) if sims else None)


def _adaptive_threshold_summary(engine) -> dict:
    d = engine.dynamic_state()['adaptive_threshold']
    state = list(d['state'].values())
    return dict(enabled=d['enabled'],
               final_a_mean=round(float(np.mean(state)), 4) if state else None,
               final_a_max=round(float(np.max(state)), 4) if state else None,
               final_a_nonzero_count=sum(1 for v in state if v > 1e-6))


def _l2i_causal_timing(engine) -> dict:
    li = engine.dynamic_state()['l2_inhibition']
    return dict(delay=li['delay'], magnitude=li['magnitude'],
               pending_count=len(li['pending']), delivered_log_count=len(li['log']))


def _influence_distribution(engine) -> dict:
    """NOTE: distance/influence VALUES are computed from geometry regardless
    of whether the pathway is actually applied to delivery -- `applied`
    (read off any one entry, uniform per pathway) says whether they
    influenced physical dynamics this run; when False, treat the
    min/median/max as descriptive geometry only, not an active effect."""
    report = engine.pathway_influence_report()['l1e_l2e']
    applied = bool(report['entries'][0]['applied']) if report['entries'] else False
    return dict(applied=applied,
               influence_min=report['influence_min'],
               influence_median=report['influence_median'],
               influence_max=report['influence_max'],
               safe=report['safe'])


# ------------------------------------------------------ short-interleaved
def _run_short_interleaved(geometry, adaptive_threshold, weight_seed, topology_seed,
                           cycles, steps, consistency_reps):
    engine = SimulationEngine(**_engine_kwargs(geometry, adaptive_threshold,
                                               weight_seed, topology_seed))
    live_records = []
    for _c in range(cycles):
        for pattern in CYCLE_ORDER:
            _present_and_record(engine, pattern, steps, live_records)

    frozen_engine = copy.deepcopy(engine)
    frozen_engine._set_plasticity_frozen(True)
    frozen_records = []
    for _r in range(consistency_reps):
        for pattern in CYCLE_ORDER:
            _present_and_record(frozen_engine, pattern, steps, frozen_records)

    run = dict(seed=weight_seed, live=live_records, frozen=frozen_records)
    s = summarize(run)

    margins = [r['latency_margin_to_second'] for r in live_records
              if r['latency_margin_to_second'] is not None]
    last_rf = live_records[-1]['receptive_fields'] if live_records else {}

    return dict(
        schedule='short_interleaved', geometry=geometry['name'],
        adaptive_threshold=adaptive_threshold, weight_seed=weight_seed,
        topology_seed=topology_seed,
        distinct_owners=s['distinct_owners'],
        per_pattern_consistency={p: pp['consistency'] for p, pp in s['per_pattern'].items()},
        mean_ambiguity_rate=round(stats.mean(pp['ambiguity_rate'] for pp in s['per_pattern'].values()), 4),
        mean_latency_margin=round(stats.mean(margins), 3) if margins else None,
        forgetting={p: f['changed'] for p, f in s['forgetting'].items()},
        silent_cells=s['silent_cells'], recruitable_cells=s['recruitable_cells'],
        collisions=s['collisions'],
        l2i_activity=s['l2i_activity'],
        l1i_all_nine_sync_rate=s['l1i_all_nine_sync_rate'],
        frozen_replay_zero_weight_drift=s['frozen_replay_zero_weight_drift'],
        frozen_first_responder_consistency=s['frozen_first_responder_consistency'],
        rf_similarity=_rf_similarity(last_rf),
        adaptive_threshold_summary=_adaptive_threshold_summary(engine),
        l2i_causal_timing=_l2i_causal_timing(engine),
        influence_distribution=_influence_distribution(engine),
    )


# ---------------------------------------------------------- long-saturation
def _run_long_saturation(geometry, adaptive_threshold, weight_seed, topology_seed,
                         train_epochs, hold_cycles, steps_per_cycle):
    engine = SimulationEngine(**_engine_kwargs(geometry, adaptive_threshold,
                                               weight_seed, topology_seed))
    for _ep in range(train_epochs):
        for name in PATTERNS:
            engine.set_pattern(name)
            for _ in range(steps_per_cycle):
                engine.step()

    per_pattern_dominance = {}
    fired = set()
    for name in PATTERNS:
        engine.set_pattern(name)
        winners = []
        for _c in range(hold_cycles):
            cycle_winner = None
            for _ in range(steps_per_cycle):
                engine.step()
                for j in range(N_OUT):
                    if engine.spiked[f'L2E{j}']:
                        fired.add(j)
                        if cycle_winner is None:
                            cycle_winner = j
            winners.append(cycle_winner)
        counts = Counter(w for w in winners if w is not None)
        modal, cnt = (counts.most_common(1)[0] if counts else (None, 0))
        per_pattern_dominance[name] = dict(
            modal_owner=f'L2E{modal}' if modal is not None else None,
            dominance=round(cnt / len(winners), 4) if winners else 0.0)

    modal_owners = [d['modal_owner'] for d in per_pattern_dominance.values() if d['modal_owner']]
    distinct_owners = len(set(modal_owners))
    dead = N_OUT - len(fired)
    mean_dominance = round(stats.mean(d['dominance'] for d in per_pattern_dominance.values()), 4)

    w_final = engine._all_weights()
    last_rf = {f'L2E{j}': [w_final[f'ff{i}->{j}'] for i in range(N_PIX)] for j in range(N_OUT)}

    return dict(
        schedule='long_saturation', geometry=geometry['name'],
        adaptive_threshold=adaptive_threshold, weight_seed=weight_seed,
        topology_seed=topology_seed,
        distinct_owners=distinct_owners, dead_cells=dead,
        per_pattern_dominance=per_pattern_dominance,
        mean_sustained_dominance=mean_dominance,
        rf_similarity=_rf_similarity(last_rf),
        adaptive_threshold_summary=_adaptive_threshold_summary(engine),
        l2i_causal_timing=_l2i_causal_timing(engine),
        influence_distribution=_influence_distribution(engine),
    )


def run_all(quick: bool):
    weight_seeds = WEIGHT_SEEDS[:2] if quick else WEIGHT_SEEDS
    topology_seeds = TOPOLOGY_SEEDS[:1] if quick else TOPOLOGY_SEEDS
    short_cycles = 4 if quick else SHORT_CYCLES
    long_epochs = 4 if quick else LONG_TRAIN_EPOCHS
    long_hold = 4 if quick else LONG_HOLD_CYCLES

    results = []
    combos = list(itertools.product(GEOMETRY_CONDITIONS, (False, True),
                                    weight_seeds, topology_seeds))
    total = len(combos) * 2
    done = 0
    for geometry, adaptive_threshold, wseed, tseed in combos:
        results.append(_run_short_interleaved(
            geometry, adaptive_threshold, wseed, tseed,
            cycles=short_cycles, steps=SHORT_STEPS,
            consistency_reps=SHORT_CONSISTENCY_REPS))
        done += 1
        print(f'[{done}/{total}] short_interleaved {geometry["name"]} '
              f'adaptive={adaptive_threshold} wseed={wseed} tseed={tseed} done')
        results.append(_run_long_saturation(
            geometry, adaptive_threshold, wseed, tseed,
            train_epochs=long_epochs, hold_cycles=long_hold,
            steps_per_cycle=LONG_STEPS_PER_CYCLE))
        done += 1
        print(f'[{done}/{total}] long_saturation {geometry["name"]} '
              f'adaptive={adaptive_threshold} wseed={wseed} tseed={tseed} done')
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--quick', action='store_true',
                    help='reduced seeds/cycles for a fast smoke run')
    ap.add_argument('--out', default='phase11_validation_report.json')
    args = ap.parse_args()

    results = run_all(quick=args.quick)
    with open(args.out, 'w') as f:
        json.dump(dict(quick=args.quick,
                       weight_seeds=WEIGHT_SEEDS[:2] if args.quick else WEIGHT_SEEDS,
                       topology_seeds=TOPOLOGY_SEEDS[:1] if args.quick else TOPOLOGY_SEEDS,
                       results=results), f, indent=2)
    print(f'\nWrote {len(results)} records to {args.out}')


if __name__ == '__main__':
    main()
