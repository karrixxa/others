"""
Phase 27 -- L2 ownership causal audit (MEASUREMENT ONLY).

Purpose: determine exactly how the L2 representation layer moves from
initial random differences to one L2E neuron owning multiple patterns.
Changes NO neural equation, NO parameter, NO initialization, NO default. Uses
DASHBOARD_PRESET unchanged. All prediction-related flags stay at their
constructor defaults (off); this script never sets them.

Non-mutating instrumentation (`CausalTracer`) patches the SAME public/
semi-public hooks Phase 13b's `WeightDeltaRecorder` used (`fire`,
`apply_delayed_inhibition`, `_homeostatic_scaling`, `set_feedforward_weight`,
`_deliver_scheduled_l2_inhibition`) -- every patch calls straight through to
the original method and only reads state immediately before/after it. Every
weight-mutating event is classified into exactly one of five MUTUALLY
EXCLUSIVE causes:

    self_spike_potentiation        -- this neuron's own fire(), active input
    self_spike_depression_inactive -- this neuron's own fire(), inactive input
    l2i_loser_depression           -- Neuron.apply_delayed_inhibition
    homeostasis                    -- Neuron._homeostatic_scaling (off by
                                       default in DASHBOARD_PRESET; patched
                                       anyway so it is never silently missed
                                       if some other caller enables it)
    manual_edit                    -- SimulationEngine.set_feedforward_weight

Any synapse delta NOT accounted for by one of the five patches above is
recorded separately as `residual_unattributed`, built by a step-level
before/after reconciliation (`CausalTracer._patch_step`) -- see
`Do not repeat Phase 13's counting ambiguity` in the module-level docstring
of `phase13b_diagnostic.py`: THIS script keeps three separate counts,
never conflated:

    synapse_delta_records      -- one row per (event, pixel) weight change.
    target_neuron_applications -- one row per apply_delayed_inhibition call
                                   that actually reached its target (applied
                                   True), REGARDLESS of whether that reach
                                   produced any synapse-delta rows (p_loss==0
                                   or no eligible synapses both apply zero
                                   synapse deltas from a real, counted reach).
    physical_l2i_deliveries    -- one row per L2I->L2E scheduled+delivered
                                   event (grouped by the L2I firing timestep),
                                   read straight from the tail of
                                   `engine._l2_inhibition_log` immediately
                                   after each `_deliver_scheduled_l2_inhibition`
                                   call -- exhaustive, not affected by that
                                   deque's maxlen=400 display truncation
                                   (Phase 13b's own finding; same fix reused
                                   here).

Ownership-collision detection (`find_earliest_modal_collision`) replays a
run's chronological per-presentation `first_l2e_spiker` log and, after EVERY
presentation, recomputes each pattern's running MODAL first-responder using
only that pattern's own presentations seen so far (never peeking ahead). The
first presentation at which any single neuron is the running modal owner for
two or more distinct patterns is reported as the earliest ownership
collision. This is pure data replay: no neuron id or pattern name is ever
hardcoded, and a run with no collision returns None (see
`test_phase27_l2_ownership_causal_audit.py`'s
`test_audit_code_contains_no_owner_assignment_or_hardcoded_outcome`).

Two schedules, reported and stored SEPARATELY, never mixed:

  - `run_interleaved_causal_audit`: the brief's row1->col1->diag\\->diag/->
    repeat cycle, 20 steps/presentation, INTERLEAVED_CYCLES rotations.
  - `run_long_hold_causal_audit`: 600-step row1 hold -> 200-step col1 hold,
    each internally chunked into 20-step sub-windows for the SAME
    presentation-level machinery (reusing `find_earliest_modal_collision`
    unchanged) -- a secondary comparison only.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.simulation import SimulationEngine, PATTERNS, N_OUT, N_PIX  # noqa: E402
from backend.presets import DASHBOARD_PRESET  # noqa: E402
from diagnostic_schedule import CYCLE_ORDER, PRESENTATION_STEPS  # noqa: E402

WEIGHT_SEEDS = list(range(1, 11))
TOPOLOGY_SEEDS = [1, 2, 3]
INTERLEAVED_CYCLES = 40          # matches Phase 13b/22's own "interleaved_40" convention
LONG_SCHEDULE = [('row 1', 600), ('col 1', 200)]
CENTER_PIXEL = 4                 # the only pixel active in all four PATTERNS -- verified below
PATTERN_ACTIVE = {p: [i for i, v in enumerate(PATTERNS[p]) if v] for p in PATTERNS}
assert all(CENTER_PIXEL in PATTERN_ACTIVE[p] for p in PATTERNS), \
    "CENTER_PIXEL constant must track PATTERNS -- verified, not assumed"


# --------------------------------------------------------------- instrumentation
class CausalTracer:
    """Non-mutating instrumentation. See module docstring for the exact cause
    taxonomy and the residual-reconciliation safety net. Never mutates a
    spike, weight, or timing decision -- every patch calls straight through
    to the original bound method and only reads state around it."""

    def __init__(self, engine: SimulationEngine):
        self.engine = engine
        self.spike_records: list[dict] = []
        self.weight_delta_records: list[dict] = []
        self.l2i_delivery_records: list[dict] = []
        self.target_applications: list[dict] = []
        self._current_due: list[dict] = []
        self._residual_seen = 0
        self._patch_step()
        self._patch_deliver()
        for j, n in enumerate(engine.l2.excitatory_neurons):
            self._patch_fire(j, n)
            self._patch_adi(j, n)
            self._patch_homeostasis(j, n)
        self._patch_manual_edit()

    # ---- shared helpers
    def _active_inputs(self) -> list[int]:
        return [i for i in range(N_PIX) if self.engine.input_vec[i] > 0.5]

    def _all_ff_weights(self) -> dict:
        """Keyed (j, i) -> stored weight, for every L2E j and pixel i."""
        return {(j, i): float(self.engine.l2.excitatory_neurons[j]._weights_array[i])
                for j in range(N_OUT) for i in range(N_PIX)}

    # ---- residual-unattributed safety net
    def _patch_step(self):
        engine = self.engine
        orig = engine.step

        def wrapped():
            before = self._all_ff_weights()
            attributed_before = len(self.weight_delta_records)
            t = engine.timestep
            pattern = engine.current_pattern
            result = orig()
            after = self._all_ff_weights()
            attributed = self.weight_delta_records[attributed_before:]
            accounted = defaultdict(float)
            for r in attributed:
                accounted[(int(r['neuron'][3:]), r['pixel'])] += r['delta']
            for key, w_after in after.items():
                w_before = before[key]
                raw_delta = w_after - w_before
                # Tolerance is above the max single-event rounding error (each
                # accounted delta is stored rounded to 4 decimals, +/-5e-5) so
                # this only flags a REAL unattributed mechanism, never the
                # rounding noise of an otherwise fully-accounted event.
                if abs(raw_delta - accounted.get(key, 0.0)) > 1e-3:
                    residual = raw_delta - accounted.get(key, 0.0)
                    j, i = key
                    self._residual_seen += 1
                    self.weight_delta_records.append(dict(
                        t=t, pattern=pattern, neuron=f'L2E{j}', cause='residual_unattributed',
                        pixel=i, pixel_active=bool(i in self._active_inputs()),
                        w_before=round(w_before, 4), delta=round(residual, 4),
                        w_after=round(w_after, 4),
                        note='weight changed by an amount no patched hook accounted for'))
            return result
        engine.step = wrapped

    # ---- exhaustive (non-truncated) physical L2I delivery log
    def _patch_deliver(self):
        engine = self.engine
        orig = engine._deliver_scheduled_l2_inhibition

        def wrapped(t):
            due = [rec for rec in engine._l2i_pending if rec['deliver_at'] <= t]
            self._current_due = due
            applied = orig(t)
            if due:
                # engine._l2_inhibition_log is a deque(maxlen=400) -- a display
                # window, not exhaustive (Phase 13b finding). Reading exactly
                # the last len(due) entries (the ones THIS call just appended)
                # is correct regardless of maxlen eviction, since appends
                # always land at the tail and len(due) is always far below 400.
                new_deliveries = list(engine._l2_inhibition_log)[-len(due):]
                for delivery in new_deliveries:
                    self.l2i_delivery_records.append(dict(delivery))
            return applied
        engine._deliver_scheduled_l2_inhibition = wrapped

    # ---- self-spike potentiation / inactive-input depression
    def _patch_fire(self, j, n):
        orig = n.fire

        def wrapped():
            w_before = n._weights_array.copy()
            v_pre = float(n.potential)
            theta = float(n.threshold)
            eff_theta = float(n.effective_threshold)
            a_i = float(n.threshold_adapt)
            active = self._active_inputs()
            eligible = sorted(getattr(self.engine, '_last_eligible', None) or [])
            eligible_ids = [f'L2E{k}' for k in eligible]
            fe_gate = (float(n._structural_free_energy_gate())
                      if self.engine.params.get('structural_free_energy') else None)
            t = self.engine.timestep
            pattern = self.engine.current_pattern
            nid = f'L2E{j}'
            orig()
            v_post = float(n.potential)
            w_after = n._weights_array.copy()
            delta = w_after - w_before
            changed = np.nonzero(np.abs(delta) > 1e-9)[0]
            self.spike_records.append(dict(
                t=t, pattern=pattern, neuron=nid, v_pre=round(v_pre, 4),
                v_post=round(v_post, 4), threshold=round(theta, 4),
                effective_threshold=round(eff_theta, 4), threshold_adapt=round(a_i, 4),
                active_inputs=active, eligible_set=eligible_ids,
                same_step_tie=len(eligible_ids) > 1))
            for i in changed:
                active_i = bool(int(i) in active)
                cause = 'self_spike_potentiation' if active_i else 'self_spike_depression_inactive'
                self.weight_delta_records.append(dict(
                    t=t, pattern=pattern, neuron=nid, cause=cause,
                    pixel=int(i), pixel_active=active_i,
                    v_pre=round(v_pre, 4), threshold=round(theta, 4), fe_gate=fe_gate,
                    active_inputs=active,
                    w_before=round(float(w_before[i]), 4), delta=round(float(delta[i]), 4),
                    w_after=round(float(w_after[i]), 4)))
        n.fire = wrapped

    # ---- L2I loser depression
    def _patch_adi(self, j, n):
        orig = n.apply_delayed_inhibition

        def wrapped(magnitude):
            w_before = n._weights_array.copy()
            active = self._active_inputs()
            t, pattern = self.engine.timestep, self.engine.current_pattern
            nid = f'L2E{j}'
            out = orig(magnitude)
            w_after = n._weights_array.copy()
            delta = w_after - w_before
            changed = np.nonzero(np.abs(delta) > 1e-9)[0]
            due = self._current_due
            l2i_time = [rec['fire_t'] for rec in due]
            l2i_source = [f'{ct}:{cid}' for rec in due for ct, cid in rec['contributors']]
            delivery_id = due[0]['fire_t'] if len(due) == 1 else tuple(l2i_time)
            if out['applied']:
                self.target_applications.append(dict(
                    t=t, pattern=pattern, neuron=nid, delivery_id=delivery_id,
                    v_pre=round(out['v_pre'], 4), v_post=round(out['v_post'], 4),
                    p_loss=round(out['p_loss'], 4), maturity=round(out['maturity'], 4),
                    depressed_count=len(out['depressed_indices'])))
            if changed.size:
                for i in changed:
                    self.weight_delta_records.append(dict(
                        t=t, pattern=pattern, neuron=nid, cause='l2i_loser_depression',
                        pixel=int(i), pixel_active=bool(int(i) in active),
                        v_pre=round(out['v_pre'], 4), threshold=round(out['theta'], 4),
                        p_loss=round(out['p_loss'], 4), active_inputs=active,
                        l2i_source=l2i_source, l2i_time=l2i_time, delivery_id=delivery_id,
                        w_before=round(float(w_before[i]), 4), delta=round(float(delta[i]), 4),
                        w_after=round(float(w_after[i]), 4)))
            return out
        n.apply_delayed_inhibition = wrapped

    # ---- homeostasis (off by default; patched for completeness/no silent gap)
    def _patch_homeostasis(self, j, n):
        orig = n._homeostatic_scaling

        def wrapped():
            w_before = n._weights_array.copy()
            t, pattern = self.engine.timestep, self.engine.current_pattern
            nid = f'L2E{j}'
            orig()
            w_after = n._weights_array.copy()
            delta = w_after - w_before
            changed = np.nonzero(np.abs(delta) > 1e-9)[0]
            for i in changed:
                self.weight_delta_records.append(dict(
                    t=t, pattern=pattern, neuron=nid, cause='homeostasis',
                    pixel=int(i), pixel_active=None,
                    w_before=round(float(w_before[i]), 4), delta=round(float(delta[i]), 4),
                    w_after=round(float(w_after[i]), 4)))
        n._homeostatic_scaling = wrapped

    # ---- manual edits (unused in this diagnostic's own schedules; patched
    # for completeness so any accidental manual call is still attributed)
    def _patch_manual_edit(self):
        engine = self.engine
        orig = engine.set_feedforward_weight

        def wrapped(j, i, weight):
            before = float(engine.l2.excitatory_neurons[j]._weights_array[i])
            t, pattern = engine.timestep, engine.current_pattern
            after = orig(j, i, weight)
            self.weight_delta_records.append(dict(
                t=t, pattern=pattern, neuron=f'L2E{j}', cause='manual_edit',
                pixel=int(i), pixel_active=None,
                w_before=round(before, 4), delta=round(after - before, 4),
                w_after=round(after, 4)))
            return after
        engine.set_feedforward_weight = wrapped


# ------------------------------------------------------------------- schedules
def build_engine(weight_seed: int, topology_seed: int) -> SimulationEngine:
    kw = dict(DASHBOARD_PRESET)
    kw['seed'] = weight_seed
    kw['topology_seed'] = topology_seed
    return SimulationEngine(**kw)


def run_causal_audit_schedule(weight_seed, topology_seed, schedule,
                              presentation_steps=PRESENTATION_STEPS, engine=None):
    """schedule: list of (pattern_name, total_steps) holds presented in
    order. Each hold is internally chunked into presentation_steps-sized
    sub-windows (floor division; any remainder steps at the end of a hold
    are still physically stepped, just not chunked into their own
    presentation record). Returns (engine, tracer, presentation_log,
    initial_weights). Builds its own disposable engine unless one is
    supplied (never mutates anything outside this call)."""
    if engine is None:
        engine = build_engine(weight_seed, topology_seed)
    tracer = CausalTracer(engine)
    initial_weights = tracer._all_ff_weights()
    presentation_log: list[dict] = []
    idx = 0
    for cycle_no, (pattern, total_steps) in enumerate(schedule):
        engine.set_pattern(pattern)
        n_windows = total_steps // presentation_steps
        for _w in range(n_windows):
            t_start = engine.timestep
            for _s in range(presentation_steps):
                engine.step()
            t_end = engine.timestep
            window = [r for r in tracer.spike_records if t_start <= r['t'] < t_end]
            first = window[0] if window else None
            same_step_tie = bool(first and sum(1 for r in window if r['t'] == first['t']) > 1)
            presentation_log.append(dict(
                presentation_index=idx, cycle=cycle_no, pattern=pattern,
                t_start=t_start, t_end=t_end,
                first_l2e_spiker=first['neuron'] if first else None,
                same_step_tie=same_step_tie))
            idx += 1
        remainder = total_steps - n_windows * presentation_steps
        for _s in range(remainder):
            engine.step()
    return engine, tracer, presentation_log, initial_weights


def run_interleaved_causal_audit(weight_seed, topology_seed, cycles=INTERLEAVED_CYCLES,
                                 presentation_steps=PRESENTATION_STEPS):
    schedule = [(p, presentation_steps) for _c in range(cycles) for p in CYCLE_ORDER]
    return run_causal_audit_schedule(weight_seed, topology_seed, schedule, presentation_steps)


def run_long_hold_causal_audit(weight_seed, topology_seed, schedule=LONG_SCHEDULE,
                               presentation_steps=PRESENTATION_STEPS):
    return run_causal_audit_schedule(weight_seed, topology_seed, schedule, presentation_steps)


# --------------------------------------------------------------------- analysis
def _modal(values):
    """Most-common non-None value; ties broken by sort order (same fix as
    diagnostic_schedule._modal -- removes PYTHONHASHSEED-dependent tie
    resolution)."""
    non_none = [v for v in values if v is not None]
    if not non_none:
        return None
    counts = Counter(non_none)
    top = max(counts.values())
    return min(v for v, c in counts.items() if c == top)


def find_earliest_modal_collision(presentation_log):
    """Chronologically replay `presentation_log` (a list of dicts with at
    least 'presentation_index', 'cycle', 'pattern', 'first_l2e_spiker', in
    chronological order) and, after EVERY presentation, recompute each
    experienced pattern's running modal first-responder from only that
    pattern's own presentations seen so far. The first presentation at which
    any single value is the running modal for two or more DISTINCT pattern
    keys is the earliest CANDIDATE collision -- reported literally, even
    though (by construction) the very first time two patterns have each had
    only n=1 presentation, any coincidental match already counts. This is
    real, not a bug: it is exactly what "the earliest point" means applied
    honestly. Because an n=1-backed match is fragile, this function keeps
    replaying to the END of the log and adds `persisted_to_run_end`: whether
    that SAME neuron is still the running modal for (at least) those same
    two patterns at the final presentation. Observation (the earliest
    literal candidate) and interpretation (did it actually stick) are kept
    as separate fields rather than conflated into one verdict. Purely
    data-driven: no pattern name or neuron id is ever referenced by literal
    value in this function. Returns None if no candidate ever occurs."""
    history_by_pattern = defaultdict(list)
    modal_established_at = defaultdict(list)
    running_modal = {}
    candidate = None
    for rec in presentation_log:
        p = rec['pattern']
        history_by_pattern[p].append(rec['first_l2e_spiker'])
        prev_modal = running_modal.get(p)
        new_modal = _modal(history_by_pattern[p])
        if new_modal != prev_modal:
            modal_established_at[p].append(dict(
                presentation_index=rec['presentation_index'], owner=new_modal,
                previous_owner=prev_modal))
        running_modal[p] = new_modal

        if candidate is None:
            owners_now = {pp: o for pp, o in running_modal.items() if o is not None}
            by_owner = defaultdict(list)
            for pp, o in owners_now.items():
                by_owner[o].append(pp)
            collided = {o: pats for o, pats in by_owner.items() if len(pats) > 1}
            if collided:
                neuron = sorted(collided.keys())[0]
                patterns = sorted(collided[neuron])
                flip_indices = {pp: modal_established_at[pp][-1]['presentation_index']
                                for pp in patterns if modal_established_at.get(pp)}
                captured_pattern = max(flip_indices, key=flip_indices.get) if flip_indices else patterns[-1]
                competitor = None
                if modal_established_at.get(captured_pattern):
                    competitor = modal_established_at[captured_pattern][-1]['previous_owner']
                candidate = dict(
                    presentation_index=rec['presentation_index'], cycle=rec['cycle'],
                    neuron=neuron, patterns_collided=patterns,
                    captured_pattern=captured_pattern, displaced_competitor=competitor,
                    per_pattern_n_so_far={pp: len(history_by_pattern[pp]) for pp in patterns})
    if candidate is None:
        return None
    final_modal = running_modal
    still_collided = all(final_modal.get(p) == candidate['neuron'] for p in candidate['patterns_collided'])
    candidate['persisted_to_run_end'] = still_collided
    candidate['final_modal_owners'] = dict(final_modal)
    return candidate


def find_persistent_ownership_collision(presentation_log):
    """Complement to `find_earliest_modal_collision`: that function reports
    the earliest LITERAL candidate, which is frequently a fragile n=1 flicker
    that later self-corrects (see its own docstring). This function instead
    starts from the run's FINAL running-modal state (least ambiguous: full
    history available) and, only if some neuron owns 2+ patterns AT THE END,
    walks backward to find the earliest presentation index after which that
    exact ownership configuration held continuously through the end of the
    run -- i.e. the onset of the collision that actually stuck, not just the
    first coincidental overlap. Returns None if the run ends with distinct
    ownership (no persistent collision to trace), which is itself a valid,
    common outcome, not an error."""
    history_by_pattern = defaultdict(list)
    running_modal = {}
    modal_established_at = defaultdict(list)
    snapshots = []   # one dict (pattern -> running_modal) per presentation, in order
    for rec in presentation_log:
        p = rec['pattern']
        history_by_pattern[p].append(rec['first_l2e_spiker'])
        prev_modal = running_modal.get(p)
        new_modal = _modal(history_by_pattern[p])
        if new_modal != prev_modal:
            modal_established_at[p].append(dict(
                presentation_index=rec['presentation_index'], owner=new_modal,
                previous_owner=prev_modal))
        running_modal[p] = new_modal
        snapshots.append(dict(running_modal))

    if not snapshots:
        return None
    final_modal = snapshots[-1]
    by_owner = defaultdict(list)
    for p, o in final_modal.items():
        if o is not None:
            by_owner[o].append(p)
    final_collisions = {o: sorted(pats) for o, pats in by_owner.items() if len(pats) > 1}
    if not final_collisions:
        return None

    neuron = sorted(final_collisions.keys())[0]
    patterns = final_collisions[neuron]

    onset_per_pattern = {}
    for p in patterns:
        onset = 0
        for k in range(len(snapshots) - 1, -1, -1):
            if snapshots[k].get(p) != neuron:
                onset = k + 1
                break
        onset_per_pattern[p] = onset
    captured_pattern = max(onset_per_pattern, key=onset_per_pattern.get)
    onset_idx = onset_per_pattern[captured_pattern]
    competitor = None
    if onset_idx > 0:
        competitor = snapshots[onset_idx - 1].get(captured_pattern)

    return dict(
        presentation_index=presentation_log[onset_idx]['presentation_index'],
        cycle=presentation_log[onset_idx]['cycle'],
        neuron=neuron, patterns_collided=patterns, captured_pattern=captured_pattern,
        displaced_competitor=competitor, onset_per_pattern=onset_per_pattern,
        final_modal_owners=dict(final_modal))


def reconstruct_weight(initial_weights, weight_delta_records, neuron, pixel, t_cutoff):
    """Sum every recorded delta (of ANY cause, including residual_
    unattributed -- it is a real delta, just one the patches didn't predict)
    for (neuron, pixel) up to and including t_cutoff, starting from the
    engine's true pre-run weight. Used both for causal-chain reporting and
    for the reconciliation test against the engine's own live weights."""
    j = int(neuron[3:])
    w = initial_weights[(j, pixel)]
    for r in weight_delta_records:
        if r['neuron'] == neuron and r['pixel'] == pixel and r['t'] <= t_cutoff:
            w += r['delta']
    return w


def analyze_center_dominance_vs_collision(tracer, initial_weights, tyrant, competitor, collision_t_cutoff):
    """Walk the tyrant's and the displaced competitor's CENTER_PIXEL weight
    chronologically and find the first t after which the tyrant's center
    weight stays strictly ahead of the competitor's for every subsequent
    recorded event touching either neuron's center synapse (a PERSISTENT
    lead, not a momentary crossing). Compares that t against the collision's
    own presentation-end cutoff to answer "does center-weight dominance
    precede or follow second-pattern acquisition" -- observation only, no
    causal claim beyond the chronological ordering."""
    if competitor is None:
        return dict(applicable=False,
                   reason='captured pattern had no prior distinct owner to displace')
    events = [r for r in tracer.weight_delta_records
             if r['pixel'] == CENTER_PIXEL and r['neuron'] in (tyrant, competitor)]
    events.sort(key=lambda r: r['t'])
    tyrant_w = initial_weights[(int(tyrant[3:]), CENTER_PIXEL)]
    competitor_w = initial_weights[(int(competitor[3:]), CENTER_PIXEL)]
    diffs = []
    for r in events:
        if r['neuron'] == tyrant:
            tyrant_w = r['w_after']
        else:
            competitor_w = r['w_after']
        diffs.append((r['t'], tyrant_w - competitor_w, r['cause']))
    dominance_t = None
    dominance_cause = None
    for k, (t, diff, cause) in enumerate(diffs):
        if diff > 0 and all(d > 0 for _, d, _ in diffs[k:]):
            dominance_t, dominance_cause = t, cause
            break
    if dominance_t is None:
        return dict(applicable=True, dominance_established=False,
                   note='tyrant never achieves a persistent center-weight lead '
                        'over the displaced competitor in the recorded events')
    order = 'precedes' if dominance_t <= collision_t_cutoff else 'follows'
    return dict(applicable=True, dominance_established=True, dominance_t=dominance_t,
               dominance_cause=dominance_cause, collision_t_cutoff=collision_t_cutoff,
               relationship=f'center-weight dominance {order} second-pattern acquisition')


def extract_causal_chain(tracer, initial_weights, collision, presentation_log):
    """Slice the tracer's full records down to just the tyrant + its
    displaced competitor, up to and including the deciding presentation --
    the full chronological answer to 'trace the first ownership collision'.
    Returns None if the run had no collision (documented honestly, never
    forced)."""
    if collision is None:
        return None
    tyrant = collision['neuron']
    competitor = collision['displaced_competitor']
    t_cutoff = next(r['t_end'] for r in presentation_log
                   if r['presentation_index'] == collision['presentation_index'])

    def row_at(nid, t):
        if nid is None:
            return None
        j = int(nid[3:])
        return {i: round(reconstruct_weight(initial_weights, tracer.weight_delta_records, nid, i, t), 3)
               for i in range(N_PIX)}

    def events_for(nid, records):
        if nid is None:
            return []
        return [r for r in records if r['neuron'] == nid and r['t'] <= t_cutoff]

    l2i_events = [d for d in tracer.l2i_delivery_records if d['fire_t'] <= t_cutoff
                 and any(tgt['id'] in (tyrant, competitor) for tgt in d['targets'])]

    dominance = analyze_center_dominance_vs_collision(tracer, initial_weights, tyrant, competitor, t_cutoff)

    return dict(
        collision=collision, t_cutoff=t_cutoff, tyrant=tyrant, competitor=competitor,
        initial_weights=dict(tyrant=row_at(tyrant, -1), competitor=row_at(competitor, -1)),
        weights_immediately_before_collision=dict(
            tyrant=row_at(tyrant, t_cutoff), competitor=row_at(competitor, t_cutoff)),
        spike_events=dict(tyrant=events_for(tyrant, tracer.spike_records),
                          competitor=events_for(competitor, tracer.spike_records)),
        weight_delta_events=dict(tyrant=events_for(tyrant, tracer.weight_delta_records),
                                 competitor=events_for(competitor, tracer.weight_delta_records)),
        l2i_delivery_events_involving_either=l2i_events,
        center_dominance_vs_collision=dominance,
    )


def analyze_run(engine, tracer, presentation_log, schedule_patterns):
    by_pattern = {p: [r for r in presentation_log if r['pattern'] == p] for p in schedule_patterns}
    per_pattern = {}
    running_modal = {}
    for p, recs in by_pattern.items():
        firsts = [r['first_l2e_spiker'] for r in recs]
        n = len(firsts)
        modal = _modal(firsts)
        non_none = [f for f in firsts if f is not None]
        consistency = (non_none.count(modal) / n) if (modal is not None and n) else 0.0
        ties = sum(1 for r in recs if r['same_step_tie'])
        no_resp = sum(1 for f in firsts if f is None)
        per_pattern[p] = dict(modal_owner=modal, consistency=round(consistency, 3),
                              ambiguity_rate=round(ties / n, 3) if n else None,
                              no_response_rate=round(no_resp / n, 3) if n else None,
                              n_presentations=n)
        running_modal[p] = modal

    owners = [o for o in running_modal.values() if o is not None]
    distinct_owners = len(set(owners))
    collisions = {o: [p for p, m in running_modal.items() if m == o]
                 for o in set(owners) if owners.count(o) > 1}

    forgetting = {}
    for p, recs in by_pattern.items():
        half = len(recs) // 2
        m1 = _modal([r['first_l2e_spiker'] for r in recs[:half]])
        m2 = _modal([r['first_l2e_spiker'] for r in recs[half:]])
        forgetting[p] = dict(first_half_owner=m1, second_half_owner=m2,
                             changed=bool(m1 and m2 and m1 != m2))

    total_first = sum(1 for r in presentation_log if r['first_l2e_spiker'])
    tyrant_share = {}
    if total_first:
        counts = Counter(r['first_l2e_spiker'] for r in presentation_log if r['first_l2e_spiker'])
        tyrant_share = {nid: round(c / total_first, 3) for nid, c in counts.items()}

    status = {f'L2E{j}': engine._l2e_status(j)['status'] for j in range(N_OUT)}
    active_count = sum(1 for s in status.values() if s == 'active')
    never_fired = [nid for nid, s in status.items() if s == 'unrecruited']

    final_weights = tracer._all_ff_weights()
    center_peripheral_ratio = {}
    for j in range(N_OUT):
        nid = f'L2E{j}'
        center_w = final_weights[(j, CENTER_PIXEL)]
        periph = [final_weights[(j, i)] for i in range(N_PIX) if i != CENTER_PIXEL]
        periph_mean = float(np.mean(periph)) if periph else 0.0
        center_peripheral_ratio[nid] = dict(
            center_weight=round(center_w, 3), peripheral_mean_weight=round(periph_mean, 3),
            ratio=round(center_w / periph_mean, 3) if periph_mean > 1e-9 else None)

    first_spike_latency = {}
    for p, recs in by_pattern.items():
        lats = []
        for r in recs:
            window = [sr for sr in tracer.spike_records if r['t_start'] <= sr['t'] < r['t_end']]
            if window:
                lats.append(window[0]['t'] - r['t_start'])
        first_spike_latency[p] = dict(mean=round(float(np.mean(lats)), 3) if lats else None, n=len(lats))

    cause_counts = Counter(r['cause'] for r in tracer.weight_delta_records)
    cause_magnitude = defaultdict(float)
    for r in tracer.weight_delta_records:
        cause_magnitude[r['cause']] += abs(r['delta'])
    cause_summary = {c: dict(count=cause_counts[c], total_abs_magnitude=round(cause_magnitude[c], 3))
                     for c in cause_counts}

    return dict(
        per_pattern=per_pattern, distinct_owners=distinct_owners, collisions=collisions,
        forgetting=forgetting, tyrant_share=tyrant_share,
        l2e_status=status, active_count=active_count, never_fired=never_fired,
        center_peripheral_ratio=center_peripheral_ratio,
        first_spike_latency=first_spike_latency,
        weight_delta_cause_summary=cause_summary,
        synapse_delta_records=len(tracer.weight_delta_records),
        target_neuron_applications=len(tracer.target_applications),
        physical_l2i_deliveries=len(tracer.l2i_delivery_records),
        residual_unattributed_count=tracer._residual_seen,
    )


# ------------------------------------------------------------------------ main
# Curated illustrative examples for the COMMITTED results file (full causal
# chains for every seed/topology combo with a collision would be tens of MB
# -- see Phase 13b's own "per-event full logs are disposable, not committed"
# convention). The `runs` list still reports EVERY seed/topology combo's own
# persistent_ownership_collision summary (neuron/patterns/onset) in full;
# only the deep per-event trace is limited to these few seeds. Chosen to
# show: two independent full (4/4) collapses with DIFFERENT tyrant neurons
# (generality, not one id-specific artifact), the earliest-onset partial
# (3/4) collision, and one more partial collision for comparison.
EXAMPLE_SEEDS_INTERLEAVED = {(6, 1), (7, 1), (9, 1), (3, 1)}
EXAMPLE_SEEDS_LONG_HOLD = {(3, 1), (5, 1)}
MAX_EVENTS_PER_CHAIN = 150


def _curate_causal_chains(chains, keep_seeds):
    kept, dropped = [], 0
    for chain in chains:
        key = (chain['weight_seed'], chain['topology_seed'])
        if key not in keep_seeds:
            dropped += 1
            continue
        for event_key in ('spike_events', 'weight_delta_events'):
            counts = {}
            for who in ('tyrant', 'competitor'):
                lst = chain[event_key].get(who) or []
                counts[who] = len(lst)
                chain[event_key][who] = lst[-MAX_EVENTS_PER_CHAIN:]
            chain[f'{event_key}_total_count'] = counts
        lst = chain['l2i_delivery_events_involving_either']
        chain['l2i_delivery_events_involving_either_total_count'] = len(lst)
        chain['l2i_delivery_events_involving_either'] = lst[-MAX_EVENTS_PER_CHAIN:]
        kept.append(chain)
    note = (f'{dropped} additional causal chains (one per other seed/topology combo '
           f'with a persistent collision) were computed but are not committed here, '
           f'to keep this file a reasonable size -- they reproduce exactly, '
           f'deterministically, by re-running this script with the same '
           f'weight_seed/topology_seed (see test_repeated_identical_seeds_are_'
           f'deterministic). The runs list above already reports EVERY seed/'
           f'topology combo\'s own persistent_ownership_collision summary '
           f'(neuron, patterns, onset) in full.')
    return kept, note


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    t0 = time.time()

    interleaved_runs = []
    interleaved_causal_chains = []
    for ws in WEIGHT_SEEDS:
        for ts in TOPOLOGY_SEEDS:
            engine, tracer, plog, initial_w = run_interleaved_causal_audit(ws, ts)
            summary = analyze_run(engine, tracer, plog, CYCLE_ORDER)
            summary['weight_seed'], summary['topology_seed'] = ws, ts
            candidate = find_earliest_modal_collision(plog)
            persistent = find_persistent_ownership_collision(plog)
            summary['earliest_candidate_collision'] = candidate
            summary['persistent_ownership_collision'] = persistent
            interleaved_runs.append(summary)
            if persistent is not None:
                chain = extract_causal_chain(tracer, initial_w, persistent, plog)
                chain['weight_seed'], chain['topology_seed'] = ws, ts
                interleaved_causal_chains.append(chain)
                # Keep the (small) dominance-vs-collision verdict on EVERY
                # run's own compact summary too, not just the curated example
                # chains below -- so the aggregate "does center dominance
                # precede acquisition" finding survives for all 30 runs
                # regardless of which full chains get curated out of the
                # committed JSON.
                summary['center_dominance_vs_collision'] = chain['center_dominance_vs_collision']
            print(f"[interleaved] ws={ws} ts={ts} distinct_owners={summary['distinct_owners']}/4 "
                 f"candidate_persisted={candidate['persisted_to_run_end'] if candidate else None} "
                 f"persistent_collision={'yes' if persistent else 'no'}  ({time.time() - t0:.1f}s elapsed)")

    long_hold_runs = []
    long_hold_causal_chains = []
    for ws in WEIGHT_SEEDS:
        for ts in TOPOLOGY_SEEDS:
            engine, tracer, plog, initial_w = run_long_hold_causal_audit(ws, ts)
            patterns_here = [p for p, _ in LONG_SCHEDULE]
            summary = analyze_run(engine, tracer, plog, patterns_here)
            summary['weight_seed'], summary['topology_seed'] = ws, ts
            candidate = find_earliest_modal_collision(plog)
            persistent = find_persistent_ownership_collision(plog)
            summary['earliest_candidate_collision'] = candidate
            summary['persistent_ownership_collision'] = persistent
            long_hold_runs.append(summary)
            if persistent is not None:
                chain = extract_causal_chain(tracer, initial_w, persistent, plog)
                chain['weight_seed'], chain['topology_seed'] = ws, ts
                long_hold_causal_chains.append(chain)
                summary['center_dominance_vs_collision'] = chain['center_dominance_vs_collision']
            print(f"[long_hold] ws={ws} ts={ts} distinct_owners={summary['distinct_owners']}/2 "
                 f"persistent_collision={'yes' if persistent else 'no'}  ({time.time() - t0:.1f}s elapsed)")

    kept_il, note_il = _curate_causal_chains(interleaved_causal_chains, EXAMPLE_SEEDS_INTERLEAVED)
    kept_lh, note_lh = _curate_causal_chains(long_hold_causal_chains, EXAMPLE_SEEDS_LONG_HOLD)

    summary_out = dict(
        weight_seeds=WEIGHT_SEEDS, topology_seeds=TOPOLOGY_SEEDS,
        interleaved_cycles=INTERLEAVED_CYCLES, long_schedule=LONG_SCHEDULE,
        interleaved=dict(runs=interleaved_runs, causal_chains=kept_il, causal_chains_note=note_il),
        long_hold=dict(runs=long_hold_runs, causal_chains=kept_lh, causal_chains_note=note_lh),
        runtime_seconds=round(time.time() - t0, 1),
    )
    with open(os.path.join(out_dir, 'phase27_l2_ownership_causal_audit_results.json'), 'w') as f:
        json.dump(summary_out, f, indent=2, default=str)

    n_interleaved_persistent = sum(1 for r in interleaved_runs if r['persistent_ownership_collision'])
    n_long_hold_persistent = sum(1 for r in long_hold_runs if r['persistent_ownership_collision'])
    print(f"\nDone in {time.time() - t0:.1f}s. "
         f"Interleaved persistent collisions: {n_interleaved_persistent}/{len(interleaved_runs)}. "
         f"Long-hold persistent collisions: {n_long_hold_persistent}/{len(long_hold_runs)}.")


if __name__ == "__main__":
    main()
