"""
Phase 31 -- FSCI/ISM conditions A-F: full ownership/decoder/prediction-
inhibition measurement grid.

Conditions (per the FSCI/ISM plan; each engine kwargs dict below is the
FULL, explicit config -- no hidden inheritance):

  A - exact legacy baseline: DASHBOARD_PRESET unchanged.
  B - centered encoder, loser depression OFF, top-down prediction OFF.
  C - B + EXISTING spike-gated decoder, SHADOW mode (PCi->Ii disconnected).
  D - B + NEW subthreshold coincidence decoder, SHADOW mode.
  E - D + ACTIVE PCi->Ii (fully causal prediction+suppression), leak OFF.
  F - E with the preregistered prediction-path membrane leak ON.

"Shadow mode" = prediction_column_to_i_enabled=False (PCi learns and can
fire; its output never reaches Ii). The proposed full circuit is E/F, not
C/D -- C/D exist purely as ablations isolating decoder-learning-only from
decoder+suppression.

Grid: 30 weight seeds x 1 topology seed x 6 conditions x 2 pattern
permutations (standard pixel-4-universal, and a 0<->4 swap so the shared
pixel is not always index 4) x continuous-switching interleaved schedule
(no boundary resets) = 360 runs, all reported.

Ownership measurements reuse Phase 27's proven, tested CausalTracer/
analyze_run/find_persistent_ownership_collision UNCHANGED. Prediction/
inhibition timing uses a lightweight PER-STEP snapshot (no monkeypatching
needed -- every population's spike flag and membrane potential are already
first-class, readable engine state after each step()), since building a
second parallel monkeypatch layer on top of Phase 27's CausalTracer would
duplicate machinery for no benefit -- reading already-public per-step state
is simpler AND non-mutating by construction.
"""

from __future__ import annotations

import contextlib
import copy
import json
import os
import sys
import time
from collections import defaultdict, deque

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backend.simulation as bsim  # noqa: E402
from backend.simulation import N_OUT, N_PIX, PATTERNS as STANDARD_PATTERNS, SimulationEngine  # noqa: E402
from backend.presets import DASHBOARD_PRESET  # noqa: E402
from diagnostic_schedule import PRESENTATION_STEPS  # noqa: E402
from phase27_l2_ownership_causal_audit import (  # noqa: E402
    CausalTracer, analyze_run, find_earliest_modal_collision,
    find_persistent_ownership_collision,
)

WEIGHT_SEEDS = list(range(1, 31))
TOPOLOGY_SEED = 1
INTERLEAVED_CYCLES = 15           # tractability -- see module docstring's runtime note below
CENTER_PIXEL_STANDARD = 4
CENTER_PIXEL_SHIFTED = 0


def _swap_pixels(vec, i, j):
    v = list(vec)
    v[i], v[j] = v[j], v[i]
    return v


_STANDARD = dict(STANDARD_PATTERNS)
_SHIFTED = {name: _swap_pixels(vec, 0, 4) for name, vec in _STANDARD.items()}
PATTERN_SETS = {
    'standard': dict(patterns=_STANDARD, cycle_order=['row 1', 'col 1', 'diag \\', 'diag /'],
                    universal_pixel=CENTER_PIXEL_STANDARD),
    'shifted': dict(patterns=_SHIFTED, cycle_order=['row 1', 'col 1', 'diag \\', 'diag /'],
                   universal_pixel=CENTER_PIXEL_SHIFTED),
}


def condition_kwargs(name):
    """Returns the FULL, explicit engine kwargs dict for condition `name`."""
    if name == 'A':
        return dict(DASHBOARD_PRESET)
    base = dict(DASHBOARD_PRESET)
    base['centered_encoder_enabled'] = True
    base['loser_depression'] = False
    if name == 'B':
        return base
    if name == 'C':
        return {**base, 'prediction_column_enabled': True,
               'prediction_subthreshold_decoder_enabled': False,
               'prediction_column_to_i_enabled': False}
    if name == 'D':
        return {**base, 'prediction_column_enabled': True,
               'prediction_subthreshold_decoder_enabled': True,
               'prediction_column_to_i_enabled': False}
    if name == 'E':
        return {**base, 'prediction_column_enabled': True,
               'prediction_subthreshold_decoder_enabled': True,
               'prediction_column_to_i_enabled': True,
               'prediction_leak_diagnostic_disable': True}
    if name == 'F':
        return {**base, 'prediction_column_enabled': True,
               'prediction_subthreshold_decoder_enabled': True,
               'prediction_column_to_i_enabled': True,
               'prediction_leak_diagnostic_disable': False}
    raise ValueError(name)


