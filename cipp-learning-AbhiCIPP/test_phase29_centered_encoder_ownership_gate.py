"""Phase 29 -- focused tests for the centered/covariance encoder feasibility
harness itself (not the engine). Verifies locality (only this neuron's own
state and the shared presynaptic trace are read), that the update triggers
only on the neuron's own physical spike, that loser depression is off for
the centered condition but the physical membrane transient/L2I competition
are untouched, that the trace uses only physical L1E spikes, determinism,
and that legacy behaves like the existing unmodified engine."""

from __future__ import annotations

import inspect

import numpy as np

from backend.simulation import N_OUT, N_PIX
from phase29_centered_encoder_ownership_gate import (
    ALPHA, XBarHolder, _centered_update, _patch_centered_condition,
    _patch_trace_update, build_engine, run_one,
)


def _all_ff_weights(engine):
    return {(j, i): float(engine.l2.excitatory_neurons[j]._weights_array[i])
           for j in range(N_OUT) for i in range(N_PIX)}


def test_legacy_condition_is_byte_identical_to_a_plain_engine():
    from backend.presets import DASHBOARD_PRESET
    from backend.simulation import SimulationEngine
    plain = SimulationEngine(seed=1, topology_seed=1, **DASHBOARD_PRESET)
    legacy = build_engine('legacy', 1, 1)
    plain.set_pattern('row 1')
    legacy.set_pattern('row 1')
    for _ in range(300):
        plain.step()
        legacy.step()
    assert _all_ff_weights(plain) == _all_ff_weights(legacy)


def test_centered_condition_disables_loser_depression_only():
    engine = build_engine('centered', 1, 1)
    assert engine.params['loser_depression'] is False
    for n in engine.l2.excitatory_neurons:
        assert n.loser_depression is False
    # l2i_hard_reset_losers (the PHYSICAL transient/competition) must remain
    # exactly as DASHBOARD_PRESET's own default -- untouched by this phase.
    from backend.presets import DASHBOARD_PRESET
    assert engine.params['l2i_hard_reset_losers'] == DASHBOARD_PRESET['l2i_hard_reset_losers']


def test_centered_update_reads_only_local_neuron_and_trace_state():
    src = inspect.getsource(_centered_update)
    code_only = src.split('"""', 2)[-1]   # drop the docstring, check code only
    banned = ('PATTERNS', 'engine.', 'rival', 'owner', 'argmax')
    for b in banned:
        assert b not in code_only, f'{b!r} found in _centered_update code'
    assert 'n._last_input_spikes' in code_only
    assert 'n._weights_array' in code_only
    assert 'holder.x_bar' in code_only


def test_centered_update_is_gated_on_this_neurons_own_spike():
    """_update_weights (which _centered_update replaces) is called from
    inside Neuron.fire() -- i.e. only on this neuron's own physical spike,
    the same trigger every other rule in this codebase already uses."""
    src = inspect.getsource(_patch_centered_condition)
    assert '_update_weights' in src


def test_centered_update_produces_zero_delta_when_signal_equals_trace():
    """s_i = x_i - x_bar_i == 0 (a pixel exactly at its own running mean)
    must produce exactly zero weight change for that synapse -- direct
    algebraic check of the equation, not just an engine-level side effect."""
    engine = build_engine('centered', 1, 1)
    n = engine.l2.excitatory_neurons[0]
    holder = XBarHolder(N_PIX)
    n._last_input_spikes = np.zeros(N_PIX)
    holder.x_bar[:] = 0.0   # x_i == x_bar_i == 0 everywhere
    w_before = n._weights_array.copy()
    _centered_update(n, v_pre=0.0, holder=holder)
    assert np.allclose(n._weights_array, w_before)


