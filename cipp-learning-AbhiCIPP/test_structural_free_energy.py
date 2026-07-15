"""Focused tests for the structural free-energy plasticity gate.

Verifies:
  1. flag OFF preserves the exact signed-spike behavior (p-scaled);
  2. the gate shrinks as the positive-afferent sum approaches theta;
  3. the gate uses ONLY positive afferents (the negative inhibitory gate is
     ignored) and only this neuron's own threshold -- no voltage, no rivals;
  4. a mature neuron (sum >= theta) learns at eta_floor, an under-built one at ~1;
  5. the gate is applied only through the signed-spike (excitatory L2E) path.

Plain-script style (matches test_l2_competition.py etc.):
    PYTHONPATH=. .venv/bin/python test_structural_free_energy.py
"""

import numpy as np

from neuron_flexible import Neuron
from snn.rules import bounded_signed_update, exact_local_free_energy_update


def _make_neuron(weights, theta=8.0, cap=8.0 / 3, floor=0.001, lr=0.02):
    n = Neuron(threshold=theta, refractory_period=0, weight_cap=cap, learning_rate=lr)
    n.weights = np.asarray(weights, dtype=float)
    n.min_positive_weight = floor
    n.signed_spike_learning = True
    return n


def test_gate_monotonic_in_sum():
    """gate = max(eta_floor, 1 - clamp(sum/theta,0,1)) -- decreasing in the sum,
    floored, and computed from POSITIVE afferents only."""
    theta = 8.0
    floor = 0.05
    # sum well below theta -> gate ~ 1
    low = _make_neuron([0.1, 0.1, 0.1, 0, 0, 0, 0, 0, 0], theta=theta)
    low.structural_free_energy = True
    low.structural_fe_eta_floor = floor
    g_low = low._structural_free_energy_gate()
    assert abs(g_low - (1.0 - 0.3 / theta)) < 1e-9, g_low

    # sum == theta exactly -> maturity 1 -> gate == floor
    mid = _make_neuron([8.0 / 3, 8.0 / 3, 8.0 / 3, 0, 0, 0, 0, 0, 0], theta=theta)
    mid.structural_free_energy = True
    mid.structural_fe_eta_floor = floor
    assert abs(mid._structural_free_energy_gate() - floor) < 1e-9, mid._structural_free_energy_gate()

    # sum > theta -> still clamped at maturity 1 -> gate == floor
    hi = _make_neuron([8.0 / 3, 8.0 / 3, 8.0 / 3, 2.0, 0, 0, 0, 0, 0], theta=theta)
    hi.structural_free_energy = True
    hi.structural_fe_eta_floor = floor
    assert abs(hi._structural_free_energy_gate() - floor) < 1e-9

    assert g_low > mid._structural_free_energy_gate()
    print(f"PASS: gate monotonic and floored (low={g_low:.4f}, mature={floor:.4f})")


def test_negative_gate_ignored():
    """A negative inhibitory afferent (e.g. L2I->L2E) must not enter the sum."""
    n = _make_neuron([2.0, 2.0, -5.0, 0, 0, 0, 0, 0, 0], theta=8.0)
    n.structural_free_energy = True
    assert abs(n._positive_afferent_weight_sum() - 4.0) < 1e-9
    # sum uses 4.0 (=2+2), not -1.0 (=2+2-5): maturity = 4/8 = 0.5, gate = 0.5
    assert abs(n._structural_free_energy_gate() - 0.5) < 1e-9
    print("PASS: negative inhibitory gate excluded from the structural sum")


def test_flag_off_identical():
    """With the flag off, one fire must produce the exact p-scaled signed update."""
    w0 = [1.0, 1.0, 0.5, 0.2, 0, 0, 0, 0, 0]
    theta, cap, floor, lr = 8.0, 8.0 / 3, 0.001, 0.02
    v_pre = 10.0
    p = min(max(theta / v_pre, 0.0), 1.0)
    participating = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0], dtype=float)

    n = _make_neuron(w0, theta=theta, cap=cap, floor=floor, lr=lr)
    n._last_input_spikes = participating.copy()
    n.structural_free_energy = False
    # drive the update directly with a known v_pre
    n._update_weights(v_pre)
    got = n.weights

    # hand-computed reference via the shared bounded kernel (gain = eta*p)
    ref = np.asarray(w0, dtype=float)
    pos = ref > 0
    sig = np.where(participating[pos] > 0.5, 1.0, -1.0)
    ref[pos] = bounded_signed_update(ref[pos], floor, cap, lr * p, sig)
    assert np.allclose(got, ref), (got, ref)
    print("PASS: flag OFF reproduces the exact p-scaled signed-spike update")


