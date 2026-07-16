"""
Phase 28A -- local common-input feasibility (MEASUREMENT/OFFLINE ONLY).

Tests whether a purely local presynaptic activity trace can prevent
universal-feature (e.g. the always-active center pixel) reinforcement
WITHOUT hardcoding a pixel index -- offline/default-off only. Nothing in
`backend/simulation.py` or `backend/presets.py` is touched. No prediction/PC
path, inhibition, physical sensory charge, inactive-input depression, loser
depression, random initialization, or default is modified.

TRACE (per pixel i, driven ONLY by physical L1E spikes, read post-hoc off
`engine.spiked[f'L1E{i}']` -- never off the raw external input_vec):

    c_i <- c_i + (s_i - c_i) / tau_c

GATE (applied ONLY to the POSITIVE-potentiation half of an L2E's own
self-spike update -- never to physical transmission/receive_input, never to
`self_spike_depression_inactive`, never to `l2i_loser_depression`):

    g_i = max(g_min, 1 - c_i)

Causal ordering: the gate value used during step t's fire() events reflects
the trace as it stood at the END of step t-1 (i.e. built only from spikes
strictly before this step's own learning event) -- the trace is updated
AFTER `engine.step()` returns, using that step's own just-observed spikes,
so nothing "sees the future."

Implementation is entirely via monkeypatches on top of a real
`SimulationEngine` (same technique as Phase 27's `CausalTracer` and Phase
13b's distance override) -- there is no new engine flag in this phase.
`GatedFirePatch` scales ONLY the genuine positive movement `fire()` already
produced for participating (active) synapses; it never touches
non-participating synapses (that is where inactive-input depression lives,
untouched) and never touches `apply_delayed_inhibition` (loser depression,
untouched). `OracleFreezePatch` (a labeled, deliberately hardcoded CONTROL
only -- never a candidate mechanism) reverts one hardcoded pixel's weight to
its pre-event value after every fire()/apply_delayed_inhibition call, on
every L2E, for the whole run -- an upper-bound reference for "what if this
exact synapse could never move at all."

PATTERN SETS (swapped in via the module-level `backend.simulation.PATTERNS`
global for the duration of one pattern-set's runs, then restored --
`set_pattern()` resolves that name fresh from its own module globals on
every call, so this affects exactly what `set_pattern` sees without
touching the file):

  - `standard`  -- the real PATTERNS (pixel 4, the true center, is the
    universal feature, active in all four trained patterns).
  - `shifted`   -- every PATTERNS vector with pixel 0 and pixel 4 SWAPPED
    (a structure-preserving relabeling of the input grid -- pairwise overlap
    counts are exactly unchanged, only which INDEX is universal moves, from
    4 to 0). Tests whether center-pixel-specific effects generalize to any
    universal pixel, or are secretly still keyed to index 4.
  - `no_universal` -- the four existing held-out PROBES (`row 0`, `row 2`,
    `col 0`, `col 2`; a plain dict copy, PROBES itself untouched) used here
    as TRAINABLE patterns for this diagnostic only. No pixel is active in
    more than 2 of these 4 patterns -- there is no universal feature at all.

CONDITIONS:
  1. `baseline`      -- completely unmodified engine.
  2. `oracle`        -- ORACLE CONTROL ONLY, hardcodes the pattern set's own
                        universal pixel index (4 for standard, 0 for
                        shifted; skipped entirely for no_universal, which
                        has none) and freezes it. Never a candidate
                        mechanism, never claimed as a solution.
  3. `gate:<tau_c>:<g_min>` -- the local trace gate, tau_c in {40,80,160,
     320}, g_min in {0.1,0.25,0.5} (12 combinations), no pixel index or
     pattern label used anywhere in the gate itself.

GRID: 30 distinct weight seeds, ONE topology seed (topology_seed is a
confirmed no-op under DASHBOARD_PRESET's legacy_distance_compat=True --
Phase 13b's own finding, reconfirmed again in Phase 27), both the
equal-interleaved and long-hold schedules, all three pattern sets. The
entire grid is reported -- no per-seed selection, no hidden tuning.

Runtime note: INTERLEAVED_CYCLES is reduced from Phase 27's 40 to 8 (32
presentations, 640 steps) purely for tractability across this much larger
condition grid (3 pattern sets x 2 schedules x up to 14 conditions x 30
seeds = 2,460 runs) -- applied IDENTICALLY to every condition/pattern-set/
seed, never varied per-condition, so it cannot bias any comparison.
"""