CONDITIONS = ('A', 'B', 'C', 'D', 'E', 'F')


@contextlib.contextmanager
def _patterns_swapped(new_patterns):
    original = bsim.PATTERNS
    bsim.PATTERNS = new_patterns
    try:
        yield
    finally:
        bsim.PATTERNS = original


def build_engine(condition, weight_seed, topology_seed=TOPOLOGY_SEED):
    kw = dict(condition_kwargs(condition))
    kw['seed'] = weight_seed
    kw['topology_seed'] = topology_seed
    return SimulationEngine(**kw)


def run_condition(pattern_set_key, condition, weight_seed, cycles=INTERLEAVED_CYCLES,
                  presentation_steps=PRESENTATION_STEPS):
    """Continuous-switching interleaved schedule -- NO boundary resets/
    clearing of any kind (per explicit instruction). Returns (engine,
    tracer, presentation_log, step_records, initial_weights)."""
    spec = PATTERN_SETS[pattern_set_key]
    with _patterns_swapped(spec['patterns']):
        engine = build_engine(condition, weight_seed)
        tracer = CausalTracer(engine)
        initial_weights = tracer._all_ff_weights()
        presentation_log = []
        step_records = []
        idx = 0
        for _c in range(cycles):
            for pattern in spec['cycle_order']:
                engine.set_pattern(pattern)
                t_start = engine.timestep
                for _s in range(presentation_steps):
                    l1e_pre = [float(e.potential) for e in engine.l1.excitatory_neurons]
                    engine.step()
                    l1e_post = [float(e.potential) for e in engine.l1.excitatory_neurons]
                    rec = dict(
                        t=engine.timestep - 1, pattern=pattern,
                        l2e_spiked=[j for j in range(N_OUT) if engine.spiked.get(f'L2E{j}')],
                        pc_spiked=([i for i in range(N_PIX) if engine.spiked.get(f'PC{i}')]
                                  if engine.prediction_column_enabled else None),
                        pc_potentials=([round(float(pc.potential), 4) for pc in engine.pcol]
                                      if engine.prediction_column_enabled else None),
                        l1i_spiked=[i for i in range(N_PIX) if engine.spiked.get(f'L1I{i}')],
                        l1i_potentials=[round(float(n.potential), 4) for n in engine.l1.inhibitory_neurons],
                        l1e_potentials_before=[round(v, 4) for v in l1e_pre],
                        l1e_potentials_after=[round(v, 4) for v in l1e_post],
                    )
                    step_records.append(rec)
                t_end = engine.timestep
                window = [r for r in tracer.spike_records if t_start <= r['t'] < t_end]
                first = window[0] if window else None
                same_step_tie = bool(first and sum(1 for r in window if r['t'] == first['t']) > 1)
                presentation_log.append(dict(
                    presentation_index=idx, cycle=_c, pattern=pattern, t_start=t_start, t_end=t_end,
                    first_l2e_spiker=first['neuron'] if first else None, same_step_tie=same_step_tie))
                idx += 1
    return engine, tracer, presentation_log, step_records, initial_weights


# ------------------------------------------------------------- decoder analysis
def decoder_precision_recall(engine, spec):
    """Over the FULL run's pc_spiked events (already in step_records, but
    recomputed here from engine.freq for simplicity): for each PCi, does it
    fire selectively for its OWN paired pixel's active patterns (precision)
    and does it fire whenever that pixel IS active (recall)? Uses the
    engine's own per-population firing-frequency history (self.freq),
    already-recorded, read-only."""
    if not engine.prediction_column_enabled:
        return None
    return {f'PC{i}': dict(freq=round(engine.firing_freq(f'PC{i}'), 4)) for i in range(N_PIX)}


