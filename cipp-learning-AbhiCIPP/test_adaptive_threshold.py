"""
Regression tests for Phase 10 (adaptive-threshold ablation,
july14-integration; see the corrected Phases 6-12 prompt file).

Covers: for each L2E neuron, effective_threshold = threshold + a_i; on that
neuron's OWN physical spike a_i += delta_threshold; every step a_i decays
exponentially toward zero with time constant tau_threshold (independent of
refractory state). A SEPARATE, default-off, separately-named mechanism from
homeostasis (self.homeostasis) and geometry -- not a rename/reuse of either.
With the flag off, check_threshold delegates straight to the Membrane's own
decision (baseline-equivalent). State/trajectory are exposed via
dynamic_state()['adaptive_threshold'] and per-neuron
threshold_adapt/effective_threshold. A probe may evolve a_i internally but
its pre-probe value is snapshotted and unconditionally restored so evaluation
cannot alter subsequent training. Isolation between neurons and deterministic
replay are both verified directly.

Plain-script style (matches test_l2_competition.py etc.):
    PYTHONPATH=. .venv/bin/python test_adaptive_threshold.py
"""

import numpy as np

from neuron_flexible import Neuron
from backend.simulation import SimulationEngine, N_OUT


def _make_l2e_neuron(theta=8.0, cap=8.0 / 3, refractory=0):
    n = Neuron(threshold=theta, refractory_period=refractory, weight_cap=cap,
              learning_rate=0.02)
    n.weights = np.array([1.0, 1.0, 1.0])
    n.min_positive_weight = 0.001
    return n


# --------------------------------------------------------------- unit level
def test_spike_local_increment():
    n = _make_l2e_neuron()
    n.adaptive_threshold = True
    n.delta_threshold = 0.5
    assert n.threshold_adapt == 0.0
    n.potential = n.threshold + 1.0
    n.fire()
    assert np.isclose(n.threshold_adapt, 0.5)
    n.potential = n.threshold + 1.0
    n.fire()
    assert np.isclose(n.threshold_adapt, 1.0)
    print("PASS: a_i increments by delta_threshold on each of this neuron's own spikes")


def test_decay_toward_zero():
    n = _make_l2e_neuron()
    n.adaptive_threshold = True
    n.tau_threshold = 5.0
    n.threshold_adapt = 10.0
    n.update()
    expected = 10.0 * np.exp(-1.0 / 5.0)
    assert np.isclose(n.threshold_adapt, expected), (n.threshold_adapt, expected)
    for _ in range(200):
        n.update()
    assert n.threshold_adapt < 1e-6, "a_i did not decay toward zero"
    print("PASS: a_i decays exponentially toward zero with tau_threshold")


def test_decay_continues_during_refractory():
    """a_i is independent of the membrane's own refractory state -- it must
    keep decaying every step, refractory or not."""
    n = _make_l2e_neuron(refractory=5)
    n.adaptive_threshold = True
    n.tau_threshold = 5.0
    n.threshold_adapt = 10.0
    n.refractory_timer = 5
    n.update()
    assert n.threshold_adapt < 10.0, "a_i did not decay during a refractory step"
    print("PASS: a_i decays even while the neuron itself is refractory")


def test_effective_threshold_equation():
    n = _make_l2e_neuron(theta=8.0)
    n.adaptive_threshold = True
    n.threshold_adapt = 2.5
    assert np.isclose(n.effective_threshold, 10.5)
    n.adaptive_threshold = False
    assert np.isclose(n.effective_threshold, 8.0), "off must ignore a_i entirely"
    print("PASS: effective_threshold = threshold + a_i (exactly threshold when off)")


def test_check_threshold_uses_effective_threshold_when_on():
    n = _make_l2e_neuron(theta=8.0, refractory=0)
    n.adaptive_threshold = True
    n.threshold_adapt = 4.0   # effective threshold now 12.0
    n.potential = 10.0
    assert not n.check_threshold(), "must not fire below the ELEVATED threshold"
    n.potential = 12.0
    assert n.check_threshold(), "must fire at/above the elevated threshold"
    print("PASS: check_threshold compares against the elevated effective threshold")


