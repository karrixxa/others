"""
Dashboard behavior diagnostic (MEASUREMENT ONLY -- per explicit user
instruction, no neural dynamics changed, no parameter tuned).

Reproduces the reported dashboard behavior ("only 3 neurons are actively
participating with a tyrant, unsure as to why") and instruments every L2E
feedforward weight delta with a directly-recorded cause, never an inference:

  self_spike_exact_fe   -- this neuron's OWN fire() -> SignedSpikeRule.on_fire,
                            routed through exact_local_free_energy_update
                            because structural_free_energy is on (dashboard
                            default). Recorded straight from the wrapped
                            Neuron.fire() call (v_pre captured before, weight
                            array diffed before/after).
  l2i_loser_depression  -- Neuron.apply_delayed_inhibition's structural
                            depression branch (loser_depression=True,
                            dashboard default), recorded straight from that
                            method's own returned diagnostic dict (v_pre,
                            theta, p_loss, depressed_indices, weights_before/
                            after) -- nothing here is re-derived.
  homeostasis           -- Neuron._homeostatic_scaling; wrapped defensively,
                            expected to be silent since homeostasis=False in
                            every config below.
  manual_edit           -- SimulationEngine.set_feedforward_weight; wrapped
                            defensively, expected to be silent (no manual RF
                            edits occur in this scripted reproduction).
  other                 -- any residual delta not attributed to one of the
                            above (a genuine finding if non-empty).

For every recorded delta: timestep, pattern, neuron, whether that neuron
itself physically spiked this step, cause, L2I delivery source/time (the
scheduled delivery record's own fire_t/contributors, when the cause is
l2i_loser_depression), this neuron's V_pre/threshold/effective_threshold/
p_loss, the active input pixel indices this step, and weight before/delta/
after for the specific pixel afferent that moved.

Also verifies the receptive-field UI path (topology()'s serialized synapse
weights) is byte-identical to the backend's own _all_weights()/raw weight
array -- not merely "close" -- and reports the pathway_influence audit for
the always-on center pixel (index 4, active in all four trained patterns).
"""

from __future__ import annotations

import copy
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.simulation import SimulationEngine, PATTERNS, N_OUT, N_PIX  # noqa: E402
from backend.presets import DASHBOARD_PRESET  # noqa: E402
from diagnostic_schedule import CYCLE_ORDER, PRESENTATION_STEPS  # noqa: E402

SEED = 1   # a recorded seed (Phase 5/11 precedent: seed=1 is the first seed in every prior sweep)

CONFIGS = {
    'default': dict(DASHBOARD_PRESET),
    'A_distance_off_adaptive_off': {**DASHBOARD_PRESET, 'distance_weighting': False,
                                     'adaptive_threshold': False},
    'B_distance_off_adaptive_on': {**DASHBOARD_PRESET, 'distance_weighting': False,
                                    'adaptive_threshold': True},
}

ROW1_ACTIVE = [i for i, v in enumerate(PATTERNS['row 1']) if v]   # [3,4,5]
COL1_ACTIVE = [i for i, v in enumerate(PATTERNS['col 1']) if v]   # [1,4,7]


