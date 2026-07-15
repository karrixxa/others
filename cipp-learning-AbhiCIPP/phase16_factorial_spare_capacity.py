"""
Phase 16 -- adaptive-threshold x developmental-protection factorial, plus a
genuine spare-capacity challenge (july14-integration). MEASUREMENT ONLY:
both mechanisms already exist (Phase 10, Phase 15); this phase adds no new
neural rule, changes no default, tunes nothing per seed, does not touch
distance/leak/initialization/L1I. Every condition uses DASHBOARD_PRESET's own
legacy distance configuration (distance_weighting=True,
legacy_distance_compat=True) and each mechanism's OWN already-documented
default reference value (adaptive_threshold's delta_threshold_frac=0.05/
tau_threshold=25.0; loser_depression_protection's ca_ref=0.02) -- toggling
only the two boolean flags themselves.

Conditions:
  A: adaptive_threshold=False, loser_depression_protection=False
  B: adaptive_threshold=True,  loser_depression_protection=False
  C: adaptive_threshold=False, loser_depression_protection=True
  D: adaptive_threshold=True,  loser_depression_protection=True

Grid: weight seeds 1-5 x topology seeds 1-3 (15 combinations) x 2 scenarios
x 4 conditions = 120 runs.
  1. 20-step equal interleaving, 40 rotations (diagnostic_schedule precedent).
  2. Long row-hold (600 steps) then column switch (200 steps).

Spare-capacity challenge (extends each condition's interleaved-40 run, since
"train the original four patterns equally" IS that scenario):
  1. (already done -- the interleaved-40 training itself)
  2. Freeze; re-present the 4 trained patterns (4 reps each) and record
     owners/consistency (summarize()-style, reused directly).
  3. Unfreeze; present one DECLARED novel pattern -- 'row 0', one of the
     existing held-out PROBES (never in the training rotation) -- repeatedly
     WITH PLASTICITY LIVE (never present_probe(), which freezes; instead
     directly sets input_vec + calls the engine's own _start_presentation,
     the same public bookkeeping set_pattern()/present_probe() already use,
     so causal_story/presentation_log track it exactly like a real
     presentation -- no engine code changed).
  4. Identify the novel pattern's eventual (modal) first-responder and look
     up ITS pre-novel-exposure status (active/quiet/unrecruited), recorded
     from step 2 -- never assumed.
  5. Freeze again; re-present the original 4 and recompute owners/consistency.
  6. Report recruitment latency, novel-pattern consistency, old-owner
     retention, collisions, and whether an existing tyrant captured the
     novel pattern. NO software rule requires exactly N quiet neurons; a
     silent neuron is only called "recruitable" here if it actually becomes
     the novel pattern's modal owner in this exact challenge.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.simulation import SimulationEngine, PATTERNS, PROBES, N_OUT, N_PIX  # noqa: E402
from backend.presets import DASHBOARD_PRESET  # noqa: E402
from diagnostic_schedule import CYCLE_ORDER, PRESENTATION_STEPS, _present_and_record, summarize  # noqa: E402

WEIGHT_SEEDS = [1, 2, 3, 4, 5]
TOPOLOGY_SEEDS = [1, 2, 3]

NOVEL_PATTERN = 'row 0'          # a declared, existing held-out PROBE -- never trained
NOVEL_EXPOSURE_REPS = 10         # repeated live-plasticity exposures -- single documented constant
FROZEN_CONSISTENCY_REPS = 4      # matches diagnostic_schedule.CONSISTENCY_REPS precedent

CONDITIONS = {
    'A_adaptive_off_protection_off': dict(adaptive_threshold=False, loser_depression_protection=False),
    'B_adaptive_on_protection_off': dict(adaptive_threshold=True, loser_depression_protection=False),
    'C_adaptive_off_protection_on': dict(adaptive_threshold=False, loser_depression_protection=True),
    'D_adaptive_on_protection_on': dict(adaptive_threshold=True, loser_depression_protection=True),
}


def build_engine(condition_name, weight_seed, topology_seed):
    kw = {**DASHBOARD_PRESET, **CONDITIONS[condition_name]}
    kw['seed'] = weight_seed
    kw['topology_seed'] = topology_seed
    return SimulationEngine(**kw)


# --------------------------------------------------------------- instrumentation
class DepressionTracer:
    """Same technique as Phase 15's tracer: wraps apply_delayed_inhibition to
    record (maturity, |delta|) per depression event, and step() to record
    each L2E's first-ever spike timestep -- read-only observation of
    already-computed engine state, no engine code touched."""

    def __init__(self, engine):
        self.engine = engine
        self.depression_events = []
        self.first_spike_t = {}
        for j, n in enumerate(engine.l2.excitatory_neurons):
            self._patch(j, n)
        self._patch_step()

    def _patch(self, j, n):
        orig = n.apply_delayed_inhibition
        nid = f'L2E{j}'

        def wrapped(magnitude):
            w_before = n._weights_array.copy()
            out = orig(magnitude)
            if out['applied'] and out['depressed_indices']:
                delta_abs = float(np.mean(np.abs(w_before[out['depressed_indices']]
                                                 - n._weights_array[out['depressed_indices']])))
                self.depression_events.append(dict(neuron=nid, maturity=out['maturity'], delta_abs=delta_abs))
            return out
        n.apply_delayed_inhibition = wrapped

    def _patch_step(self):
        engine = self.engine
        orig = engine.step

        def wrapped():
            result = orig()
            t_done = engine.timestep - 1
            for j in range(N_OUT):
                nid = f'L2E{j}'
                if engine.spiked.get(nid) and nid not in self.first_spike_t:
                    self.first_spike_t[nid] = t_done
            return result
        engine.step = wrapped


def _maturity_bucket(m):
    if m < 0.25:
        return '0.00-0.25'
    if m < 0.5:
        return '0.25-0.50'
    if m < 0.75:
        return '0.50-0.75'
    return '0.75-1.00'


# ------------------------------------------------------------------- scenarios
def run_long_hold_switch(condition_name, weight_seed, topology_seed, row1_steps=600, col1_steps=200):
    engine = build_engine(condition_name, weight_seed, topology_seed)
    tracer = DepressionTracer(engine)
    engine.set_pattern('row 1')
    for _ in range(row1_steps):
        engine.step()
    engine.set_pattern('col 1')
    for _ in range(col1_steps):
        engine.step()
    return engine, tracer


def run_interleaved_40(condition_name, weight_seed, topology_seed, cycles=40,
                       presentation_steps=PRESENTATION_STEPS):
    engine = build_engine(condition_name, weight_seed, topology_seed)
    tracer = DepressionTracer(engine)
    presentation_records = []
    for _c in range(cycles):
        for pattern in CYCLE_ORDER:
            _present_and_record(engine, pattern, presentation_steps, presentation_records)
    return engine, tracer, presentation_records


# --------------------------------------------------------------------- analysis
def analyze_run(condition_name, weight_seed, topology_seed, scenario, engine, tracer):
    status = {f'L2E{j}': engine._l2e_status(j)['status'] for j in range(N_OUT)}
    spikes_total = {f'L2E{j}': engine._neuron_total_spikes.get(f'L2E{j}', 0) for j in range(N_OUT)}
    total_spikes = sum(spikes_total.values())
    tyrant = max(spikes_total, key=spikes_total.get) if total_spikes > 0 else None
    tyrant_share = (spikes_total[tyrant] / total_spikes) if tyrant else None

    by_bucket = defaultdict(list)
    for ev in tracer.depression_events:
        by_bucket[_maturity_bucket(ev['maturity'])].append(ev['delta_abs'])
    depression_by_maturity = {b: dict(n=len(v), mean_delta_abs=round(float(np.mean(v)), 4))
                              for b, v in by_bucket.items()}

    tyrant_weights = None
    tyrant_union_mean = tyrant_other_mean = None
    if tyrant is not None:
        j = int(tyrant[3:])
        n = engine.l2.excitatory_neurons[j]
        tyrant_weights = {i: round(float(n._weights_array[i]), 2) for i in range(N_PIX)}
        row1_active = [i for i, v in enumerate(PATTERNS['row 1']) if v]
        col1_active = [i for i, v in enumerate(PATTERNS['col 1']) if v]
        union_pixels = sorted(set(row1_active) | set(col1_active))
        other_pixels = [i for i in range(N_PIX) if i not in union_pixels]
        tyrant_union_mean = float(np.mean([tyrant_weights[i] for i in union_pixels]))
        tyrant_other_mean = float(np.mean([tyrant_weights[i] for i in other_pixels])) if other_pixels else None

    at = engine.dynamic_state()['adaptive_threshold']
    adaptive_trajectory = dict(enabled=at['enabled'], final_state=at['state'],
                               final_effective_threshold=at['effective_threshold'])

    return dict(
        condition=condition_name, weight_seed=weight_seed, topology_seed=topology_seed, scenario=scenario,
        status=status,
        active_count=sum(1 for s in status.values() if s == 'active'),
        quiet_count=sum(1 for s in status.values() if s == 'quiet'),
        unrecruited_count=sum(1 for s in status.values() if s == 'unrecruited'),
        never_fired_neurons=[nid for nid, s in status.items() if s == 'unrecruited'],
        first_spike_latency={nid: tracer.first_spike_t.get(nid) for nid in [f'L2E{j}' for j in range(N_OUT)]},
        tyrant=tyrant, tyrant_share=round(tyrant_share, 4) if tyrant_share is not None else None,
        tyrant_weights=tyrant_weights,
        tyrant_union_mean_weight=round(tyrant_union_mean, 2) if tyrant_union_mean is not None else None,
        tyrant_other_mean_weight=round(tyrant_other_mean, 2) if tyrant_other_mean is not None else None,
        depression_by_maturity=depression_by_maturity,
        adaptive_threshold=adaptive_trajectory,
    )


def analyze_interleaved(condition_name, weight_seed, topology_seed, engine, tracer, presentation_records):
    base = analyze_run(condition_name, weight_seed, topology_seed, 'interleaved_40', engine, tracer)
    s = summarize(dict(seed=weight_seed, live=presentation_records, frozen=[]))
    base['distinct_owners'] = s['distinct_owners']
    base['per_pattern_consistency'] = {p: pp['consistency'] for p, pp in s['per_pattern'].items()}
    base['modal_owner'] = {p: pp['modal_owner'] for p, pp in s['per_pattern'].items()}
    base['collisions'] = s['collisions']
    base['forgetting'] = {p: f['changed'] for p, f in s['forgetting'].items()}
    base['silent_cells'] = s['silent_cells']
    base['recruitable_cells_old_definition'] = s['recruitable_cells']
    ambiguity_rates = [pp['ambiguity_rate'] for pp in s['per_pattern'].values()]
    base['mean_ambiguity_rate'] = round(float(np.mean(ambiguity_rates)), 4) if ambiguity_rates else None
    return base


# ------------------------------------------------------------ spare capacity
def _present_novel_and_record(engine, name, steps, records):
    """Present a held-out PROBE by name, WITH PLASTICITY LIVE (never
    present_probe(), which freezes) -- mirrors diagnostic_schedule.
    _present_and_record's exact recording logic but drives the probe vector
    directly (set_pattern() rejects any name not in PATTERNS), using only
    existing public engine mechanics (input_vec + _start_presentation, the
    same bookkeeping set_pattern()/present_probe() already call)."""
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
    records.append(dict(
        pattern=name, first_l2e_spiker=first[1] if first else None,
        first_l2e_spike_t=first[0] if first else None,
        same_step_tie=story['same_step_tie'],
        all_l2e_spikes=l2e_spike_order,
    ))


def _frozen_reevaluate(engine, weight_seed):
    """Freeze, present the 4 trained patterns FROZEN_CONSISTENCY_REPS times
    each (diagnostic_schedule._present_and_record, reused verbatim), unfreeze,
    and return the per-pattern modal-owner/consistency summary."""
    engine._set_plasticity_frozen(True)
    records = []
    for _r in range(FROZEN_CONSISTENCY_REPS):
        for pattern in CYCLE_ORDER:
            _present_and_record(engine, pattern, PRESENTATION_STEPS, records)
    engine._set_plasticity_frozen(False)
    s = summarize(dict(seed=weight_seed, live=records, frozen=[]))
    return {p: dict(modal_owner=pp['modal_owner'], consistency=pp['consistency'])
           for p, pp in s['per_pattern'].items()}


def spare_capacity_challenge(condition_name, weight_seed, topology_seed, trained_engine):
    """Steps 2-6 of the spare-capacity protocol, continuing from an
    ALREADY-TRAINED engine (the interleaved-40 run IS "train the original
    four patterns equally", step 1)."""
    engine = trained_engine
    pre_status = {f'L2E{j}': engine._l2e_status(j)['status'] for j in range(N_OUT)}

    pre_novel = _frozen_reevaluate(engine, weight_seed)

    novel_records = []
    for _r in range(NOVEL_EXPOSURE_REPS):
        _present_novel_and_record(engine, NOVEL_PATTERN, PRESENTATION_STEPS, novel_records)

    firsts = [r['first_l2e_spiker'] for r in novel_records]
    non_none = [f for f in firsts if f is not None]
    novel_modal_owner = None
    novel_consistency = None
    if non_none:
        from collections import Counter
        counts = Counter(non_none)
        top = max(counts.values())
        novel_modal_owner = min(v for v, c in counts.items() if c == top)
        novel_consistency = round(non_none.count(novel_modal_owner) / len(firsts), 4)

    # Recruitment latency: first rep index (and absolute step within that
    # rep) that produced ANY response, and the first rep index whose
    # first_l2e_spiker equals the eventual modal owner (when it "locked in").
    first_response_rep = next((i for i, r in enumerate(novel_records) if r['first_l2e_spiker']), None)
    first_response_t = (novel_records[first_response_rep]['first_l2e_spike_t']
                        if first_response_rep is not None else None)
    locked_in_rep = None
    if novel_modal_owner is not None:
        locked_in_rep = next((i for i, r in enumerate(novel_records)
                             if r['first_l2e_spiker'] == novel_modal_owner), None)

    responder_pre_novel_status = (pre_status.get(novel_modal_owner) if novel_modal_owner else None)

    post_novel = _frozen_reevaluate(engine, weight_seed)

    retention = {p: (pre_novel[p]['modal_owner'] == post_novel[p]['modal_owner']) for p in pre_novel}
    tyrant_captured_novel = (novel_modal_owner is not None
                            and novel_modal_owner in {v['modal_owner'] for v in pre_novel.values()})

    return dict(
        condition=condition_name, weight_seed=weight_seed, topology_seed=topology_seed,
        pre_novel_owners=pre_novel, post_novel_owners=post_novel, retention=retention,
        novel_pattern=NOVEL_PATTERN, novel_modal_owner=novel_modal_owner,
        novel_consistency=novel_consistency,
        responder_pre_novel_status=responder_pre_novel_status,
        first_response_rep=first_response_rep, first_response_t=first_response_t,
        locked_in_rep=locked_in_rep,
        tyrant_captured_novel=tyrant_captured_novel,
        collisions_with_original_four=[p for p, v in pre_novel.items() if v['modal_owner'] == novel_modal_owner],
    )


# ------------------------------------------------------------------------ main
def main():
    factorial_results = []
    spare_capacity_results = []
    for condition_name in CONDITIONS:
        for ws in WEIGHT_SEEDS:
            for ts in TOPOLOGY_SEEDS:
                engine_lh, tracer_lh = run_long_hold_switch(condition_name, ws, ts)
                factorial_results.append(analyze_run(condition_name, ws, ts, 'long_hold_switch', engine_lh, tracer_lh))

                engine_il, tracer_il, pres = run_interleaved_40(condition_name, ws, ts)
                factorial_results.append(analyze_interleaved(condition_name, ws, ts, engine_il, tracer_il, pres))

                spare_capacity_results.append(
                    spare_capacity_challenge(condition_name, ws, ts, engine_il))

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'phase16_factorial_spare_capacity_summary.json'), 'w') as f:
        json.dump(dict(weight_seeds=WEIGHT_SEEDS, topology_seeds=TOPOLOGY_SEEDS,
                       novel_pattern=NOVEL_PATTERN, novel_exposure_reps=NOVEL_EXPOSURE_REPS,
                       factorial_results=factorial_results,
                       spare_capacity_results=spare_capacity_results), f, indent=2, default=str)
    print(f"factorial runs: {len(factorial_results)}  spare-capacity runs: {len(spare_capacity_results)}")


if __name__ == "__main__":
    main()
