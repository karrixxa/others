"""Phase 39.1: run the existing Phase 39 harness (unmodified acceptance
logic, backend.presets.FINAL_CANDIDATE_PRESET) across five FIXED seeds, no
tuning between seeds, same exact configuration every time. Stops at the
first non-PASS verdict and reports its earliest causal blocker. 30 seeds
requires separate approval -- not run here.
"""

from __future__ import annotations

import json
import os

from phase39_final_candidate_harness import run, TOPOLOGY_SEED

SEEDS = [1, 2, 3, 4, 5]


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'artifacts', 'phase39_1')
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    per_seed_summaries = []
    stopped_at = None
    for seed in SEEDS:
        result = run(seed=seed, topology_seed=TOPOLOGY_SEED)
        out_path = os.path.join(out_dir, f'seed{seed}.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        m = result['metrics']
        summary = dict(
            seed=seed,
            verdict=result['verdict'],
            per_pattern_owner=m['per_pattern_owner'],
            collisions=m['collisions'],
            max_tyrant_share=m['max_tyrant_share'],
            pc_fire_events=m['pc_fire_events'],
            first_pc_fire_step=m['first_pc_fire_step'],
            nonzero_eligibility_events=m['nonzero_eligibility_events'],
            switchi_requests_queued=m['switchi_requests_queued'],
            switchi_deliveries_applied=m['switchi_deliveries_applied'],
            paired_target_violations=len(m['paired_target_violations']),
            causal_violations=len(m['causal_violations']),
            exact_zero_feedforward_weights=m['exact_zero_feedforward_weights'],
            silent_l2e_count=len(m['silent_l2e']),
            wall_seconds=m['wall_seconds'],
        )
        per_seed_summaries.append(summary)
        print(json.dumps(summary, indent=2))
        print('wrote', out_path)

        if result['verdict'] != 'PASS_FINAL_CANDIDATE':
            stopped_at = seed
            print(f"STOPPING: seed {seed} did not PASS (verdict={result['verdict']}). "
                  f"Per task instructions, no further seeds are run; do not tune between seeds.")
            break

    summary_path = os.path.join(out_dir, 'five_seed_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(dict(seeds_run=[s['seed'] for s in per_seed_summaries],
                       stopped_at_first_failure=stopped_at,
                       all_passed=(stopped_at is None and len(per_seed_summaries) == len(SEEDS)),
                       per_seed=per_seed_summaries), f, indent=2)
    print('wrote', summary_path)


if __name__ == '__main__':
    main()
