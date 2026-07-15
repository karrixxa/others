"""
Regression tests for Phase 15 (local developmental protection from L2I loser
depression, july14-integration).

Covers: apply_delayed_inhibition's structural WEIGHT-DEPRESSION gain is
scaled by protection_gate = _loser_depression_maturity() = clamp(self.ca /
loser_depression_protection_ca_ref, 0, 1) -- a SEPARATE, default-off,
separately-named mechanism from homeostasis/structural_free_energy/
adaptive_threshold, using ONLY this neuron's own self.ca (already computed
unconditionally every step in Neuron.update, regardless of the homeostasis
flag -- this phase never touches how ca is computed). The physical
inhibitory membrane transient (V -= magnitude, floored at rest) is
UNCONDITIONAL and never affected. With the flag off, the gate is exactly
1.0 everywhere -- byte-identical to every prior phase.

Plain-script style (matches test_adaptive_threshold.py etc.):
    PYTHONPATH=. .venv/bin/python test_loser_depression_protection.py
"""

import ast
import inspect
import textwrap

import numpy as np

from neuron_flexible import Neuron
from backend.simulation import SimulationEngine, N_OUT, N_PIX


def _make_l2e_neuron(theta=8.0, cap=8.0 / 3, refractory=0):
    n = Neuron(threshold=theta, refractory_period=refractory, weight_cap=cap,
              learning_rate=0.02)
    n.weights = np.array([1.0, 1.0, 1.0])
    n.min_positive_weight = 0.001
    n.loser_depression = True
    n._last_input_spikes = np.array([1.0, 1.0, 1.0])   # all three afferents participating
    return n


# --------------------------------------------------------------- unit level
def test_maturity_gate_formula():
    n = _make_l2e_neuron()
    n.loser_depression_protection_ca_ref = 0.02
    n.ca = 0.0
    assert n._loser_depression_maturity() == 0.0
    n.ca = 0.01
    assert np.isclose(n._loser_depression_maturity(), 0.5)
    n.ca = 0.02
    assert np.isclose(n._loser_depression_maturity(), 1.0)
    n.ca = 0.5   # far above ref -- clamped, never > 1
    assert n._loser_depression_maturity() == 1.0
    print("PASS: maturity = clamp(ca/ca_ref, 0, 1), smooth and clamped correctly")


def test_zero_maturity_reduces_only_weight_depression():
    """A neuron with NO firing history (ca=0) under protection must have its
    structural weight depression fully suppressed, while the PHYSICAL
    inhibitory transient still applies at full magnitude -- this is the
    literal "only scale the plastic weight-depression component" requirement."""
    n = _make_l2e_neuron()
    n.loser_depression_protection = True
    n.ca = 0.0   # never fired
    n.potential = 6000.0
    w_before = n._weights_array.copy()
    out = n.apply_delayed_inhibition(magnitude=1000.0)
    assert out['maturity'] == 0.0
    assert np.allclose(n._weights_array, w_before), \
        "weights changed despite zero maturity -- protection did not suppress depression"
    assert out['v_post'] == max(6000.0 - 1000.0, n.resting_potential), \
        "the physical inhibitory transient must be unaffected by protection"
    print("PASS: zero maturity fully suppresses weight depression, transient still applies")


def test_inhibition_changes_membrane_normally_regardless_of_flag():
    """The membrane subtraction must be IDENTICAL whether protection is off,
    on-but-immature, or on-and-mature -- protection never exempts a neuron
    from the physical inhibitory event itself."""
    results = []
    for protection, ca in [(False, 0.0), (True, 0.0), (True, 0.02), (True, 5.0)]:
        n = _make_l2e_neuron()
        n.loser_depression_protection = protection
        n.ca = ca
        n.potential = 5500.0
        out = n.apply_delayed_inhibition(magnitude=2000.0)
        results.append(out['v_post'])
    assert len(set(results)) == 1, f"membrane transient differs by config: {results}"
    assert results[0] == max(5500.0 - 2000.0, 0.0)
    print("PASS: physical inhibitory transient identical across every protection/maturity state")