# --------------------------------------------------------------- instrumentation
class WeightDeltaRecorder:
    """Wraps every L2E neuron's fire()/apply_delayed_inhibition() and the
    engine's own set_feedforward_weight()/_homeostatic_scaling to record every
    feedforward weight delta with a directly-observed cause. Read-only from
    the engine's perspective otherwise -- these wrappers call the original
    method unchanged and only observe before/after state and already-returned
    diagnostic dicts."""

    def __init__(self, engine: SimulationEngine):
        self.engine = engine
        self.records: list[dict] = []
        self._current_due: list[dict] = []
        self._patch_deliver()
        for j, n in enumerate(engine.l2.excitatory_neurons):
            self._patch_fire(j, n)
            self._patch_adi(j, n)
            self._patch_homeostasis(j, n)
        self._patch_manual_edit()

    def _active_inputs(self):
        return [i for i in range(N_PIX) if self.engine.input_vec[i] > 0.5]

    def _patch_deliver(self):
        engine = self.engine
        orig = engine._deliver_scheduled_l2_inhibition

        def wrapped(t):
            self._current_due = [dict(rec) for rec in engine._l2i_pending if rec['deliver_at'] <= t]
            return orig(t)
        engine._deliver_scheduled_l2_inhibition = wrapped

    def _patch_fire(self, j, n):
        orig = n.fire

        def wrapped():
            w_before = n._weights_array.copy()
            v_pre = float(n.potential)
            theta = float(n.threshold)
            eff_theta = float(n.effective_threshold)
            active = self._active_inputs()
            t, pattern = self.engine.timestep, self.engine.current_pattern
            orig()
            w_after = n._weights_array.copy()
            delta = w_after - w_before
            changed = np.nonzero(np.abs(delta) > 1e-9)[0]
            cause = ('self_spike_exact_fe' if self.engine.params['structural_free_energy']
                     else 'self_spike_signed')
            for i in changed:
                self.records.append(dict(
                    t=t, pattern=pattern, neuron=f'L2E{j}', spiked=True, cause=cause,
                    pixel=int(i), pixel_active=bool(i in active),
                    v_pre=round(v_pre, 4), threshold=round(theta, 4),
                    effective_threshold=round(eff_theta, 4), p_loss=None,
                    active_inputs=active, l2i_source=None, l2i_time=None,
                    w_before=round(float(w_before[i]), 4), delta=round(float(delta[i]), 4),
                    w_after=round(float(w_after[i]), 4)))
        n.fire = wrapped

    def _patch_adi(self, j, n):
        orig = n.apply_delayed_inhibition

        def wrapped(magnitude):
            w_before = n._weights_array.copy()
            active = self._active_inputs()
            t, pattern = self.engine.timestep, self.engine.current_pattern
            out = orig(magnitude)
            w_after = n._weights_array.copy()
            delta = w_after - w_before
            changed = np.nonzero(np.abs(delta) > 1e-9)[0]
            if changed.size:
                due = self._current_due
                l2i_time = [rec['fire_t'] for rec in due]
                l2i_source = [f"{ct}:{cid}" for rec in due for ct, cid in rec['contributors']]
                spiked_now = bool(self.engine.spiked.get(f'L2E{j}', False))
                for i in changed:
                    self.records.append(dict(
                        t=t, pattern=pattern, neuron=f'L2E{j}', spiked=spiked_now,
                        cause='l2i_loser_depression',
                        pixel=int(i), pixel_active=bool(i in active),
                        v_pre=round(out['v_pre'], 4), threshold=round(out['theta'], 4),
                        effective_threshold=round(float(n.effective_threshold), 4),
                        p_loss=round(out['p_loss'], 4), active_inputs=active,
                        l2i_source=l2i_source, l2i_time=l2i_time,
                        w_before=round(float(w_before[i]), 4), delta=round(float(delta[i]), 4),
                        w_after=round(float(w_after[i]), 4)))
            return out
        n.apply_delayed_inhibition = wrapped

    def _patch_homeostasis(self, j, n):
        orig = n._homeostatic_scaling

        def wrapped():
            w_before = n._weights_array.copy()
            t, pattern = self.engine.timestep, self.engine.current_pattern
            orig()
            w_after = n._weights_array.copy()
            delta = w_after - w_before
            changed = np.nonzero(np.abs(delta) > 1e-9)[0]
            for i in changed:
                self.records.append(dict(
                    t=t, pattern=pattern, neuron=f'L2E{j}',
                    spiked=bool(self.engine.spiked.get(f'L2E{j}', False)),
                    cause='homeostasis', pixel=int(i), pixel_active=None,
                    v_pre=None, threshold=None, effective_threshold=None, p_loss=None,
                    active_inputs=self._active_inputs(), l2i_source=None, l2i_time=None,
                    w_before=round(float(w_before[i]), 4), delta=round(float(delta[i]), 4),
                    w_after=round(float(w_after[i]), 4)))
        n._homeostatic_scaling = wrapped

    def _patch_manual_edit(self):
        engine = self.engine
        orig = engine.set_feedforward_weight

        def wrapped(j, i, weight):
            before = float(engine.l2.excitatory_neurons[j]._weights_array[i])
            t, pattern = engine.timestep, engine.current_pattern
            after = orig(j, i, weight)
            self.records.append(dict(
                t=t, pattern=pattern, neuron=f'L2E{j}', spiked=None, cause='manual_edit',
                pixel=int(i), pixel_active=None, v_pre=None, threshold=None,
                effective_threshold=None, p_loss=None, active_inputs=self._active_inputs(),
                l2i_source=None, l2i_time=None, w_before=round(before, 4),
                delta=round(after - before, 4), w_after=round(after, 4)))
            return after
        engine.set_feedforward_weight = wrapped


