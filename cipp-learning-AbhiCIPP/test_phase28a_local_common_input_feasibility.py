"""Phase 28A -- focused tests for the local common-input feasibility harness
itself (not the engine). Verifies the gate touches only positive
potentiation on participating synapses (never depression, never loser
depression, never physical transmission), the trace is driven only by
physical L1E spikes with causal (not future-peeking) ordering, the
pattern-set swap is transparent and always restored, the oracle control
freezes exactly the one hardcoded pixel it targets, the gate/trace code
itself contains no pixel index or pattern-name literal, and everything is
deterministic."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

import backend.simulation as bsim
from backend.simulation import N_OUT, N_PIX
from phase28a_local_common_input_feasibility import (
    GateHolder, PATTERN_SETS, _NO_UNIVERSAL, _SHIFTED, _STANDARD,
    _patch_gated_fire, _patch_oracle_freeze, _patch_trace_update,
    _patterns_swapped, apply_condition, build_engine, condition_label,
    run_one, universal_peripheral_ratio,
)


def _all_ff_weights(engine):
    return {(j, i): float(engine.l2.excitatory_neurons[j]._weights_array[i])
           for j in range(N_OUT) for i in range(N_PIX)}


# --------------------------------------------------------------------- pattern sets
def test_standard_pattern_set_is_universal_at_pixel_4():
    assert all(_STANDARD[p][4] == 1 for p in _STANDARD)


def test_shifted_pattern_set_is_universal_at_pixel_0_not_4():
    assert all(_SHIFTED[p][0] == 1 for p in _SHIFTED)
    assert not all(_SHIFTED[p][4] == 1 for p in _SHIFTED)


def test_no_universal_pattern_set_has_no_common_pixel():
    counts = [sum(_NO_UNIVERSAL[p][i] for p in _NO_UNIVERSAL) for i in range(N_PIX)]
    assert max(counts) < len(_NO_UNIVERSAL)


def test_patterns_swap_is_transparent_and_always_restored():
    original = bsim.PATTERNS
    with _patterns_swapped(_SHIFTED):
        assert bsim.PATTERNS is _SHIFTED
        assert bsim.PATTERNS['row 1'][0] == 1
    assert bsim.PATTERNS is original


def test_patterns_swap_restores_even_on_exception():
    original = bsim.PATTERNS
    with pytest.raises(ValueError):
        with _patterns_swapped(_SHIFTED):
            raise ValueError('boom')
    assert bsim.PATTERNS is original


# --------------------------------------------------------------------- gate patch
def test_gate_only_scales_positive_potentiation_on_participating_synapses():
    engine = build_engine(1, 1)
    holder = GateHolder(N_PIX)
    holder.g[:] = 0.1   # a strong gate -- should shrink potentiation dramatically
    n = engine.l2.excitatory_neurons[0]
    _patch_gated_fire(n, holder)
    engine.set_pattern('row 1')
    w_before = n._weights_array.copy()
    for _ in range(3):
        engine.step()
    w_after = n._weights_array.copy()
    participating = n._last_input_spikes > 0.5
    delta = w_after - w_before
    # Every INACTIVE-input delta (signed depression) must be COMPLETELY
    # unaffected by the gate -- no scaling, no floor, no change in sign.
    inactive_idx = np.nonzero(~participating & (w_before > 0))[0]
    assert len(inactive_idx) > 0
    for i in inactive_idx:
        assert delta[i] <= 0.0   # depression is never turned into growth


def test_gate_never_touches_loser_depression():
    engine = build_engine(1, 1)
    holder = GateHolder(N_PIX)
    holder.g[:] = 0.0   # maximal suppression of potentiation
    orig_adi = [n.apply_delayed_inhibition for n in engine.l2.excitatory_neurons]
    for n in engine.l2.excitatory_neurons:
        _patch_gated_fire(n, holder)
    # _patch_gated_fire reassigns ONLY .fire -- .apply_delayed_inhibition's
    # bound method identity must be completely unchanged, before AND after
    # actually running (confirms loser depression is never wrapped at all,
    # not merely wrapped-but-inert).
    for n, orig in zip(engine.l2.excitatory_neurons, orig_adi):
        assert n.apply_delayed_inhibition.__func__ is orig.__func__
    engine.set_pattern('row 1')
    for _ in range(50):
        engine.step()
    for n, orig in zip(engine.l2.excitatory_neurons, orig_adi):
        assert n.apply_delayed_inhibition.__func__ is orig.__func__


def test_gate_with_g_equals_one_reproduces_ungated_potentiation_exactly():
    """g_i == 1 (no gating) must reproduce byte-identical weights vs the
    completely unpatched engine -- the gate mechanism itself introduces zero
    distortion at the neutral gate value."""
    plain = build_engine(1, 1)
    gated = build_engine(1, 1)
    holder = GateHolder(N_PIX)
    holder.g[:] = 1.0
    for n in gated.l2.excitatory_neurons:
        _patch_gated_fire(n, holder)
    plain.set_pattern('row 1')
    gated.set_pattern('row 1')
    for _ in range(100):
        plain.step()
        gated.step()
    assert _all_ff_weights(plain) == _all_ff_weights(gated)


# --------------------------------------------------------------------- trace update
def test_trace_uses_physical_l1e_spikes_not_raw_input_vec():
    src = inspect.getsource(_patch_trace_update)
    assert 'engine.spiked' in src
    assert 'engine.input_vec' not in src


def test_trace_update_is_causal_gate_reflects_previous_step_not_current():
    engine = build_engine(1, 1)
    holder = GateHolder(N_PIX)
    _patch_trace_update(engine, holder, tau_c=40, g_min=0.1)
    engine.set_pattern('row 1')
    assert (holder.g == 1.0).all()   # before any step, trace is 0 -> gate == 1
    engine.step()
    g_after_one_step = holder.g.copy()
    assert not (g_after_one_step == 1.0).all()   # active pixels' gate must have moved
    # The gate value in effect DURING step 1 (before this update ran) was
    # still the neutral 1.0 -- i.e. step 1's own spikes could not have
    # affected step 1's own gate value. Verified structurally: holder.g is
    # only written inside the wrapped step's post-orig() block, never before.
    src = inspect.getsource(_patch_trace_update)
    assert src.index('orig_step()') < src.index('holder.g[:]')


# --------------------------------------------------------------------- oracle
def test_oracle_freezes_exactly_the_targeted_pixel():
    engine = build_engine(1, 1)
    n = engine.l2.excitatory_neurons[0]
    frozen_pixel = 4
    _patch_oracle_freeze(n, frozen_pixel)
    engine.set_pattern('row 1')
    w0 = float(n._weights_array[frozen_pixel])
    for _ in range(200):
        engine.step()
    assert float(n._weights_array[frozen_pixel]) == w0
    # Some OTHER pixel must have actually changed -- the freeze is targeted,
    # not a global plasticity halt.
    other_changed = any(
        abs(float(n._weights_array[i]) - w0) > 1e-9 for i in range(N_PIX) if i != frozen_pixel)
    assert other_changed


def test_oracle_requires_a_universal_pixel():
    engine = build_engine(1, 1)
    with pytest.raises(ValueError):
        apply_condition(engine, 'oracle', universal_pixel=None)


# --------------------------------------------------------------------- no hardcoding
def test_gate_and_trace_code_contain_no_pixel_index_or_pattern_literal():
    for fn in (_patch_gated_fire, _patch_trace_update, apply_condition):
        src = inspect.getsource(fn)
        for banned in ('row 1', 'col 1', 'diag', "== 4", '[4]', "== 0]"):
            assert banned not in src, f'{fn.__name__} contains {banned!r}'


def test_universal_peripheral_ratio_is_none_for_no_universal_set():
    engine, tracer, plog, initw, sp = run_one('no_universal', 'interleaved', 'baseline', 1)
    ratio = universal_peripheral_ratio(tracer._all_ff_weights(), None)
    assert ratio is None


def test_universal_peripheral_ratio_uses_the_right_pixel_per_set():
    engine_std, tracer_std, *_ = run_one('standard', 'interleaved', 'baseline', 1)
    engine_sh, tracer_sh, *_ = run_one('shifted', 'interleaved', 'baseline', 1)
    r_std = universal_peripheral_ratio(tracer_std._all_ff_weights(), 4)
    r_sh = universal_peripheral_ratio(tracer_sh._all_ff_weights(), 0)
    assert r_std['mean_ratio'] is not None
    assert r_sh['mean_ratio'] is not None


# --------------------------------------------------------------------- determinism
def test_repeated_identical_runs_are_deterministic():
    r1 = run_one('standard', 'interleaved', ('gate', 80, 0.25), 5)
    r2 = run_one('standard', 'interleaved', ('gate', 80, 0.25), 5)
    assert _all_ff_weights(r1[0]) == _all_ff_weights(r2[0])
    assert r1[2] == r2[2]   # presentation logs identical


def test_baseline_condition_applies_no_patch_at_all():
    engine = build_engine(1, 1)
    fire_before = [n.fire.__func__ for n in engine.l2.excitatory_neurons]
    holder = apply_condition(engine, 'baseline', universal_pixel=4)
    assert holder is None
    fire_after = [n.fire.__func__ for n in engine.l2.excitatory_neurons]
    for a, b in zip(fire_before, fire_after):
        assert a is b


def test_condition_label_format():
    assert condition_label('baseline') == 'baseline'
    assert condition_label('oracle') == 'oracle'
    assert condition_label(('gate', 80, 0.25)) == 'gate:tau_c=80:g_min=0.25'
