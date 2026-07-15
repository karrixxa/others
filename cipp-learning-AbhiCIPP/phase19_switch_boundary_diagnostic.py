"""
Phase 19-v2 switch-boundary diagnostic (LPS Lecture 14 LOCAL-COINCIDENCE
prediction architecture). Runs the standard 20-step equal-interleaved
schedule (CYCLE_ORDER / PRESENTATION_STEPS, matching diagnostic_schedule.py)
continuously across many cycles under three conditions:

  1. ordinary continuous leak      -- no clearing at all (the real mechanism).
  2. washout-gap                   -- a brief blank/zero-input interval
                                       inserted between presentations
                                       (diagnostic measurement only).
  3. explicit boundary-clearing    -- PCi potential + both delayed queues are
                                       forcibly reset to zero at every
                                       presentation switch (DIAGNOSTIC
                                       CONTROL ONLY -- never the primary
                                       mechanism; see Phase18b_Lecture14_
                                       Local_Coincidence_Architecture_
                                       Contract.md).

For every PCi spike, records: current pattern, previous pattern, PCi's
membrane charge immediately before this step's arrivals, the queued S/L2E
contributor vectors and the PRESENTATION each was produced under (read from
this script's own step-by-step history, never from the engine), whether
pixel i is active in the CURRENT pattern, and a classification:
  - "coincidence"    : both S and R contributors originate in the CURRENT
                       presentation, and pixel i is active in it.
  - "mature_replay"  : the S (lateral) contributor is 0 (no sensory
                       evidence at all this event) but PCi still fired from
                       R alone -- the eventual input-free-reconstruction
                       capability, not carryover.
  - "carryover"      : the S or R contributor was queued during the
                       PREVIOUS presentation (i.e. produced before the
                       pattern switch) -- a false-prediction risk.
  - "inactive_pixel" : pixel i is NOT active in the current pattern at all
                       (a false spike regardless of contributor origin).
"""

import json

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS
from backend.presets import DASHBOARD_PRESET

CYCLE_ORDER = ['row 1', 'col 1', 'diag \\', 'diag /']
PRESENTATION_STEPS = 20
N_CYCLES = 50   # 50 * 4 patterns * 20 steps = 4000 steps of continuous operation
WASHOUT_STEPS = 5


def _make_engine(seed=1):
    return SimulationEngine(seed=seed, prediction_column_enabled=True, **DASHBOARD_PRESET)


def _classify(pattern, prev_pattern, i, s_origin_pattern, r_origin_pattern, s_val, r_any):
    active = bool(PATTERNS[pattern][i])
    if not active:
        return 'inactive_pixel'
    if s_val < 0.5:
        return 'mature_replay' if r_any else 'no_contributor'
    stale = (s_origin_pattern is not None and s_origin_pattern != pattern) or \
            (r_origin_pattern is not None and r_origin_pattern != pattern)
    return 'carryover' if stale else 'coincidence'


def run_condition(condition, seed=1):
    """condition in {'continuous', 'washout', 'boundary_clear'}."""
    e = _make_engine(seed)
    records = []
    # Parallel diagnostic history: what pattern was active when each queued
    # step's (l1e, l2e) pair was PRODUCED -- read off this script's own
    # bookkeeping, never inferred from engine internals beyond input_vec.
    origin_history = []   # origin_history[t] = pattern active when step t's l1e/l2e were produced
    prev_pattern = None
    t = 0
    for cycle in range(N_CYCLES):
        for pattern in CYCLE_ORDER:
            if condition == 'boundary_clear' and prev_pattern is not None:
                for pc in e.pcol:
                    pc.potential = 0.0
                for i in range(len(e.l2e_to_pcol_queue)):
                    e.l2e_to_pcol_queue[i] = np.zeros(N_OUT)
                    e.s_to_pcol_queue[i] = np.zeros(N_PIX)
            if condition == 'washout' and prev_pattern is not None:
                e.input_vec = np.zeros(N_PIX)
                for _ in range(WASHOUT_STEPS):
                    pots_before = [pc.potential for pc in e.pcol]
                    e.step()
                    origin_history.append(None)   # washout has no "pattern" origin
                    t += 1
                    for i in range(N_PIX):
                        if e.spiked.get(f'PC{i}'):
                            records.append(dict(
                                t=t, pattern='(washout)', prev_pattern=prev_pattern, pixel=i,
                                pre_charge=round(pots_before[i], 2), classification='washout_spike'))
            e.set_pattern(pattern)
            for _ in range(PRESENTATION_STEPS):
                pots_before = [pc.potential for pc in e.pcol]
                # This step's about-to-be-delivered pair (front of each queue,
                # BEFORE step() pops it) -- its origin is looked up from
                # origin_history at the point it was appended (delay steps ago).
                queued_s = e.s_to_pcol_queue[0].copy()
                queued_r = e.l2e_to_pcol_queue[0].copy()
                delay = e.prediction_feedback_delay
                origin_idx = t - delay
                origin_pattern = (origin_history[origin_idx]
                                  if 0 <= origin_idx < len(origin_history) else None)
                e.step()
                origin_history.append(pattern)
                t += 1
                for i in range(N_PIX):
                    if e.spiked.get(f'PC{i}'):
                        cls = _classify(pattern, prev_pattern, i, origin_pattern, origin_pattern,
                                        queued_s[i], bool(queued_r.any()))
                        records.append(dict(
                            t=t, pattern=pattern, prev_pattern=prev_pattern, pixel=i,
                            pre_charge=round(pots_before[i], 2),
                            queued_s_active=bool(queued_s[i] > 0.5),
                            queued_r_contributors=[int(j) for j in np.nonzero(queued_r)[0]],
                            contributor_origin_pattern=origin_pattern,
                            pixel_active_in_current=bool(PATTERNS[pattern][i]),
                            classification=cls))
            prev_pattern = pattern
    return records


def summarize(records):
    total = len(records)
    by_class = {}
    for r in records:
        by_class.setdefault(r['classification'], 0)
        by_class[r['classification']] += 1
    false_predictions = by_class.get('carryover', 0) + by_class.get('inactive_pixel', 0)
    rate = false_predictions / total if total else 0.0
    return dict(total_spikes=total, by_classification=by_class,
               false_prediction_count=false_predictions,
               false_prediction_rate=round(rate, 4))


def main():
    results = {}
    for condition in ('continuous', 'washout', 'boundary_clear'):
        records = run_condition(condition, seed=1)
        summary = summarize(records)
        results[condition] = dict(summary=summary,
                                  sample_records=records[:5] + records[-5:] if records else [])
        print(f"\n=== condition: {condition} ===")
        print(json.dumps(summary, indent=2))

    with open('phase19_switch_boundary_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("\nFull records + summaries written to phase19_switch_boundary_results.json")


if __name__ == "__main__":
    main()