# ------------------------------------------------------------------- scenarios
def build_engine(config_name: str, seed: int = SEED) -> SimulationEngine:
    kwargs = dict(CONFIGS[config_name])
    kwargs['seed'] = seed
    return SimulationEngine(**kwargs)


def run_hold_row1_then_col1(config_name: str, hold_steps: int = PRESENTATION_STEPS, seed: int = SEED):
    """Reproduce steps 1-3 of the user's report: reset with a recorded seed,
    hold row 1, then switch to col 1. Returns (engine, recorder)."""
    engine = build_engine(config_name, seed)
    rec = WeightDeltaRecorder(engine)
    engine.set_pattern('row 1')
    for _ in range(hold_steps):
        engine.step()
    engine.set_pattern('col 1')
    for _ in range(hold_steps):
        engine.step()
    return engine, rec


def run_equal_interleaved(config_name: str, cycles: int = 10,
                          presentation_steps: int = PRESENTATION_STEPS, seed: int = SEED):
    """Reproduce step 4: the intended 20-step equal-interleaved schedule
    (row 1 -> col 1 -> diag \\ -> diag / -> repeat), reusing the exact cycle
    order/step count diagnostic_schedule.py already validated in Phase 5/11.
    Returns (engine, recorder, l1i_sync_samples) where l1i_sync_samples is a
    list of booleans, one per step in which >=1 L1I fired, True iff all nine
    fired together (for the L1I-synchrony question)."""
    engine = build_engine(config_name, seed)
    rec = WeightDeltaRecorder(engine)
    l1i_sync_samples: list[bool] = []
    for _c in range(cycles):
        for pattern in CYCLE_ORDER:
            engine.set_pattern(pattern)
            for _s in range(presentation_steps):
                engine.step()
                fired = [i for i in range(N_PIX) if engine.spiked[f'L1I{i}']]
                if fired:
                    l1i_sync_samples.append(len(fired) == N_PIX)
    return engine, rec, l1i_sync_samples


# ------------------------------------------------------------------------ RF check
def verify_rf_matches_backend(engine: SimulationEngine) -> dict:
    """topology()'s serialized synapse weights vs the engine's own
    _all_weights()/raw weight array -- exact equality (not "close"), since
    topology() reads the SAME dict with no separate computation path. Also
    cross-checks against the raw per-neuron weights_array directly (bypassing
    _all_weights entirely) as a second, independent read."""
    topo = engine.topology()
    all_w = engine._all_weights()
    mismatches = []
    checked = 0
    for s in topo['synapses']:
        sid = s['id']
        if not sid.startswith('ff'):
            continue
        checked += 1
        i, j = sid[2:].split('->')
        i, j = int(i), int(j)
        raw = float(engine.l2.excitatory_neurons[j]._weights_array[i])
        ui = s['weight']
        via_all_weights = all_w[sid]
        if abs(ui - round(raw, 4)) > 1e-9 or abs(via_all_weights - raw) > 1e-9:
            mismatches.append(dict(id=sid, ui=ui, raw=raw, via_all_weights=via_all_weights))
    return dict(checked=checked, mismatches=mismatches, exact_match=(len(mismatches) == 0))


