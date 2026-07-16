"""
Phase 28A -- pre-registered stop/go analysis of
phase28a_local_common_input_feasibility_results.json.

These criteria are written BEFORE looking at the results, to avoid picking a
"robust region" post hoc. A gate condition (tau_c, g_min) is ROBUST for a
given pattern set only if ALL of the following hold, aggregated over all 30
weight seeds, relative to that SAME pattern set's own baseline (never
compared across pattern sets):

  1. Ownership improves: mean distinct_owners is at least 0.5 higher than
     baseline's mean distinct_owners (out of 4 for interleaved, out of 2 for
     long-hold), OR the persistent-collision rate (fraction of seeds with
     any persistent_ownership_collision) drops by at least 30% relative to
     baseline.
  2. No excessive ambiguity: mean overall_ambiguity_rate does not exceed
     baseline's by more than 0.05 (absolute) -- a same-step-tie explosion
     would itself be a regression, not an improvement.
  3. No excessive forgetting: the fraction of (seed, pattern) forgetting
     events ('changed'=True) does not exceed baseline's by more than 0.10
     (absolute).
  4. Peripheral learning retained: mean peripheral_weight_mean_active_neurons
     is at least 70% of baseline's own value (a gate that merely suppresses
     ALL learning, not just the universal pixel, is not a solution).
  5. Must hold on BOTH schedules (interleaved AND long_hold) for that
     pattern set -- a fix that only works on one schedule is not robust.
  6. Must hold on BOTH the standard AND shifted pattern sets with the SAME
     (tau_c, g_min) pair (not fitted separately per pattern set) -- this is
     the generalization check: a gate that only works when the universal
     pixel happens to be index 4 is fitted to that index, not genuinely
     local/general, and does not pass.

The oracle condition is reported alongside as the upper-bound reference
ONLY, never as a bar the gate condition must clear to qualify -- clearing it
is a bonus, not a requirement, since the oracle is explicitly an unfair
hardcoded control (bar (1)'s absolute margin already reflects a partial
improvement being an acceptable minimum, not "must equal oracle").

no_universal is reported as a REGRESSION-only check: a robust gate must NOT
make no_universal's ownership meaningfully WORSE than its own baseline (it
has no universal feature to suppress, so the gate should be close to a
no-op there) -- it is not required to "improve" a pattern set that has
nothing to fix.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'phase28a_local_common_input_feasibility_results.json')


def load_results(path=RESULTS_PATH):
    with open(path) as f:
        data = json.load(f)
    return data['results']


def _group(results, pattern_set, schedule, condition):
    return [r for r in results if r['pattern_set'] == pattern_set
           and r['schedule'] == schedule and r['condition'] == condition]


def _mean_distinct_owners(rows):
    return float(np.mean([r['distinct_owners'] for r in rows])) if rows else None


def _persistent_collision_rate(rows):
    return float(np.mean([1.0 if r['persistent_ownership_collision'] else 0.0 for r in rows])) if rows else None


def _mean_ambiguity(rows):
    vals = [r['overall_ambiguity_rate'] for r in rows if r['overall_ambiguity_rate'] is not None]
    return float(np.mean(vals)) if vals else None


def _forgetting_rate(rows):
    total, changed = 0, 0
    for r in rows:
        for p, f in r['forgetting'].items():
            total += 1
            changed += 1 if f['changed'] else 0
    return (changed / total) if total else None


def _mean_peripheral_weight(rows):
    vals = [r['peripheral_weight_mean_active_neurons'] for r in rows
           if r['peripheral_weight_mean_active_neurons'] is not None]
    return float(np.mean(vals)) if vals else None


def _mean_universal_ratio(rows):
    vals = [r['universal_peripheral_ratio']['mean_ratio'] for r in rows
           if r.get('universal_peripheral_ratio') and r['universal_peripheral_ratio']['mean_ratio'] is not None]
    return float(np.mean(vals)) if vals else None


def condition_metrics(results, pattern_set, schedule, condition):
    rows = _group(results, pattern_set, schedule, condition)
    return dict(
        n=len(rows),
        mean_distinct_owners=_mean_distinct_owners(rows),
        persistent_collision_rate=_persistent_collision_rate(rows),
        mean_ambiguity=_mean_ambiguity(rows),
        forgetting_rate=_forgetting_rate(rows),
        mean_peripheral_weight=_mean_peripheral_weight(rows),
        mean_universal_ratio=_mean_universal_ratio(rows),
    )


def gate_conditions(results):
    seen = set()
    conds = []
    for r in results:
        c = r['condition']
        if c.startswith('gate:') and c not in seen:
            seen.add(c)
            conds.append(c)
    return sorted(conds)


def evaluate_gate_condition(results, condition):
    """Returns (passes: bool, detail: dict) for ONE gate condition string,
    checked against ALL six pre-registered criteria above."""
    detail = {}
    passes = True
    reasons = []

    for pattern_set in ('standard', 'shifted'):
        for schedule in ('interleaved', 'long_hold'):
            base = condition_metrics(results, pattern_set, schedule, 'baseline')
            gate = condition_metrics(results, pattern_set, schedule, condition)
            key = f'{pattern_set}/{schedule}'
            detail[key] = dict(baseline=base, gate=gate)

            if base['mean_distinct_owners'] is None or gate['mean_distinct_owners'] is None:
                passes = False
                reasons.append(f'{key}: missing data')
                continue

            owners_improved = (gate['mean_distinct_owners'] - base['mean_distinct_owners']) >= 0.5
            collision_rate_improved = False
            if base['persistent_collision_rate'] not in (None, 0.0):
                collision_rate_improved = (
                    (base['persistent_collision_rate'] - gate['persistent_collision_rate'])
                    / base['persistent_collision_rate']) >= 0.30
            criterion_1 = owners_improved or collision_rate_improved

            criterion_2 = True
            if base['mean_ambiguity'] is not None and gate['mean_ambiguity'] is not None:
                criterion_2 = (gate['mean_ambiguity'] - base['mean_ambiguity']) <= 0.05

            criterion_3 = True
            if base['forgetting_rate'] is not None and gate['forgetting_rate'] is not None:
                criterion_3 = (gate['forgetting_rate'] - base['forgetting_rate']) <= 0.10

            criterion_4 = True
            if base['mean_peripheral_weight'] not in (None, 0.0) and gate['mean_peripheral_weight'] is not None:
                criterion_4 = gate['mean_peripheral_weight'] >= 0.70 * base['mean_peripheral_weight']

            detail[key]['criteria'] = dict(
                ownership_improves=criterion_1, no_excess_ambiguity=criterion_2,
                no_excess_forgetting=criterion_3, peripheral_learning_retained=criterion_4)
            if not (criterion_1 and criterion_2 and criterion_3 and criterion_4):
                passes = False
                reasons.append(f'{key}: fails {[k for k, v in detail[key]["criteria"].items() if not v]}')

    # Regression-only check on no_universal (both schedules): must not make
    # ownership meaningfully WORSE there.
    for schedule in ('interleaved', 'long_hold'):
        base = condition_metrics(results, 'no_universal', schedule, 'baseline')
        gate = condition_metrics(results, 'no_universal', schedule, condition)
        key = f'no_universal/{schedule}'
        detail[key] = dict(baseline=base, gate=gate)
        regression = False
        if base['mean_distinct_owners'] is not None and gate['mean_distinct_owners'] is not None:
            regression = (base['mean_distinct_owners'] - gate['mean_distinct_owners']) >= 0.5
        detail[key]['criteria'] = dict(no_regression=not regression)
        if regression:
            passes = False
            reasons.append(f'{key}: regression on the no-universal-feature control')

    detail['reasons_if_failed'] = reasons
    return passes, detail


def main():
    results = load_results()
    conds = gate_conditions(results)
    print(f'Loaded {len(results)} result rows, {len(conds)} gate conditions to evaluate.\n')

    passing = []
    for c in conds:
        ok, detail = evaluate_gate_condition(results, c)
        status = 'PASS' if ok else 'fail'
        print(f'{c}: {status}' + ('' if ok else f'  ({detail["reasons_if_failed"]})'))
        if ok:
            passing.append((c, detail))

    print(f'\n{len(passing)}/{len(conds)} gate conditions pass all six pre-registered criteria.')
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'phase28a_stop_go_analysis.json')
    with open(out_path, 'w') as f:
        json.dump(dict(n_conditions=len(conds),
                       passing_conditions=[c for c, _ in passing],
                       details={c: d for c, d in passing}), f, indent=2, default=str)
    print(f'Wrote {out_path}')
    return passing


if __name__ == '__main__':
    main()
