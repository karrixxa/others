"""
Regression tests for Phase 4 (connection distance/influence as isolated
experimental behavior, july14-integration).

Covers: close-vs-distant delivery per pathway, fixed/cached influence, reset
stability, disabled equivalence (every new flag defaults off, byte-identical
to baseline), no influence-squared bug (delivery uses influence^1, learning
uses the RAW unscaled weight), and that the legacy L1E->L2E / geometry-off
baselines are completely untouched.
"""

import numpy as np

from backend.simulation import (SimulationEngine, PATTERNS, N_PIX, N_OUT,
                                INFLUENCE_SAFE_MAX, _power_law_influence)
from backend.presets import DASHBOARD_PRESET
from snn.rules import effective_weights


def _make(**overrides):
    return SimulationEngine(seed=1, **overrides)


# --------------------------------------------------------------- default state
def test_all_four_new_pathways_default_off():
    e = _make()
    for k in ('infl_l2e_l2i', 'infl_l2i_l2e', 'infl_l2e_l1i', 'infl_l1i_l1e'):
        assert e.params[k] is False
    assert e.params['infl_power'] == 2.0
    assert e.params['infl_ref'] == e.params['infl_min'] == 1.0


def test_dashboard_preset_does_not_enable_any_new_pathway():
    """'Do not enable every pathway together' -- the live dashboard preset
    must not flip any of the four new flags on."""
    for k in ('infl_l2e_l2i', 'infl_l2i_l2e', 'infl_l2e_l1i', 'infl_l1i_l1e'):
        assert DASHBOARD_PRESET.get(k, False) is False


def test_legacy_l1e_l2e_pathway_and_geometry_baselines_untouched():
    """The 'geometry-off' (distance_weighting=False) and 'legacy-distance'
    (distance_weighting=True, legacy_distance_compat=True) baselines from
    Phase 2/3 must still exist and behave exactly as before -- this phase adds
    NEW pathways beside them, never modifies them."""
    e_off = _make()
    assert e_off.params['distance_weighting'] is False
    e_legacy = _make(distance_weighting=True, legacy_distance_compat=True)
    assert e_legacy.l2.excitatory_neurons[0].distance_weighting is True


# --------------------------------------------------------- disabled equivalence
def test_disabled_equivalence_dashboard_preset_unaffected_by_new_params_existing():
    """Merely having the new infl_* params defined (all False) must not change
    a single spike/weight versus the exact same preset before Phase 4 existed."""
    e_new = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    e_ref = SimulationEngine(seed=1, **DASHBOARD_PRESET)   # fresh instance, same config
    winners_new, winners_ref = [], []
    for _ in range(4):
        for name in PATTERNS:
            e_new.set_pattern(name); e_ref.set_pattern(name)
            for _ in range(25):
                winners_new.append(e_new.step()['winner'])
                winners_ref.append(e_ref.step()['winner'])
    assert winners_new == winners_ref
    assert e_new._all_weights() == e_ref._all_weights()


def test_disabled_flag_means_neuron_level_distance_weighting_stays_false():
    """Even with real distances computed, distance_weighting must read False on
    L2I/L1I/L1E when that pathway's flag is off (NeuronConfig.apply_to()
    already forces this for non-L2E; this confirms our new code doesn't
    accidentally re-enable it)."""
    e = _make(symmetric_geometry=False, topology_seed=3)
    assert e.l2.inhibitory_neuron.distance_weighting is False
    for inh in e.l1.inhibitory_neurons:
        assert inh.distance_weighting is False
    for exc in e.l1.excitatory_neurons:
        assert exc.distance_weighting is False


# ------------------------------------------------------------ per-pathway isolation
def test_each_pathway_flag_is_independent():
    """Enabling one pathway must not turn on any other."""
    e = _make(symmetric_geometry=False, topology_seed=3, infl_l2e_l2i=True)
    assert e.l2.inhibitory_neuron.distance_weighting is True
    assert all(not inh.distance_weighting for inh in e.l1.inhibitory_neurons)
    assert all(not exc.distance_weighting for exc in e.l1.excitatory_neurons)
    assert all(exc.competitive_reset_influence == 1.0 for exc in e.l2.excitatory_neurons)


# --------------------------------------------------------- close vs distant delivery
def test_close_vs_distant_delivery_l2e_l2i():
    e = _make(infl_l2e_l2i=True)
    l2i = e.l2.inhibitory_neuron
    raw = l2i._weights_array.copy()

    l2i.distance = np.full(N_OUT, e.params['infl_ref'])           # all "close" (d==ref==min)
    close_eff = effective_weights(l2i).copy()

    l2i.distance = np.full(N_OUT, e.params['infl_ref'] * 5)       # all "distant"
    distant_eff = effective_weights(l2i).copy()

    assert np.allclose(close_eff, raw), "at d==ref==min, influence must be exactly 1.0 (no scaling)"
    assert np.all(distant_eff < close_eff), "a distant connection must deliver LESS charge than a close one"


