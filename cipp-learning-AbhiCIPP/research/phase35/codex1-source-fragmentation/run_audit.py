#!/usr/bin/env python3
"""Measurement-only Phase 35 L2 source-fragmentation causal audit."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np

ROOT = Path('/home/cxiong/codex-runs/codex1-phase35-source-fragmentation')
PROJECT = ROOT / 'repo' / 'cipp-learning-AbhiCIPP'
sys.dont_write_bytecode = True
sys.path.insert(0, str(PROJECT))

from backend.presets import DASHBOARD_PRESET  # noqa: E402
from backend.simulation import N_OUT, N_PIX, PATTERNS, SimulationEngine  # noqa: E402

ORDER = tuple(PATTERNS)
PRESENTATION_STEPS = 20
FULL_STEPS = 12_800
CENTER = 4


def engine_for(seed):
    params = dict(DASHBOARD_PRESET)
    params.update(
        seed=seed,
        prediction_excitatory_enabled=False,
        prediction_column_enabled=True,
        prediction_column_to_i_enabled=False,
        loser_depression=False,
        signed_depression=False,
        l2e_budget=False,
        homeostasis=False,
        confidence_consolidation=False,
    )
    engine = SimulationEngine(**params)
    assert engine.prediction_column_enabled
    assert not engine.prediction_column_to_i_enabled
    assert not engine.prediction_excitatory_enabled
    assert not any(s['source'].startswith('PC') for s in engine.synapses)
    assert not engine.params['loser_depression']
    assert not engine.params['signed_depression']
    assert not engine.params['l2e_budget']
    return engine


def owner_from_first(presentation):
    first = presentation.get('first_responder')
    return int(first[3:]) if first else None


def running_mode(history):
    if not history:
        return None
    counts = Counter(history)
    best = max(counts.values())
    return min(owner for owner, count in counts.items() if count == best)


def classify_updates(updates, presentations):
    by_index = {p['index']: p for p in presentations}
    pixel_patterns = defaultdict(set)
    pixel_pattern_sources = defaultdict(lambda: defaultdict(set))
    for u in updates:
        for pattern in u['origin_patterns']:
            pixel_patterns[u['pixel']].add(pattern)
            pixel_pattern_sources[u['pixel']][pattern].add(u['source_index'])

    prior_first = defaultdict(list)
    for p in presentations:
        owner = owner_from_first(p)
        p['prior_modal_owner'] = running_mode(prior_first[p['pattern']])
        if owner is not None:
            prior_first[p['pattern']].append(owner)

    counts = Counter()
    for update in updates:
        factors = []
        origin = by_index.get(update['origin_presentation'])
        if update['origin_class'] == 'mixed' or update['origin_class'].startswith('stale-'):
            factors.append('STALE_QUEUE_CARRYOVER')
        if origin:
            before = set(origin['spikes_before_first_inhibition'])
            if len(before) > 1 and update['source'] in before:
                factors.append('SAME_PRESENTATION_RACE')
            prior_modal = origin.get('prior_modal_owner')
            responders = {source for _, source in origin['responders']}
            if (prior_modal is not None and update['source_index'] != prior_modal
                    and update['source'] in responders):
                factors.append('OWNER_SWITCHING')
        patterns = pixel_patterns[update['pixel']]
        source_sets = pixel_pattern_sources[update['pixel']]
        if len(patterns) > 1 and len({s for values in source_sets.values() for s in values}) > 1:
            factors.append('CROSS_PATTERN_COMMON_PIXEL')
        factors = sorted(set(factors))
        if len(factors) > 1:
            classification = 'MIXED'
        elif factors:
            classification = factors[0]
        elif update['new_source_credit'] and update['source_count_after'] > 1:
            classification = 'MIXED'
        else:
            # A repeated update from the established same owner/source is not a
            # new fragmentation event; retain it explicitly rather than invent a cause.
            classification = 'ESTABLISHED_SOURCE_REPEAT'
        update['causal_factors'] = factors
        update['classification'] = classification
        counts[classification] += 1
    return dict(counts)


def collision_onsets(presentations):
    histories = defaultdict(list)
    causal_histories = defaultdict(list)
    snapshots = []
    max_distinct = 0
    compression = None
    for p in presentations:
        owner = owner_from_first(p)
        if owner is not None:
            histories[p['pattern']].append(owner)
        causal = p.get('threshold_source')
        if causal and causal.startswith('L2E'):
            causal_histories[p['pattern']].append(int(causal[3:]))
        modes = {name: running_mode(histories[name]) for name in ORDER}
        causal_modes = {name: running_mode(causal_histories[name]) for name in ORDER}
        complete = all(modes[name] is not None for name in ORDER)
        first_collision = complete and len(set(modes.values())) < len(ORDER)
        causal_complete = all(causal_modes[name] is not None for name in ORDER)
        causal_collision = causal_complete and len(set(causal_modes.values())) < len(ORDER)
        distinct = len({x for x in modes.values() if x is not None})
        if complete:
            if max_distinct and distinct < max_distinct and compression is None:
                compression = p['index']
            max_distinct = max(max_distinct, distinct)
        snapshots.append((p['index'], first_collision, causal_collision))
    first_onset = next((i for i, fc, _ in snapshots if fc), None)
    causal_onset = next((i for i, _, cc in snapshots if cc), None)
    persistent = None
    for pos, (index, _, _) in enumerate(snapshots):
        suffix = snapshots[pos:]
        if suffix and all(fc for _, fc, _ in suffix):
            persistent = index
            break
    return dict(first_responder_collision_onset=first_onset,
                causal_winner_collision_onset=causal_onset,
                persistent_ownership_collision_onset=persistent,
                compression_onset=compression)


def run_seed(seed, steps):
    start = time.monotonic()
    engine = engine_for(seed)
    presentations = []
    updates = []
    update_mass = defaultdict(float)
    credited = [set() for _ in range(N_PIX)]
    count_thresholds = {i: {} for i in range(N_PIX)}
    step_to_presentation = {}

    n_presentations = steps // PRESENTATION_STEPS
    for pidx in range(n_presentations):
        pattern = ORDER[pidx % len(ORDER)]
        engine.set_pattern(pattern)
        p = dict(index=pidx, pattern=pattern, start_step=engine.timestep,
                 end_step=engine.timestep + PRESENTATION_STEPS - 1,
                 first_responder=None, responders=[], subsequent_responders=[],
                 spikes_before_first_inhibition=[], post_inhibition_spikes=[],
                 l2i_contributor_sets=[], threshold_source=None,
                 inhibition_schedules=[], inhibition_deliveries=[])
        presentations.append(p)
        for _ in range(PRESENTATION_STEPS):
            t = engine.timestep
            step_to_presentation[t] = pidx
            before = np.array([pc.decoder_weights for pc in engine.pcol], dtype=float).T
            engine.step()
            spikes = [f'L2E{j}' for j in range(N_OUT) if engine.spiked[f'L2E{j}']]
            if spikes:
                had_response = bool(p['responders'])
                if p['first_responder'] is None:
                    p['first_responder'] = spikes[0]
                for offset, source in enumerate(spikes):
                    p['responders'].append([t, source])
                    if had_response or offset > 0:
                        p['subsequent_responders'].append([t, source])

            newly_scheduled = [dict(record) for record in engine._l2i_pending
                               if int(record['fire_t']) == t]
            for record in newly_scheduled:
                contributors = [list(item) for item in record['contributors']]
                p['l2i_contributor_sets'].append(contributors)
                threshold_source = contributors[-1][1] if contributors else 'residual'
                if p['threshold_source'] is None:
                    p['threshold_source'] = threshold_source
                p['inhibition_schedules'].append(dict(
                    fire_step=int(record['fire_t']), arrival_step=int(record['deliver_at']),
                    contributors=contributors, threshold_source=threshold_source,
                    magnitude=float(record['magnitude'])))

            delivery = engine._last_l2_inhibition_delivery
            if delivery and int(delivery['deliver_at']) == t:
                p['inhibition_deliveries'].append(dict(delivery))

            first_arrival = (p['inhibition_deliveries'][0]['deliver_at']
                             if p['inhibition_deliveries'] else None)
            if first_arrival is None or t < first_arrival:
                p['spikes_before_first_inhibition'].extend(spikes)
            elif t > first_arrival:
                p['post_inhibition_spikes'].extend(spikes)

            after = np.array([pc.decoder_weights for pc in engine.pcol], dtype=float).T
            changed = np.argwhere(after > before)
            delivery_records = list(engine._prediction_column_last_deliveries)
            for j, i in changed:
                source, target = f'L2E{j}', f'PC{i}'
                relevant = [record for record in delivery_records
                            if record['target'] == target
                            and (record['source'] == source or record['target_compartment'] == 'basal')]
                origins = sorted({record['origin_pattern'] for record in relevant
                                  if record.get('origin_pattern') is not None})
                origin_classes = sorted({record['origin_class'] for record in relevant})
                scheduled_steps = sorted({int(record['scheduled_step']) for record in relevant})
                origin_step = scheduled_steps[0] if scheduled_steps else t - 1
                origin_presentation = step_to_presentation.get(origin_step, pidx)
                delta = float(after[j, i] - before[j, i])
                is_new = int(j) not in credited[int(i)]
                credited[int(i)].add(int(j))
                source_count_after = len(credited[int(i)])
                if is_new and len(credited[int(i)]) in range(2, 7):
                    count_thresholds[int(i)].setdefault(str(len(credited[int(i)])), dict(
                        step=t, presentation=pidx, source=source, pattern=pattern))
                update_mass[(int(i), int(j))] += delta
                updates.append(dict(
                    step=t, presentation=pidx, pattern=pattern,
                    origin_presentation=origin_presentation,
                    origin_patterns=origins, origin_class=(origin_classes[0]
                        if len(origin_classes) == 1 else 'mixed'),
                    scheduled_steps=scheduled_steps, delivered_step=t,
                    pixel=int(i), source=source, source_index=int(j),
                    d_before=float(before[j, i]), delta=delta,
                    d_after=float(after[j, i]), new_source_credit=is_new,
                    source_count_after=source_count_after))

    classifications = classify_updates(updates, presentations)
    new_classifications = Counter(u['classification'] for u in updates
                                  if u['new_source_credit'] and u['source_count_after'] > 1)
    new_factor_counts = Counter(
        factor for u in updates if u['new_source_credit'] and u['source_count_after'] > 1
        for factor in u['causal_factors'])
    onsets = collision_onsets(presentations)
    source_counts = {str(i): len(credited[i]) for i in range(N_PIX)}
    masses = {str(i): {str(j): update_mass[(i, j)] for j in range(N_OUT)
                       if update_mass[(i, j)] > 0} for i in range(N_PIX)}
    result = dict(seed=seed, steps=steps, presentations=len(presentations),
                  runtime_seconds=time.monotonic() - start,
                  config={k: engine.params[k] for k in (
                      'loser_depression', 'signed_depression', 'l2e_budget',
                      'prediction_column_enabled', 'prediction_column_to_i_enabled')},
                  all_update_classifications=classifications,
                  new_source_classifications=dict(new_classifications),
                  new_source_factor_counts=dict(new_factor_counts),
                  final_credited_source_counts=source_counts,
                  credited_sources={str(i): sorted(credited[i]) for i in range(N_PIX)},
                  update_mass_per_pixel_source=masses,
                  credited_source_threshold_onsets=count_thresholds,
                  collision_onsets=onsets,
                  presentations_trace=presentations,
                  decoder_updates=updates)
    return result


def aggregate(runs):
    new_causes = Counter()
    pixel_counts = defaultdict(list)
    center_sources = []
    stale = 0
    factor_counts = Counter()
    fragmentation_events = 0
    for run in runs:
        new_causes.update(run['new_source_classifications'])
        factor_counts.update(run['new_source_factor_counts'])
        fragmentation_events += sum(run['new_source_classifications'].values())
        for pixel, count in run['final_credited_source_counts'].items():
            pixel_counts[pixel].append(count)
        center_sources.append(run['final_credited_source_counts'][str(CENTER)])
        stale += run['new_source_classifications'].get('STALE_QUEUE_CARRYOVER', 0)
    causal = {k: factor_counts[k] for k in (
        'SAME_PRESENTATION_RACE', 'OWNER_SWITCHING', 'CROSS_PATTERN_COMMON_PIXEL',
        'STALE_QUEUE_CARRYOVER')}
    dominant = max(causal, key=causal.get) if sum(causal.values()) else None
    verdict_map = {
        'SAME_PRESENTATION_RACE': 'FRAGMENTATION_FROM_PRE_INHIBITION_RACE',
        'OWNER_SWITCHING': 'FRAGMENTATION_FROM_OWNER_SWITCHING',
        'CROSS_PATTERN_COMMON_PIXEL': 'FRAGMENTATION_FROM_COMMON_PIXEL',
        'STALE_QUEUE_CARRYOVER': 'FRAGMENTATION_FROM_STALE_CARRYOVER',
    }
    # Factor counts may overlap. A cause is primary only when it participates
    # in more than half of fragmenting new-source events.
    verdict = (verdict_map[dominant] if dominant and causal[dominant] > fragmentation_events / 2
               else 'MIXED_FRAGMENTATION_CAUSE')
    return dict(verdict=verdict, new_source_cause_counts=dict(new_causes),
                causal_factor_counts=causal,
                fragmentation_new_source_events=fragmentation_events,
                final_source_counts_per_pixel=dict(pixel_counts),
                center_source_counts=center_sources, stale_new_source_credits=stale)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--seeds', nargs='*', type=int, default=[1, 2, 3, 4, 5])
    args = parser.parse_args()
    started = time.monotonic()
    if args.smoke:
        smoke = run_seed(0, 80)
        (ROOT / 'smoke.json').write_text(json.dumps(smoke, indent=2, sort_keys=True))
        print(json.dumps(dict(smoke='PASS', seed=0, steps=80,
                              updates=len(smoke['decoder_updates']))))
        return
    runs = []
    for seed in args.seeds:
        run = run_seed(seed, FULL_STEPS)
        runs.append(run)
        (ROOT / f'seed-{seed}-trace.json').write_text(json.dumps(run, indent=2, sort_keys=True))
        print(json.dumps(dict(seed=seed, runtime=run['runtime_seconds'],
                              updates=len(run['decoder_updates']),
                              source_counts=run['final_credited_source_counts'])), flush=True)
    result = dict(commit='db30ceadbe18cf90e01f6d54dee0203f342b24a8',
                  host=platform.node(), python=sys.version, steps_per_seed=FULL_STEPS,
                  presentation_steps=PRESENTATION_STEPS, seeds=args.seeds,
                  runtime_seconds=time.monotonic() - started,
                  aggregate=aggregate(runs), runs=[{
                      k: v for k, v in run.items() if k not in ('presentations_trace', 'decoder_updates')
                  } for run in runs])
    (ROOT / 'results.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(dict(verdict=result['aggregate']['verdict'],
                          runtime=result['runtime_seconds'])))


if __name__ == '__main__':
    main()
