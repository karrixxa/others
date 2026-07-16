"""
Phase 29 -- FSCI/ISM centered/covariance encoder ownership gate
(MEASUREMENT/OFFLINE ONLY, no engine flag, no default changed).

The prior session's own centered/covariance-encoder runs
(`/tmp/l2-commonness-budget-review/audit.py`) are not accessible from this
session (isolated sandbox, confirmed gone even after those processes
finished) -- per explicit user direction, this phase implements and runs the
SAME candidate rule from scratch instead of guessing at their numbers:

    x_bar_i(t+1) = (1-alpha) x_bar_i(t) + alpha x_i(t)      (leaky trace)
    s_i          = x_i - x_bar_i                             (centered signal)
    delta_w_ji   = eta * FE_j * (1 - w_ji/w_max)^2 * s_i      (per synapse)

`x_i(t)` is the PHYSICAL L1E_i spike this step (`n._last_input_spikes[i]`,
the same field every existing rule already reads -- never the raw external
input_vec). `x_bar_i` is ONE shared per-pixel trace (a presynaptic-side
quantity, identical for every downstream L2E, matching Phase 28A's `c_i`
convention). `FE_j` is this neuron's OWN EXISTING `_structural_free_energy_
gate()` (no new quantity). `w_max`/`w_min` are the neuron's own existing
`excitatory_saturation_cap`/`min_positive_weight` bounds. The update is
gated on the postsynaptic neuron's OWN physical spike (`fire()`), matching
the ONE convention every other learning rule in this codebase already uses
(signed-spike rule, PC decoder rule) -- this is a deliberate, documented
design choice, not an oversight: introducing a continuously-running
(non-spike-triggered) plasticity convention would itself be a bigger,
independent change this gate does not test.

This REPLACES the existing per-synapse update for L2E neurons in the
`centered` condition only, by monkeypatching `Neuron._update_weights`
(never editing `snn/rules/excitatory.py` or `backend/simulation.py`) --
offline, exactly like Phase 27/28A's own instrumentation technique. Loser
depression (the STRUCTURAL weight-depression half of `apply_delayed_
inhibition`) is OFF for the centered condition (`loser_depression=False`),
per instruction -- retained ON, unchanged, for the `legacy` control. The
transient membrane subtraction and L2I hard-reset (the PHYSICAL competition)
are untouched in both conditions -- `loser_depression=False` only disables
the structural weight-depression block inside `apply_delayed_inhibition`
(verified directly against `neuron_flexible.py`), never the membrane event.

PREREGISTERED VALUES (chosen and written down BEFORE running this
experiment, not fit to its own results):

  - alpha = 1/80 = 0.0125. Derived from Phase 28A's OWN prior, independent
    grid: tau_c=80 was the one value that generalized across BOTH the
    standard (pixel 4) and shifted (pixel 0) pattern sets on the
    interleaved schedule (see Phase28A_Local_Common_Input_Feasibility.md)
    -- the best available evidence-based choice from a DIFFERENT, already-
    completed experiment, not tuned against this one.
  - eta: reuses each neuron's own EXISTING `learning_rate` (DASHBOARD_
    PRESET's `l2e_lr_frac * weight_cap`) unchanged -- no new free parameter.

Grid: 30 weight seeds x 1 topology seed (confirmed inert) x 2 conditions
(legacy, centered) x 2 schedules (interleaved, long-hold) = 120 runs, all
reported. Reuses Phase 27's `run_causal_audit_schedule`/`analyze_run`/
`find_persistent_ownership_collision` unchanged.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.simulation import N_OUT, N_PIX, SimulationEngine  # noqa: E402
from backend.presets import DASHBOARD_PRESET  # noqa: E402
from diagnostic_schedule import CYCLE_ORDER, PRESENTATION_STEPS  # noqa: E402
from phase27_l2_ownership_causal_audit import (  # noqa: E402
    analyze_run, find_earliest_modal_collision, find_persistent_ownership_collision,
    run_causal_audit_schedule,
)

WEIGHT_SEEDS = list(range(1, 31))
TOPOLOGY_SEED = 1
INTERLEAVED_CYCLES = 40          # Phase 27's own validated convention
LONG_SCHEDULE = [('row 1', 600), ('col 1', 200)]
ALPHA = 1.0 / 80.0               # preregistered -- see module docstring
CENTER_PIXEL = 4


class XBarHolder:
    """Mutable shared per-pixel presynaptic trace x_bar, updated once per
    step from that step's own physical L1E spikes (never the raw input_vec)."""
    __slots__ = ('x_bar',)

    def __init__(self, n_pix):
        self.x_bar = np.zeros(n_pix)


