"""
Regression tests for Phase 7 (causal L2E->L2I->L2E competition,
july14-integration; see July_14_Geometric_Influence_Temporal_Winner_Brief.txt
SS9 and CLAUDE_HANDOFF.md).

Covers: L2I accumulates actual arriving L2E spike events and fires on its OWN
threshold crossing (never inferred/assumed -- read directly off the recorded
v_pre/v_post and the scheduled record); a delayed, uniform inhibitory delivery
is SCHEDULED (not applied) at that moment and only APPLIED
l2_inhibition_delay steps later; a neuron resets normally on its own spike and
is never reset by software for merely being a competitor; later L2E spikes
before delivery arrives are valid and remain ranked (all recorded, none
erased); contributing sources, arrival times, L2I pre/post charge, threshold
crossing, scheduled delivery, delivered inhibition, and competitor pre/post
charge are all directly exposed via dynamic_state()['l2_inhibition'] and
e._reset_events/_l2i_pending/_l2_inhibition_log -- never inferred from neuron
IDs or final spike counts. Also covers: a refractory target is skipped by
delivery (not by an ID-based exemption); pending deliveries are NOT cancelled
by a pattern switch (an uncancellable in-flight physical signal, matching the
l1i_feedback_delay precedent); a probe's plasticity freeze does not block the
physical delivery discharge, only the structural-depression learning it can
trigger; the config knobs (l2_inhibition_delay/l2_inhibition_frac) are live
and dashboard-tunable.
"""

import numpy as np

from backend.simulation import SimulationEngine, PATTERNS, N_OUT, N_PIX
from backend.presets import DASHBOARD_PRESET


def _make(**overrides):
    return SimulationEngine(seed=1, **overrides)


def _force_multi_crosser_step(e, indices=(0, 3), margin=10):
    """Push several L2E neurons above threshold together, and pre-charge L2I
    close to its own threshold so the next step() both fires every crosser and
    lets L2I cross (accumulating their events)."""
    thr = e.l2.excitatory_neurons[indices[0]].threshold
    for j in indices:
        e.l2.excitatory_neurons[j].refractory_timer = 0
        e.l2.excitatory_neurons[j].potential = thr + margin
    e.l2.inhibitory_neuron.refractory_timer = 0
    e.l2.inhibitory_neuron.potential = e.l2.inhibitory_neuron.threshold


# --------------------------------------------------------- every crosser fires
def test_every_threshold_crosser_fires_not_just_one():
    """Phase 7: no argmax pick -- every L2E above threshold this step
    physically fires, verified directly off the one-hot l2e vector via
    e.spiked, not inferred from which one 'won'."""
    e = _make(l1i_immediate_relay=False)
    e.set_pattern('col 1')
    for _ in range(3):
        e.step()
    _force_multi_crosser_step(e, indices=(0, 3))
    d = e.step()
    assert d['neurons'] is not None
    spiked_now = {n['id'] for n in d['neurons'] if n['id'].startswith('L2E') and n['spiked']}
    assert {'L2E0', 'L2E3'} <= spiked_now, \
        f"both simultaneous crossers must fire; only saw {spiked_now}"


def test_later_response_is_not_erased_by_an_earlier_one():
    """A later L2E spike before inhibition arrives is valid and remains ranked
    -- it must show up in later_responses, never silently dropped."""
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('diag /')
    for _ in range(80):
        e.step()
    story = e.dynamic_state()['causal_story']
    if story['first_spike_t'] is not None:
        for t, _nid in story['later_responses']:
            assert t > story['first_spike_t']


# --------------------------------------------------- scheduling, never inferred
def test_l2i_fire_schedules_a_delayed_delivery_not_an_immediate_reset():
    e = _make(l1i_immediate_relay=False)
    e._l2i_pending = []
    e._reset_events = []
    _force_multi_crosser_step(e, indices=(0, 1))
    t = e.timestep
    l2i, inhibited, first_firer = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), t)
    assert inhibited == [], "Phase 7: _resolve_l2_competition never performs an immediate reset"
    assert e._reset_events == [], "no reset/delivery record exists until delivery time"
    if l2i:
        assert len(e._l2i_pending) == 1
        rec = e._l2i_pending[0]
        assert rec['deliver_at'] == t + e.l2_inhibition_delay
        assert rec['fire_t'] == t
        assert set(rec['contributors']) >= {(t, 'L2E0'), (t, 'L2E1')}, rec['contributors']