def test_toggle_off_is_baseline_equivalent():
    """With the flag off, check_threshold must delegate to the Membrane's own
    decision -- even if a_i somehow holds a nonzero value (e.g. toggled off
    mid-run), it must be completely ignored."""
    n = _make_l2e_neuron(theta=8.0, refractory=0)
    n.adaptive_threshold = False
    n.threshold_adapt = 500.0   # would fail every check_threshold if consulted
    n.potential = 8.0
    assert n.check_threshold(), "flag off must ignore a stray nonzero a_i entirely"
    print("PASS: flag off reproduces baseline exactly, ignoring any stray a_i")


def test_isolation_between_neurons():
    n1 = _make_l2e_neuron()
    n2 = _make_l2e_neuron()
    for n in (n1, n2):
        n.adaptive_threshold = True
        n.delta_threshold = 1.0
    n1.potential = n1.threshold + 1.0
    n1.fire()
    assert n1.threshold_adapt == 1.0
    assert n2.threshold_adapt == 0.0, "firing one neuron must not affect another's a_i"
    print("PASS: a_i is fully isolated per neuron (no cross-neuron coupling)")


def test_separate_from_homeostasis_flag():
    """adaptive_threshold and homeostasis are independent flags -- toggling
    one must not silently enable or rename the other."""
    n = _make_l2e_neuron()
    assert n.adaptive_threshold is False
    assert n.homeostasis is False
    n.homeostasis = True
    assert n.adaptive_threshold is False, "homeostasis must not imply adaptive_threshold"
    n2 = _make_l2e_neuron()
    n2.adaptive_threshold = True
    assert n2.homeostasis is False, "adaptive_threshold must not imply homeostasis"
    print("PASS: adaptive_threshold and homeostasis are fully independent flags")


# ----------------------------------------------------------- engine level
def test_engine_default_is_off_and_baseline_equivalent():
    e = SimulationEngine(seed=1)
    assert e.params['adaptive_threshold'] is False
    for n in e.l2.excitatory_neurons:
        assert n.adaptive_threshold is False

    e_on_off = SimulationEngine(seed=1, adaptive_threshold=False)
    e_default = SimulationEngine(seed=1)
    e_on_off.set_pattern('col 1')
    e_default.set_pattern('col 1')
    for _ in range(60):
        d1 = e_on_off.step()
        d2 = e_default.step()
        assert d1['winner'] == d2['winner']
    assert e_on_off._all_weights() == e_default._all_weights()
    print("PASS: explicit adaptive_threshold=False is byte-identical to the default")


def test_engine_config_scales_delta_by_threshold_l2():
    e = SimulationEngine(seed=1, adaptive_threshold=True, delta_threshold_frac=0.1)
    thr_l2 = e.params['threshold_l2']
    for n in e.l2.excitatory_neurons:
        assert np.isclose(n.delta_threshold, 0.1 * thr_l2)
        assert n.adaptive_threshold is True
    print("PASS: delta_threshold_frac scales with threshold_l2 (scale-invariant config)")


def test_non_l2e_populations_never_get_adaptive_threshold():
    e = SimulationEngine(seed=1, adaptive_threshold=True)
    for nid, n in e.neurons.items():
        if not nid.startswith('L2E'):
            assert n.adaptive_threshold is False, f"{nid} unexpectedly has adaptive_threshold on"
    print("PASS: adaptive_threshold is scoped to L2E only")


def test_state_and_trajectory_exposed():
    e = SimulationEngine(seed=1, adaptive_threshold=True, delta_threshold_frac=0.15,
                         tau_threshold=8.0, l1i_immediate_relay=False)
    e.set_pattern('row 1')
    d = None
    for _ in range(200):
        d = e.step()
    at = d['adaptive_threshold']
    assert at['enabled'] is True
    assert set(at['state'].keys()) == {f'L2E{j}' for j in range(N_OUT)}
    assert set(at['effective_threshold'].keys()) == {f'L2E{j}' for j in range(N_OUT)}
    assert any(v > 0.0 for v in at['state'].values()), "no L2E ever accumulated a_i in 200 steps"
    for j in range(N_OUT):
        nid = f'L2E{j}'
        neuron_entry = next(n for n in d['neurons'] if n['id'] == nid)
        assert np.isclose(neuron_entry['effective_threshold'], neuron_entry['threshold_adapt']
                          + e.params['threshold_l2'], atol=1e-2)
    assert any(len(h) > 0 for h in at['history'].values()), "no trajectory recorded"
    print("PASS: per-neuron and top-level state/trajectory are exposed")