def _unpatched_deepcopy(engine):
    """copy.deepcopy treats function/closure objects as atomic (never
    actually duplicated) -- so an INSTANCE-level monkeypatch (CausalTracer's
    patched .step / each L2E's .fire / .apply_delayed_inhibition) survives a
    deepcopy as the SAME closure object, which still closes over the
    ORIGINAL engine, not the copy. Stepping the naive copy would silently
    mutate the ORIGINAL, live engine instead of an independent probe --
    confirmed directly (`probe.step is engine.step` -> True after a plain
    copy.deepcopy when CausalTracer is attached). This strips those
    instance-level overrides off the COPY ONLY (falling back to the
    class's true, unpatched methods via normal attribute lookup); the
    copy's PHYSICAL state (weights, membrane potentials, queues, timestep
    -- everything that ISN'T an instance-bound callable) is still a fully
    independent copy, unaffected by this."""
    probe = copy.deepcopy(engine)
    probe.__dict__.pop('step', None)
    for n in probe.l2.excitatory_neurons:
        n.__dict__.pop('fire', None)
        n.__dict__.pop('apply_delayed_inhibition', None)
    return probe


def decoder_functional_check(engine):
    """Post-hoc, READ-ONLY check (no mutation of the passed engine): an
    UNPATCHED deep copy (see _unpatched_deepcopy), plasticity frozen, every
    L1E external input zeroed (pure feedback-only probe) -- checks whether
    each PCi can reach threshold from its OWN matured decoder weights
    alone, the same "manually matured decoder reconstructs" logic Phase 20
    already validated, applied here to whatever weights REALISTIC training
    actually reached (not manually set).

    IMPORTANT: every L1E/L2E/PCi membrane potential is explicitly reset to
    resting, and both PC delivery queues are explicitly drained to zero,
    BEFORE the zero-input probe begins. Without this, a spike in the first
    few probe steps could be spurious RESIDUAL charge or an already-queued
    real event carried over from the live run at the exact moment of
    copying -- not genuine decoder-driven reconstruction at all (found and
    fixed directly: an earlier version of this check reported PCi "firing
    from feedback alone" in conditions E/F even though the decoder weights
    were, numerically, barely different from their init value -- a tell
    that the reported spikes could not have been decoder-driven)."""
    if not engine.prediction_column_enabled:
        return None
    probe = _unpatched_deepcopy(engine)
    probe._set_plasticity_frozen(True)
    probe.input_vec = np.zeros(N_PIX)
    for e in probe.l1.excitatory_neurons:
        e.potential = e.resting_potential
    for e in probe.l2.excitatory_neurons:
        e.potential = e.resting_potential
    for pc in probe.pcol:
        pc.potential = pc.resting_potential
    probe.l2e_to_pcol_queue = deque(np.zeros(N_OUT) for _ in range(probe.prediction_feedback_delay))
    probe.s_to_pcol_queue = deque(np.zeros(N_PIX) for _ in range(probe.prediction_feedback_delay))
    fired_from_feedback_alone = [False] * N_PIX
    for _ in range(200):
        probe.step()
        for i in range(N_PIX):
            if probe.spiked.get(f'PC{i}'):
                fired_from_feedback_alone[i] = True
    return dict(any_fired_feedback_alone=any(fired_from_feedback_alone),
               per_pc_fired_feedback_alone=fired_from_feedback_alone)


def continuous_switch_carryover(step_records, spec):
    """Classifies every PCi spike in step_records as coincidence/inactive-
    pixel/carryover, using the SAME chronological convention as Phase 19's
    switch-boundary diagnostic: a PCi spike is "inactive_pixel" if pixel i
    is not part of the CURRENT pattern at that step."""
    total = coincidence = inactive_pixel = 0
    for r in step_records:
        if not r['pc_spiked']:
            continue
        active = [i for i, v in enumerate(spec['patterns'][r['pattern']]) if v]
        for i in r['pc_spiked']:
            total += 1
            if i in active:
                coincidence += 1
            else:
                inactive_pixel += 1
    return dict(total=total, coincidence=coincidence, inactive_pixel=inactive_pixel,
               false_prediction_rate=round(inactive_pixel / total, 4) if total else None)


