"""
Harness-verification tests for Phase 16 (factorial + spare-capacity
challenge, july14-integration). These test the MEASUREMENT SCRIPT's own
bookkeeping, not the (already-tested, Phase 10/15) neural mechanisms --
same convention as test_phase11_validation.py / test_phase13b_tracer_timing.py.

Plain-script style (matches test_adaptive_threshold.py etc.):
    PYTHONPATH=. .venv/bin/python test_phase16_harness.py
"""

import numpy as np

from backend.simulation import N_OUT, PATTERNS, PROBES
from phase16_factorial_spare_capacity import (
    build_engine, run_interleaved_40, _present_novel_and_record,
    spare_capacity_challenge, NOVEL_PATTERN, CYCLE_ORDER,
)


def test_novel_presentation_keeps_plasticity_live():
    """_present_novel_and_record must NOT freeze plasticity -- unlike
    present_probe(), the novel pattern's feedforward weights must actually
    change across repeated exposures with real spikes."""
    engine, _tracer, _pres = run_interleaved_40('A_adaptive_off_protection_off', 1, 1, cycles=10)
    assert engine.plasticity_frozen is False
    w_before = np.array([e._weights_array.copy() for e in engine.l2.excitatory_neurons])
    records = []
    any_spike = False
    for _ in range(15):
        _present_novel_and_record(engine, NOVEL_PATTERN, 20, records)
        if any(r['first_l2e_spiker'] for r in records):
            any_spike = True
    w_after = np.array([e._weights_array.copy() for e in engine.l2.excitatory_neurons])
    assert engine.plasticity_frozen is False, "novel presentation must never leave plasticity frozen"
    assert any_spike, "expected at least one real spike across 15 novel-pattern exposures"
    assert not np.allclose(w_before, w_after), \
        "weights never changed during novel exposure -- plasticity was not actually live"
    print("PASS: novel-pattern presentation keeps plasticity live (weights actually change)")


def test_novel_presentation_uses_presentation_tracking():
    """Each call to _present_novel_and_record must register as its own
    presentation (causal_story's presentation_id advances, role='novel') --
    confirms it goes through the same bookkeeping set_pattern()/
    present_probe() already use, not an ad hoc side channel."""
    engine, _tracer, _pres = run_interleaved_40('A_adaptive_off_protection_off', 1, 1, cycles=5)
    id_before = engine.presentation_id
    records = []
    _present_novel_and_record(engine, NOVEL_PATTERN, 20, records)
    assert engine.presentation_id == id_before + 1
    assert engine.presentation_role == 'novel'
    assert engine.current_pattern == NOVEL_PATTERN
    assert np.array_equal(engine.input_vec, np.array(PROBES[NOVEL_PATTERN], dtype=float))
    print("PASS: novel presentation advances presentation_id/role through the real bookkeeping")


def test_spare_capacity_challenge_shape_and_invariants():
    """Run the full challenge on a small, fast engine and check the report's
    own internal consistency -- not the neural outcome (which varies by
    seed and is reported honestly in the Phase 16 report, not asserted
    here)."""
    engine, _tracer, _pres = run_interleaved_40('A_adaptive_off_protection_off', 1, 1, cycles=10)
    result = spare_capacity_challenge('A_adaptive_off_protection_off', 1, 1, engine)

    assert set(result['pre_novel_owners'].keys()) == set(CYCLE_ORDER)
    assert set(result['post_novel_owners'].keys()) == set(CYCLE_ORDER)
    assert set(result['retention'].keys()) == set(CYCLE_ORDER)
    for p in CYCLE_ORDER:
        expected = result['pre_novel_owners'][p]['modal_owner'] == result['post_novel_owners'][p]['modal_owner']
        assert result['retention'][p] == expected, f"retention mismatch for {p}"

    if result['novel_modal_owner'] is not None:
        assert 0.0 <= result['novel_consistency'] <= 1.0
        owners_pre = {v['modal_owner'] for v in result['pre_novel_owners'].values()}
        expected_capture = result['novel_modal_owner'] in owners_pre
        assert result['tyrant_captured_novel'] == expected_capture
        expected_collisions = [p for p in CYCLE_ORDER
                               if result['pre_novel_owners'][p]['modal_owner'] == result['novel_modal_owner']]
        assert result['collisions_with_original_four'] == expected_collisions
    else:
        assert result['novel_consistency'] is None
        assert result['tyrant_captured_novel'] is False

    if result['locked_in_rep'] is not None and result['first_response_rep'] is not None:
        assert result['locked_in_rep'] >= result['first_response_rep'] or \
            result['locked_in_rep'] == result['first_response_rep'], \
            "locked-in rep should not precede the first-ever response rep"
    print("PASS: spare-capacity challenge report is internally consistent "
         f"(this run: novel owner={result['novel_modal_owner']}, "
         f"pre-novel status={result['responder_pre_novel_status']})")


def test_no_hardcoded_quiet_neuron_count_rule():
    """The harness must not assert or require any specific quiet/unrecruited
    count anywhere in its own logic -- confirms the source contains no such
    gate (a literal grep-style check on the module's own code)."""
    import inspect
    import phase16_factorial_spare_capacity as mod
    src = inspect.getsource(mod)
    # No assertion anywhere in the measurement module itself gating on a
    # specific count of quiet/unrecruited neurons (the module only ever
    # reports counts, never requires one).
    assert 'assert' not in src, "the measurement harness must not assert/gate on outcomes -- report only"
    print("PASS: the harness contains no hardcoded quiet-neuron-count acceptance rule")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
