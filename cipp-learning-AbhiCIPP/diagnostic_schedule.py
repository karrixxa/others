"""
Diagnostic-only equal-interleaved presentation schedule (brief SS1 "preserve a
baseline" + SS12 "training schedule must change" + SS15 Phase 6 "temporal-
winner diagnostics"). MEASUREMENT ONLY -- this file changes no engine
mechanism, no learning rule, no competition code, and no default. It ONLY
observes a SimulationEngine through its existing public/semi-public state
(spiked flags, l2_drive/l2_charge, presentation tracking, _all_weights) via
brief presentations in the brief's fixed cycle:

    row 1 -> col 1 -> diag \\ -> diag / -> repeat

never training one pattern to saturation before showing the others.

NON-MUTATING EVALUATION ("evaluate using plasticity-frozen copies or proven
save/restore"): run_diagnostic() always builds its OWN disposable engine (or
deep-copies one you hand it) -- nothing outside this module is ever touched.
Two passes per seed:

  1. LIVE interleaved pass: `cycles` rotations of the fixed order above, each
     presentation BRIEF (PRESENTATION_STEPS, not a saturating hold), with
     normal learning ON. Records every requested per-presentation field,
     including real weight changes.
  2. FROZEN consistency re-test: a FURTHER deep copy of pass 1's final
     (trained) state has its plasticity explicitly frozen via the Phase 2
     present_probe() mechanism's own _set_plasticity_frozen() (already
     proven/tested there), then each pattern is re-presented several times
     with NO learning -- isolating "does the same neuron respond first every
     time" from any confound of weights still drifting during the read.
     weight_changes are 0 in this pass by construction; the report checks
     that as a live sanity confirmation that the freeze actually held.

Usage:
    PYTHONPATH=. python diagnostic_schedule.py                  # default sweep
    PYTHONPATH=. python diagnostic_schedule.py --seeds 1 2 3 4 5
"""

from __future__ import annotations

import argparse
import copy
import statistics as stats
from collections import Counter

from backend.simulation import SimulationEngine, N_OUT, N_PIX
from backend.presets import DASHBOARD_PRESET

CYCLE_ORDER = ['row 1', 'col 1', 'diag \\', 'diag /']   # brief's fixed equal-interleaved order
PRESENTATION_STEPS = 20     # BRIEF window per presentation -- never saturating
DEFAULT_CYCLES = 15         # rotations of the 4-pattern cycle per seed (live pass)
CONSISTENCY_REPS = 5        # repetitions per pattern in the frozen re-test pass


# --------------------------------------------------------------- measurement
def _snapshot_weights(engine):
    return engine._all_weights()


def _weight_deltas(before, after):
    return {k: round(after[k] - before.get(k, 0.0), 4) for k in after}


def _present_and_record(engine, pattern, steps, records):
    """Present `pattern` for `steps` BRIEF steps and append one record to
    `records`. Reads ONLY already-existing engine state -- no engine or
    competition code is touched by this function."""
    engine.set_pattern(pattern)
    w_before = _snapshot_weights(engine)
    l2e_spike_order = []          # [(t_rel, 'L2Ej'), ...] in presentation-relative time
    l1i_fired_positions = []      # [(t_rel, [i, ...]), ...]
    l2i_spike_steps = []
    pre_inhibition_charge = []    # engine.l2_drive snapshot per step (pre-WTA)
    post_inhibition_charge = []   # engine.l2_charge snapshot per step (post-inhibition)

    for t_rel in range(steps):
        engine.step()
        for j in range(N_OUT):
            if engine.spiked[f'L2E{j}']:
                l2e_spike_order.append((t_rel, f'L2E{j}'))
        if engine.spiked['L2I']:
            l2i_spike_steps.append(t_rel)
        fired = [i for i in range(N_PIX) if engine.spiked[f'L1I{i}']]
        if fired:
            l1i_fired_positions.append((t_rel, fired))
        pre_inhibition_charge.append(dict(engine.l2_drive))
        post_inhibition_charge.append(dict(engine.l2_charge))

    w_after = _snapshot_weights(engine)
    story = engine.dynamic_state()['causal_story']

    first = l2e_spike_order[0] if l2e_spike_order else None
    second = next((s for s in l2e_spike_order if first and s[1] != first[1]), None)
    latency_margin = (second[0] - first[0]) if (first and second) else None

    receptive_fields = {f'L2E{j}': [round(w_after[f'ff{i}->{j}'], 3) for i in range(N_PIX)]
                        for j in range(N_OUT)}

    records.append(dict(
        presentation_id=story['presentation_id'],
        pattern=pattern,
        plasticity_frozen=engine.plasticity_frozen,
        first_l2e_spiker=first[1] if first else None,
        first_l2e_spike_t=first[0] if first else None,
        same_step_tie=story['same_step_tie'],
        all_l2e_spikes=l2e_spike_order,
        latency_margin_to_second=latency_margin,
        l2i_spike_steps=l2i_spike_steps,
        l2i_spike_count=len(l2i_spike_steps),
        l1i_fired_positions=l1i_fired_positions,
        pre_inhibition_charge=pre_inhibition_charge,
        post_inhibition_charge=post_inhibition_charge,
        receptive_fields=receptive_fields,
        weight_changes=_weight_deltas(w_before, w_after),
    ))