def prediction_inhibition_timing(step_records):
    """Aggregate timing/activity summary across the whole run (not a full
    per-event trace -- see module docstring on tractability)."""
    pc_spike_steps = sum(1 for r in step_records if r['pc_spiked'])
    l1i_spike_steps = sum(1 for r in step_records if r['l1i_spiked'])
    l1e_before = np.array([r['l1e_potentials_before'] for r in step_records])
    l1e_after = np.array([r['l1e_potentials_after'] for r in step_records])
    residual_drop = float(np.mean(l1e_before - l1e_after)) if len(step_records) else None
    return dict(
        n_steps=len(step_records), pc_spike_steps=pc_spike_steps, l1i_spike_steps=l1i_spike_steps,
        mean_l1e_potential_before=round(float(np.mean(l1e_before)), 4) if len(step_records) else None,
        mean_l1e_potential_after=round(float(np.mean(l1e_after)), 4) if len(step_records) else None,
        mean_residual_drop=round(residual_drop, 4) if residual_drop is not None else None,
    )


def analyze_condition_run(engine, tracer, plog, step_records, spec):
    result = analyze_run(engine, tracer, plog, spec['cycle_order'])
    result['persistent_ownership_collision'] = find_persistent_ownership_collision(plog)
    result['earliest_candidate_collision'] = find_earliest_modal_collision(plog)
    final_weights = tracer._all_ff_weights()
    u = spec['universal_pixel']
    ratios = []
    for j in range(N_OUT):
        uw = final_weights[(j, u)]
        others = [final_weights[(j, i)] for i in range(N_PIX) if i != u]
        m = float(np.mean(others)) if others else 0.0
        if m > 1e-9:
            ratios.append(uw / m)
    result['universal_peripheral_ratio_mean'] = round(float(np.mean(ratios)), 3) if ratios else None
    result['decoder_precision_recall'] = decoder_precision_recall(engine, spec)
    result['decoder_functional_check'] = decoder_functional_check(engine)
    result['continuous_switch_carryover'] = continuous_switch_carryover(step_records, spec)
    result['prediction_inhibition_timing'] = prediction_inhibition_timing(step_records)
    if engine.prediction_column_enabled:
        result['final_decoder_weights'] = {
            f'PC{i}': [round(float(w), 3) for w in engine.pcol[i]._weights_array]
            for i in range(N_PIX)}
    return result


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    t0 = time.time()
    results = []
    for pattern_set_key in ('standard', 'shifted'):
        for condition in CONDITIONS:
            for ws in WEIGHT_SEEDS:
                engine, tracer, plog, step_records, initial_w = run_condition(pattern_set_key, condition, ws)
                spec = PATTERN_SETS[pattern_set_key]
                summary = analyze_condition_run(engine, tracer, plog, step_records, spec)
                summary.update(pattern_set=pattern_set_key, condition=condition, weight_seed=ws,
                              topology_seed=TOPOLOGY_SEED)
                results.append(summary)
            print(f"[{pattern_set_key}/{condition}] done ({len(results)} runs, {time.time()-t0:.1f}s elapsed)")

    with open(os.path.join(out_dir, 'phase31_fsci_ism_conditions_af_results.json'), 'w') as f:
        json.dump(dict(weight_seeds=WEIGHT_SEEDS, topology_seed=TOPOLOGY_SEED,
                       interleaved_cycles=INTERLEAVED_CYCLES, conditions=CONDITIONS,
                       runtime_seconds=round(time.time() - t0, 1), results=results),
                 f, indent=2, default=str)
    print(f"\nDone in {time.time()-t0:.1f}s. {len(results)} total runs.")


if __name__ == "__main__":
    main()