# --------------------------------------------------------------------- questions
def summarize_config(name: str, hold_engine, hold_rec, interleaved_engine, interleaved_rec,
                     l1i_sync_samples) -> dict:
    all_records = hold_rec.records + interleaved_rec.records

    # Q1/Q2: non-spiking weight increases, and how much non-spiking change is
    # loser depression. "non-spiking" = the record's own `spiked` flag is
    # False (this neuron did not itself fire this step).
    non_spiking = [r for r in all_records if r['spiked'] is False]
    non_spiking_increases = [r for r in non_spiking if r['delta'] > 1e-9]
    non_spiking_by_cause = defaultdict(int)
    for r in non_spiking:
        non_spiking_by_cause[r['cause']] += 1
    loser_dep_total = sum(1 for r in all_records if r['cause'] == 'l2i_loser_depression')
    loser_dep_non_spiking = sum(1 for r in non_spiking if r['cause'] == 'l2i_loser_depression')

    # Q3: L2E5 union-of-row1-and-col1 receptive field, from the interleaved
    # engine's final weights (the run that actually trains both patterns).
    l2e5 = interleaved_engine.l2.excitatory_neurons[5]
    l2e5_weights = {i: round(float(l2e5._weights_array[i]), 2) for i in range(N_PIX)}
    union_pixels = sorted(set(ROW1_ACTIVE) | set(COL1_ACTIVE))
    other_pixels = [i for i in range(N_PIX) if i not in union_pixels]
    l2e5_union_mean = float(np.mean([l2e5_weights[i] for i in union_pixels]))
    l2e5_other_mean = float(np.mean([l2e5_weights[i] for i in other_pixels])) if other_pixels else None

    # Q4: exact-FE capped weights unable to depress. A weight is "capped" when
    # it sits at/near this neuron's own weight_cap. Check every recorded
    # self-spike depression event (delta<0, pixel_active=False) against
    # whether w_before was already at cap, and separately check whether ANY
    # loser-depression event moved an at-cap weight (bounded_signed_update's
    # reflected kernel, a DIFFERENT kernel from exact_local_free_energy_update,
    # is not zero at the cap).
    cap = float(interleaved_engine.l2.excitatory_neurons[0].weight_cap)
    at_cap_eps = max(1.0, 0.001 * cap)
    self_spike_off_depression = [r for r in all_records
                                 if r['cause'].startswith('self_spike') and r['delta'] < -1e-9
                                 and r['pixel_active'] is False]
    self_spike_stuck_at_cap = [r for r in self_spike_off_depression
                               if r['w_before'] >= cap - at_cap_eps]
    loser_dep_moved_at_cap = [r for r in all_records
                             if r['cause'] == 'l2i_loser_depression'
                             and r['w_before'] >= cap - at_cap_eps and r['delta'] < -1e-9]

    # Q5: legacy distance amplification of the shared center pixel (index 4,
    # active in all four trained patterns) -- read directly from the audited
    # pathway_influence_report(), never recomputed ad hoc.
    report = interleaved_engine.pathway_influence_report()['l1e_l2e']
    center_entries = [e for e in report['entries'] if e['source'] == 'L1E4']
    other_entries = [e for e in report['entries'] if e['source'] != 'L1E4']
    center_influence_mean = float(np.mean([e['influence'] for e in center_entries])) if center_entries else None
    other_influence_mean = float(np.mean([e['influence'] for e in other_entries])) if other_entries else None

    # Q6: why L2E6/L2E7 remain unrecruited -- pull the evidence-based RF
    # status + raw spike counts directly (never a weight-sum guess).
    unrecruited_evidence = {}
    for j in (6, 7):
        nid = f'L2E{j}'
        status = interleaved_engine._l2e_status(j)
        n = interleaved_engine.l2.excitatory_neurons[j]
        depression_hits = sum(1 for r in all_records
                              if r['neuron'] == nid and r['cause'] == 'l2i_loser_depression')
        self_spike_hits = sum(1 for r in all_records
                              if r['neuron'] == nid and r['cause'].startswith('self_spike'))
        unrecruited_evidence[nid] = dict(
            status=status, weight_cap=float(n.weight_cap),
            positive_weight_sum=float(np.maximum(n._weights_array, 0.0).sum()),
            weights=[round(float(w), 2) for w in n._weights_array],
            loser_depression_events_recorded=depression_hits,
            self_spike_events_recorded=self_spike_hits)

    # Q7: L1I synchrony -- fraction of firing steps where all nine fired
    # together, plus a direct weight-vector-identity check (all nine L1I
    # units still literally share one feedback weight vector).
    l1i_weights = [interleaved_engine.l1.inhibitory_neurons[i].weights for i in range(N_PIX)]
    all_identical = all(np.allclose(l1i_weights[0], w) for w in l1i_weights[1:])
    sync_rate = (sum(l1i_sync_samples) / len(l1i_sync_samples)) if l1i_sync_samples else None

    # RF UI vs backend exact-match check, on both engines.
    rf_check_hold = verify_rf_matches_backend(hold_engine)
    rf_check_interleaved = verify_rf_matches_backend(interleaved_engine)

    return dict(
        config=name,
        total_weight_delta_records=len(all_records),
        non_spiking_records=len(non_spiking),
        non_spiking_increases=len(non_spiking_increases),
        non_spiking_increase_examples=non_spiking_increases[:5],
        non_spiking_by_cause=dict(non_spiking_by_cause),
        loser_depression_total_events=loser_dep_total,
        loser_depression_non_spiking_events=loser_dep_non_spiking,
        l2e5_weights=l2e5_weights,
        l2e5_union_pixels=union_pixels,
        l2e5_union_mean_weight=round(l2e5_union_mean, 2),
        l2e5_other_mean_weight=round(l2e5_other_mean, 2) if l2e5_other_mean is not None else None,
        weight_cap=cap,
        self_spike_off_depression_events=len(self_spike_off_depression),
        self_spike_stuck_at_cap_events=len(self_spike_stuck_at_cap),
        loser_depression_moved_at_cap_events=len(loser_dep_moved_at_cap),
        center_pixel_influence_mean=round(center_influence_mean, 4) if center_influence_mean else None,
        other_pixel_influence_mean=round(other_influence_mean, 4) if other_influence_mean else None,
        unrecruited_evidence=unrecruited_evidence,
        l1i_all_identical_weight_vector=bool(all_identical),
        l1i_all_nine_sync_rate=round(sync_rate, 4) if sync_rate is not None else None,
        rf_ui_matches_backend_hold_scenario=rf_check_hold['exact_match'],
        rf_ui_matches_backend_interleaved_scenario=rf_check_interleaved['exact_match'],
        rf_check_details=dict(hold=rf_check_hold, interleaved=rf_check_interleaved),
        final_l2e_status={f'L2E{j}': interleaved_engine._l2e_status(j) for j in range(N_OUT)},
    )