from __future__ import annotations

import contextlib
import itertools
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backend.simulation as bsim  # noqa: E402
from backend.simulation import N_OUT, N_PIX, PROBES  # noqa: E402
from backend.presets import DASHBOARD_PRESET  # noqa: E402
from phase27_l2_ownership_causal_audit import (  # noqa: E402
    CausalTracer, _modal, analyze_run, find_earliest_modal_collision,
    find_persistent_ownership_collision, run_causal_audit_schedule,
)

WEIGHT_SEEDS = list(range(1, 31))
TOPOLOGY_SEED = 1
PRESENTATION_STEPS = 20
INTERLEAVED_CYCLES = 8
LONG_SCHEDULE_STEPS = (600, 200)

TAU_C_GRID = [40, 80, 160, 320]
G_MIN_GRID = [0.1, 0.25, 0.5]


# --------------------------------------------------------------- pattern sets
def _swap_pixels(vec, i, j):
    v = list(vec)
    v[i], v[j] = v[j], v[i]
    return v


_STANDARD = dict(bsim.PATTERNS)
_SHIFTED = {name: _swap_pixels(vec, 0, 4) for name, vec in _STANDARD.items()}
_NO_UNIVERSAL = dict(PROBES)

assert all(_STANDARD[p][4] == 1 for p in _STANDARD), "standard set must be universal at pixel 4"
assert all(_SHIFTED[p][0] == 1 for p in _SHIFTED), "shifted set must be universal at pixel 0"
_no_universal_counts = [sum(_NO_UNIVERSAL[p][i] for p in _NO_UNIVERSAL) for i in range(N_PIX)]
assert max(_no_universal_counts) < len(_NO_UNIVERSAL), "no_universal set must have no pixel active in all patterns"

PATTERN_SETS = {
    'standard': dict(patterns=_STANDARD, cycle_order=['row 1', 'col 1', 'diag \\', 'diag /'],
                     long_schedule=[('row 1', LONG_SCHEDULE_STEPS[0]), ('col 1', LONG_SCHEDULE_STEPS[1])],
                     universal_pixel=4),
    'shifted': dict(patterns=_SHIFTED, cycle_order=['row 1', 'col 1', 'diag \\', 'diag /'],
                    long_schedule=[('row 1', LONG_SCHEDULE_STEPS[0]), ('col 1', LONG_SCHEDULE_STEPS[1])],
                    universal_pixel=0),
    'no_universal': dict(patterns=_NO_UNIVERSAL, cycle_order=['row 0', 'col 0', 'row 2', 'col 2'],
                         long_schedule=[('row 0', LONG_SCHEDULE_STEPS[0]), ('col 0', LONG_SCHEDULE_STEPS[1])],
                         universal_pixel=None),
}


@contextlib.contextmanager
def _patterns_swapped(new_patterns):
    """set_pattern() resolves the bare name `PATTERNS` fresh from
    backend.simulation's own module globals on every call -- reassigning the
    module attribute (not mutating the dict in place, so other modules'
    already-bound imports of the ORIGINAL dict are left untouched) changes
    exactly what set_pattern sees, for the duration of this context, with no
    file edit and no change to any default. Restored unconditionally."""
    original = bsim.PATTERNS
    bsim.PATTERNS = new_patterns
    try:
        yield
    finally:
        bsim.PATTERNS = original


def build_engine(weight_seed: int, topology_seed: int = TOPOLOGY_SEED):
    kw = dict(DASHBOARD_PRESET)
    kw['seed'] = weight_seed
    kw['topology_seed'] = topology_seed
    return bsim.SimulationEngine(**kw)


# --------------------------------------------------------------- condition patches
class GateHolder:
    """Mutable per-pixel gate array, updated once per step by
    `_patch_trace_update` and read by every L2E's `_patch_gated_fire`."""
    __slots__ = ('g',)

    def __init__(self, n_pix):
        self.g = np.ones(n_pix)


