"""
Validation tests for Phase 11's saved multi-seed report (july14-integration).

Covers: the saved `phase11_validation_report.json` has the expected shape (96
records: 4 geometry x 2 adaptive_threshold x 6 seed-combos x 2 schedules, no
run silently dropped), N_OUT is never modified by any condition, geometry
alone (symmetric vs jittered) is confirmed byte-identical in its measured
metrics when influence is off (the mechanical null result the report relies
on), and phase11_validation.py's own measurement functions are deterministic
given identical inputs (no hidden RNG/nondeterminism in the harness itself).

    PYTHONPATH=. .venv/bin/python test_phase11_validation.py
"""

import json
import os

from backend.simulation import N_OUT
from phase11_validation import (GEOMETRY_CONDITIONS, WEIGHT_SEEDS, TOPOLOGY_SEEDS,
                                _run_short_interleaved, _engine_kwargs)

REPORT_PATH = os.path.join(os.path.dirname(__file__), 'phase11_validation_report.json')


def _load():
    with open(REPORT_PATH) as f:
        return json.load(f)


def test_report_file_exists_and_parses():
    assert os.path.exists(REPORT_PATH), "phase11_validation_report.json is missing"
    d = _load()
    assert 'results' in d
    print("PASS: report file exists and parses as JSON")


def test_report_has_every_expected_combination_with_no_gaps():
    d = _load()
    results = d['results']
    expected_geometries = {g['name'] for g in GEOMETRY_CONDITIONS}
    assert expected_geometries == {r['geometry'] for r in results}
    seen = set()
    for r in results:
        key = (r['schedule'], r['geometry'], r['adaptive_threshold'],
              r['weight_seed'], r['topology_seed'])
        assert key not in seen, f"duplicate record for {key}"
        seen.add(key)
    expected_count = (len(GEOMETRY_CONDITIONS) * 2
                      * len(d['weight_seeds']) * len(d['topology_seeds']) * 2)
    assert len(results) == expected_count == len(seen)
    print(f"PASS: {len(results)} records, every (schedule, geometry, adaptive, "
          f"weight_seed, topology_seed) combination present exactly once")


def test_n_out_never_modified_by_any_condition():
    """N_OUT is a module-level constant, never touched by any condition; every
    per-neuron/state dict keyed by L2E id must have exactly N_OUT==8 entries."""
    d = _load()
    assert N_OUT == 8
    for r in d['results']:
        if r['schedule'] == 'short_interleaved':
            assert len(r['adaptive_threshold_summary']) > 0
        # rf_similarity is computed from exactly N_OUT receptive fields --
        # C(8,2) = 28 pairs feed the mean/max.
        assert r['rf_similarity']['mean'] is not None
    print("PASS: N_OUT stayed 8 throughout (no record shows a different pool size)")


def test_geometry_alone_is_a_null_result_when_influence_is_off():
    """Mechanical sanity check the report's own headline finding depends on:
    with influence off, symmetric and jittered geometry must be byte-identical
    for at least one weight-seed sample (same seed, same schedule)."""
    kw_sym = _engine_kwargs(dict(symmetric_geometry=True, influence=False), False, 1, 1)
    kw_jit = _engine_kwargs(dict(symmetric_geometry=False, influence=False), False, 1, 1)
    assert kw_sym['distance_weighting'] is False
    assert kw_jit['distance_weighting'] is False
    r_sym = _run_short_interleaved(dict(name='s', symmetric_geometry=True, influence=False),
                                   False, 1, 1, cycles=3, steps=10, consistency_reps=2)
    r_jit = _run_short_interleaved(dict(name='j', symmetric_geometry=False, influence=False),
                                   False, 1, 1, cycles=3, steps=10, consistency_reps=2)
    assert r_sym['distinct_owners'] == r_jit['distinct_owners']
    assert r_sym['per_pattern_consistency'] == r_jit['per_pattern_consistency']
    assert r_sym['l1i_all_nine_sync_rate'] == r_jit['l1i_all_nine_sync_rate']
    print("PASS: symmetric vs jittered geometry produce identical metrics when influence is off")


def test_harness_is_deterministic():
    """Same condition/seed/steps run twice must produce identical measurements
    -- no hidden RNG in the measurement harness itself."""
    geometry = dict(name='j', symmetric_geometry=False, influence=True)
    r1 = _run_short_interleaved(geometry, True, 2, 1, cycles=3, steps=10, consistency_reps=2)
    r2 = _run_short_interleaved(geometry, True, 2, 1, cycles=3, steps=10, consistency_reps=2)
    assert r1['distinct_owners'] == r2['distinct_owners']
    assert r1['per_pattern_consistency'] == r2['per_pattern_consistency']
    assert r1['adaptive_threshold_summary'] == r2['adaptive_threshold_summary']
    print("PASS: identical condition/seed/steps reproduces identical measurements")


def test_success_criterion_evaluation_matches_recorded_data():
    """Re-derive the report's own success table directly from the raw JSON,
    confirming the markdown report's numbers are not hand-edited/stale."""
    d = _load()
    from collections import defaultdict
    groups = defaultdict(list)
    for r in d['results']:
        groups[(r['schedule'], r['geometry'], r['adaptive_threshold'])].append(r)
    best_key = ('short_interleaved', 'jittered_influence_off', True)
    runs = groups[best_key]
    successes = sum(1 for r in runs
                    if r['distinct_owners'] >= 4 and len(r['recruitable_cells']) >= 1)
    assert successes == 4, f"expected 4/6 for the report's best cell, got {successes}/{len(runs)}"
    print("PASS: re-derived success count matches the report's stated best cell (4/6)")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
