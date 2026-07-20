#!/usr/bin/env python3
"""Offline timing decomposition over existing Phase 35 fragmentation traces."""

from collections import Counter
import glob
import json
from pathlib import Path
import statistics
import time

SOURCE = Path('/home/cxiong/codex-runs/codex1-phase35-source-fragmentation')
OUT = Path('/home/cxiong/codex-runs/codex1-phase35-race-timing-decomposition')


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def distribution(values):
    counts = Counter(values)
    return {
        'count': len(values), 'min': min(values) if values else None,
        'median': statistics.median(values) if values else None,
        'p90': percentile(values, .9), 'max': max(values) if values else None,
        'histogram': {str(k): counts[k] for k in sorted(counts)},
    }


def decompose():
    started = time.monotonic()
    events = []
    for trace_path in sorted(glob.glob(str(SOURCE / 'seed-*-trace.json'))):
        run = json.loads(Path(trace_path).read_text())
        presentations = {p['index']: p for p in run['presentations_trace']}
        for update in run['decoder_updates']:
            if not (update['new_source_credit'] and update['source_count_after'] > 1
                    and 'SAME_PRESENTATION_RACE' in update['causal_factors']):
                continue
            presentation = presentations[update['origin_presentation']]
            first_step, first_source = presentation['responders'][0]
            rival_step = min(update['scheduled_steps'])
            schedule = min(presentation['inhibition_schedules'],
                           key=lambda x: (x['fire_step'], x['arrival_step']))
            crossing_step = schedule['fire_step']
            delivery_step = schedule['arrival_step']
            matching_delivery = next(
                (d for d in presentation['inhibition_deliveries']
                 if d['deliver_at'] == delivery_step), None)
            target_record = None
            if matching_delivery:
                target_record = next(
                    (t for t in matching_delivery['targets']
                     if t['id'] == update['source']), None)
            later_source_steps = [t for t, source in presentation['responders']
                                  if source == update['source'] and t > delivery_step]
            rebound_step = min(later_source_steps) if later_source_steps else None

            credited_first = update['source'] == first_source and rival_step == first_step
            if credited_first:
                interval = 'AMBIGUOUS_OR_MIXED'
            # L2E firing precedes L2I receive/threshold evaluation within the
            # same engine step, so equality belongs to the accumulation window.
            elif rival_step <= crossing_step:
                interval = 'ACCUMULATION_WINDOW'
            elif rival_step < delivery_step:
                interval = 'DELIVERY_DELAY'
            elif rival_step >= delivery_step and target_record:
                interval = 'POST_INHIBITION_RESIDUAL'
            else:
                interval = 'AMBIGUOUS_OR_MIXED'

            events.append({
                'seed': run['seed'], 'pixel': update['pixel'],
                'decoder_source': update['source'], 'pattern': presentation['pattern'],
                'presentation': presentation['index'], 'decoder_update_step': update['step'],
                'first_l2e_source': first_source, 'first_l2e_spike_step': first_step,
                'rival_new_source_l2e_spike_step': rival_step,
                'l2i_contributor_arrival_steps': [item[0] for item in schedule['contributors']],
                'l2i_contributors': schedule['contributors'],
                'l2i_threshold_crossing_step': crossing_step,
                'threshold_causing_source': schedule['threshold_source'],
                'inhibition_scheduling_step': schedule['fire_step'],
                'inhibition_delivery_step': delivery_step,
                'rival_fired_before_threshold_crossing': rival_step <= crossing_step,
                'rival_fired_after_crossing_before_delivery': crossing_step < rival_step < delivery_step,
                'rival_fired_after_receiving_inhibition': rival_step >= delivery_step,
                'rival_membrane_before_inhibition': target_record['v_pre'] if target_record else None,
                'rival_membrane_after_inhibition': target_record['v_post'] if target_record else None,
                'inhibition_applied_to_rival': target_record['applied'] if target_record else None,
                'residual_charge': target_record['v_post'] if target_record else None,
                'later_rebound_spike_step': rebound_step,
                'rebound_delay': rebound_step - delivery_step if rebound_step is not None else None,
                'first_to_rival_margin': rival_step - first_step,
                'accumulation_delay': crossing_step - first_step,
                'delivery_delay': delivery_step - crossing_step,
                'primary_causal_interval': interval,
                'credited_source_was_first_responder': credited_first,
            })

    intervals = Counter(e['primary_causal_interval'] for e in events)
    secondary = [e for e in events if not e['credited_source_was_first_responder']]
    accumulation = [e for e in secondary if e['primary_causal_interval'] == 'ACCUMULATION_WINDOW']
    delivery = [e for e in secondary if e['primary_causal_interval'] == 'DELIVERY_DELAY']
    residual = [e for e in secondary if e['primary_causal_interval'] == 'POST_INHIBITION_RESIDUAL']
    ambiguous = [e for e in secondary if e['primary_causal_interval'] == 'AMBIGUOUS_OR_MIXED']

    # Offline interval-removal estimates. These count observed secondary spikes;
    # they do not mutate or re-simulate membrane dynamics.
    zero_delay_remaining = len(accumulation) + len(residual) + len(ambiguous)
    first_spike_cross_remaining = sum(
        e['rival_new_source_l2e_spike_step'] == e['first_l2e_spike_step']
        for e in secondary) + len(residual) + len(ambiguous)
    zero_residual_remaining = len(accumulation) + len(delivery) + len(ambiguous)

    causal_counts = {k: intervals[k] for k in (
        'ACCUMULATION_WINDOW', 'DELIVERY_DELAY',
        'POST_INHIBITION_RESIDUAL', 'AMBIGUOUS_OR_MIXED')}
    dominant = max(('ACCUMULATION_WINDOW', 'DELIVERY_DELAY', 'POST_INHIBITION_RESIDUAL'),
                   key=lambda k: intervals[k])
    verdicts = {
        'ACCUMULATION_WINDOW': 'ACCUMULATION_WINDOW_DOMINATES',
        'DELIVERY_DELAY': 'DELIVERY_DELAY_DOMINATES',
        'POST_INHIBITION_RESIDUAL': 'POST_INHIBITION_RESIDUAL_DOMINATES',
    }
    verdict = (verdicts[dominant]
               if intervals[dominant] > len(secondary) / 2 else 'MIXED_TIMING_FAILURE')
    result = {
        'verdict': verdict,
        'source_commit': 'db30ceadbe18cf90e01f6d54dee0203f342b24a8',
        'input_trace_count': 5,
        'race_involved_fragmenting_credits': len(events),
        'genuine_secondary_rival_credits': len(secondary),
        'credited_first_responder_ambiguous_events': sum(
            e['credited_source_was_first_responder'] for e in events),
        'primary_interval_counts': causal_counts,
        'counterfactual_estimates': {
            'observed_secondary_spikes': len(secondary),
            'secondary_spikes_remaining_if_delivery_delay_zero': zero_delay_remaining,
            'secondary_spikes_remaining_if_l2i_crossed_on_first_l2_spike': first_spike_cross_remaining,
            'secondary_spikes_remaining_if_post_inhibition_residual_removed': zero_residual_remaining,
            'method': 'offline removal of events in the addressed causal interval; same-step races remain causal',
        },
        'minimum_first_to_rival_margin': min(
            e['first_to_rival_margin'] for e in secondary) if secondary else None,
        'timing_distributions': {
            'first_to_rival_margin': distribution([e['first_to_rival_margin'] for e in secondary]),
            'accumulation_delay': distribution([e['accumulation_delay'] for e in secondary]),
            'delivery_delay': distribution([e['delivery_delay'] for e in secondary]),
            'rebound_delay': distribution([e['rebound_delay'] for e in secondary
                                           if e['rebound_delay'] is not None]),
        },
        'membrane_summary': {
            'delivery_records_present': sum(e['rival_membrane_before_inhibition'] is not None for e in events),
            'nonzero_residual_after_delivery': sum(
                (e['residual_charge'] or 0) > 0 for e in events),
            'later_rebound_observed': sum(e['later_rebound_spike_step'] is not None for e in events),
        },
        'runtime_seconds': time.monotonic() - started,
        'events': events,
    }
    return result


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    result = decompose()
    (OUT / 'results.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    (OUT / 'event_decomposition.json').write_text(json.dumps(result['events'], indent=2, sort_keys=True))
    print(json.dumps({k: result[k] for k in (
        'verdict', 'race_involved_fragmenting_credits',
        'genuine_secondary_rival_credits', 'primary_interval_counts',
        'counterfactual_estimates', 'runtime_seconds')}, sort_keys=True))