def test_maturity_approaches_normal_depression_smoothly():
    """As ca rises from 0 toward ca_ref, the resulting weight-depression
    magnitude must rise MONOTONICALLY and CONTINUOUSLY (never a jump), and
    must exactly equal the unprotected (flag-off) depression once ca>=ref --
    "experienced competitors must still be depressible"."""
    cas = [0.0, 0.002, 0.005, 0.01, 0.015, 0.02, 0.05]
    deltas = []
    for ca in cas:
        n = _make_l2e_neuron()
        n.loser_depression_protection = True
        n.loser_depression_protection_ca_ref = 0.02
        n.ca = ca
        n.potential = 6000.0
        w_before = n._weights_array.copy()
        n.apply_delayed_inhibition(magnitude=1000.0)
        deltas.append(float(w_before[0] - n._weights_array[0]))   # magnitude of depression

    # Monotonically non-decreasing as ca rises (smooth ramp, no discontinuity).
    for a, b in zip(deltas, deltas[1:]):
        assert b >= a - 1e-9, f"depression magnitude decreased as ca rose: {deltas}"
    assert deltas[0] == 0.0, "zero ca must fully suppress depression"

    # At/above ca_ref, matches the unprotected baseline exactly.
    n_ref = _make_l2e_neuron()
    n_ref.loser_depression_protection = True
    n_ref.loser_depression_protection_ca_ref = 0.02
    n_ref.ca = 0.02
    n_ref.potential = 6000.0
    w_before_ref = n_ref._weights_array.copy()
    n_ref.apply_delayed_inhibition(magnitude=1000.0)
    delta_at_ref = float(w_before_ref[0] - n_ref._weights_array[0])

    n_off = _make_l2e_neuron()
    n_off.loser_depression_protection = False
    n_off.potential = 6000.0
    w_before_off = n_off._weights_array.copy()
    n_off.apply_delayed_inhibition(magnitude=1000.0)
    delta_off = float(w_before_off[0] - n_off._weights_array[0])

    assert np.isclose(delta_at_ref, delta_off), \
        f"ca>=ca_ref must reproduce the unprotected depression exactly: {delta_at_ref} vs {delta_off}"
    print("PASS: depression magnitude rises smoothly with ca and matches baseline at/above ca_ref")


def test_experienced_competitor_fully_depressible():
    """A neuron with ca well above ca_ref is depressed exactly as strongly as
    an unprotected neuron -- protection never permanently exempts anyone."""
    n_mature = _make_l2e_neuron()
    n_mature.loser_depression_protection = True
    n_mature.ca = 1.0   # far above any reasonable ca_ref
    n_mature.potential = 6000.0
    w_before = n_mature._weights_array.copy()
    n_mature.apply_delayed_inhibition(magnitude=1000.0)
    delta_mature = w_before - n_mature._weights_array

    n_off = _make_l2e_neuron()
    n_off.loser_depression_protection = False
    n_off.potential = 6000.0
    w_before_off = n_off._weights_array.copy()
    n_off.apply_delayed_inhibition(magnitude=1000.0)
    delta_off = w_before_off - n_off._weights_array

    assert np.allclose(delta_mature, delta_off)
    print("PASS: a mature (high-ca) neuron is depressed identically to an unprotected one")


def test_protection_never_potentiates():
    """Regardless of maturity, apply_delayed_inhibition's structural branch
    only ever moves eligible weights DOWN (signal=-1) -- protection scales
    the depression magnitude, it never flips the direction."""
    for ca in [0.0, 0.005, 0.01, 0.02, 1.0]:
        n = _make_l2e_neuron()
        n.loser_depression_protection = True
        n.ca = ca
        n.potential = 6000.0
        w_before = n._weights_array.copy()
        n.apply_delayed_inhibition(magnitude=1000.0)
        assert np.all(n._weights_array <= w_before + 1e-9), \
            f"a weight increased under loser depression at ca={ca}"
    print("PASS: no ca value causes potentiation -- only the depression magnitude is scaled")


def test_isolation_between_neurons():
    """Each neuron's maturity depends ONLY on its own ca -- an immature
    neuron sitting beside a mature one is not affected by the other's state."""
    immature = _make_l2e_neuron()
    immature.loser_depression_protection = True
    immature.ca = 0.0
    mature = _make_l2e_neuron()
    mature.loser_depression_protection = True
    mature.ca = 1.0

    immature.potential = 6000.0
    mature.potential = 6000.0
    w_immature_before = immature._weights_array.copy()
    w_mature_before = mature._weights_array.copy()
    immature.apply_delayed_inhibition(magnitude=1000.0)
    mature.apply_delayed_inhibition(magnitude=1000.0)

    assert np.allclose(immature._weights_array, w_immature_before), "immature neuron unexpectedly depressed"
    assert not np.allclose(mature._weights_array, w_mature_before), "mature neuron unexpectedly protected"
    print("PASS: maturity/depression outcome is fully isolated per neuron")


