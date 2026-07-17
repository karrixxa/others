"""
Phase 33 -- Gate A: row/column two-pattern acquisition.

Sequential gate, not a grid. Centered encoder ON, prediction OFF, causal
microstep L2 race ON (K=20, the one preregistered value) versus K=1 (the
exact baseline control) -- no other configuration, no sweep. 3 fixed
seeds (1, 2, 3).

STABLE OWNER: the same physical first responder on at least 8 of a
pattern's own final 10 presentations (within this pattern's own
chronological sequence in the interleaved schedule -- never a global
across-pattern window).

PASS condition: both patterns (row 1, col 1) have a distinct stable owner
in ALL 3 seeds. If Gate A fails, per instruction, STOP -- no K or
parameter tuning, no retry.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.simulation import SimulationEngine, N_OUT, N_PIX  # noqa: E402
from backend.presets import DASHBOARD_PRESET  # noqa: E402
from diagnostic_schedule import PRESENTATION_STEPS  # noqa: E402

SEEDS = (1, 2, 3)
TOPOLOGY_SEED = 1
PATTERNS_GATE_A = ('row 1', 'col 1')
PRESENTATIONS_PER_PATTERN = 40   # interleaved: 80 total presentations, 1600 steps
STABLE_MIN_COUNT = 8             # out of the final 10 presentations of that pattern
STABLE_WINDOW = 10
K_CANDIDATE = 20                 # the one preregistered value
K_CONTROL = 1                    # exact baseline control


def base_kwargs():
    kw = dict(DASHBOARD_PRESET)
    kw['centered_encoder_enabled'] = True
    kw['loser_depression'] = False
    kw['prediction_column_enabled'] = False
    return kw


def build_engine(weight_seed, K, causal_microstep):
    kw = base_kwargs()
    kw['seed'] = weight_seed
    kw['topology_seed'] = TOPOLOGY_SEED
    kw['l2_charge_chunks'] = K
    kw['causal_microstep_l2_race_enabled'] = causal_microstep
    return SimulationEngine(**kw)


def run(weight_seed, K, causal_microstep, presentations_per_pattern=PRESENTATIONS_PER_PATTERN,
       presentation_steps=PRESENTATION_STEPS):
    engine = build_engine(weight_seed, K, causal_microstep)
    presentation_log = []
    idx = 0
    for _round in range(presentations_per_pattern):
        for pattern in PATTERNS_GATE_A:
            engine.set_pattern(pattern)
            t_start = engine.timestep
            spikes_this_pres = []
            for _s in range(presentation_steps):
                engine.step()
                t = engine.timestep - 1
                for j in range(N_OUT):
                    if engine.spiked.get(f'L2E{j}'):
                        spikes_this_pres.append((t, f'L2E{j}'))
            t_end = engine.timestep
            first = spikes_this_pres[0] if spikes_this_pres else None
            same_step_tie = bool(first and sum(1 for s in spikes_this_pres if s[0] == first[0]) > 1)
            presentation_log.append(dict(
                presentation_index=idx, pattern=pattern, t_start=t_start, t_end=t_end,
                first_l2e_spiker=first[1] if first else None,
                first_spike_latency=(first[0] - t_start) if first else None,
                same_step_tie=same_step_tie))
            idx += 1
    return engine, presentation_log


def stable_owner(presentation_log, pattern, min_count=STABLE_MIN_COUNT, window=STABLE_WINDOW):
    recs = [r for r in presentation_log if r['pattern'] == pattern]
    last_window = recs[-window:]
    counts = Counter(r['first_l2e_spiker'] for r in last_window if r['first_l2e_spiker'] is not None)
    if not counts:
        return None, 0
    owner, count = counts.most_common(1)[0]
    if count >= min_count:
        return owner, count
    return None, count


def analyze(presentation_log):
    result = {}
    for p in PATTERNS_GATE_A:
        owner, count = stable_owner(presentation_log, p)
        result[p] = dict(stable_owner=owner, count_in_window=count)

    early = [r for r in presentation_log if r['presentation_index'] < 20]
    late = [r for r in presentation_log if r['presentation_index'] >= len(presentation_log) - 20]
    early_lat = [r['first_spike_latency'] for r in early if r['first_spike_latency'] is not None]
    late_lat = [r['first_spike_latency'] for r in late if r['first_spike_latency'] is not None]
    ties = sum(1 for r in presentation_log if r['same_step_tie'])

    return dict(
        per_pattern=result,
        both_have_stable_owner=all(result[p]['stable_owner'] is not None for p in PATTERNS_GATE_A),
        distinct=(result[PATTERNS_GATE_A[0]]['stable_owner'] != result[PATTERNS_GATE_A[1]]['stable_owner']
                 if all(result[p]['stable_owner'] is not None for p in PATTERNS_GATE_A) else False),
        early_mean_latency=round(float(np.mean(early_lat)), 4) if early_lat else None,
        late_mean_latency=round(float(np.mean(late_lat)), 4) if late_lat else None,
        exact_tie_rate=round(ties / len(presentation_log), 4) if presentation_log else None,
        n_presentations=len(presentation_log),
    )


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    t0 = time.time()
    results = []
    for causal_microstep, K, label in [(True, K_CANDIDATE, 'causal_microstep_K20'),
                                       (True, K_CONTROL, 'causal_microstep_K1'),
                                       (False, K_CONTROL, 'existing_K1_baseline'),
                                       (False, K_CANDIDATE, 'existing_K20_baseline')]:
        for seed in SEEDS:
            engine, plog = run(seed, K, causal_microstep)
            analysis = analyze(plog)
            analysis.update(condition=label, weight_seed=seed, K=K,
                           causal_microstep_l2_race_enabled=causal_microstep)
            results.append(analysis)
        print(f"[{label}] done ({time.time()-t0:.1f}s elapsed)")

    candidate_rows = [r for r in results if r['condition'] == 'causal_microstep_K20']
    gate_a_pass = all(r['both_have_stable_owner'] and r['distinct'] for r in candidate_rows)

    out = dict(seeds=SEEDS, topology_seed=TOPOLOGY_SEED, patterns=PATTERNS_GATE_A,
              presentations_per_pattern=PRESENTATIONS_PER_PATTERN,
              stable_min_count=STABLE_MIN_COUNT, stable_window=STABLE_WINDOW,
              k_candidate=K_CANDIDATE, k_control=K_CONTROL,
              gate_a_verdict='PASS' if gate_a_pass else 'FAIL',
              runtime_seconds=round(time.time() - t0, 1), results=results)
    with open(os.path.join(out_dir, 'phase33_gate_a_results.json'), 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nGate A verdict: {'PASS' if gate_a_pass else 'FAIL'}")
    for r in candidate_rows:
        print(f"  seed={r['weight_seed']}: {r['per_pattern']}")


if __name__ == "__main__":
    main()