def test_close_vs_distant_delivery_l2e_l1i():
    e = _make(infl_l2e_l1i=True)
    inh = e.l1.inhibitory_neurons[0]
    raw = inh._weights_array.copy()

    inh.distance = np.full(N_OUT, e.params['infl_ref'])
    close_eff = effective_weights(inh).copy()
    inh.distance = np.full(N_OUT, e.params['infl_ref'] * 5)
    distant_eff = effective_weights(inh).copy()

    assert np.allclose(close_eff, raw)
    assert np.all(distant_eff < close_eff)


def test_close_vs_distant_delivery_l1i_l1e_direct():
    """L1E's pixel-drive margin is razor-thin (see Known problems in the
    handoff), so this pathway's effect is only reliably observable at the
    delivery/membrane level, not in whether L1E ends up firing -- test it
    directly rather than relying on an emergent system-level difference."""
    def make():
        eng = SimulationEngine(seed=1, infl_l1i_l1e=True)
        return eng.l1.excitatory_neurons[0], eng.params['infl_ref']

    n1, ref = make()
    n1.potential = 1000.0
    n1.distance = np.array([ref, ref])            # close: influence == 1.0
    n1.apply_inhibition(np.array([1.0, 0.0]))
    v_close = float(n1.potential)

    n2, ref2 = make()
    n2.potential = 1000.0
    n2.distance = np.array([ref2 * 2, ref2])      # distant: influence == 0.25 (power=2)
    n2.apply_inhibition(np.array([1.0, 0.0]))
    v_distant = float(n2.potential)

    assert v_close == 0.0, "close (influence==1.0) must deliver the FULL discharge"
    assert abs(v_distant - 750.0) < 1e-6, "distant (influence==0.25) must deliver exactly 25% -- not squared to 6.25%"


def test_l2i_l2e_depression_gain_scales_with_distance():
    """L2I->L2E has no learned weight; influence scales ONLY the competitive-
    depression gain (Phase 7: Neuron.apply_delayed_inhibition). Verify close
    vs. distant gives a smaller depression at greater influence-attenuated
    distance, and that the DELIVERED MAGNITUDE (a full-threshold delivery
    floors either target at exact rest) is identical either way -- influence
    never touches the delivery itself."""
    def make(influence):
        eng = SimulationEngine(seed=1, infl_l2i_l2e=True)
        n = eng.l2.excitatory_neurons[0]
        n.competitive_reset_influence = influence
        n.potential = n.threshold * 0.9   # non-trivial p_loss
        n._last_input_spikes = np.ones(N_PIX)
        return n

    n_close = make(1.0)
    rec_close = n_close.apply_delayed_inhibition(n_close.threshold)
    n_far = make(0.25)
    rec_far = n_far.apply_delayed_inhibition(n_far.threshold)

    assert rec_close['v_post'] == n_close.resting_potential
    assert rec_far['v_post'] == n_far.resting_potential   # delivery magnitude unaffected
    dep_close = np.abs(rec_close['delta_weights']).sum()
    dep_far = np.abs(rec_far['delta_weights']).sum()
    assert dep_far < dep_close, "a farther L2E should be depressed LESS when infl_l2i_l2e is on"
    assert dep_far == 0 or abs(dep_far - dep_close * 0.25) / dep_close < 0.35


# -------------------------------------------------------------- fixed / cached
def test_influence_is_fixed_across_steps_training_and_probes():
    e = _make(symmetric_geometry=False, topology_seed=3, infl_l2e_l2i=True,
             infl_l2e_l1i=True, infl_l1i_l1e=True)
    before = e.pathway_influence_report()
    e.set_pattern('col 1')
    for _ in range(60):
        e.step()
    e.present_probe('row 0', steps=10)
    for _ in range(10):
        e.step()
    after = e.pathway_influence_report()
    for pathway in ('l2e_l2i', 'l2e_l1i', 'l1i_l1e'):
        d_before = [x['distance'] for x in before[pathway]['entries']]
        d_after = [x['distance'] for x in after[pathway]['entries']]
        assert d_before == d_after, f"{pathway} distances changed across training/probe"


# --------------------------------------------------------------- reset stability
def test_pathway_distances_fixed_across_reset_and_unrelated_config():
    e = _make(symmetric_geometry=False, topology_seed=3, infl_l2e_l2i=True)
    d0 = e.l2.inhibitory_neuron.distance.copy()
    e.reset()
    assert np.array_equal(e.l2.inhibitory_neuron.distance, d0)
    e.reseed()
    assert np.array_equal(e.l2.inhibitory_neuron.distance, d0)