def run_diagnostic(seed, engine_kwargs=None, cycles=DEFAULT_CYCLES,
                   presentation_steps=PRESENTATION_STEPS,
                   consistency_reps=CONSISTENCY_REPS, engine=None):
    """Run the brief's equal-interleaved schedule for one seed. If `engine` is
    given, a deep copy of it is used (the original is never touched or
    stepped); otherwise a fresh engine is built from `engine_kwargs` (default
    DASHBOARD_PRESET). Returns dict(seed, live=[...], frozen=[...])."""
    if engine is not None:
        working = copy.deepcopy(engine)
    else:
        working = SimulationEngine(seed=seed, **(engine_kwargs or DASHBOARD_PRESET))

    live_records = []
    for _c in range(cycles):
        for pattern in CYCLE_ORDER:
            _present_and_record(working, pattern, presentation_steps, live_records)

    frozen_engine = copy.deepcopy(working)
    frozen_engine._set_plasticity_frozen(True)
    frozen_records = []
    for _r in range(consistency_reps):
        for pattern in CYCLE_ORDER:
            _present_and_record(frozen_engine, pattern, presentation_steps, frozen_records)

    return dict(seed=seed, live=live_records, frozen=frozen_records)


# ------------------------------------------------------------------- report
def _modal(values):
    """Most-common non-None value. Deterministic even on an exact count tie:
    `max(set(...), key=count)` (the original form) breaks ties by set
    iteration order, which depends on Python's per-process string hash
    randomization (PYTHONHASHSEED) -- two runs of the identical seed/cycles
    could report a different "owner" label on a genuine tie, purely from hash
    seed, with no change in the underlying spike counts. Sorting the tied
    candidates before picking removes that dependency; found and fixed during
    Phase 6 validation (col 1 at seed=1 has an exact 7-7 first-spiker tie
    between L2E3/L2E4 -- a real, reproducible tie in the data, not a bug in
    counting)."""
    non_none = [v for v in values if v is not None]
    if not non_none:
        return None
    counts = Counter(non_none)
    top = max(counts.values())
    return min(v for v, c in counts.items() if c == top)