def _patch_gated_fire(n, holder):
    """Scales ONLY the genuine positive movement fire() already produced for
    PARTICIPATING (active) synapses, by that pixel's current gate value.
    Non-participating synapses (inactive-input depression) and any negative
    movement are left completely untouched -- the gate never creates or
    amplifies depression, only dampens potentiation. apply_delayed_inhibition
    (loser depression) is never patched by this function at all."""
    orig = n.fire

    def wrapped():
        w_before = n._weights_array.copy()
        orig()
        w_after = n._weights_array.copy()
        participating = n._last_input_spikes > 0.5
        pos = w_before > 0
        active_pos = np.nonzero(pos & participating)[0]
        for i in active_pos:
            natural_delta = w_after[i] - w_before[i]
            if natural_delta > 0.0:
                n._weights_array[i] = w_before[i] + holder.g[i] * natural_delta
    n.fire = wrapped


def _patch_trace_update(engine, holder, tau_c, g_min):
    """Updates the local per-pixel trace c AFTER each real step, from that
    step's own just-observed PHYSICAL L1E spikes (engine.spiked['L1Ei'] --
    never the raw external input_vec), then refreshes the gate holder for
    the NEXT step's fire() events. Causal: a step's own fire() events read
    the gate as it stood at the end of the PREVIOUS step."""
    orig_step = engine.step
    c = np.zeros(N_PIX)

    def wrapped():
        result = orig_step()
        s = np.array([1.0 if engine.spiked.get(f'L1E{i}', False) else 0.0 for i in range(N_PIX)])
        c[:] = c + (s - c) / tau_c
        holder.g[:] = np.maximum(g_min, 1.0 - c)
        return result
    engine.step = wrapped


def _patch_oracle_freeze(n, pixel):
    """ORACLE CONTROL ONLY -- hardcodes `pixel` and reverts its weight to
    the pre-event value after EVERY fire() and EVERY apply_delayed_inhibition
    call, on this one neuron, for the whole run. A deliberate cheat (this is
    the only place in this phase that references a specific pixel index) to
    establish an upper bound, never a candidate mechanism."""
    orig_fire = n.fire
    orig_adi = n.apply_delayed_inhibition

    def wrapped_fire():
        frozen = float(n._weights_array[pixel])
        orig_fire()
        n._weights_array[pixel] = frozen
    n.fire = wrapped_fire

    def wrapped_adi(magnitude):
        frozen = float(n._weights_array[pixel])
        out = orig_adi(magnitude)
        n._weights_array[pixel] = frozen
        return out
    n.apply_delayed_inhibition = wrapped_adi


def apply_condition(engine, condition, universal_pixel):
    """condition is 'baseline', 'oracle', or ('gate', tau_c, g_min). Returns
    the GateHolder for gate conditions (caller must also call
    _patch_trace_update), else None."""
    if condition == 'baseline':
        return None
    if condition == 'oracle':
        if universal_pixel is None:
            raise ValueError('oracle condition requires a universal pixel')
        for n in engine.l2.excitatory_neurons:
            _patch_oracle_freeze(n, universal_pixel)
        return None
    kind, tau_c, g_min = condition
    assert kind == 'gate'
    holder = GateHolder(N_PIX)
    for n in engine.l2.excitatory_neurons:
        _patch_gated_fire(n, holder)
    _patch_trace_update(engine, holder, tau_c, g_min)
    return holder


def conditions_for(pattern_set_key):
    conds = ['baseline']
    if PATTERN_SETS[pattern_set_key]['universal_pixel'] is not None:
        conds.append('oracle')
    for tau_c, g_min in itertools.product(TAU_C_GRID, G_MIN_GRID):
        conds.append(('gate', tau_c, g_min))
    return conds


def condition_label(condition):
    if isinstance(condition, str):
        return condition
    return f'gate:tau_c={condition[1]}:g_min={condition[2]}'


# --------------------------------------------------------------------- run + analyze
def run_one(pattern_set_key, schedule_kind, condition, weight_seed):
    spec = PATTERN_SETS[pattern_set_key]
    with _patterns_swapped(spec['patterns']):
        engine = build_engine(weight_seed, TOPOLOGY_SEED)
        apply_condition(engine, condition, spec['universal_pixel'])
        if schedule_kind == 'interleaved':
            schedule = [(p, PRESENTATION_STEPS) for _c in range(INTERLEAVED_CYCLES)
                       for p in spec['cycle_order']]
            schedule_patterns = spec['cycle_order']
        else:
            schedule = spec['long_schedule']
            schedule_patterns = [p for p, _ in spec['long_schedule']]
        engine, tracer, plog, initial_w = run_causal_audit_schedule(
            weight_seed, TOPOLOGY_SEED, schedule, PRESENTATION_STEPS, engine=engine)
    return engine, tracer, plog, initial_w, schedule_patterns