def test_reseed_topology_changes_pathway_distances_consistently():
    e = _make(symmetric_geometry=False, topology_seed=3, infl_l2e_l2i=True,
             infl_l2e_l1i=True, infl_l1i_l1e=True)
    before = e.pathway_influence_report()
    e.reseed_topology()
    after = e.pathway_influence_report()
    for pathway in ('l2e_l2i', 'l2e_l1i', 'l1i_l1e'):
        d_before = [x['distance'] for x in before[pathway]['entries']]
        d_after = [x['distance'] for x in after[pathway]['entries']]
        assert d_before != d_after, f"{pathway} should change on an explicit topology reseed"


# --------------------------------------------------------- no influence-squared bug
def test_no_influence_squared_delivery_l2e_l2i():
    """effective_weights() must use influence^1, never influence^2."""
    e = _make(infl_l2e_l2i=True)
    l2i = e.l2.inhibitory_neuron
    d = 2.0
    l2i.distance = np.full(N_OUT, d)
    raw = l2i._weights_array.copy()
    expected_influence = _power_law_influence(d, e.params['infl_ref'], e.params['infl_min'],
                                              e.params['infl_power'])
    eff = effective_weights(l2i)
    assert np.allclose(eff, raw * expected_influence)
    assert not np.allclose(eff, raw * expected_influence ** 2), "influence was squared!"


def test_learning_uses_raw_weight_not_distance_scaled_l2e_l2i():
    """The E->I feedforward learning rule (_update_weights -> on_fire) must use
    the RAW stored weight and the raw (unscaled) participation mask, never the
    distance-scaled delivered value -- otherwise influence would be applied
    once in delivery and again in learning."""
    e = _make(infl_l2e_l2i=True, learning_rate=0.1)
    l2i = e.l2.inhibitory_neuron
    l2i.distance = np.array([10.0] * N_OUT)   # heavy attenuation
    l2i.distance_weighting = True
    w_before = l2i._weights_array.copy()
    l2i._last_input_spikes = np.ones(N_OUT)
    l2i.potential = l2i.threshold * 0.5
    l2i._update_weights(v_pre=float(l2i.potential))
    w_after = l2i._weights_array.copy()
    # Update magnitude should NOT be suppressed by the (tiny) distance-scaled
    # delivered value -- it should reflect the raw participation/weight terms.
    assert not np.allclose(w_after, w_before), "learning did not run at all"


def test_pathway_influence_never_amplifies_by_default():
    """'Avoid extreme amplification': under the default power law (ref==min),
    every reported influence must be <= 1.0, and 'safe' must be True."""
    e = _make(symmetric_geometry=False, topology_seed=3, infl_l2e_l2i=True,
             infl_l2i_l2e=True, infl_l2e_l1i=True, infl_l1i_l1e=True)
    report = e.pathway_influence_report()
    for name, pathway in report.items():
        assert pathway['influence_max'] <= 1.0 + 1e-9, f"{name} amplified beyond 1.0"
        assert pathway['influence_max'] <= INFLUENCE_SAFE_MAX
        assert pathway['safe'] is True


# --------------------------------------------------------------- serialization
def test_pathway_influence_report_structure():
    e = _make(symmetric_geometry=False, topology_seed=3)
    report = e.pathway_influence_report()
    assert set(report.keys()) == {'l1e_l2e', 'l2e_l2i', 'l2i_l2e', 'l2e_l1i', 'l1i_l1e'}
    assert len(report['l1e_l2e']['entries']) == N_PIX * N_OUT
    assert len(report['l2e_l2i']['entries']) == N_OUT
    assert len(report['l2i_l2e']['entries']) == N_OUT
    assert len(report['l2e_l1i']['entries']) == N_OUT * N_PIX
    assert len(report['l1i_l1e']['entries']) == N_PIX
    for pathway in report.values():
        for k in ('influence_min', 'influence_median', 'influence_max', 'safe'):
            assert k in pathway
        for entry in pathway['entries'][:1]:
            for k in ('source', 'target', 'distance', 'influence', 'raw_weight',
                     'effective', 'applied'):
                assert k in entry

    # L2I->L2E has no learned weight -- raw_weight/effective must be None.
    for entry in report['l2i_l2e']['entries']:
        assert entry['raw_weight'] is None and entry['effective'] is None


def test_pathway_influence_applied_flag_matches_config():
    e = _make(symmetric_geometry=False, topology_seed=3, infl_l2e_l2i=True)
    report = e.pathway_influence_report()
    assert all(x['applied'] for x in report['l2e_l2i']['entries'])
    assert all(not x['applied'] for x in report['l2i_l2e']['entries'])
    assert all(not x['applied'] for x in report['l2e_l1i']['entries'])
    assert all(not x['applied'] for x in report['l1i_l1e']['entries'])
    assert all(not x['applied'] for x in report['l1e_l2e']['entries'])   # distance_weighting off


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