def test_centered_update_potentiates_above_mean_and_depresses_below_mean():
    engine = build_engine('centered', 1, 1)
    n = engine.l2.excitatory_neurons[0]
    n._weights_array[:] = 100.0   # mid-range, away from both bounds
    holder = XBarHolder(N_PIX)
    holder.x_bar[:] = 0.3
    n._last_input_spikes = np.zeros(N_PIX)
    n._last_input_spikes[0] = 1.0   # x_0=1 > x_bar_0=0.3 -> potentiate
    n._last_input_spikes[1] = 0.0   # x_1=0 < x_bar_1=0.3 -> depress
    w_before = n._weights_array.copy()
    _centered_update(n, v_pre=0.0, holder=holder)
    assert n._weights_array[0] > w_before[0]
    assert n._weights_array[1] < w_before[1]


def test_centered_update_never_creates_negative_weight():
    engine = build_engine('centered', 1, 1)
    n = engine.l2.excitatory_neurons[0]
    n._weights_array[:] = 1.0   # near the floor
    holder = XBarHolder(N_PIX)
    holder.x_bar[:] = 1.0
    n._last_input_spikes = np.zeros(N_PIX)   # every pixel far below its trace -> strong depress signal
    _centered_update(n, v_pre=0.0, holder=holder)
    assert (n._weights_array >= (n.min_positive_weight or 0.0)).all()


def test_centered_update_respects_weight_cap():
    engine = build_engine('centered', 1, 1)
    n = engine.l2.excitatory_neurons[0]
    w_max = n.excitatory_saturation_cap if n.excitatory_saturation_cap is not None else n.weight_cap
    n._weights_array[:] = w_max - 0.5
    holder = XBarHolder(N_PIX)
    holder.x_bar[:] = 0.0
    n._last_input_spikes = np.ones(N_PIX)   # maximal potentiation signal
    for _ in range(50):
        _centered_update(n, v_pre=0.0, holder=holder)
    assert (n._weights_array <= w_max + 1e-6).all()


def test_no_update_when_plasticity_frozen():
    engine = build_engine('centered', 1, 1)
    n = engine.l2.excitatory_neurons[0]
    n.plasticity_frozen = True
    holder = XBarHolder(N_PIX)
    holder.x_bar[:] = 0.0
    n._last_input_spikes = np.ones(N_PIX)
    w_before = n._weights_array.copy()
    _centered_update(n, v_pre=0.0, holder=holder)
    assert np.array_equal(n._weights_array, w_before)


def test_trace_update_uses_physical_l1e_spikes_not_input_vec():
    src = inspect.getsource(_patch_trace_update)
    assert 'engine.spiked' in src
    assert 'engine.input_vec' not in src


def test_trace_shared_across_all_l2e_neurons():
    """x_bar is ONE presynaptic-side array, not per-(neuron,pixel) -- every
    L2E neuron's _update_weights closure must reference the SAME holder
    object, confirmed by mutating it once and observing both react."""
    engine = build_engine('centered', 1, 1)
    holder = XBarHolder(N_PIX)
    _patch_centered_condition(engine, holder)
    holder.x_bar[:] = 0.42
    n0, n1 = engine.l2.excitatory_neurons[0], engine.l2.excitatory_neurons[1]
    n0._last_input_spikes = np.full(N_PIX, 0.42)
    n1._last_input_spikes = np.full(N_PIX, 0.42)
    w0, w1 = n0._weights_array.copy(), n1._weights_array.copy()
    n0._update_weights(0.0)
    n1._update_weights(0.0)
    assert np.allclose(n0._weights_array, w0)   # s == 0 everywhere -> no change
    assert np.allclose(n1._weights_array, w1)


def test_repeated_identical_seeds_are_deterministic():
    r1 = run_one('centered', 'interleaved', 5)
    r2 = run_one('centered', 'interleaved', 5)
    assert _all_ff_weights(r1[0]) == _all_ff_weights(r2[0])
    assert r1[2] == r2[2]


def test_preregistered_alpha_matches_documented_value():
    assert ALPHA == 1.0 / 80.0