def main():
    results = {}
    full_logs = {}
    for name in CONFIGS:
        hold_engine, hold_rec = run_hold_row1_then_col1(name)
        interleaved_engine, interleaved_rec, l1i_sync = run_equal_interleaved(name, cycles=40)
        summary = summarize_config(name, hold_engine, hold_rec, interleaved_engine,
                                   interleaved_rec, l1i_sync)
        results[name] = summary
        full_logs[name] = dict(hold_row1_then_col1=hold_rec.records,
                               equal_interleaved=interleaved_rec.records)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'dashboard_behavior_diagnostic_summary.json'), 'w') as f:
        json.dump(results, f, indent=2, default=str)
    # The full per-event log (tens of MB) is a disposable, ad-hoc diagnostic
    # artifact -- CLAUDE.md's commit-hygiene rule keeps generated report
    # artifacts like this out of the repo. Written to a scratch dir (override
    # via DASHBOARD_DIAGNOSTIC_SCRATCH) instead of alongside the script.
    scratch_dir = os.environ.get('DASHBOARD_DIAGNOSTIC_SCRATCH', '/tmp')
    with open(os.path.join(scratch_dir, 'dashboard_behavior_diagnostic_full_log.json'), 'w') as f:
        json.dump(full_logs, f, indent=2, default=str)
    print(f"\n(full per-event log written to {scratch_dir}/dashboard_behavior_diagnostic_full_log.json, not committed)")

    for name, s in results.items():
        print(f"\n===== {name} =====")
        print(f"  total weight-delta records: {s['total_weight_delta_records']} "
             f"(non-spiking: {s['non_spiking_records']})")
        print(f"  non-spiking weight INCREASES: {s['non_spiking_increases']}")
        print(f"  non-spiking by cause: {s['non_spiking_by_cause']}")
        print(f"  loser-depression events: {s['loser_depression_total_events']} total, "
             f"{s['loser_depression_non_spiking_events']} on non-spiking neurons")
        print(f"  L2E5 weights: {s['l2e5_weights']}  union(row1,col1)={s['l2e5_union_pixels']} "
             f"union_mean={s['l2e5_union_mean_weight']} other_mean={s['l2e5_other_mean_weight']}")
        print(f"  self-spike OFF-depression events: {s['self_spike_off_depression_events']}, "
             f"stuck-at-cap: {s['self_spike_stuck_at_cap_events']}")
        print(f"  loser-depression events that moved an at-cap weight: "
             f"{s['loser_depression_moved_at_cap_events']}")
        print(f"  center pixel (L1E4) mean influence: {s['center_pixel_influence_mean']} "
             f"vs other pixels: {s['other_pixel_influence_mean']}")
        print(f"  L2E6/L2E7 status: "
             f"{ {k: v['status'] for k, v in s['unrecruited_evidence'].items()} }")
        print(f"  L1I identical weight vectors: {s['l1i_all_identical_weight_vector']}  "
             f"all-nine sync rate: {s['l1i_all_nine_sync_rate']}")
        print(f"  RF UI == backend weights (hold scenario): {s['rf_ui_matches_backend_hold_scenario']}  "
             f"(interleaved scenario): {s['rf_ui_matches_backend_interleaved_scenario']}")
        print(f"  final L2E status: "
             f"{ {k: v['status'] for k, v in s['final_l2e_status'].items()} }")


if __name__ == "__main__":
    main()
