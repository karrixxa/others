"""
Phase 13b -- corrected and strengthened dashboard behavior diagnostic
(MEASUREMENT ONLY, per explicit user instruction: no neural mechanism
changed, no default changed, nothing tuned).

Corrects a real methodology bug in Phase 13
(dashboard_behavior_diagnostic.py): that script tagged every
loser-depression weight-delta record with `spiked=engine.spiked[nid]` read
AT THE MOMENT apply_delayed_inhibition() is called -- which happens at the
very TOP of step(), before this step's own L1E/L2E competition has run. At
that point `engine.spiked[nid]` still holds LAST step's outcome (t-1), not
"did this neuron spike THIS step" -- Phase 13's "non-spiking" claims were
still directionally correct (loser depression's own target selection logic
never touches a currently-firing neuron's charge in a self-serving way), but
the field itself was mislabeled. This version records three explicit,
separately-timed facts instead of one ambiguous one:

  spiked_previous_step      -- engine.spiked[nid] snapshotted BEFORE
                                _deliver_scheduled_l2_inhibition runs this
                                step (i.e. this neuron's own recorded result
                                from timestep t-1).
  inhibited_at_start_of_step -- apply_delayed_inhibition's own returned
                                `applied` flag (delivery actually reached
                                this neuron, at the top of step t, before
                                any new charge this step).
  spiked_later_current_step -- engine.spiked[nid] read AFTER step() fully
                                completes for timestep t (the neuron's real,
                                finished result for THIS step -- delivery
                                happens before this step's own L1E/L2E
                                competition, so a neuron hit by delayed
                                inhibition at the top of a step can still
                                cross threshold and fire later in that same
                                step; this is the fact Phase 13 conflated).

Also adds, per explicit request: weight seeds 1-5 x topology seeds 1-3;
three named scenarios (short hold/switch, long hold/switch, 40-rotation
equal-interleave); unique L2I delivery-event counts alongside individual
synapse-delta counts; per-run tyrant identification (the neuron with the
most total recorded spikes -- never assumed to be L2E5); tyrant-vs-
pattern-specific weight comparison; a per-run count of loser-depression
synapse deltas landing on neurons that NEVER fired in that run; and a third
config (C) -- distance_weighting on with every L1E->L2E connection's
distance overridden to one uniform scalar solved so the MEAN delivered
influence factor exactly matches config A's own mean (same total/mean
"charge budget", no spatial pattern) -- to separate "does the AMOUNT of
distance amplification matter" from "does WHICH pixel gets more of it
matter". C is diagnostic-only (built by overriding `.distance` arrays
in-script after construction, the same public property every existing test
already uses) and touches no default in backend/presets.py or
backend/simulation.py.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.simulation import SimulationEngine, PATTERNS, N_OUT, N_PIX  # noqa: E402
from backend.presets import DASHBOARD_PRESET  # noqa: E402
from diagnostic_schedule import CYCLE_ORDER, PRESENTATION_STEPS, _present_and_record, summarize  # noqa: E402

WEIGHT_SEEDS = [1, 2, 3, 4, 5]
TOPOLOGY_SEEDS = [1, 2, 3]

ROW1_ACTIVE = [i for i, v in enumerate(PATTERNS['row 1']) if v]
COL1_ACTIVE = [i for i, v in enumerate(PATTERNS['col 1']) if v]

SCENARIOS = ('short_hold_switch', 'long_hold_switch', 'interleaved_40')


# --------------------------------------------------------------- config A/B/C
def config_A() -> dict:
    """The literal current dashboard default: distance_weighting on,
    legacy_distance_compat on (delivery distances pinned to the fixed
    legacy reference geometry, regardless of topology_seed)."""
    return dict(DASHBOARD_PRESET)


def config_B() -> dict:
    """Raw distance off: no per-connection attenuation/amplification at
    all (effective_weights() returns the stored weight unchanged)."""
    return {**DASHBOARD_PRESET, 'distance_weighting': False}


def _grand_mean_influence_A():
    """Mean L1E->L2E influence factor under config A, computed once (it is
    seed/topology-independent under legacy_distance_compat=True -- verified
    empirically below, see verify_topology_seed_inertness). Returns
    (mean_influence, distance_ref, distance_power, distance_min)."""
    ref = SimulationEngine(seed=1, topology_seed=1, **config_A())
    report = ref.pathway_influence_report()['l1e_l2e']
    vals = [e['influence'] for e in report['entries']]
    p = ref.params
    return float(np.mean(vals)), p['distance_ref'], p['distance_power'], p['distance_min']


_MEAN_INFLUENCE_A, _DIST_REF, _DIST_POWER, _DIST_MIN = _grand_mean_influence_A()
# Solve (distance_ref / max(d, distance_min))**power == mean_influence_A for d.
_D_UNIFORM = _DIST_REF / (_MEAN_INFLUENCE_A ** (1.0 / _DIST_POWER))


def build_engine(config_name: str, weight_seed: int, topology_seed: int) -> SimulationEngine:
    if config_name == 'A':
        kw = config_A()
    elif config_name == 'B':
        kw = config_B()
    elif config_name == 'C':
        kw = config_A()   # same distance_weighting/power/ref/min as A
    else:
        raise ValueError(config_name)
    kw['seed'] = weight_seed
    kw['topology_seed'] = topology_seed
    engine = SimulationEngine(**kw)
    if config_name == 'C':
        # Diagnostic-only override: every L1E->L2E connection gets the SAME
        # distance (hence the same influence factor, == config A's mean),
        # so total/mean delivered amplification matches A but the SPATIAL
        # PATTERN (center pixel closer/farther than others) is removed.
        # `.distance` is the same public property neuron_flexible.py's own
        # tests already use to set per-afferent distances directly.
        uniform = np.full(N_PIX, _D_UNIFORM)
        for e in engine.l2.excitatory_neurons:
            e.distance = uniform.copy()
    return engine


# --------------------------------------------------------------- instrumentation
class WeightDeltaRecorder:
    """See module docstring for the corrected spiked_previous_step /
    inhibited_at_start_of_step / spiked_later_current_step timing fields."""

    def __init__(self, engine: SimulationEngine):
        self.engine = engine
        self.records: list[dict] = []
        self._current_due: list[dict] = []
        self._pre_step_spiked: dict = {}
        self._pending_fill: list[dict] = []   # loser-depression records awaiting spiked_later_current_step
        self._patch_step()
        self._patch_deliver()
        for j, n in enumerate(engine.l2.excitatory_neurons):
            self._patch_fire(j, n)
            self._patch_adi(j, n)
            self._patch_homeostasis(j, n)
        self._patch_manual_edit()

    def _active_inputs(self):
        return [i for i in range(N_PIX) if self.engine.input_vec[i] > 0.5]

    def _patch_step(self):
        engine = self.engine
        orig = engine.step

        def wrapped():
            # Snapshot BEFORE this step's own processing -- this is each
            # neuron's real, finished result from timestep t-1.
            self._pre_step_spiked = dict(engine.spiked)
            result = orig()
            # engine.timestep has now advanced; engine.spiked holds THIS
            # just-completed step's real, finished result -- fill in the
            # deferred field on only the records created during this step
            # (self._pending_fill, populated by _patch_adi below), never by
            # rescanning the whole history (that made every step O(total
            # records so far) -- a real quadratic-time bug in the first
            # draft of this instrumentation, fixed here).
            for r in self._pending_fill:
                r['spiked_later_current_step'] = bool(engine.spiked.get(r['neuron'], False))
            self._pending_fill = []
            return result
        engine.step = wrapped

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
                    t=t, pattern=pattern, neuron=f'L2E{j}', cause=cause,
                    pixel=int(i), pixel_active=bool(i in active),
                    v_pre=round(v_pre, 4), threshold=round(theta, 4),
                    effective_threshold=round(eff_theta, 4), p_loss=None,
                    active_inputs=active, l2i_source=None, l2i_time=None,
                    delivery_id=None,
                    spiked_previous_step=None, inhibited_at_start_of_step=None,
                    spiked_later_current_step=True,   # this record IS the spike
                    w_before=round(float(w_before[i]), 4), delta=round(float(delta[i]), 4),
                    w_after=round(float(w_after[i]), 4)))
        n.fire = wrapped

    def _patch_adi(self, j, n):
        orig = n.apply_delayed_inhibition

        def wrapped(magnitude):
            w_before = n._weights_array.copy()
            active = self._active_inputs()
            t, pattern = self.engine.timestep, self.engine.current_pattern
            nid = f'L2E{j}'
            spiked_prev = bool(self._pre_step_spiked.get(nid, False))
            out = orig(magnitude)
            w_after = n._weights_array.copy()
            delta = w_after - w_before
            changed = np.nonzero(np.abs(delta) > 1e-9)[0]
            due = self._current_due
            l2i_time = [rec['fire_t'] for rec in due]
            l2i_source = [f"{ct}:{cid}" for rec in due for ct, cid in rec['contributors']]
            # Unique-delivery-event id: the L2I firing timestep uniquely
            # identifies one scheduled delivery (a single shared L2I neuron
            # fires at most once per timestep).
            delivery_id = due[0]['fire_t'] if len(due) == 1 else tuple(l2i_time)
            if changed.size:
                for i in changed:
                    rec_dict = dict(
                        t=t, pattern=pattern, neuron=nid, cause='l2i_loser_depression',
                        pixel=int(i), pixel_active=bool(i in active),
                        v_pre=round(out['v_pre'], 4), threshold=round(out['theta'], 4),
                        effective_threshold=round(float(n.effective_threshold), 4),
                        p_loss=round(out['p_loss'], 4), active_inputs=active,
                        l2i_source=l2i_source, l2i_time=l2i_time, delivery_id=delivery_id,
                        spiked_previous_step=spiked_prev,
                        inhibited_at_start_of_step=bool(out['applied']),
                        spiked_later_current_step=None,   # filled by the step() wrapper below
                        w_before=round(float(w_before[i]), 4), delta=round(float(delta[i]), 4),
                        w_after=round(float(w_after[i]), 4))
                    self.records.append(rec_dict)
                    self._pending_fill.append(rec_dict)
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
                    t=t, pattern=pattern, neuron=f'L2E{j}', cause='homeostasis',
                    pixel=int(i), pixel_active=None, v_pre=None, threshold=None,
                    effective_threshold=None, p_loss=None,
                    active_inputs=self._active_inputs(), l2i_source=None, l2i_time=None,
                    delivery_id=None, spiked_previous_step=None,
                    inhibited_at_start_of_step=None, spiked_later_current_step=None,
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
                t=t, pattern=pattern, neuron=f'L2E{j}', cause='manual_edit',
                pixel=int(i), pixel_active=None, v_pre=None, threshold=None,
                effective_threshold=None, p_loss=None, active_inputs=self._active_inputs(),
                l2i_source=None, l2i_time=None, delivery_id=None,
                spiked_previous_step=None, inhibited_at_start_of_step=None,
                spiked_later_current_step=None, w_before=round(before, 4),
                delta=round(after - before, 4), w_after=round(after, 4)))
            return after
        engine.set_feedforward_weight = wrapped


# ------------------------------------------------------------------- scenarios
def run_short_hold_switch(config_name, weight_seed, topology_seed,
                          row1_steps=20, col1_steps=20):
    engine = build_engine(config_name, weight_seed, topology_seed)
    rec = WeightDeltaRecorder(engine)
    engine.set_pattern('row 1')
    for _ in range(row1_steps):
        engine.step()
    engine.set_pattern('col 1')
    for _ in range(col1_steps):
        engine.step()
    return engine, rec


def run_long_hold_switch(config_name, weight_seed, topology_seed,
                         row1_steps=600, col1_steps=200):
    return run_short_hold_switch(config_name, weight_seed, topology_seed,
                                 row1_steps=row1_steps, col1_steps=col1_steps)


def run_interleaved_40(config_name, weight_seed, topology_seed,
                       cycles=40, presentation_steps=PRESENTATION_STEPS):
    engine = build_engine(config_name, weight_seed, topology_seed)
    rec = WeightDeltaRecorder(engine)
    presentation_records: list[dict] = []
    l1i_sync_samples: list[bool] = []
    for _c in range(cycles):
        for pattern in CYCLE_ORDER:
            _present_and_record(engine, pattern, presentation_steps, presentation_records)
    # l1i sync needs its own step-level trace; diagnostic_schedule's own
    # _present_and_record already ran every step above, so recompute sync
    # from the SAME already-stepped engine's spike history is not possible
    # post-hoc (spiked is transient) -- instead this is reported from a
    # dedicated pass below (run_interleaved_40_with_sync) when needed.
    return engine, rec, presentation_records


def run_interleaved_40_with_sync(config_name, weight_seed, topology_seed,
                                 cycles=40, presentation_steps=PRESENTATION_STEPS):
    """Like run_interleaved_40 but also tracks per-step L1I all-nine-sync,
    by stepping manually (same cycle order/steps) instead of reusing
    _present_and_record. Used only for the example/illustrative runs, not
    the full grid (to keep the grid's runtime and output size bounded)."""
    engine = build_engine(config_name, weight_seed, topology_seed)
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


# --------------------------------------------------------------------- analysis
def identify_tyrant(engine: SimulationEngine) -> str | None:
    """The neuron with the most total recorded spikes this run -- never
    assumed to be any specific index. None if nobody ever fired."""
    counts = {f'L2E{j}': engine._neuron_total_spikes.get(f'L2E{j}', 0) for j in range(N_OUT)}
    if max(counts.values()) == 0:
        return None
    return max(counts, key=counts.get)


def never_fired_neurons(engine: SimulationEngine) -> list[str]:
    return [f'L2E{j}' for j in range(N_OUT) if engine._neuron_total_spikes.get(f'L2E{j}', 0) == 0]


def analyze_run(config_name, weight_seed, topology_seed, scenario, engine, rec) -> dict:
    records = rec.records
    loser = [r for r in records if r['cause'] == 'l2i_loser_depression']
    self_spike = [r for r in records if r['cause'].startswith('self_spike')]

    unique_delivery_ids = {r['delivery_id'] for r in loser if r['delivery_id'] is not None}
    unique_delivery_events = len(unique_delivery_ids)
    individual_synapse_deltas = len(loser)

    # Corrected non-spiking analysis: "non-spiking" now means
    # spiked_previous_step is False (this neuron was not the (or a) most
    # recent winner going into this delivery) -- distinct from
    # spiked_later_current_step (did it fire AFTER this delivery, later
    # in the SAME step).
    non_spiking_prev = [r for r in loser if r['spiked_previous_step'] is False]
    non_spiking_increases = [r for r in non_spiking_prev if r['delta'] > 1e-9]
    fired_later_same_step = [r for r in loser if r['spiked_later_current_step'] is True]

    tyrant = identify_tyrant(engine)
    tyrant_weights = None
    tyrant_union_mean = None
    tyrant_other_mean = None
    if tyrant is not None:
        j = int(tyrant[3:])
        n = engine.l2.excitatory_neurons[j]
        tyrant_weights = {i: round(float(n._weights_array[i]), 2) for i in range(N_PIX)}
        union_pixels = sorted(set(ROW1_ACTIVE) | set(COL1_ACTIVE))
        other_pixels = [i for i in range(N_PIX) if i not in union_pixels]
        tyrant_union_mean = float(np.mean([tyrant_weights[i] for i in union_pixels]))
        tyrant_other_mean = float(np.mean([tyrant_weights[i] for i in other_pixels])) if other_pixels else None

    never_fired = never_fired_neurons(engine)
    never_fired_depression_counts = {
        nid: sum(1 for r in loser if r['neuron'] == nid) for nid in never_fired}

    status = {f'L2E{j}': engine._l2e_status(j)['status'] for j in range(N_OUT)}
    active_count = sum(1 for s in status.values() if s == 'active')

    return dict(
        config=config_name, weight_seed=weight_seed, topology_seed=topology_seed,
        scenario=scenario,
        total_records=len(records),
        unique_delivery_events=unique_delivery_events,
        individual_synapse_deltas=individual_synapse_deltas,
        engine_l2_inhibition_log_len=len(engine._l2_inhibition_log),
        non_spiking_prev_step_records=len(non_spiking_prev),
        non_spiking_prev_step_increases=len(non_spiking_increases),
        loser_depression_events_where_target_fires_later_same_step=len(fired_later_same_step),
        tyrant=tyrant,
        tyrant_weights=tyrant_weights,
        tyrant_union_mean_weight=round(tyrant_union_mean, 2) if tyrant_union_mean is not None else None,
        tyrant_other_mean_weight=round(tyrant_other_mean, 2) if tyrant_other_mean is not None else None,
        never_fired_neurons=never_fired,
        never_fired_loser_depression_counts=never_fired_depression_counts,
        l2e_status=status,
        active_count=active_count,
        self_spike_events=len(self_spike),
    )


def verify_topology_seed_inertness(config_name, weight_seed=1) -> dict:
    """Configs A/B/C never let real per-topology-seed geometry drive
    delivered distance (A/C are legacy-pinned or uniform-overridden; B has
    distance_weighting off entirely) -- so topology_seed should be a
    complete no-op for these three configs' weight/recruitment outcomes.
    Verified directly rather than assumed: run the short scenario at 3
    topology seeds, same weight seed, and diff the final feedforward
    weight matrices exactly."""
    finals = []
    for ts in TOPOLOGY_SEEDS:
        engine, _ = run_short_hold_switch(config_name, weight_seed, ts)
        finals.append({f'ff{i}->{j}': float(engine.l2.excitatory_neurons[j]._weights_array[i])
                       for j in range(N_OUT) for i in range(N_PIX)})
    identical = all(
        all(abs(finals[0][k] - f[k]) < 1e-9 for k in finals[0])
        for f in finals[1:])
    return dict(config=config_name, weight_seed=weight_seed,
               topology_seeds_tested=TOPOLOGY_SEEDS, identical_across_topology_seed=identical)


# ------------------------------------------------------------------------ main
def main():
    configs = ['A', 'B', 'C']
    scenarios = SCENARIOS

    grid_results = []
    for config_name in configs:
        for ws in WEIGHT_SEEDS:
            for ts in TOPOLOGY_SEEDS:
                engine, rec = run_short_hold_switch(config_name, ws, ts)
                grid_results.append(analyze_run(config_name, ws, ts, 'short_hold_switch', engine, rec))

                engine, rec = run_long_hold_switch(config_name, ws, ts)
                grid_results.append(analyze_run(config_name, ws, ts, 'long_hold_switch', engine, rec))

                engine, rec, _pres = run_interleaved_40(config_name, ws, ts)
                grid_results.append(analyze_run(config_name, ws, ts, 'interleaved_40', engine, rec))

    # Phase-11-style distinct-owners/consistency metrics for the
    # interleaved schedule, for direct reconciliation with Phase 11.
    phase11_style = []
    for config_name in configs:
        for ws in WEIGHT_SEEDS:
            engine, rec, pres_records = run_interleaved_40(config_name, ws, 1)
            s = summarize(dict(seed=ws, live=pres_records, frozen=[]))
            phase11_style.append(dict(
                config=config_name, weight_seed=ws, topology_seed=1,
                distinct_owners=s['distinct_owners'],
                per_pattern_consistency={p: pp['consistency'] for p, pp in s['per_pattern'].items()},
                collisions=s['collisions'],
                silent_cells=s['silent_cells'], recruitable_cells=s['recruitable_cells']))

    # Topology-seed inertness verification, all three configs.
    inertness = [verify_topology_seed_inertness(c) for c in configs]

    # Illustrative full-detail examples (weight_seed=1, topology_seed=1) for
    # the tracer-timing tests and the written report's example records.
    examples = {}
    for config_name in configs:
        eng_short, rec_short = run_short_hold_switch(config_name, 1, 1)
        eng_long, rec_long = run_long_hold_switch(config_name, 1, 1)
        eng_il, rec_il, sync = run_interleaved_40_with_sync(config_name, 1, 1)
        examples[config_name] = dict(
            short=dict(records=rec_short.records[:50]),
            long=dict(records=rec_long.records[:50]),
            interleaved=dict(records=rec_il.records[:50], l1i_sync_rate=(
                round(sum(sync) / len(sync), 4) if sync else None)),
        )

    out_dir = os.path.dirname(os.path.abspath(__file__))
    summary = dict(
        mean_influence_A=_MEAN_INFLUENCE_A, d_uniform_C=_D_UNIFORM,
        weight_seeds=WEIGHT_SEEDS, topology_seeds=TOPOLOGY_SEEDS,
        grid_results=grid_results,
        phase11_style_interleaved_metrics=phase11_style,
        topology_seed_inertness=inertness,
    )
    with open(os.path.join(out_dir, 'phase13b_diagnostic_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    scratch_dir = os.environ.get('DASHBOARD_DIAGNOSTIC_SCRATCH', '/tmp')
    with open(os.path.join(scratch_dir, 'phase13b_diagnostic_examples.json'), 'w') as f:
        json.dump(examples, f, indent=2, default=str)

    print(f"mean_influence_A={_MEAN_INFLUENCE_A:.4f}  d_uniform_C={_D_UNIFORM:.4f}")
    print(f"grid runs: {len(grid_results)}")
    for r in inertness:
        print(f"topology-seed inertness [{r['config']}]: identical={r['identical_across_topology_seed']}")
    print(f"(examples written to {scratch_dir}/phase13b_diagnostic_examples.json, not committed)")


if __name__ == "__main__":
    main()