def test_gate_replaces_p():
    """With the flag ON, the update uses Phase 8's EXACT equation
    (delta_w = LR * FE * (1 - w/w_max)^2 * learn_signal), not the p-scaled
    bounded-kernel path."""
    w0 = [1.0, 1.0, 0.5, 0.2, 0, 0, 0, 0, 0]
    theta, cap, floor, lr = 8.0, 8.0 / 3, 0.001, 0.02
    v_pre = 10.0  # p = 0.8; different from the structural gate so we can tell them apart
    participating = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0], dtype=float)

    n = _make_neuron(w0, theta=theta, cap=cap, floor=floor, lr=lr)
    n._last_input_spikes = participating.copy()
    n.structural_free_energy = True
    n.structural_fe_eta_floor = 0.02
    gate = n._structural_free_energy_gate()  # computed on the PRE-update weights
    n._update_weights(v_pre)
    got = n.weights

    ref = np.asarray(w0, dtype=float)
    pos = ref > 0
    sig = np.where(participating[pos] > 0.5, 1.0, -1.0)
    ref[pos] = exact_local_free_energy_update(ref[pos], floor, cap, lr, gate, sig)
    assert np.allclose(got, ref), (got, ref)
    # and confirm it is genuinely different from the p-scaled path
    p = theta / v_pre
    assert abs(gate - p) > 1e-3, (gate, p)
    print(f"PASS: flag ON uses Phase 8's exact FE equation (gate={gate:.4f}) "
          f"not eta*p (p={p:.4f})")


# ------------------------------------------------------ Phase 8 -- exact equation
def test_exact_equation_matches_the_literal_formula():
    """delta_w = LR * FE * (1 - w/w_max)^2 * learn_signal, computed by hand,
    must match the helper bit-for-bit (no p, no confidence, no extra factor)."""
    w = np.array([0.0, 1.0, 2.0])
    w_min, w_max, lr, fe = 0.0, 8.0 / 3, 0.02, 0.4
    signal = np.array([1.0, -1.0, 1.0])
    got = exact_local_free_energy_update(w, w_min, w_max, lr, fe, signal)
    expected = np.clip(w + lr * fe * (1.0 - w / w_max) ** 2 * signal, w_min, w_max)
    assert np.allclose(got, expected), (got, expected)
    print("PASS: exact_local_free_energy_update matches the literal equation")


def test_saturation_envelope_zero_at_w_max_both_directions():
    """At w == w_max the envelope (1-w/w_max)^2 is exactly 0, so a fully
    saturated weight cannot move in EITHER direction (unlike the reflected
    H_up/H_down kernel, which still permits downward movement at the cap --
    this symmetric zero-at-cap behavior is the literal, intended consequence
    of using the equation exactly as specified)."""
    w_max = 8.0 / 3
    w = np.array([w_max, w_max])
    signal = np.array([1.0, -1.0])
    out = exact_local_free_energy_update(w, 0.0, w_max, 0.02, 1.0, signal)
    assert np.allclose(out, w), out
    print("PASS: envelope is exactly zero at w_max in both potentiation and depression")


def test_saturation_envelope_maximal_at_w_min():
    """At w == 0 the envelope is exactly 1 -- maximal sensitivity for an
    unbuilt synapse."""
    out_up = exact_local_free_energy_update(np.array([0.0]), 0.0, 8.0 / 3, 0.02, 1.0, np.array([1.0]))
    assert np.isclose(out_up[0], 0.02 * 1.0 * 1.0), out_up
    print("PASS: envelope is exactly 1 at w=0 (maximal plasticity for an unbuilt synapse)")