def summarize(run) -> dict:
    """Per-seed report: per-pattern consistency/ambiguity/no-response,
    distinct owners, collisions, forgetting, silent/recruitable cells, L2I
    activity, L1I selectivity, and the frozen re-test's own consistency +
    zero-weight-drift sanity check. Computed purely from recorded data;
    touches no engine state."""
    live = run['live']
    by_pattern = {p: [r for r in live if r['pattern'] == p] for p in CYCLE_ORDER}

    per_pattern = {}
    modal_owner = {}
    for p, recs in by_pattern.items():
        firsts = [r['first_l2e_spiker'] for r in recs]
        n = len(firsts)
        no_resp = sum(1 for f in firsts if f is None)
        ties = sum(1 for r in recs if r['same_step_tie'])
        modal = _modal(firsts)
        non_none = [f for f in firsts if f is not None]
        consistency = (non_none.count(modal) / n) if (modal is not None and n) else 0.0
        modal_owner[p] = modal
        per_pattern[p] = dict(consistency=round(consistency, 3),
                              ambiguity_rate=round(ties / n, 3) if n else None,
                              no_response_rate=round(no_resp / n, 3) if n else None,
                              modal_owner=modal, n_presentations=n)

    # Forgetting: modal owner in the first half of this pattern's presentations
    # vs. the second half of the same run.
    forgetting = {}
    for p, recs in by_pattern.items():
        half = len(recs) // 2
        m1 = _modal([r['first_l2e_spiker'] for r in recs[:half]])
        m2 = _modal([r['first_l2e_spiker'] for r in recs[half:]])
        forgetting[p] = dict(first_half_owner=m1, second_half_owner=m2,
                             changed=bool(m1 and m2 and m1 != m2))

    owners = [o for o in modal_owner.values() if o is not None]
    distinct_owners = len(set(owners))
    collisions = {o: [p for p, m in modal_owner.items() if m == o]
                 for o in set(owners) if owners.count(o) > 1}

    ever_first = {r['first_l2e_spiker'] for r in live if r['first_l2e_spiker']}
    all_l2e = {f'L2E{j}' for j in range(N_OUT)}
    silent_cells = sorted(all_l2e - ever_first)
    recruitable_cells = sorted(ever_first - set(owners))

    l2i_counts = [r['l2i_spike_count'] for r in live]
    l2i_activity = dict(mean_per_presentation=round(stats.mean(l2i_counts), 3) if l2i_counts else 0.0,
                        total=sum(l2i_counts))

    all9 = 0
    any_fire_steps = 0
    for r in live:
        for _t, positions in r['l1i_fired_positions']:
            any_fire_steps += 1
            if len(positions) == N_PIX:
                all9 += 1
    l1i_all_nine_sync_rate = round(all9 / any_fire_steps, 3) if any_fire_steps else None

    frozen = run['frozen']
    frozen_weight_drift = any(abs(v) > 1e-9 for r in frozen for v in r['weight_changes'].values())
    frozen_by_pattern = {p: [r['first_l2e_spiker'] for r in frozen if r['pattern'] == p]
                         for p in CYCLE_ORDER}
    frozen_consistency = {}
    for p, vals in frozen_by_pattern.items():
        modal = _modal(vals)
        non_none = [v for v in vals if v is not None]
        frozen_consistency[p] = round(non_none.count(modal) / len(vals), 3) if (modal and vals) else 0.0

    return dict(seed=run['seed'],
               per_pattern=per_pattern,
               forgetting=forgetting,
               distinct_owners=distinct_owners,
               collisions=collisions,
               silent_cells=silent_cells,
               recruitable_cells=recruitable_cells,
               l2i_activity=l2i_activity,
               l1i_all_nine_sync_rate=l1i_all_nine_sync_rate,
               frozen_replay_zero_weight_drift=not frozen_weight_drift,
               frozen_first_responder_consistency=frozen_consistency)


def _print_report(summary):
    s = summary
    print(f"\n===== seed {s['seed']} =====")
    for p in CYCLE_ORDER:
        pp = s['per_pattern'][p]
        print(f"  {p:9s} owner={pp['modal_owner'] or '--':6s} "
             f"consistency={pp['consistency']:.2f} ambiguity={pp['ambiguity_rate']:.2f} "
             f"no_response={pp['no_response_rate']:.2f} (n={pp['n_presentations']})")
    print(f"  distinct_owners={s['distinct_owners']}/4  collisions={s['collisions']}")
    print(f"  silent_cells={s['silent_cells']}  recruitable_cells={s['recruitable_cells']}")
    print(f"  forgetting={ {p: v['changed'] for p, v in s['forgetting'].items()} }")
    print(f"  L2I activity: {s['l2i_activity']}")
    print(f"  L1I all-nine-sync rate: {s['l1i_all_nine_sync_rate']}")
    print(f"  frozen replay zero-weight-drift: {s['frozen_replay_zero_weight_drift']}  "
         f"frozen first-responder consistency: {s['frozen_first_responder_consistency']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seeds', nargs='+', type=int, default=[1, 2, 3])
    ap.add_argument('--cycles', type=int, default=DEFAULT_CYCLES)
    ap.add_argument('--presentation-steps', type=int, default=PRESENTATION_STEPS)
    args = ap.parse_args()

    summaries = []
    for seed in args.seeds:
        run = run_diagnostic(seed, cycles=args.cycles, presentation_steps=args.presentation_steps)
        summary = summarize(run)
        _print_report(summary)
        summaries.append(summary)

    print(f"\n===== MEAN over {len(args.seeds)} seeds =====")
    mean_distinct = stats.mean(s['distinct_owners'] for s in summaries)
    mean_consistency = {p: round(stats.mean(s['per_pattern'][p]['consistency'] for s in summaries), 3)
                        for p in CYCLE_ORDER}
    print(f"  distinct_owners = {mean_distinct:.2f}/4")
    print(f"  per-pattern consistency = {mean_consistency}")


if __name__ == "__main__":
    main()
