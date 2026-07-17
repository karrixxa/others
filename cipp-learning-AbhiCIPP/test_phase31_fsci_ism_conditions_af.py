"""Phase 31 -- regression tests for the A-F condition harness itself,
focused on the one real bug found and fixed during this phase:
copy.deepcopy does not actually duplicate Python closures, so an
instrumented (CausalTracer-patched) engine's naive deep copy still steps
the ORIGINAL engine, not an independent probe. Also covers the
decoder_functional_check's membrane/queue reset (the fix that made the
false-positive "fired from feedback alone" result go away once residual
carried-over charge was eliminated)."""

from __future__ import annotations

import copy

import numpy as np

from backend.simulation import N_OUT, N_PIX, SimulationEngine
from backend.presets import DASHBOARD_PRESET
from phase27_l2_ownership_causal_audit import CausalTracer
from phase31_fsci_ism_conditions_af import (
    _unpatched_deepcopy, condition_kwargs, decoder_functional_check,
)


def _traced_engine(**overrides):
    e = SimulationEngine(seed=1, topology_seed=1, **{**DASHBOARD_PRESET, **overrides})
    CausalTracer(e)
    return e


def test_naive_deepcopy_of_a_traced_engine_shares_the_step_closure():
    """Documents the exact failure mode this phase found: a plain
    copy.deepcopy of an instrumented engine produces a copy whose .step
    (and each L2E's .fire) are the SAME closure objects as the original,
    which still operate on the ORIGINAL engine."""
    e = _traced_engine()
    e.set_pattern('row 1')
    for _ in range(20):
        e.step()
    naive_copy = copy.deepcopy(e)
    assert naive_copy.step is e.step
    t_before = e.timestep
    naive_copy.step()
    assert e.timestep == t_before + 1   # stepping the "copy" mutated the original


def test_unpatched_deepcopy_is_a_genuinely_independent_probe():
    e = _traced_engine()
    e.set_pattern('row 1')
    for _ in range(20):
        e.step()
    probe = _unpatched_deepcopy(e)
    assert probe.step is not e.step
    t_before = e.timestep
    for _ in range(30):
        probe.step()
    assert e.timestep == t_before   # the original is untouched
    assert probe.timestep == t_before + 30


def test_unpatched_deepcopy_preserves_weights_and_state():
    e = _traced_engine(prediction_column_enabled=True)
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    probe = _unpatched_deepcopy(e)
    for j in range(N_OUT):
        assert np.array_equal(probe.l2.excitatory_neurons[j]._weights_array,
                              e.l2.excitatory_neurons[j]._weights_array)
    assert probe.timestep == e.timestep


def test_decoder_functional_check_does_not_mutate_the_original_engine():
    e = _traced_engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    w_before = [n._weights_array.copy() for n in e.l2.excitatory_neurons]
    t_before = e.timestep
    decoder_functional_check(e)
    assert e.timestep == t_before
    for j, w in enumerate(w_before):
        assert np.array_equal(e.l2.excitatory_neurons[j]._weights_array, w)


def test_decoder_functional_check_resets_residual_charge_before_probing():
    """The bug this test locks in: without resetting PC/L1E/L2E membrane
    potentials and draining the PC delivery queues first, LEFTOVER charge
    from the live run could cause a spurious spike in the probe's first few
    steps -- reported as "reconstructed from feedback alone" even when the
    decoder weights are, numerically, barely different from their init
    value. Directly force every PC's membrane far above threshold right
    before the check and confirm the probe still reports no reconstruction
    (since the reset must zero it before the zero-input phase begins)."""
    e = _traced_engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    e.set_pattern('row 1')
    for _ in range(20):
        e.step()
    for pc in e.pcol:
        pc.potential = e.prediction_threshold * 10   # far above threshold
    result = decoder_functional_check(e)
    assert result['any_fired_feedback_alone'] is False


def test_condition_kwargs_are_explicit_and_mutually_distinguishable():
    seen = set()
    for name in 'ABCDEF':
        kw = condition_kwargs(name)
        key = tuple(sorted((k, v) for k, v in kw.items()
                          if k in ('centered_encoder_enabled', 'loser_depression',
                                  'prediction_column_enabled',
                                  'prediction_subthreshold_decoder_enabled',
                                  'prediction_column_to_i_enabled',
                                  'prediction_leak_diagnostic_disable')))
        assert key not in seen, f'condition {name} duplicates an earlier condition'
        seen.add(key)
    # A is the untouched legacy baseline.
    assert condition_kwargs('A') == dict(DASHBOARD_PRESET)