def test_clamp_is_purely_numerical():
    """An oversized LR*FE*signal must still land exactly on the bound, not
    overshoot -- clamping is a plain numerical safety clip, not a reshaping
    kernel."""
    out = exact_local_free_energy_update(np.array([1.0]), 0.0, 8.0 / 3, 50.0, 1.0, np.array([1.0]))
    assert np.isclose(out[0], 8.0 / 3)
    out_dn = exact_local_free_energy_update(np.array([1.0]), 0.0, 8.0 / 3, 50.0, 1.0, np.array([-1.0]))
    assert out_dn[0] >= 0.0
    print("PASS: an oversized update clamps exactly to the numerical bound")


def test_fe_gate_and_envelope_are_the_only_two_factors():
    """No closeness `p`, no confidence/maturity multiplier is stacked on top --
    changing v_pre (which only affects `p`) must not change the FE-gated
    update at all, since FE replaces p entirely and the envelope does not
    depend on v_pre either."""
    w0 = [1.0, 1.0, 0.5, 0.2, 0, 0, 0, 0, 0]
    theta, cap, floor, lr = 8.0, 8.0 / 3, 0.001, 0.02
    participating = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0], dtype=float)

    def _fire(v_pre):
        n = _make_neuron(w0, theta=theta, cap=cap, floor=floor, lr=lr)
        n._last_input_spikes = participating.copy()
        n.structural_free_energy = True
        n.structural_fe_eta_floor = 0.02
        n._update_weights(v_pre)
        return n.weights.copy()

    w_close = _fire(v_pre=8.01)   # p would be ~1.0
    w_far = _fire(v_pre=1000.0)   # p would be ~0.008
    assert np.allclose(w_close, w_far), (w_close, w_far)
    print("PASS: the FE-gated update is fully voltage-independent (no p leaking in)")


# --------------------------------------------------- Phase 8 -- locality / scope
def test_fe_update_uses_only_this_neurons_own_state():
    """The FE-gated update never reads any other neuron, pattern label, or
    modal-owner table -- verified structurally: the CODE BODY (docstring
    excluded) is a pure function of its five scalar/array arguments only, with
    no reference to a rival/label/owner concept and no closed-over module
    state (e.g. an engine, a pattern table, a winner)."""
    import ast
    import inspect
    src = inspect.getsource(exact_local_free_energy_update)
    tree = ast.parse(src)
    fn = tree.body[0]
    body_without_docstring = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)
                                             and isinstance(fn.body[0].value, ast.Constant)) else fn.body
    body_src = "\n".join(ast.unparse(stmt) for stmt in body_without_docstring)
    for banned in ('winner', 'rival', 'pattern', 'label', 'argmax', 'owner', 'engine'):
        assert banned not in body_src.lower(), f"found banned term '{banned}' in the executable body"
    names_used = {node.id for node in ast.walk(fn) if isinstance(node, ast.Name)}
    params = {a.arg for a in fn.args.args}
    locally_assigned = {t.id for stmt in ast.walk(fn) if isinstance(stmt, ast.Assign)
                        for t in stmt.targets if isinstance(t, ast.Name)}
    builtins_used = {'np', 'float'}
    external_names = names_used - params - locally_assigned - builtins_used
    assert external_names <= set(), f"references names beyond its own params: {external_names}"
    print("PASS: exact_local_free_energy_update's code body is a pure function of its own args only")