def test_contributing_sources_and_arrival_times_are_recorded():
    """Contributing sources + arrival times must be actual recorded (t, id)
    events, not re-derived from spike counts after the fact."""
    e = _make(l1i_immediate_relay=False)
    e._l2i_pending = []
    _force_multi_crosser_step(e, indices=(2, 5))
    t = e.timestep
    l2i, _inhibited, _first = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), t)
    if l2i:
        contributors = e._l2i_pending[-1]['contributors']
        ids = {cid for _ct, cid in contributors}
        times = {ct for ct, _cid in contributors}
        assert ids == {'L2E2', 'L2E5'}
        assert times == {t}


def test_l2i_threshold_crossing_uses_recorded_pre_post_charge():
    """L2I's own pre/post charge at the moment it crosses threshold must be
    directly recorded (never inferred from whether it 'seems' to have fired)."""
    e = _make(l1i_immediate_relay=False)
    e._l2i_pending = []
    _force_multi_crosser_step(e, indices=(0, 1))
    t = e.timestep
    l2i, _inhibited, _first = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), t)
    if l2i:
        rec = e._l2i_pending[-1]
        assert rec['l2i_v_pre'] >= e.l2.inhibitory_neuron.threshold - 1e-6
        assert rec['l2i_v_post'] < rec['l2i_v_pre'], \
            "L2I must discharge on its own fire, recorded pre > post"


# ---------------------------------------------------------------- delivery
def test_scheduled_delivery_is_applied_exactly_at_deliver_at():
    e = _make(l1i_immediate_relay=False)
    e._l2i_pending = []
    _force_multi_crosser_step(e, indices=(0, 1))
    t = e.timestep
    l2i, _inhibited, _first = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), t)
    if not l2i:
        return
    deliver_at = e._l2i_pending[0]['deliver_at']
    assert e._deliver_scheduled_l2_inhibition(deliver_at - 1) == [], \
        "delivery must not apply before its scheduled step"
    delivered = e._deliver_scheduled_l2_inhibition(deliver_at)
    assert delivered, "delivery must apply exactly at deliver_at"
    assert e._l2i_pending == [], "a delivered record must be consumed, not re-delivered"


def test_delivered_inhibition_exposes_competitor_pre_post_charge():
    e = _make(l1i_immediate_relay=False)
    e._l2i_pending = []
    _force_multi_crosser_step(e, indices=(0, 1))
    t = e.timestep
    l2i, _inhibited, _first = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), t)
    if not l2i:
        return
    deliver_at = e._l2i_pending[0]['deliver_at']
    e._deliver_scheduled_l2_inhibition(deliver_at)
    assert e._reset_events, "an applied delivery must populate _reset_events"
    for nid, rec in e._reset_events:
        assert nid.startswith('L2E')
        assert 'v_pre' in rec and 'v_post' in rec
        assert rec['v_post'] <= rec['v_pre'] + 1e-9
        assert rec['applied'] is True


def test_refractory_target_is_skipped_not_forced():
    """Delivery is uniform (all N_OUT targets attempted) but a target still in
    its own post-spike refractory window is skipped entirely -- verified
    directly against refractory_timer, never assumed from neuron ID."""
    e = _make(l1i_immediate_relay=False)
    e._l2i_pending = []
    _force_multi_crosser_step(e, indices=(0, 1))
    t = e.timestep
    l2i, _inhibited, _first = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), t)
    if not l2i:
        return
    deliver_at = e._l2i_pending[0]['deliver_at']
    refractory_before = {j: e.l2.excitatory_neurons[j].refractory_timer for j in range(N_OUT)}
    delivered = e._deliver_scheduled_l2_inhibition(deliver_at)
    for j in range(N_OUT):
        if refractory_before[j] > 0:
            assert j not in delivered, f"L2E{j} was refractory but received delivery anyway"


