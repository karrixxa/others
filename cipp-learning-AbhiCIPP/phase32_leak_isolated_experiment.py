"""
Phase 32 -- FSCI/ISM prediction-path leak, isolated factor.

Per the plan's explicit instruction: "Leak is not assumed to solve
ownership. Test it as an isolated factor for prediction carryover... Do
not search for a winning time constant." This is a DEDICATED, standalone
2x2 factorial -- PCi->Ii topology (shadow vs active) x prediction-path
leak (OFF vs ON, ONE preregistered time constant, the EXISTING default) --
kept separate from the full A-F ownership/decoder measurement suite
(phase31) so the leak comparison is never conflated with anything else.

Reuses the EXISTING `prediction_leak`/`prediction_leak_diagnostic_disable`
mechanism (Phase 19) -- no second, inconsistent leak equation is
introduced. PCi is the only population whose leak is varied here; every
other leak flag (leak_enabled, l1i_leak_enabled, l2i_leak_enabled) stays at
DASHBOARD_PRESET's own default (all OFF) in every one of these four
conditions -- documented explicitly so it is clear exactly which
population's leak this phase is testing.

Four conditions (all built on top of Phase 31's condition D -- centered
encoder, loser depression off, subthreshold decoder, continuous-switching
interleaved schedule, standard pattern set):

  shadow_leak_off  - PCi->Ii disconnected, PC leak OFF  (D + leak off, i.e. D itself)
  shadow_leak_on   - PCi->Ii disconnected, PC leak ON   (D's own implicit default)
  active_leak_off  - PCi->Ii ACTIVE,       PC leak OFF  (= condition E)
  active_leak_on   - PCi->Ii ACTIVE,       PC leak ON   (= condition F)

30 weight seeds x 1 topology seed x 4 conditions = 120 runs, all reported.
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from phase31_fsci_ism_conditions_af import (  # noqa: E402
    PATTERN_SETS, WEIGHT_SEEDS, analyze_condition_run, condition_kwargs, run_condition,
)
import backend.simulation as bsim  # noqa: E402
from phase31_fsci_ism_conditions_af import _patterns_swapped, build_engine  # noqa: E402
from phase27_l2_ownership_causal_audit import CausalTracer  # noqa: E402
from diagnostic_schedule import PRESENTATION_STEPS  # noqa: E402

INTERLEAVED_CYCLES = 15
TOPOLOGY_SEED = 1


def leak_condition_kwargs(name):
    base = dict(condition_kwargs('D'))   # centered encoder, loser_dep off, subthreshold decoder, shadow
    if name == 'shadow_leak_off':
        base['prediction_column_to_i_enabled'] = False
        base['prediction_leak_diagnostic_disable'] = True
        return base
    if name == 'shadow_leak_on':
        base['prediction_column_to_i_enabled'] = False
        base['prediction_leak_diagnostic_disable'] = False
        return base
    if name == 'active_leak_off':
        base['prediction_column_to_i_enabled'] = True
        base['prediction_leak_diagnostic_disable'] = True
        return base
    if name == 'active_leak_on':
        base['prediction_column_to_i_enabled'] = True
        base['prediction_leak_diagnostic_disable'] = False
        return base
    raise ValueError(name)


LEAK_CONDITIONS = ('shadow_leak_off', 'shadow_leak_on', 'active_leak_off', 'active_leak_on')


def run_leak_condition(condition, weight_seed, cycles=INTERLEAVED_CYCLES,
                       presentation_steps=PRESENTATION_STEPS):
    spec = PATTERN_SETS['standard']
    kw = leak_condition_kwargs(condition)
    kw['seed'] = weight_seed
    kw['topology_seed'] = TOPOLOGY_SEED
    with _patterns_swapped(spec['patterns']):
        engine = bsim.SimulationEngine(**kw)
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
                    step_records.append(dict(
                        t=engine.timestep - 1, pattern=pattern,
                        pc_spiked=[i for i in range(9) if engine.spiked.get(f'PC{i}')],
                        l1i_spiked=[i for i in range(9) if engine.spiked.get(f'L1I{i}')],
                        l1e_potentials_before=[round(v, 4) for v in l1e_pre],
                        l1e_potentials_after=[round(v, 4) for v in l1e_post],
                    ))
                t_end = engine.timestep
                window = [r for r in tracer.spike_records if t_start <= r['t'] < t_end]
                first = window[0] if window else None
                same_step_tie = bool(first and sum(1 for r in window if r['t'] == first['t']) > 1)
                presentation_log.append(dict(
                    presentation_index=idx, cycle=_c, pattern=pattern, t_start=t_start, t_end=t_end,
                    first_l2e_spiker=first['neuron'] if first else None, same_step_tie=same_step_tie))
                idx += 1
    return engine, tracer, presentation_log, step_records


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    t0 = time.time()
    results = []
    for condition in LEAK_CONDITIONS:
        for ws in WEIGHT_SEEDS:
            engine, tracer, plog, step_records = run_leak_condition(condition, ws)
            spec = PATTERN_SETS['standard']
            summary = analyze_condition_run(engine, tracer, plog, step_records, spec)
            summary.update(condition=condition, weight_seed=ws, topology_seed=TOPOLOGY_SEED,
                          prediction_leak_value=engine.prediction_leak)
            results.append(summary)
        print(f"[{condition}] done ({len(results)} runs, {time.time()-t0:.1f}s elapsed)")

    with open(os.path.join(out_dir, 'phase32_leak_isolated_experiment_results.json'), 'w') as f:
        json.dump(dict(weight_seeds=WEIGHT_SEEDS, topology_seed=TOPOLOGY_SEED,
                       interleaved_cycles=INTERLEAVED_CYCLES, conditions=LEAK_CONDITIONS,
                       runtime_seconds=round(time.time() - t0, 1), results=results),
                 f, indent=2, default=str)
    print(f"\nDone in {time.time()-t0:.1f}s. {len(results)} total runs.")


if __name__ == "__main__":
    main()