def test_deterministic_replay():
    """Same seed, same steps -> identical a_i trajectories (no hidden RNG)."""
    def _run():
        e = SimulationEngine(seed=2, adaptive_threshold=True, delta_threshold_frac=0.1,
                             tau_threshold=15.0, l1i_immediate_relay=False)
        e.set_pattern('diag \\')
        traj = []
        for _ in range(150):
            d = e.step()
            traj.append(tuple(d['adaptive_threshold']['state'].values()))
        return traj

    t1 = _run()
    t2 = _run()
    assert t1 == t2, "adaptive-threshold trajectory is not deterministic across identical replays"
    print("PASS: deterministic replay produces an identical a_i trajectory")


# ---------------------------------------------------------------- probe
def test_probe_restores_pre_probe_threshold_adapt():
    e = SimulationEngine(seed=1, adaptive_threshold=True, delta_threshold_frac=0.2,
                         tau_threshold=30.0, l1i_immediate_relay=False)
    e.set_pattern('col 1')
    for _ in range(150):
        e.step()
    pre_probe_state = {j: float(n.threshold_adapt) for j, n in enumerate(e.l2.excitatory_neurons)}

    e.present_probe('row 0', steps=40)
    assert e.plasticity_frozen is True
    for _ in range(40):
        e.step()
    post_probe_state = {j: float(n.threshold_adapt) for j, n in enumerate(e.l2.excitatory_neurons)}

    assert post_probe_state == pre_probe_state, \
        "adaptive-threshold state was not restored after the probe elapsed"
    print("PASS: a_i is restored to its pre-probe snapshot after the probe elapses")


def test_probe_cancellation_also_restores_threshold_adapt():
    """Even a probe cancelled by manual input (not naturally elapsed) must not
    leak its a_i evolution into subsequent training."""
    e = SimulationEngine(seed=1, adaptive_threshold=True, delta_threshold_frac=0.2,
                         tau_threshold=30.0, l1i_immediate_relay=False)
    e.set_pattern('col 1')
    for _ in range(150):
        e.step()
    pre_probe_state = {j: float(n.threshold_adapt) for j, n in enumerate(e.l2.excitatory_neurons)}

    e.present_probe('row 0', steps=200)
    for _ in range(10):
        e.step()
    e.clear_input()   # cancels the probe via _cancel_probe_if_active(restore=False)
    post_cancel_state = {j: float(n.threshold_adapt) for j, n in enumerate(e.l2.excitatory_neurons)}

    assert post_cancel_state == pre_probe_state, \
        "adaptive-threshold state leaked out of a CANCELLED probe"
    print("PASS: a_i is restored even when the probe is cancelled, not just when it elapses")


def test_probe_lets_a_i_evolve_internally_during_the_window():
    """The probe does not FREEZE a_i -- real physical spikes during the probe
    legitimately move it while the window is open."""
    e = SimulationEngine(seed=1, adaptive_threshold=True, delta_threshold_frac=0.3,
                         tau_threshold=40.0, l1i_immediate_relay=False)
    e.set_pattern('col 1')
    for _ in range(150):
        e.step()

    e.present_probe('row 0', steps=40)
    saw_change = False
    prev = {j: float(n.threshold_adapt) for j, n in enumerate(e.l2.excitatory_neurons)}
    for _ in range(40):
        e.step()
        now = {j: float(n.threshold_adapt) for j, n in enumerate(e.l2.excitatory_neurons)}
        if now != prev:
            saw_change = True
        prev = now
    assert saw_change, "a_i never changed during the probe -- physics look frozen, not just plasticity"
    print("PASS: a_i evolves internally during a probe (only restored afterward, not frozen live)")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