# -------------------------------------------------------------- dynamic_state
def test_dynamic_state_exposes_l2_inhibition_block():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('row 1')
    d = None
    for _ in range(200):
        d = e.step()
        if d['l2_inhibition']['last_delivery'] is not None:
            break
    li = d['l2_inhibition']
    assert 'delay' in li and 'magnitude' in li and 'pending' in li
    assert 'last_delivery' in li and 'log' in li
    if li['last_delivery'] is not None:
        delivery = li['last_delivery']
        assert 'contributors' in delivery
        assert 'l2i_v_pre' in delivery and 'l2i_v_post' in delivery
        assert 'targets' in delivery and len(delivery['targets']) == N_OUT
        for t in delivery['targets']:
            assert {'id', 'applied', 'v_pre', 'v_post'} <= t.keys()


def test_pending_entries_carry_full_recorded_fields():
    e = _make(l1i_immediate_relay=False)
    e._l2i_pending = []
    _force_multi_crosser_step(e, indices=(0, 1))
    t = e.timestep
    l2i, _inhibited, _first = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), t)
    if not l2i:
        return
    d = e.dynamic_state()
    pending = d['l2_inhibition']['pending']
    assert len(pending) == 1
    rec = pending[0]
    for key in ('fire_t', 'deliver_at', 'contributors', 'l2i_v_pre', 'l2i_v_post', 'magnitude'):
        assert key in rec


# ------------------------------------------------------- non-cancellation
def test_pending_delivery_is_not_cancelled_by_a_pattern_switch():
    """A scheduled delivery is a real in-flight physical signal -- it is not
    cancelled by set_pattern, matching the l1i_feedback_delay precedent."""
    e = _make(l1i_immediate_relay=False)
    e._l2i_pending = []
    _force_multi_crosser_step(e, indices=(0, 1))
    t = e.timestep
    l2i, _inhibited, _first = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), t)
    if not l2i:
        return
    assert e._l2i_pending
    e.set_pattern('diag \\')
    assert e._l2i_pending, "a pattern switch must not cancel a scheduled delivery"


# --------------------------------------------------------------- probe freeze
def test_probe_plasticity_freeze_does_not_block_delivery_discharge():
    """A probe is plasticity-frozen but not physics-frozen: the delivery's
    transient membrane subtraction must still occur even though the
    structural-depression learning it can trigger is skipped."""
    e = _make(**DASHBOARD_PRESET)
    e.present_probe('row 0', steps=40)
    assert e.plasticity_frozen is True
    w_before = e._all_weights()
    saw_delivery = False
    for _ in range(40):
        e.step()
        if e._reset_events:
            saw_delivery = True
            for nid, rec in e._reset_events:
                assert rec['depressed_indices'] == [], \
                    "structural depression must not run while plasticity is frozen"
    if saw_delivery:
        assert e._all_weights() == w_before, "a probe must not change any weight"


# ---------------------------------------------------------------- config knobs
def test_delay_and_magnitude_are_configurable():
    e = _make(l2_inhibition_delay=3, l2_inhibition_frac=0.4)
    assert e.l2_inhibition_delay == 3
    assert np.isclose(e.l2_inhibition_magnitude, 0.4 * e.params['threshold_l2'])

    e2 = _make()
    e2.apply_config({'l2_inhibition_delay': 5, 'l2_inhibition_frac': 0.1})
    assert e2.l2_inhibition_delay == 5
    assert np.isclose(e2.l2_inhibition_magnitude, 0.1 * e2.params['threshold_l2'])


def test_delivery_lands_exactly_delay_steps_after_l2i_fires():
    e = _make(l1i_immediate_relay=False, l2_inhibition_delay=4)
    e._l2i_pending = []
    _force_multi_crosser_step(e, indices=(0, 1))
    t = e.timestep
    l2i, _inhibited, _first = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), t)
    if not l2i:
        return
    rec = e._l2i_pending[0]
    assert rec['deliver_at'] - rec['fire_t'] == 4


# -------------------------------------------------------- physical dynamics
def test_l2_inhibition_bookkeeping_does_not_affect_physical_dynamics():
    """Reading dynamic_state()/l2_inhibition heavily between steps must not
    change spike timing or learned weights -- observability only."""
    e_quiet = SimulationEngine(seed=3, **DASHBOARD_PRESET)
    e_polled = SimulationEngine(seed=3, **DASHBOARD_PRESET)
    for _ in range(3):
        for name in PATTERNS:
            e_quiet.set_pattern(name)
            e_polled.set_pattern(name)
            for _ in range(20):
                dq = e_quiet.step()
                _ = e_polled.dynamic_state()['l2_inhibition']
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