def universal_peripheral_ratio(final_weights, universal_pixel):
    """Mean-over-L2E ratio of the universal pixel's weight to the mean of
    every OTHER pixel's weight, for whichever pixel is universal in this
    pattern set (None for no_universal -- reported as N/A, never guessed)."""
    if universal_pixel is None:
        return None
    per_neuron = []
    for j in range(N_OUT):
        u = final_weights[(j, universal_pixel)]
        others = [final_weights[(j, i)] for i in range(N_PIX) if i != universal_pixel]
        m = float(np.mean(others)) if others else 0.0
        per_neuron.append(u / m if m > 1e-9 else None)
    valid = [r for r in per_neuron if r is not None]
    return dict(mean_ratio=round(float(np.mean(valid)), 3) if valid else None,
               per_neuron=[round(r, 3) if r is not None else None for r in per_neuron])


def peripheral_weight_summary(final_weights, universal_pixel, active_neuron_ids):
    """Mean final weight on non-universal pixels, restricted to neurons that
    fired at least once this run (active_neuron_ids) -- the "was peripheral
    learning retained" observable. universal_pixel=None means every pixel
    counts as peripheral (no_universal set)."""
    vals = []
    for j in range(N_OUT):
        if f'L2E{j}' not in active_neuron_ids:
            continue
        for i in range(N_PIX):
            if universal_pixel is not None and i == universal_pixel:
                continue
            vals.append(final_weights[(j, i)])
    return round(float(np.mean(vals)), 3) if vals else None


def analyze_condition_run(engine, tracer, plog, schedule_patterns, universal_pixel):
    base = analyze_run(engine, tracer, plog, schedule_patterns)
    final_weights = tracer._all_ff_weights()
    active_ids = [nid for nid, s in base['l2e_status'].items() if s != 'unrecruited']
    persistent = find_persistent_ownership_collision(plog)
    candidate = find_earliest_modal_collision(plog)
    base['persistent_ownership_collision'] = persistent
    base['earliest_candidate_collision'] = candidate
    base['universal_peripheral_ratio'] = universal_peripheral_ratio(final_weights, universal_pixel)
    base['peripheral_weight_mean_active_neurons'] = peripheral_weight_summary(
        final_weights, universal_pixel, active_ids)
    # same_step_tie / ambiguity across ALL presentations this run (distinct
    # from per-pattern ambiguity_rate already in per_pattern).
    ties = sum(1 for r in plog if r['same_step_tie'])
    base['overall_ambiguity_rate'] = round(ties / len(plog), 4) if plog else None
    return base


# ------------------------------------------------------------------------ main
def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    t0 = time.time()
    results = []
    n_total = 0
    for pattern_set_key in ('standard', 'shifted', 'no_universal'):
        conds = conditions_for(pattern_set_key)
        for schedule_kind in ('interleaved', 'long_hold'):
            for condition in conds:
                for ws in WEIGHT_SEEDS:
                    engine, tracer, plog, initial_w, schedule_patterns = run_one(
                        pattern_set_key, schedule_kind, condition, ws)
                    universal_pixel = PATTERN_SETS[pattern_set_key]['universal_pixel']
                    summary = analyze_condition_run(engine, tracer, plog, schedule_patterns, universal_pixel)
                    summary.update(pattern_set=pattern_set_key, schedule=schedule_kind,
                                   condition=condition_label(condition), weight_seed=ws,
                                   topology_seed=TOPOLOGY_SEED)
                    results.append(summary)
                    n_total += 1
                print(f"[{pattern_set_key}/{schedule_kind}] {condition_label(condition)} "
                     f"done ({n_total} runs, {time.time() - t0:.1f}s elapsed)")

    with open(os.path.join(out_dir, 'phase28a_local_common_input_feasibility_results.json'), 'w') as f:
        json.dump(dict(weight_seeds=WEIGHT_SEEDS, topology_seed=TOPOLOGY_SEED,
                       interleaved_cycles=INTERLEAVED_CYCLES, tau_c_grid=TAU_C_GRID,
                       g_min_grid=G_MIN_GRID, runtime_seconds=round(time.time() - t0, 1),
                       results=results), f, indent=2, default=str)
    print(f"\nDone in {time.time() - t0:.1f}s. {n_total} total runs.")


if __name__ == "__main__":
    main()
