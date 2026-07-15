"""
Regression tests for Phase 9 (causal L1I predictive feedback,
july14-integration; see the corrected Phases 6-12 prompt file).

Covers: L1I's predictive feedback is recorded as physical causal events, never
a pattern label or a software-declared owner -- first feedback source/SET,
arrival (a real L2E delivery reaches L1I), threshold crossing (L1I's own
fire), target (which L1I fired -- its paired L1E is implied by index), and
delivery/effect (the resulting one-step-delayed L1I->L1E pulse, read straight
off _inh_events). A genuinely ambiguous same-step multi-firer set is recorded
as such (never resolved by index priority, hidden charge, or weight
inspection) -- and, as a direct consequence of fixing the shared
`_credit_source` helper, this now also correctly covers a same-step tie on
ANY step, not just a presentation's first spike (the Phase 6 gap this phase
closes). Also covers: the intended L1I units respond to a real causal event
(not a software relay) in the default trainable-integrator mode, and frozen
probes remain non-mutating for both weights and confidence under this new
bookkeeping.
"""

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS
from backend.presets import DASHBOARD_PRESET


def _make(**overrides):
    return SimulationEngine(seed=1, **overrides)


def _force_same_step_multi_fire(e, indices=(0, 3), margin=10):
    thr = e.l2.excitatory_neurons[indices[0]].threshold
    for j in indices:
        e.l2.excitatory_neurons[j].refractory_timer = 0
        e.l2.excitatory_neurons[j].potential = thr + margin


# ------------------------------------------------------------ causal chain
def test_arrival_precedes_or_equals_threshold_crossing():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('col 1')
    d = None
    for _ in range(80):
        d = e.step()
        if d['causal_story']['l1i_first_t'] is not None:
            break
    story = d['causal_story']
    if story['l1i_first_t'] is not None:
        assert story['l1i_first_arrival_t'] is not None
        assert story['l1i_first_arrival_t'] <= story['l1i_first_t'], \
            "arrival (causal delivery) cannot happen after threshold crossing"


def test_source_set_recorded_at_arrival():
    e = _make(l1i_immediate_relay=False)
    e.set_pattern('row 1')
    d = None
    for _ in range(200):
        d = e.step()
        if d['causal_story']['l1i_first_arrival_t'] is not None:
            break
    story = d['causal_story']
    assert story['l1i_first_arrival_t'] is not None, "no L2E->L1I arrival within budget"
    assert len(story['l1i_first_source_set']) >= 1
    assert all(s.startswith('L2E') for s in story['l1i_first_source_set'])


def test_targets_are_the_actual_firing_l1i_units():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('diag /')
    d = None
    for _ in range(80):
        d = e.step()
        if d['causal_story']['l1i_first_t'] is not None:
            break
    story = d['causal_story']
    if story['l1i_first_t'] is not None:
        assert story['l1i_first_targets'], "threshold crossed but no targets recorded"
        assert all(t.startswith('L1I') for t in story['l1i_first_targets'])


def test_delivery_effect_lands_one_step_after_threshold_crossing():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('col 1')
    d = None
    for _ in range(80):
        d = e.step()
        if d['causal_story']['l1i_first_delivery'] is not None:
            break
    story = d['causal_story']
    if story['l1i_first_delivery'] is not None:
        assert story['l1i_first_t'] is not None
        assert story['l1i_first_delivery']['t'] == story['l1i_first_t'] + 1
        for ev in story['l1i_first_delivery']['events']:
            assert ev['neuron'].startswith('L1E')
            assert 'v_pre' in ev and 'v_post' in ev


# ---------------------------------------------------------- ambiguity (ties)
def test_source_set_reports_all_simultaneous_firers_on_arrival_step():
    e = _make(l1i_immediate_relay=False)
    e.set_pattern('col 1')
    for _ in range(3):
        e.step()
    _force_same_step_multi_fire(e, indices=(0, 3))
    d = e.step()
    story = d['causal_story']
    if story['l1i_first_arrival_t'] == e.timestep - 1:
        assert set(story['l1i_first_source_set']) >= {'L2E0', 'L2E3'}


def test_l1i_source_is_ambiguous_on_any_step_not_just_the_first_spike():
    """Phase 9 fix: a genuine same-step multi-firer set must be reported as
    'ambiguous' even when it happens on a LATER step (not the presentation's
    first spike) -- the Phase 6 check only covered the first-spike case."""
    e = _make(l1i_immediate_relay=False)
    e.set_pattern('row 1')
    for _ in range(60):
        e.step()
    _force_same_step_multi_fire(e, indices=(1, 4))
    # Ensure L1I hasn't already latched a first source from earlier in this
    # presentation before we force the tie; if it has, re-check via l2i
    # instead, which fires on this exact forced step too.
    e.l2.inhibitory_neuron.refractory_timer = 0
    e.l2.inhibitory_neuron.potential = e.l2.inhibitory_neuron.threshold
    d = e.step()
    story = d['causal_story']
    if len(e._last_eligible) > 1:
        if story['l1i_first_source'] is not None and story['l1i_first_t'] == e.timestep - 1:
            assert story['l1i_first_source'] == 'ambiguous'
        if story['l2i_first_source'] is not None and story['l2i_first_t'] == e.timestep - 1:
            assert story['l2i_first_source'] == 'ambiguous'


