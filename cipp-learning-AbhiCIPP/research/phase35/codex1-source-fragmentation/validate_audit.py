#!/usr/bin/env python3
"""Integrity checks for the measurement-only fragmentation audit."""

import glob
import json
from pathlib import Path

ROOT = Path('/home/cxiong/codex-runs/codex1-phase35-source-fragmentation')
ALLOWED = {
    'SAME_PRESENTATION_RACE', 'OWNER_SWITCHING',
    'CROSS_PATTERN_COMMON_PIXEL', 'STALE_QUEUE_CARRYOVER', 'MIXED'
}

result = json.loads((ROOT / 'results.json').read_text())
assert result['commit'] == 'db30ceadbe18cf90e01f6d54dee0203f342b24a8'
assert result['seeds'] == [1, 2, 3, 4, 5]
assert result['steps_per_seed'] == 12_800
assert result['presentation_steps'] == 20
assert result['aggregate']['verdict'] in {
    'FRAGMENTATION_FROM_PRE_INHIBITION_RACE',
    'FRAGMENTATION_FROM_OWNER_SWITCHING', 'FRAGMENTATION_FROM_COMMON_PIXEL',
    'FRAGMENTATION_FROM_STALE_CARRYOVER', 'MIXED_FRAGMENTATION_CAUSE'}

traces = sorted(glob.glob(str(ROOT / 'seed-*-trace.json')))
assert len(traces) == 5
presentations = updates = fragmenting = 0
for trace in traces:
    run = json.loads(Path(trace).read_text())
    assert run['steps'] == 12_800 and run['presentations'] == 640
    assert run['config'] == {
        'l2e_budget': False, 'loser_depression': False,
        'prediction_column_enabled': True,
        'prediction_column_to_i_enabled': False,
        'signed_depression': False}
    presentations += len(run['presentations_trace'])
    updates += len(run['decoder_updates'])
    for update in run['decoder_updates']:
        if update['new_source_credit'] and update['source_count_after'] > 1:
            fragmenting += 1
            assert update['classification'] in ALLOWED
        assert update['delivered_step'] == update['step']
        assert update['delta'] > 0
assert presentations == 3_200
assert updates == 93_318
assert fragmenting == 165
print(json.dumps({'status': 'PASS', 'traces': 5, 'presentations': presentations,
                  'decoder_updates': updates, 'fragmenting_new_sources': fragmenting},
                 sort_keys=True))
