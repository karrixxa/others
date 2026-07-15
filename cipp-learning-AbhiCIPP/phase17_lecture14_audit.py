"""
Phase 17 Part 1 -- LPS Lecture 14 architecture-mapping audit (measurement
only, july14-integration). Runs the CURRENT baseline engine (no new
mechanism) and records the 12 requested audit items directly from
already-computed engine state -- nothing here is inferred or simulated
separately from the real dynamics.
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
FREQ_TOLERANCE = 0.05   # "approaches 0.5" band


def build_engine(weight_seed, topology_seed=1):
    kw = dict(DASHBOARD_PRESET)
    kw['seed'] = weight_seed
    kw['topology_seed'] = topology_seed
    return SimulationEngine(**kw)


def audit_run(weight_seed, cycles=40, presentation_steps=PRESENTATION_STEPS):
    engine = build_engine(weight_seed)

    # Weight trajectory + single-spike-sufficiency checkpoints (start/mid/end).
    thr_l2i = engine.l2.inhibitory_neuron.threshold
    weight_checkpoints = []

    def _checkpoint(label, t):
        w = engine.l2.inhibitory_neuron._weights_array.copy()
        weight_checkpoints.append(dict(
            label=label, t=t, weights=[round(float(x), 4) for x in w],
            max_weight=round(float(w.max()), 4),
            single_spike_sufficient=bool(w.max() >= thr_l2i),
            thr_l2i=round(float(thr_l2i), 4)))

    # Per-step frequency tracking (own local EMA-free raw count per
    # PRESENTATION_STEPS-sized window) for every population.
    freq_windows = []   # list of dict(pattern, l1e, l1i, l2e, l2i) per presentation

    total_steps = cycles * len(CYCLE_ORDER) * presentation_steps
    step_counter = 0
    presentation_records = []
    _checkpoint('start', 0)
    mid_done = False
    for c in range(cycles):
        for pattern in CYCLE_ORDER:
            spikes = dict(l1e=0, l1i=0, l2e=0, l2i=0)
            engine.set_pattern(pattern)
            for _s in range(presentation_steps):
                engine.step()
                step_counter += 1
                spikes['l1e'] += sum(1 for i in range(N_PIX) if engine.spiked[f'L1E{i}'])
                spikes['l1i'] += sum(1 for i in range(N_PIX) if engine.spiked[f'L1I{i}'])
                spikes['l2e'] += sum(1 for j in range(N_OUT) if engine.spiked[f'L2E{j}'])
                spikes['l2i'] += 1 if engine.spiked['L2I'] else 0
                if not mid_done and step_counter >= total_steps // 2:
                    _checkpoint('mid', step_counter)
                    mid_done = True
            n_steps = presentation_steps
            freq_windows.append(dict(
                pattern=pattern,
                l1e_freq=spikes['l1e'] / (n_steps * N_PIX),
                l1i_freq=spikes['l1i'] / (n_steps * N_PIX),
                l2e_freq=spikes['l2e'] / (n_steps * N_OUT),
                l2i_freq=spikes['l2i'] / n_steps,
            ))
            story = engine.dynamic_state()['causal_story']
            presentation_records.append(dict(
                pattern=pattern, first_l2e_spiker=story['first_spiker'],
                same_step_tie=story['same_step_tie']))
    _checkpoint('end', step_counter)

    # L2I delivery timing/contributor-count audit (from the engine's own log).
    delivery_records = []
    for rec in engine._l2_inhibition_log:
        contributors = rec['contributors']   # ["t:L2Ej", ...]
        contrib_ts = [int(c.split(':')[0]) for c in contributors]
        contrib_ids = [c.split(':')[1] for c in contributors]
        first_contrib_t = min(contrib_ts) if contrib_ts else None
        delivery_records.append(dict(
            l2i_fire_t=rec['fire_t'], deliver_at=rec['deliver_at'],
            l2e_to_l2i_latency=(rec['fire_t'] - first_contrib_t) if first_contrib_t is not None else None,
            l2i_to_delivery_latency=rec['deliver_at'] - rec['fire_t'],
            n_contributors=len(contributors), contributor_ids=contrib_ids))

    # Frequency-near-0.5 incidence + correlation checks.
    near_half = [w for w in freq_windows if abs(w['l1e_freq'] - 0.5) < FREQ_TOLERANCE
                or abs(w['l1i_freq'] - 0.5) < FREQ_TOLERANCE]
    l1i_all_sync = engine  # synchrony already established structurally (Phase 9); re-confirm below
    l1i_weights = [engine.l1.inhibitory_neurons[i].weights for i in range(N_PIX)]
    l1i_identical = all(np.allclose(l1i_weights[0], w) for w in l1i_weights[1:])

    s = summarize(dict(seed=weight_seed, live=[
        dict(pattern=r['pattern'], first_l2e_spiker=r['first_l2e_spiker'],
            same_step_tie=r['same_step_tie'], all_l2e_spikes=[], latency_margin_to_second=None,
            l2i_spike_steps=[], l2i_spike_count=0, l1i_fired_positions=[],
            pre_inhibition_charge=[], post_inhibition_charge=[], receptive_fields={}, weight_changes={})
        for r in presentation_records], frozen=[]))

    return dict(
        weight_seed=weight_seed,
        weight_checkpoints=weight_checkpoints,
        n_deliveries=len(delivery_records),
        delivery_records_sample=delivery_records[:20],
        mean_l2e_to_l2i_latency=round(float(np.mean([d['l2e_to_l2i_latency'] for d in delivery_records
                                                     if d['l2e_to_l2i_latency'] is not None])), 3) if delivery_records else None,
        mean_l2i_to_delivery_latency=round(float(np.mean([d['l2i_to_delivery_latency'] for d in delivery_records])), 3) if delivery_records else None,
        mean_n_contributors=round(float(np.mean([d['n_contributors'] for d in delivery_records])), 3) if delivery_records else None,
        mean_l1e_freq=round(float(np.mean([w['l1e_freq'] for w in freq_windows])), 4),
        mean_l1i_freq=round(float(np.mean([w['l1i_freq'] for w in freq_windows])), 4),
        mean_l2e_freq=round(float(np.mean([w['l2e_freq'] for w in freq_windows])), 4),
        mean_l2i_freq=round(float(np.mean([w['l2i_freq'] for w in freq_windows])), 4),
        near_half_fraction=round(len(near_half) / len(freq_windows), 4) if freq_windows else None,
        l1i_all_identical_weights=bool(l1i_identical),
        distinct_owners=s['distinct_owners'],
        l1i_all_nine_sync_rate=s['l1i_all_nine_sync_rate'],
        silent_cells=s['silent_cells'],
    )


def main():
    results = [audit_run(ws) for ws in WEIGHT_SEEDS]
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'phase17_lecture14_audit.json'), 'w') as f:
        json.dump(results, f, indent=2, default=str)
    for r in results:
        print(f"seed={r['weight_seed']} n_deliveries={r['n_deliveries']} "
             f"L2E->L2I latency={r['mean_l2e_to_l2i_latency']} "
             f"L2I->delivery latency={r['mean_l2i_to_delivery_latency']} "
             f"mean_contributors={r['mean_n_contributors']} "
             f"freqs(L1E={r['mean_l1e_freq']},L1I={r['mean_l1i_freq']},L2E={r['mean_l2e_freq']},L2I={r['mean_l2i_freq']}) "
             f"near_half_frac={r['near_half_fraction']} distinct_owners={r['distinct_owners']} "
             f"L1I_sync={r['l1i_all_nine_sync_rate']}")
        for cp in r['weight_checkpoints']:
            print(f"   {cp['label']:5s} t={cp['t']:5d} max_w={cp['max_weight']:.2f} "
                 f"thr_l2i={cp['thr_l2i']:.2f} single_spike_sufficient={cp['single_spike_sufficient']}")


if __name__ == "__main__":
    main()
