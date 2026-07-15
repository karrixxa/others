"""
Phase 15 -- local developmental protection from L2I loser depression
(measurement + comparison script, july14-integration). MEASUREMENT ONLY in
the sense that no parameter is tuned per seed; this phase DOES introduce one
new, default-off neural mechanism (see neuron_flexible.Neuron.
_loser_depression_maturity / apply_delayed_inhibition), and this script is
the required A-vs-B comparison for it.

Configs (identical weight/topology seeds, everything else DASHBOARD_PRESET):
  A. current default (loser_depression_protection=False, i.e. omitted)
  B. protection enabled (loser_depression_protection=True, ca_ref=0.02 -- the
     single documented default, never swept per seed)

Scenarios:
  1. 20-step equal interleaving, 40 rotations (diagnostic_schedule.CYCLE_ORDER,
     reused directly).
  2. Long row-hold then column switch (600 steps row 1, 200 steps col 1).

Grid: weight seeds 1-5 x topology seeds 1-3 = 15 combinations, both scenarios,
both configs = 60 runs.
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

CONFIGS = {
    'A_default': dict(DASHBOARD_PRESET),
    'B_protection': {**DASHBOARD_PRESET, 'loser_depression_protection': True,
                     'loser_depression_protection_ca_ref': 0.02},
}


def build_engine(config_name, weight_seed, topology_seed):
    kw = dict(CONFIGS[config_name])
    kw['seed'] = weight_seed
    kw['topology_seed'] = topology_seed
    return SimulationEngine(**kw)


# --------------------------------------------------------------- instrumentation
class DepressionTracer:
    """Wraps every L2E neuron's apply_delayed_inhibition to record
    (maturity, |delta|) per depression event and the raw applied/refractory
    outcome of every delivery attempt -- for the "physical inhibition events
    unchanged" and "loser-depression magnitude grouped by maturity"
    requirements. Also tracks per-neuron first-spike timestep and the
    per-step simultaneous-firer count, all from already-existing engine
    state (self.engine.spiked / self._last_eligible), never re-derived."""

    def __init__(self, engine):
        self.engine = engine
        self.depression_events = []      # [{neuron, t, maturity, delta_abs, applied}]
        self.delivery_attempts = []      # [{neuron, t, applied, v_pre, v_post, magnitude}]
        self.first_spike_t = {}         # nid -> first timestep it ever spiked
        self.simultaneous_firer_counts = []   # per-step count of L2E that spiked THIS step
        for j, n in enumerate(engine.l2.excitatory_neurons):
            self._patch(j, n)
        self._patch_step()

    def _patch(self, j, n):
        orig = n.apply_delayed_inhibition
        nid = f'L2E{j}'

        def wrapped(magnitude):
            w_before = n._weights_array.copy()
            t = self.engine.timestep
            out = orig(magnitude)
            self.delivery_attempts.append(dict(
                neuron=nid, t=t, applied=out['applied'],
                v_pre=out['v_pre'], v_post=out['v_post'], magnitude=float(magnitude)))
            if out['applied'] and out['depressed_indices']:
                delta_abs = float(np.mean(np.abs(w_before[out['depressed_indices']]
                                                 - n._weights_array[out['depressed_indices']])))
                self.depression_events.append(dict(
                    neuron=nid, t=t, maturity=out['maturity'], delta_abs=delta_abs))
            return out
        n.apply_delayed_inhibition = wrapped

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
            self.simultaneous_firer_counts.append(count)
            return result
        engine.step = wrapped


# ------------------------------------------------------------------- scenarios
def run_long_hold_switch(config_name, weight_seed, topology_seed, row1_steps=600, col1_steps=200):
    engine = build_engine(config_name, weight_seed, topology_seed)
    tracer = DepressionTracer(engine)
    engine.set_pattern('row 1')
    for _ in range(row1_steps):
        engine.step()
    engine.set_pattern('col 1')
    for _ in range(col1_steps):
        engine.step()
    return engine, tracer


def run_interleaved_40(config_name, weight_seed, topology_seed, cycles=40,
                       presentation_steps=PRESENTATION_STEPS):
    engine = build_engine(config_name, weight_seed, topology_seed)
    tracer = DepressionTracer(engine)
    presentation_records = []
    for _c in range(cycles):
        for pattern in CYCLE_ORDER:
            _present_and_record(engine, pattern, presentation_steps, presentation_records)
    return engine, tracer, presentation_records


# --------------------------------------------------------------------- analysis
def _maturity_bucket(m):
    if m < 0.25:
        return '0.00-0.25'
    if m < 0.5:
        return '0.25-0.50'
    if m < 0.75:
        return '0.50-0.75'
    return '0.75-1.00'


def analyze_run(config_name, weight_seed, topology_seed, scenario, engine, tracer,
                first_half_never_fired=None):
    status = {f'L2E{j}': engine._l2e_status(j)['status'] for j in range(N_OUT)}
    never_fired = [nid for nid, s in status.items() if s == 'unrecruited']
    spikes_total = {f'L2E{j}': engine._neuron_total_spikes.get(f'L2E{j}', 0) for j in range(N_OUT)}
    total_spikes = sum(spikes_total.values())
    tyrant = max(spikes_total, key=spikes_total.get) if total_spikes > 0 else None
    tyrant_share = (spikes_total[tyrant] / total_spikes) if tyrant else None

    by_bucket = defaultdict(list)
    for ev in tracer.depression_events:
        by_bucket[_maturity_bucket(ev['maturity'])].append(ev['delta_abs'])
    depression_by_maturity = {b: dict(n=len(v), mean_delta_abs=round(float(np.mean(v)), 4))
                              for b, v in by_bucket.items()}

    applied_count = sum(1 for d in tracer.delivery_attempts if d['applied'])
    skipped_refractory_count = sum(1 for d in tracer.delivery_attempts if not d['applied'])
    first_delivery = tracer.delivery_attempts[0] if tracer.delivery_attempts else None

    sim_counts = tracer.simultaneous_firer_counts
    multi_firer_steps = sum(1 for c in sim_counts if c > 1)
    multi_firer_rate = round(multi_firer_steps / len(sim_counts), 4) if sim_counts else None

    eventually_fired_after_never_early = None
    if first_half_never_fired is not None:
        eventually_fired_after_never_early = {
            nid: (spikes_total.get(nid, 0) > 0) for nid in first_half_never_fired}

    return dict(
        config=config_name, weight_seed=weight_seed, topology_seed=topology_seed, scenario=scenario,
        never_fired_neurons=never_fired,
        first_spike_latency={nid: tracer.first_spike_t.get(nid) for nid in [f'L2E{j}' for j in range(N_OUT)]},
        status=status,
        active_count=sum(1 for s in status.values() if s == 'active'),
        quiet_count=sum(1 for s in status.values() if s == 'quiet'),
        unrecruited_count=sum(1 for s in status.values() if s == 'unrecruited'),
        tyrant=tyrant, tyrant_share=round(tyrant_share, 4) if tyrant_share is not None else None,
        depression_by_maturity=depression_by_maturity,
        physical_inhibition_applied_count=applied_count,
        physical_inhibition_skipped_refractory_count=skipped_refractory_count,
        first_delivery_event=first_delivery,
        multi_firer_rate=multi_firer_rate,
        multi_firer_steps=multi_firer_steps,
        total_steps=len(sim_counts),
        eventually_fired_after_never_early=eventually_fired_after_never_early,
    )


def analyze_interleaved(config_name, weight_seed, topology_seed, engine, tracer, presentation_records):
    base = analyze_run(config_name, weight_seed, topology_seed, 'interleaved_40', engine, tracer)
    s = summarize(dict(seed=weight_seed, live=presentation_records, frozen=[]))
    base['distinct_owners'] = s['distinct_owners']
    base['per_pattern_consistency'] = {p: pp['consistency'] for p, pp in s['per_pattern'].items()}
    base['collisions'] = s['collisions']
    base['forgetting'] = {p: f['changed'] for p, f in s['forgetting'].items()}
    base['silent_cells'] = s['silent_cells']
    base['recruitable_cells'] = s['recruitable_cells']
    ambiguity_rates = [pp['ambiguity_rate'] for pp in s['per_pattern'].values()]
    base['mean_ambiguity_rate'] = round(float(np.mean(ambiguity_rates)), 4) if ambiguity_rates else None
    return base


# ------------------------------------------------------------------------ main
def main():
    grid_results = []
    for config_name in CONFIGS:
        for ws in WEIGHT_SEEDS:
            for ts in TOPOLOGY_SEEDS:
                # Long hold/switch, with a first-half never-fired checkpoint
                # (after row 1's 600 steps, before the switch) to test
                # whether a protected-but-immature neuron eventually fires.
                engine = build_engine(config_name, ws, ts)
                tracer = DepressionTracer(engine)
                engine.set_pattern('row 1')
                for _ in range(600):
                    engine.step()
                half_status = {f'L2E{j}': engine._l2e_status(j)['status'] for j in range(N_OUT)}
                first_half_never_fired = [nid for nid, s in half_status.items() if s == 'unrecruited']
                engine.set_pattern('col 1')
                for _ in range(200):
                    engine.step()
                grid_results.append(analyze_run(config_name, ws, ts, 'long_hold_switch',
                                                engine, tracer, first_half_never_fired))

                engine2, tracer2, pres = run_interleaved_40(config_name, ws, ts)
                grid_results.append(analyze_interleaved(config_name, ws, ts, engine2, tracer2, pres))

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'phase15_loser_depression_protection_summary.json'), 'w') as f:
        json.dump(dict(weight_seeds=WEIGHT_SEEDS, topology_seeds=TOPOLOGY_SEEDS,
                       grid_results=grid_results), f, indent=2, default=str)
    print(f"grid runs: {len(grid_results)}")


if __name__ == "__main__":
    main()