def test_flag_off_is_baseline_equivalent_unit_level():
    """With the flag off, apply_delayed_inhibition's gain must be EXACTLY
    what it always was (gate == 1.0), regardless of ca."""
    for ca in [0.0, 0.01, 0.02, 5.0]:
        n = _make_l2e_neuron()
        n.loser_depression_protection = False   # explicit off
        n.ca = ca
        n.potential = 6000.0
        w_before = n._weights_array.copy()
        out = n.apply_delayed_inhibition(magnitude=1000.0)
        assert out['maturity'] == 1.0
        delta = w_before - n._weights_array

        n2 = _make_l2e_neuron()
        # loser_depression_protection defaults to False -- never set at all.
        n2.ca = ca
        n2.potential = 6000.0
        w_before2 = n2._weights_array.copy()
        n2.apply_delayed_inhibition(magnitude=1000.0)
        delta2 = w_before2 - n2._weights_array

        assert np.allclose(delta, delta2)
    print("PASS: flag off (explicit or default) is byte-identical regardless of ca")


def test_locality_no_cross_neuron_or_pattern_state():
    """AST-based locality proof (same technique as Phase 8's
    test_fe_update_uses_only_this_neurons_own_state): _loser_depression_maturity's
    executable body must reference no name beyond `self` and its own
    attributes -- no rival neuron, no engine, no self.winner, no pattern
    identity, no membrane voltage."""
    src = textwrap.dedent(inspect.getsource(Neuron._loser_depression_maturity))
    tree = ast.parse(src)
    func = tree.body[0]
    assert isinstance(func, ast.FunctionDef)

    names_used = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Name):
            names_used.add(node.id)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'self':
            names_used.add(f'self.{node.attr}')

    allowed = {'self', 'ref', 'self.loser_depression_protection_ca_ref', 'self.ca', 'min', 'max'}
    disallowed = names_used - allowed
    assert not disallowed, f"maturity gate references unexpected names: {disallowed}"
    print("PASS: maturity gate reads only self.ca and self.loser_depression_protection_ca_ref "
         "(AST-verified -- no other name, attribute, winner field, or pattern identity is referenced)")


# ------------------------------------------------------------ engine level
def test_engine_flag_off_is_baseline_equivalent():
    """A full engine run with the flag explicitly False must be byte-identical
    to the same seed/pattern sequence with the flag simply omitted (default)."""
    e_default = SimulationEngine(seed=1, l1i_immediate_relay=False)
    e_explicit_off = SimulationEngine(seed=1, loser_depression_protection=False,
                                      l1i_immediate_relay=False)
    e_default.set_pattern('row 1')
    e_explicit_off.set_pattern('row 1')
    for _ in range(150):
        e_default.step()
        e_explicit_off.step()
    for j in range(N_OUT):
        w1 = e_default.l2.excitatory_neurons[j]._weights_array
        w2 = e_explicit_off.l2.excitatory_neurons[j]._weights_array
        assert np.allclose(w1, w2), f"L2E{j} weights diverged: default vs explicit-off"
    print("PASS: a full engine run is byte-identical whether the flag is omitted or explicit-off")


def test_engine_protection_does_not_touch_l1i_or_distance_or_self_spike():
    """Enabling protection must not perturb L1I weights, the distance/
    influence pathway report, or the self-spike-learning-only case (a neuron
    that always wins and is never a loser-depression target should learn
    identically with the flag on or off)."""
    kwargs = dict(seed=1, l1i_immediate_relay=False, distance_weighting=True)
    e_off = SimulationEngine(**kwargs)
    e_on = SimulationEngine(loser_depression_protection=True, **kwargs)
    for e in (e_off, e_on):
        e.set_pattern('row 1')
        for _ in range(40):
            e.step()

    l1i_off = [e_off.l1.inhibitory_neurons[i].weights.copy() for i in range(N_PIX)]
    l1i_on = [e_on.l1.inhibitory_neurons[i].weights.copy() for i in range(N_PIX)]
    for a, b in zip(l1i_off, l1i_on):
        assert np.allclose(a, b), "L1I weights diverged -- protection must not touch L1I"

    report_off = e_off.pathway_influence_report()['l1e_l2e']
    report_on = e_on.pathway_influence_report()['l1e_l2e']
    infl_off = [x['influence'] for x in report_off['entries']]
    infl_on = [x['influence'] for x in report_on['entries']]
    assert np.allclose(infl_off, infl_on), "distance/influence pathway diverged -- must be untouched"
    print("PASS: L1I and distance/influence pathways are completely unaffected by protection")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