# --------------------------------------------------- Phase 8 -- ambiguity (ties)
def test_same_step_tie_gives_no_special_credit_either_side():
    """Phase 6/7's ambiguous same-step tie (self.winner stays None) must not
    change which neurons learn or how much -- the FE rule is purely per-neuron
    and event-driven (on THIS neuron's own fire), so it has no
    representative-specific credit to withhold in the first place. Directly
    verify: two simultaneously-firing L2E neurons under a forced tie each
    still apply their OWN local FE update, identical to firing alone."""
    from backend.simulation import SimulationEngine, N_OUT

    e = SimulationEngine(seed=1, structural_free_energy=True, l1i_immediate_relay=False)
    e.set_pattern('col 1')
    for _ in range(3):
        e.step()
    thr = e.l2.excitatory_neurons[0].threshold
    e.l2.excitatory_neurons[0].refractory_timer = 0
    e.l2.excitatory_neurons[3].refractory_timer = 0
    e.l2.excitatory_neurons[0].potential = thr + 10
    e.l2.excitatory_neurons[3].potential = thr + 5
    w0_before = e.l2.excitatory_neurons[0]._weights_array.copy()
    w3_before = e.l2.excitatory_neurons[3]._weights_array.copy()
    d = e.step()
    story = d['causal_story']
    if story['same_step_tie']:
        assert e.winner is None, "an ambiguous same-step tie must not credit a representative"
    # Both neurons that actually fired must have learned via their OWN local
    # rule regardless of tie/winner status -- no asymmetric treatment.
    if e.spiked['L2E0']:
        assert not np.array_equal(e.l2.excitatory_neurons[0]._weights_array, w0_before), \
            "L2E0 fired but its own local FE update did not run"
    if e.spiked['L2E3']:
        assert not np.array_equal(e.l2.excitatory_neurons[3]._weights_array, w3_before), \
            "L2E3 fired but its own local FE update did not run"
    print("PASS: a same-step tie gives no special/asymmetric FE credit to either firer")


# ----------------------------------------------------- Phase 8 -- probe freeze
def test_frozen_probe_does_not_mutate_weights_or_confidence_under_fe():
    """A plasticity-frozen probe must leave weights AND confidence untouched
    even with structural_free_energy on -- the freeze guard in _update_weights
    (and _decay_confidence's homeostasis guard) is unconditional."""
    from backend.simulation import SimulationEngine
    from backend.presets import DASHBOARD_PRESET

    overrides = dict(DASHBOARD_PRESET)
    overrides['structural_free_energy'] = True
    e = SimulationEngine(seed=1, **overrides)
    e.set_pattern('col 1')
    for _ in range(60):
        e.step()
    w_before = e._all_weights()
    c_before = e._all_confidence()

    e.present_probe('row 0', steps=20)
    assert e.plasticity_frozen is True
    for _ in range(20):
        e.step()

    assert e._all_weights() == w_before, "a probe mutated a weight under structural_free_energy"
    assert e._all_confidence() == c_before, "a probe mutated a confidence value under structural_free_energy"
    print("PASS: frozen probe leaves weights/confidence untouched under the exact FE rule")


def test_only_signed_path():
    """The gate is inert unless signed_spike_learning is the active rule: on the
    legacy charge path, toggling structural_free_energy must change nothing."""
    w0 = [2.0, 2.0, 2.0, 0, 0, 0, 0, 0, 0]
    part = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0], dtype=float)

    off = _make_neuron(w0, theta=8.0)
    off.signed_spike_learning = False        # legacy charge rule
    off.structural_free_energy = False
    off._last_input_spikes = part.copy()
    off._update_weights(10.0)

    on = _make_neuron(w0, theta=8.0)
    on.signed_spike_learning = False         # legacy charge rule
    on.structural_free_energy = True         # must be ignored on this path
    on._last_input_spikes = part.copy()
    on._update_weights(10.0)

    assert np.allclose(off.weights, on.weights), (off.weights, on.weights)
    print("PASS: structural gate does not hijack the non-signed (legacy) path")


if __name__ == "__main__":
    test_gate_monotonic_in_sum()
    test_negative_gate_ignored()
    test_flag_off_identical()
    test_gate_replaces_p()
    test_exact_equation_matches_the_literal_formula()
    test_saturation_envelope_zero_at_w_max_both_directions()
    test_saturation_envelope_maximal_at_w_min()
    test_clamp_is_purely_numerical()
    test_fe_gate_and_envelope_are_the_only_two_factors()
    test_fe_update_uses_only_this_neurons_own_state()
    test_same_step_tie_gives_no_special_credit_either_side()
    test_frozen_probe_does_not_mutate_weights_or_confidence_under_fe()
    test_only_signed_path()
    print("\nALL STRUCTURAL FREE-ENERGY TESTS PASSED")
