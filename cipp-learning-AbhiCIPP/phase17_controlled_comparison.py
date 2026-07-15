"""
Phase 17 Parts 3-5 -- controlled comparison of pre-trained vs. learned L2I
recruitment, plus the genuine spare-capacity challenge (july14-integration,
LPS Lecture 14 architecture mapping). MEASUREMENT ONLY: the mechanism under
test (pretrained_l2i_recruitment) is implemented in backend/simulation.py/
neuron_flexible.py; this script only compares it against the learned
baseline. No new neural rule is added here; nothing is tuned per seed.

Configs (identical weight/topology seeds, everything else DASHBOARD_PRESET):
  A: current learned L2I recruitment (pretrained_l2i_recruitment=False)
  B: fixed/pre-trained single-spike L2I recruitment (=True)

Grid: weight seeds 1-5 x topology seeds 1-3 (15 combinations) x 3 schedules:
  1. Equal interleaving: row 1 -> col 1 -> diag \\ -> diag /, 20 steps each,
     40 rotations (diagnostic_schedule precedent).
  2. Long hold/switch: row 1 for 600 steps -> col 1 for 200 steps.
  3. Short hold/switch: row 1 for 20 steps -> col 1 for 20 steps.

Spare-capacity challenge extends each config/seed's own equal-interleaving
run (schedule 1 IS "train the original four patterns equally"):
  1. (the equal-interleaving training itself)
  2. Freeze; re-present the original four (FROZEN_CONSISTENCY_REPS reps
     each) and record first responders/ties/consistency/later responses.
  3. Record every L2E's PRIOR status (active/quiet/never-fired == this
     repo's existing rf_status 'unrecruited').
  4. Unfreeze; present ONE declared novel pattern ('row 0', an existing
     held-out PROBES vector) NOVEL_EXPOSURE_REPS times, WITH PLASTICITY
     LIVE, under a FIXED schedule identical for A and B (never
     present_probe(), which freezes -- instead directly drives
     input_vec + _start_presentation, the same public bookkeeping
     set_pattern()/present_probe() already use; the pattern's NAME is used
     only for that bookkeeping/dict lookup, never read by a learning rule
     -- see test_pretrained_l2i_recruitment.py's harness-discipline test).
  5. Identify the eventual (modal) responder and its PRE-novel-exposure
     status.
  6. Freeze again; re-evaluate the original four AND the novel pattern.
  7. Report recruitment latency, novel-pattern consistency, old-owner
     retention, collisions, and whether an existing tyrant captured the
     novel pattern.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.simulation import SimulationEngine, PATTERNS, PROBES, N_OUT, N_PIX  # noqa: E402
from backend.presets import DASHBOARD_PRESET  # noqa: E402
from diagnostic_schedule import CYCLE_ORDER, PRESENTATION_STEPS, _present_and_record, summarize  # noqa: E402

WEIGHT_SEEDS = [1, 2, 3, 4, 5]
TOPOLOGY_SEEDS = [1, 2, 3]

NOVEL_PATTERN = 'row 0'
NOVEL_EXPOSURE_REPS = 10
FROZEN_CONSISTENCY_REPS = 4

CONFIGS = {
    'A_learned_recruitment': dict(pretrained_l2i_recruitment=False),
    'B_pretrained_recruitment': dict(pretrained_l2i_recruitment=True),
}


def build_engine(condition_name, weight_seed, topology_seed):
    kw = {**DASHBOARD_PRESET, **CONFIGS[condition_name]}
    kw['seed'] = weight_seed
    kw['topology_seed'] = topology_seed
    return SimulationEngine(**kw)


# --------------------------------------------------------------- instrumentation
class L2ITracer:
    """Wraps step() to record per-step L2E/L2I spike counts (for one-hot/
    no-response rate and per-neuron first-spike timestep), and the engine's
    own _deliver_scheduled_l2_inhibition to count deliveries exhaustively
    (the engine's own _l2_inhibition_log is a bounded deque(maxlen=400) --
    see Phase 13b's finding -- so this tracer, not that log's length, is the
    correct source for a full-run delivery count). Read-only observation of
    already-computed engine state; no engine code touched."""

    def __init__(self, engine):
        self.engine = engine
        self.first_spike_t = {}
        self.step_l2e_counts = []     # per-step count of L2E that spiked THIS step
        self.delivery_count = 0
        self.l2i_weight_checkpoints = []
        self._patch_step()
        self._patch_deliver()

    def _patch_step(self):
        engine = self.engine
        orig = engine.step

        def wrapped():
            result = orig()
            t_done = engine.timestep - 1
            count = 0
            for j in range(N_OUT):
                nid = f'L2E{j}'
                if engine.spiked.get(nid):
                    count += 1
                    if nid not in self.first_spike_t:
                        self.first_spike_t[nid] = t_done
            self.step_l2e_counts.append(count)
            return result
        engine.step = wrapped

    def _patch_deliver(self):
        engine = self.engine
        orig = engine._deliver_scheduled_l2_inhibition

        def wrapped(t):
            due = [rec for rec in engine._l2i_pending if rec['deliver_at'] <= t]
            self.delivery_count += len(due)
            return orig(t)
        engine._deliver_scheduled_l2_inhibition = wrapped

    def checkpoint_l2i_weights(self, label, t):
        w = self.engine.l2.inhibitory_neuron._weights_array.copy()
        self.l2i_weight_checkpoints.append(dict(label=label, t=t,
                                                 weights=[round(float(x), 4) for x in w]))


def _center_vs_pattern_weights(engine, nid):
    j = int(nid[3:])
    n = engine.l2.excitatory_neurons[j]
    w = {i: round(float(n._weights_array[i]), 2) for i in range(N_PIX)}
    row1_active = [i for i, v in enumerate(PATTERNS['row 1']) if v]
    col1_active = [i for i, v in enumerate(PATTERNS['col 1']) if v]
    union_pixels = sorted(set(row1_active) | set(col1_active))
    other_pixels = [i for i in range(N_PIX) if i not in union_pixels]
    return dict(weights=w, center_weight=w[4],
               union_mean=round(float(np.mean([w[i] for i in union_pixels])), 2),
               other_mean=round(float(np.mean([w[i] for i in other_pixels])), 2) if other_pixels else None)


# ------------------------------------------------------------------- scenarios
def run_equal_interleaving(condition_name, weight_seed, topology_seed, cycles=40,
                          presentation_steps=PRESENTATION_STEPS):
    engine = build_engine(condition_name, weight_seed, topology_seed)
    tracer = L2ITracer(engine)
    tracer.checkpoint_l2i_weights('start', 0)
    presentation_records = []
    total = cycles * len(CYCLE_ORDER)
    done = 0
    mid_done = False
    for _c in range(cycles):
        for pattern in CYCLE_ORDER:
            _present_and_record(engine, pattern, presentation_steps, presentation_records)
            done += 1
            if not mid_done and done >= total // 2:
                tracer.checkpoint_l2i_weights('mid', engine.timestep)
                mid_done = True
    tracer.checkpoint_l2i_weights('end', engine.timestep)
    return engine, tracer, presentation_records


def run_hold_switch(condition_name, weight_seed, topology_seed, row1_steps, col1_steps):
    engine = build_engine(condition_name, weight_seed, topology_seed)
    tracer = L2ITracer(engine)
    tracer.checkpoint_l2i_weights('start', 0)
    engine.set_pattern('row 1')
    for _ in range(row1_steps):
        engine.step()
    tracer.checkpoint_l2i_weights('mid', engine.timestep)
    engine.set_pattern('col 1')
    for _ in range(col1_steps):
        engine.step()
    tracer.checkpoint_l2i_weights('end', engine.timestep)
    return engine, tracer


# --------------------------------------------------------------------- analysis
def analyze_common(condition_name, weight_seed, topology_seed, scenario, engine, tracer):
    status = {f'L2E{j}': engine._l2e_status(j)['status'] for j in range(N_OUT)}
    spikes_total = {f'L2E{j}': engine._neuron_total_spikes.get(f'L2E{j}', 0) for j in range(N_OUT)}
    total_spikes = sum(spikes_total.values())
    tyrant = max(spikes_total, key=spikes_total.get) if total_spikes > 0 else None
    tyrant_share = (spikes_total[tyrant] / total_spikes) if tyrant else None

    counts = tracer.step_l2e_counts
    n_steps = len(counts)
    one_hot_rate = round(sum(1 for c in counts if c == 1) / n_steps, 4) if n_steps else None
    no_response_rate = round(sum(1 for c in counts if c == 0) / n_steps, 4) if n_steps else None
    multi_rate = round(sum(1 for c in counts if c > 1) / n_steps, 4) if n_steps else None

    l2i_firing_rate = round(engine._neuron_total_spikes.get('L2I', 0) / n_steps, 4) if n_steps else None

    tyrant_rf = _center_vs_pattern_weights(engine, tyrant) if tyrant else None

    return dict(
        condition=condition_name, weight_seed=weight_seed, topology_seed=topology_seed, scenario=scenario,
        status=status,
        active_count=sum(1 for s in status.values() if s == 'active'),
        quiet_count=sum(1 for s in status.values() if s == 'quiet'),
        never_fired_count=sum(1 for s in status.values() if s == 'unrecruited'),
        never_fired_neurons=[nid for nid, s in status.items() if s == 'unrecruited'],
        first_spike_latency={nid: tracer.first_spike_t.get(nid) for nid in [f'L2E{j}' for j in range(N_OUT)]},
        one_hot_response_rate=one_hot_rate, no_response_rate=no_response_rate,
        multi_firer_rate=multi_rate,
        tyrant=tyrant, tyrant_share=round(tyrant_share, 4) if tyrant_share is not None else None,
        tyrant_receptive_field=tyrant_rf,
        l2i_firing_rate=l2i_firing_rate,
        l2i_delivery_count=tracer.delivery_count,
        l2i_weight_checkpoints=tracer.l2i_weight_checkpoints,
    )


def analyze_interleaved(condition_name, weight_seed, topology_seed, engine, tracer, presentation_records):
    base = analyze_common(condition_name, weight_seed, topology_seed, 'equal_interleaving', engine, tracer)
    s = summarize(dict(seed=weight_seed, live=presentation_records, frozen=[]))
    later_counts = [len(r['all_l2e_spikes']) - 1 for r in presentation_records if r['all_l2e_spikes']]
    latency_margins = [r['latency_margin_to_second'] for r in presentation_records
                       if r['latency_margin_to_second'] is not None]
    base['distinct_owners'] = s['distinct_owners']
    base['per_pattern_consistency'] = {p: pp['consistency'] for p, pp in s['per_pattern'].items()}
    base['modal_owner'] = {p: pp['modal_owner'] for p, pp in s['per_pattern'].items()}
    base['collisions'] = s['collisions']
    base['forgetting'] = {p: f['changed'] for p, f in s['forgetting'].items()}
    base['mean_ambiguity_rate'] = round(float(np.mean([pp['ambiguity_rate'] for pp in s['per_pattern'].values()])), 4)
    base['mean_later_responses'] = round(float(np.mean(later_counts)), 3) if later_counts else 0.0
    base['mean_latency_to_second_response'] = round(float(np.mean(latency_margins)), 3) if latency_margins else None
    return base


# ------------------------------------------------------------ spare capacity
def _present_novel_and_record(engine, name, steps, records):
    """Present a held-out PROBE by name, WITH PLASTICITY LIVE. The name is
    used only to look up the pixel vector and for presentation bookkeeping
    (input_vec/current_pattern/_start_presentation) -- evaluation metadata
    only, never read by any learning rule (verified directly, see
    test_pretrained_l2i_recruitment.py)."""
    engine._cancel_probe_if_active()
    engine.input_vec = np.array(PROBES[name], dtype=float)
    engine.current_pattern = name
    engine._start_presentation(name, 'novel')

    l2e_spike_order = []
    for t_rel in range(steps):
        engine.step()
        for j in range(N_OUT):
            if engine.spiked[f'L2E{j}']:
                l2e_spike_order.append((t_rel, f'L2E{j}'))
    story = engine.dynamic_state()['causal_story']
    first = l2e_spike_order[0] if l2e_spike_order else None
    records.append(dict(pattern=name, first_l2e_spiker=first[1] if first else None,
                        first_l2e_spike_t=first[0] if first else None,
                        same_step_tie=story['same_step_tie'], all_l2e_spikes=l2e_spike_order))


def _frozen_reevaluate(engine, weight_seed, patterns=CYCLE_ORDER, reps=FROZEN_CONSISTENCY_REPS):
    engine._set_plasticity_frozen(True)
    records = []
    for _r in range(reps):
        for pattern in patterns:
            _present_and_record(engine, pattern, PRESENTATION_STEPS, records)
    engine._set_plasticity_frozen(False)
    s = summarize(dict(seed=weight_seed, live=records, frozen=[]))
    return {p: dict(modal_owner=pp['modal_owner'], consistency=pp['consistency'])
           for p, pp in s['per_pattern'].items()}


def spare_capacity_challenge(condition_name, weight_seed, topology_seed, trained_engine):
    engine = trained_engine
    pre_status = {f'L2E{j}': engine._l2e_status(j)['status'] for j in range(N_OUT)}

    pre_novel = _frozen_reevaluate(engine, weight_seed)

    novel_records = []
    for _r in range(NOVEL_EXPOSURE_REPS):
        _present_novel_and_record(engine, NOVEL_PATTERN, PRESENTATION_STEPS, novel_records)

    firsts = [r['first_l2e_spiker'] for r in novel_records]
    non_none = [f for f in firsts if f is not None]
    novel_modal_owner = novel_consistency = None
    if non_none:
        counts = Counter(non_none)
        top = max(counts.values())
        novel_modal_owner = min(v for v, c in counts.items() if c == top)
        novel_consistency = round(non_none.count(novel_modal_owner) / len(firsts), 4)

    first_response_rep = next((i for i, r in enumerate(novel_records) if r['first_l2e_spiker']), None)
    first_response_t = (novel_records[first_response_rep]['first_l2e_spike_t']
                        if first_response_rep is not None else None)
    locked_in_rep = (next((i for i, r in enumerate(novel_records) if r['first_l2e_spiker'] == novel_modal_owner), None)
                    if novel_modal_owner is not None else None)

    responder_pre_novel_status = pre_status.get(novel_modal_owner) if novel_modal_owner else None

    # Post-novel re-evaluation covers the original four AND the novel
    # pattern itself (per instruction step 8) -- the four via the same
    # frozen re-test helper, the novel pattern via its own dedicated probe
    # presentation right below (a plain CYCLE_ORDER pattern name and a
    # held-out PROBES name go through different presentation helpers in
    # this codebase, so they are evaluated separately, then combined).
    post_novel = _frozen_reevaluate(engine, weight_seed, patterns=CYCLE_ORDER, reps=FROZEN_CONSISTENCY_REPS)
    novel_post_records = []
    for _r in range(FROZEN_CONSISTENCY_REPS):
        _present_novel_and_record(engine, NOVEL_PATTERN, PRESENTATION_STEPS, novel_post_records)
    engine._set_plasticity_frozen(False)
    post_novel_firsts = [r['first_l2e_spiker'] for r in novel_post_records if r['first_l2e_spiker']]
    post_novel_owner = Counter(post_novel_firsts).most_common(1)[0][0] if post_novel_firsts else None
    post_novel_consistency = (round(post_novel_firsts.count(post_novel_owner) / len(novel_post_records), 4)
                              if post_novel_firsts else None)

    retention = {p: (pre_novel[p]['modal_owner'] == post_novel[p]['modal_owner']) for p in pre_novel}
    tyrant_captured_novel = (novel_modal_owner is not None
                            and novel_modal_owner in {v['modal_owner'] for v in pre_novel.values()})

    return dict(
        condition=condition_name, weight_seed=weight_seed, topology_seed=topology_seed,
        pre_novel_owners=pre_novel, post_novel_owners=post_novel, retention=retention,
        novel_pattern=NOVEL_PATTERN, novel_modal_owner=novel_modal_owner,
        novel_consistency=novel_consistency,
        post_novel_owner=post_novel_owner, post_novel_consistency=post_novel_consistency,
        responder_pre_novel_status=responder_pre_novel_status,
        first_response_rep=first_response_rep, first_response_t=first_response_t,
        locked_in_rep=locked_in_rep,
        tyrant_captured_novel=tyrant_captured_novel,
        collisions_with_original_four=[p for p, v in pre_novel.items() if v['modal_owner'] == novel_modal_owner],
    )


# ------------------------------------------------------------------------ main
def main():
    grid_results = []
    spare_capacity_results = []
    for condition_name in CONFIGS:
        for ws in WEIGHT_SEEDS:
            for ts in TOPOLOGY_SEEDS:
                e_short, t_short = run_hold_switch(condition_name, ws, ts, 20, 20)
                grid_results.append(analyze_common(condition_name, ws, ts, 'short_hold_switch', e_short, t_short))

                e_long, t_long = run_hold_switch(condition_name, ws, ts, 600, 200)
                grid_results.append(analyze_common(condition_name, ws, ts, 'long_hold_switch', e_long, t_long))

                e_il, t_il, pres = run_equal_interleaving(condition_name, ws, ts)
                grid_results.append(analyze_interleaved(condition_name, ws, ts, e_il, t_il, pres))

                spare_capacity_results.append(spare_capacity_challenge(condition_name, ws, ts, e_il))

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'phase17_controlled_comparison_summary.json'), 'w') as f:
        json.dump(dict(weight_seeds=WEIGHT_SEEDS, topology_seeds=TOPOLOGY_SEEDS,
                       novel_pattern=NOVEL_PATTERN, novel_exposure_reps=NOVEL_EXPOSURE_REPS,
                       grid_results=grid_results,
                       spare_capacity_results=spare_capacity_results), f, indent=2, default=str)
    print(f"grid runs: {len(grid_results)}  spare-capacity runs: {len(spare_capacity_results)}")


if __name__ == "__main__":
    main()
