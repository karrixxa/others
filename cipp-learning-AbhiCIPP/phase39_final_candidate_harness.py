"""Phase 39 compact acceptance harness for FINAL_CANDIDATE_PRESET.

Read-only measurement: builds one engine from the named preset, runs a
single bounded seed, and writes a JSON verdict report. No sweep, no new
mechanism -- every metric below reads state the engine already produces.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

import numpy as np

from backend.presets import FINAL_CANDIDATE_PRESET
from backend.simulation import N_OUT, N_PIX, SimulationEngine

CYCLE_ORDER = ['row 1', 'col 1', 'diag \\', 'diag /']
PRESENTATION_STEPS = 20
SEED = 1
TOPOLOGY_SEED = 1
N_CYCLES = 100  # 100 * 4 * 20 = 8000 steps -- bounded, one seed only


def _config_fingerprint(engine: SimulationEngine) -> str:
    keys = sorted(FINAL_CANDIDATE_PRESET.keys()) + ['seed', 'topology_seed']
    parts = [f"{k}={engine.params.get(k)}" for k in keys]
    return "|".join(parts)


def run() -> dict:
    t_wall = time.time()
    engine = SimulationEngine(seed=SEED, topology_seed=TOPOLOGY_SEED, **FINAL_CANDIDATE_PRESET)

    presentations = []
    same_step_multi_firer_steps = 0
    index_bias_counts = Counter()  # which L2E index appears in a multi-firer tie
    pc_fire_events = 0
    first_pc_fire_step = None
    elig_bump_events = 0
    switchi_requests = 0
    switchi_applied = 0
    paired_target_violations = []
    causal_violations = []

    prev_elig = engine.switchi_local_elig.copy() if engine.switchi_local_mismatch_enabled else None

    for _cycle in range(N_CYCLES):
        for pattern in CYCLE_ORDER:
            engine.set_pattern(pattern)
            t_start = engine.timestep
            first = None
            same_step_tie = False
            for _s in range(PRESENTATION_STEPS):
                pending_before = list(engine._switchi_local_pending)

                engine.step()

                # -- same-step ties / index bias --
                if len(engine._last_eligible) > 1:
                    same_step_multi_firer_steps += 1
                    for j in engine._last_eligible:
                        index_bias_counts[j] += 1
                if first is None:
                    firers = [f'L2E{j}' for j in range(N_OUT) if engine.spiked[f'L2E{j}']]
                    if firers:
                        first = firers[0]
                        same_step_tie = len(firers) > 1

                # -- PC firing --
                for i in range(N_PIX):
                    if engine.spiked.get(f'PC{i}'):
                        pc_fire_events += 1
                        if first_pc_fire_step is None:
                            first_pc_fire_step = engine.timestep

                # -- eligibility growth events --
                if engine.switchi_local_mismatch_enabled:
                    cur_elig = engine.switchi_local_elig
                    elig_bump_events += int(np.count_nonzero(cur_elig > prev_elig + 1e-12))
                    prev_elig = cur_elig.copy()

                # -- SwitchI requests queued this step --
                switchi_requests += sum(
                    1 for row in engine._switchi_local_last_events if row.get('queued'))

                # -- deliveries applied + paired-target / causal checks --
                # Every delivered record this step must (a) have been queued
                # at least 2 steps ago (paired, delayed, never same-step) and
                # (b) target exactly one L2E each -- no delivery may name a
                # target outside 0..N_OUT-1 or duplicate a target within the
                # same batch (that would mean two independent shunts landed
                # on one neuron in one step from what should be one request).
                deliveries = engine._switchi_local_last_deliveries
                seen_targets = set()
                for row in deliveries:
                    if not row.get('applied'):
                        continue
                    switchi_applied += 1
                    j = int(row['target'][3:])
                    if not (0 <= j < N_OUT):
                        paired_target_violations.append(dict(reason='target_out_of_range', row=row))
                    if j in seen_targets:
                        paired_target_violations.append(dict(reason='duplicate_target_in_batch', row=row))
                    seen_targets.add(j)
                    matched = next((r for r in pending_before
                                   if r['target_index'] == j and r['deliver_at'] == engine.timestep - 1), None)
                    if matched is None or matched['deliver_at'] < matched['fire_t'] + 2:
                        causal_violations.append(dict(kind='delivery_not_registered_t_plus_2', row=row))

            presentations.append(dict(
                pattern=pattern, t_start=t_start, t_end=engine.timestep,
                first_l2e_spiker=first, same_step_tie=same_step_tie))

    # -- ownership summary --
    by_pattern = {p: [r for r in presentations if r['pattern'] == p] for p in CYCLE_ORDER}
    per_pattern = {}
    for p, recs in by_pattern.items():
        firsts = [r['first_l2e_spiker'] for r in recs]
        counts = Counter(f for f in firsts if f is not None)
        modal = counts.most_common(1)[0][0] if counts else None
        consistency = (counts[modal] / len(firsts)) if modal else 0.0
        per_pattern[p] = dict(owner=modal, consistency=round(consistency, 4),
                              same_step_ties=sum(1 for r in recs if r['same_step_tie']))
    owners = [row['owner'] for row in per_pattern.values() if row['owner']]
    distinct_owners = len(set(owners))
    collisions = {o: [p for p, row in per_pattern.items() if row['owner'] == o]
                 for o in set(owners) if owners.count(o) > 1}
    total_first = sum(1 for r in presentations if r['first_l2e_spiker'])
    tyrant_counts = Counter(r['first_l2e_spiker'] for r in presentations if r['first_l2e_spiker'])
    tyrant_share = {nid: round(c / total_first, 4) for nid, c in tyrant_counts.items()} if total_first else {}
    max_tyrant_share = max(tyrant_share.values()) if tyrant_share else 0.0

    # -- weights / silence --
    weights = engine._all_weights()
    ff = np.array([weights[f'ff{i}->{j}'] for j in range(N_OUT) for i in range(N_PIX)])
    exact_zero_ff = int(np.count_nonzero(np.isclose(ff, 0.0, atol=1e-9)))
    silent_l2e = [f'L2E{j}' for j in range(N_OUT) if engine._neuron_total_spikes.get(f'L2E{j}', 0) == 0]

    metrics = dict(
        distinct_owners=distinct_owners,
        per_pattern_owner={p: row['owner'] for p, row in per_pattern.items()},
        per_pattern_consistency={p: row['consistency'] for p, row in per_pattern.items()},
        collisions=collisions,
        collision_stable=all(row['consistency'] >= 0.99 for row in per_pattern.values() if row['owner']),
        tyrant_share=tyrant_share,
        max_tyrant_share=round(max_tyrant_share, 4),
        same_step_multi_firer_steps=same_step_multi_firer_steps,
        index_bias_counts={f'L2E{j}': c for j, c in sorted(index_bias_counts.items())},
        silent_l2e=silent_l2e,
        active_l2e_count=N_OUT - len(silent_l2e),
        pc_fire_events=pc_fire_events,
        first_pc_fire_step=first_pc_fire_step,
        nonzero_eligibility_events=elig_bump_events,
        switchi_requests_queued=switchi_requests,
        switchi_deliveries_applied=switchi_applied,
        paired_target_violations=paired_target_violations,
        causal_violations=causal_violations,
        exact_zero_feedforward_weights=exact_zero_ff,
        config_fingerprint=_config_fingerprint(engine),
        total_steps=N_CYCLES * len(CYCLE_ORDER) * PRESENTATION_STEPS,
        wall_seconds=round(time.time() - t_wall, 3),
    )

    # -- verdict, earliest blocker first --
    if metrics['causal_violations'] or metrics['paired_target_violations']:
        verdict = 'CAUSAL_VIOLATION'
    elif metrics['exact_zero_feedforward_weights'] > 0:
        verdict = 'WEIGHT_DISCONNECTION'
    elif metrics['active_l2e_count'] < 2:
        verdict = 'COMPETITION_FAILURE'
    elif metrics['pc_fire_events'] == 0:
        verdict = 'PREDICTION_IMMATURE'
    elif metrics['nonzero_eligibility_events'] == 0 or (
            metrics['switchi_requests_queued'] == 0 and metrics['switchi_deliveries_applied'] == 0):
        verdict = 'SWITCHI_INACTIVE'
    elif metrics['distinct_owners'] < 4 or metrics['max_tyrant_share'] > 0.6:
        verdict = 'TYRANNY'
    else:
        verdict = 'PASS_FINAL_CANDIDATE'

    return dict(verdict=verdict, metrics=metrics)


def main():
    result = run()
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'artifacts', 'phase39')
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'seed1_smoke.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(dict(verdict=result['verdict'],
                          distinct_owners=result['metrics']['distinct_owners'],
                          max_tyrant_share=result['metrics']['max_tyrant_share'],
                          pc_fire_events=result['metrics']['pc_fire_events'],
                          first_pc_fire_step=result['metrics']['first_pc_fire_step'],
                          switchi_requests_queued=result['metrics']['switchi_requests_queued'],
                          switchi_deliveries_applied=result['metrics']['switchi_deliveries_applied'],
                          wall_seconds=result['metrics']['wall_seconds']), indent=2))
    print('wrote', out_path)


if __name__ == '__main__':
    main()