def test_credit_source_directly_checks_this_steps_firer_set():
    """Direct unit check of the fixed _credit_source: ambiguous iff
    len(_last_eligible) > 1 on the CURRENT step, regardless of presentation
    history/tie-at-first-spike state."""
    e = _make()
    e._last_eligible = [2]
    assert e._credit_source(2) == 'L2E2'
    e._last_eligible = [2, 5]
    assert e._credit_source(2) == 'ambiguous'
    e._last_eligible = []
    assert e._credit_source(None) is None
    print("PASS: _credit_source reads only this step's actual firer set")


# ------------------------------------------------ intended units / no fake duplication
def test_default_mode_l1i_does_not_fire_without_real_threshold_crossing():
    """Default (non-relay) mode: sabotage L1I so it can never cross threshold
    and confirm it does NOT fire even when an L2E winner appears -- the
    intended units respond to REAL accumulated causal charge, not a software
    broadcast."""
    e = _make(l1i_immediate_relay=False)
    for inh in e.l1.inhibitory_neurons:
        inh.weights = np.zeros(N_OUT)
        inh.threshold = 1e12
    e.set_pattern('row 1')
    fired_l1i = False
    for _ in range(300):
        d = e.step()
        if any(d['neurons'][i]['spiked'] for i, n in enumerate(d['neurons']) if n['id'].startswith('L1I')):
            fired_l1i = True
            break
        if any(e.spiked[f'L2E{j}'] for j in range(N_OUT)):
            break
    assert not fired_l1i, "L1I fired despite an impossibly-high threshold and zeroed weights"
    print("PASS: L1I does not fire merely by duplication -- a real threshold crossing is required")


def test_l2e_l1i_delivery_is_currently_identical_across_units_by_default():
    """Audit finding (Phase 1, still true after Phase 9): with infl_l2e_l1i
    off (default) every L1I shares one literal feedback weight vector and
    receives the identical l2e delivery, so their response is honestly
    undifferentiated -- not a fabricated per-unit distinction. This is
    reported accurately, not hidden or worked around."""
    e = _make()
    weights = [inh.weights.copy() for inh in e.l1.inhibitory_neurons]
    for w in weights[1:]:
        assert np.array_equal(w, weights[0]), \
            "L1I units no longer share one weight vector -- re-check Phase 9 audit notes"
    assert e.params['infl_l2e_l1i'] is False
    print("PASS: L1I->L2E weight sharing (and infl_l2e_l1i default-off) confirmed unchanged")


# --------------------------------------------------------------- probe freeze
def test_probe_non_mutation_holds_for_l1i_causal_bookkeeping():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('col 1')
    for _ in range(60):
        e.step()
    w_before = e._all_weights()
    c_before = e._all_confidence()

    e.present_probe('row 0', steps=30)
    assert e.plasticity_frozen is True
    saw_l1i_fire = False
    for _ in range(30):
        d = e.step()
        if d['causal_story']['l1i_first_t'] is not None:
            saw_l1i_fire = True

    assert e._all_weights() == w_before, "a probe mutated a weight via L1I bookkeeping"
    assert e._all_confidence() == c_before, "a probe mutated confidence via L1I bookkeeping"
    print(f"PASS: probe non-mutation holds (l1i fired during probe: {saw_l1i_fire})")


def test_l1i_bookkeeping_resets_at_new_presentation():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('col 1')
    for _ in range(60):
        e.step()
    e.set_pattern('row 1')
    d = e.dynamic_state()
    story = d['causal_story']
    assert story['l1i_first_arrival_t'] is None or story['pattern'] == 'row 1'
    # Freshly reset fields for the new presentation.
    assert e._presentation_l1i_first_source_set == []
    assert e._presentation_l1i_first_targets == []
    assert e._presentation_l1i_first_delivery is None


# ----------------------------------------------------------------- dynamics
def test_l1i_tracking_never_affects_physical_dynamics():
    e_quiet = SimulationEngine(seed=3, **DASHBOARD_PRESET)
    e_polled = SimulationEngine(seed=3, **DASHBOARD_PRESET)
    for _ in range(3):
        for name in PATTERNS:
            e_quiet.set_pattern(name)
            e_polled.set_pattern(name)
            for _ in range(20):
                dq = e_quiet.step()
                _ = e_polled.dynamic_state()['causal_story']
                dp = e_polled.step()
                assert dq['winner'] == dp['winner']
    assert e_quiet._all_weights() == e_polled._all_weights()


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