def _centered_update(n, v_pre, holder):
    """Replaces the neuron's normal excitatory rule for the 'centered'
    condition. Reads ONLY this neuron's own _last_input_spikes/_weights_
    array/structural-FE-gate and the shared presynaptic trace -- no cross-
    neuron state, no pattern label, no owner table."""
    if n.plasticity_frozen:
        return
    w = n._weights_array
    if w is None or len(w) == 0:
        return
    w_max = n.excitatory_saturation_cap if n.excitatory_saturation_cap is not None else n.weight_cap
    if w_max <= 0:
        return
    fe = n._structural_free_energy_gate() if n.structural_free_energy else 1.0
    x = n._last_input_spikes[:len(holder.x_bar)]
    s = x - holder.x_bar
    w_min = n.min_positive_weight if n.min_positive_weight is not None else 0.0
    pos = np.nonzero(w > 0)[0]
    if pos.size == 0:
        return
    envelope = (1.0 - w[pos] / w_max) ** 2
    dw = n.learning_rate * fe * envelope * s[pos]
    w[pos] = np.clip(w[pos] + dw, w_min, w_max)


def _patch_centered_condition(engine, holder):
    for n in engine.l2.excitatory_neurons:
        n._update_weights = (lambda v_pre, _n=n: _centered_update(_n, v_pre, holder))


def _patch_trace_update(engine, holder, alpha):
    orig_step = engine.step

    def wrapped():
        result = orig_step()
        s = np.array([1.0 if engine.spiked.get(f'L1E{i}', False) else 0.0 for i in range(N_PIX)])
        holder.x_bar[:] = (1.0 - alpha) * holder.x_bar + alpha * s
        return result
    engine.step = wrapped


def build_engine(condition, weight_seed, topology_seed=TOPOLOGY_SEED):
    kw = dict(DASHBOARD_PRESET)
    kw['seed'] = weight_seed
    kw['topology_seed'] = topology_seed
    if condition == 'centered':
        kw['loser_depression'] = False
    engine = SimulationEngine(**kw)
    if condition == 'centered':
        holder = XBarHolder(N_PIX)
        _patch_centered_condition(engine, holder)
        _patch_trace_update(engine, holder, ALPHA)
    return engine


def run_one(condition, schedule_kind, weight_seed):
    engine = build_engine(condition, weight_seed)
    if schedule_kind == 'interleaved':
        schedule = [(p, PRESENTATION_STEPS) for _c in range(INTERLEAVED_CYCLES) for p in CYCLE_ORDER]
        schedule_patterns = CYCLE_ORDER
    else:
        schedule = LONG_SCHEDULE
        schedule_patterns = [p for p, _ in LONG_SCHEDULE]
    engine, tracer, plog, initial_w = run_causal_audit_schedule(
        weight_seed, TOPOLOGY_SEED, schedule, PRESENTATION_STEPS, engine=engine)
    return engine, tracer, plog, initial_w, schedule_patterns


def analyze_condition_run(engine, tracer, plog, schedule_patterns):
    base = analyze_run(engine, tracer, plog, schedule_patterns)
    persistent = find_persistent_ownership_collision(plog)
    candidate = find_earliest_modal_collision(plog)
    base['persistent_ownership_collision'] = persistent
    base['earliest_candidate_collision'] = candidate
    final_weights = tracer._all_ff_weights()
    ratios = []
    for j in range(N_OUT):
        u = final_weights[(j, CENTER_PIXEL)]
        others = [final_weights[(j, i)] for i in range(N_PIX) if i != CENTER_PIXEL]
        m = float(np.mean(others)) if others else 0.0
        if m > 1e-9:
            ratios.append(u / m)
    base['center_peripheral_ratio_mean'] = round(float(np.mean(ratios)), 3) if ratios else None
    ties = sum(1 for r in plog if r['same_step_tie'])
    base['overall_ambiguity_rate'] = round(ties / len(plog), 4) if plog else None
    return base


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    t0 = time.time()
    results = []
    for condition in ('legacy', 'centered'):
        for schedule_kind in ('interleaved', 'long_hold'):
            for ws in WEIGHT_SEEDS:
                engine, tracer, plog, initial_w, schedule_patterns = run_one(condition, schedule_kind, ws)
                summary = analyze_condition_run(engine, tracer, plog, schedule_patterns)
                summary.update(condition=condition, schedule=schedule_kind,
                              weight_seed=ws, topology_seed=TOPOLOGY_SEED, alpha=ALPHA)
                results.append(summary)
            print(f"[{condition}/{schedule_kind}] done ({len(results)} runs, {time.time()-t0:.1f}s elapsed)")

    with open(os.path.join(out_dir, 'phase29_centered_encoder_ownership_gate_results.json'), 'w') as f:
        json.dump(dict(weight_seeds=WEIGHT_SEEDS, topology_seed=TOPOLOGY_SEED, alpha=ALPHA,
                       interleaved_cycles=INTERLEAVED_CYCLES, long_schedule=LONG_SCHEDULE,
                       runtime_seconds=round(time.time() - t0, 1), results=results),
                 f, indent=2, default=str)
    print(f"\nDone in {time.time()-t0:.1f}s. {len(results)} total runs.")


if __name__ == "__main__":
    main()
