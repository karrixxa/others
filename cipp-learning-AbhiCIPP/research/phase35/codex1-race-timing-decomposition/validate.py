#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path('/home/cxiong/codex-runs/codex1-phase35-race-timing-decomposition')
x = json.loads((ROOT / 'results.json').read_text())
events = json.loads((ROOT / 'event_decomposition.json').read_text())
allowed = {'ACCUMULATION_WINDOW', 'DELIVERY_DELAY',
           'POST_INHIBITION_RESIDUAL', 'AMBIGUOUS_OR_MIXED'}
assert x['source_commit'] == 'db30ceadbe18cf90e01f6d54dee0203f342b24a8'
assert len(events) == x['race_involved_fragmenting_credits'] == 120
assert sum(x['primary_interval_counts'].values()) == 120
assert all(e['primary_causal_interval'] in allowed for e in events)
assert all(e['l2i_threshold_crossing_step'] is not None for e in events)
assert all(e['inhibition_delivery_step'] is not None for e in events)
assert all(e['rival_membrane_before_inhibition'] is not None for e in events)
assert all(e['rival_membrane_after_inhibition'] is not None for e in events)
assert all(e['inhibition_applied_to_rival'] for e in events)
assert all(e['decoder_update_step'] == e['rival_new_source_l2e_spike_step'] + 1
           for e in events)
print(json.dumps({'status': 'PASS', 'events': len(events),
                  'interval_counts': x['primary_interval_counts']}, sort_keys=True))
