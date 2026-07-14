"""
Regression tests for Phase 6 (representation candidate == first physical L2E
threshold crossing, july14-integration).

Covers: self.winner tracks the presentation's first physical L2E spike (never
re-derived by argmax/index/hidden-charge/weights/geometry/UI logic) and stays
None for the whole presentation on an ambiguous same-step tie; physicalFirstSpiker/
physicalFirstSpikeStep/earliestResponseSet/later-responses/latency-to-second
are all recorded correctly; a same-step tie earns no winner-specific evidence
credit and no unambiguous L1I/L2I source attribution; the retired latest-
spike-wins "episode" mechanism is fully gone; probe non-mutation (Phase 2) and
physical dynamics (spike timing, learning) are completely unaffected by this
phase -- only the reporting/representation layer changed.
"""

import numpy as np

from backend.simulation import SimulationEngine, PATTERNS, N_OUT
from backend.presets import DASHBOARD_PRESET


def _make(**overrides):
    return SimulationEngine(seed=1, **overrides)


def _force_same_step_tie(e, hi=0, lo=3, margin=10):
    """Push two L2E neurons above threshold together so the next step()
    produces a genuine same-step tie in _resolve_l2_competition's eligible set."""
    thr = e.l2.excitatory_neurons[hi].threshold
    e.l2.excitatory_neurons[hi].potential = thr + margin
    e.l2.excitatory_neurons[lo].potential = thr + margin / 2


# --------------------------------------------------------- non-tied first spike
def test_winner_equals_first_physical_spiker_when_not_tied():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('col 1')
    d = None
    for _ in range(60):
        d = e.step()
        if d['causal_story']['first_spiker'] is not None:
            break
    story = d['causal_story']
    assert story['first_spiker'] is not None
    assert story['same_step_tie'] is False
    assert e.winner == story['first_spiker']
    assert d['winner'] == story['first_spiker']


def test_earliest_response_set_is_singleton_when_not_tied():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('diag \\')
    for _ in range(60):
        d = e.step()
        if d['causal_story']['first_spiker'] is not None:
            break
    assert d['causal_story']['earliest_response_set'] == [d['causal_story']['first_spiker']]


# -------------------------------------------------------------------- tie case
def test_winner_is_none_during_a_same_step_tie():
    e = _make()
    e.set_pattern('col 1')
    for _ in range(3):
        e.step()
    _force_same_step_tie(e)
    d = e.step()
    story = d['causal_story']
    assert story['same_step_tie'] is True
    assert len(story['earliest_response_set']) >= 2
    assert set(['L2E0', 'L2E3']) <= set(story['earliest_response_set'])
    assert e.winner is None
    assert d['winner'] is None
    # physicalFirstSpiker is still recorded as a raw fact even though tied.
    assert story['first_spiker'] in story['earliest_response_set']


def test_winner_stays_none_for_rest_of_presentation_after_a_tie():
    e = _make()
    e.set_pattern('col 1')
    for _ in range(3):
        e.step()
    _force_same_step_tie(e)
    e.step()
    assert e.winner is None
    for _ in range(15):
        e.step()
        assert e.winner is None, "a later unambiguous spike must not retroactively become the winner"


def test_no_evidence_credit_for_a_tied_first_response():
    e = _make()
    e.set_pattern('col 1')
    for _ in range(3):
        e.step()
    _force_same_step_tie(e)
    e.step()
    e.set_pattern('row 1')   # archives the tied 'col 1' presentation
    assert 'col 1' not in e._pattern_first_responder_log
    counted_patterns = {p for counts in e._neuron_first_responder_counts.values() for p in counts}
    assert 'col 1' not in counted_patterns


def test_l1i_l2i_source_is_ambiguous_when_it_would_credit_the_tied_first_spiker():
    e = _make()
    e.set_pattern('col 1')
    for _ in range(3):
        e.step()
    _force_same_step_tie(e)
    # Also push L2I to fire on this exact step.
    e.l2.inhibitory_neuron.potential = e.l2.inhibitory_neuron.threshold - 1
    d = e.step()
    story = d['causal_story']
    if story['l2i_first_t'] == story['first_spike_t']:
        assert story['l2i_first_source'] == 'ambiguous'


# ------------------------------------------------------ later responses / latency
def test_later_responses_recorded_in_chronological_order():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('col 1')
    for _ in range(60):
        e.step()
    story = e.dynamic_state()['causal_story']
    ts = [t for t, _nid in story['later_responses']]
    assert ts == sorted(ts)
    if story['first_spike_t'] is not None:
        assert all(t > story['first_spike_t'] for t in ts)


def test_latency_to_second_response_only_counts_a_distinct_identity():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('diag /')
    for _ in range(60):
        e.step()
    story = e.dynamic_state()['causal_story']
    if story['latency_to_second_response'] is not None:
        distinct = {nid for _t, nid in story['later_responses']}
        distinct.discard(story['first_spiker'])
        assert distinct, "latency_to_second_response was set but no distinct later identity exists"
        assert story['latency_to_second_response'] >= 0


# -------------------------------------------------------------- presentation reset
def test_winner_resets_to_none_at_a_new_presentation():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('col 1')
    for _ in range(60):
        e.step()
    assert e.winner is not None   # sanity: something won by now
    e.set_pattern('row 1')
    assert e.winner is None


# ------------------------------------------------------ legacy episode removed
def test_latest_spike_wins_episode_machinery_is_fully_removed():
    e = _make()
    dyn = e.dynamic_state()
    assert 'episode' not in dyn
    for attr in ('episode_active', 'episode_timer', 'episode_last_spike_time',
                'episode_l2_spikes'):
        assert not hasattr(e, attr), f"retired episode attribute {attr} still exists"
    assert not hasattr(e, '_update_episode')
    assert not hasattr(e, '_resolve_episode')


# ------------------------------------------------------------- probe preserved
def test_probe_non_mutation_still_holds():
    e = _make(**DASHBOARD_PRESET)
    e.set_pattern('col 1')
    for _ in range(60):
        e.step()
    w_before = e._all_weights()
    c_before = e._all_confidence()

    e.present_probe('row 0', steps=20)
    assert e.plasticity_frozen is True
    assert e.winner is None   # presentation reset when the probe started
    spikes = 0
    for _ in range(20):
        d = e.step()
        spikes += sum(1 for n in d['neurons'] if n['id'].startswith('L2E') and n['spiked'])

    assert e._all_weights() == w_before, "a probe presentation changed a synaptic weight"
    assert e._all_confidence() == c_before, "a probe presentation changed a confidence value"
    assert spikes > 0, "no L2E spiked during the probe; physical dynamics look dead"
    assert e.plasticity_frozen is False
    assert e.presentation_role == 'train'
    assert e.presentation_pattern == 'col 1'


def test_probe_presentation_can_still_report_a_winner_while_frozen():
    """A probe is plasticity-frozen but NOT physics-frozen -- it can still have
    a first physical spiker/representation candidate, recorded the same way."""
    e = _make(**DASHBOARD_PRESET)
    e.present_probe('col 0', steps=30)
    story = None
    for _ in range(30):
        d = e.step()
        if d['causal_story']['first_spiker'] is not None:
            story = d['causal_story']
            break
    if story is not None:
        assert story['role'] == 'probe'
        assert story['plasticity_frozen'] is True


# --------------------------------------------------------- physical dynamics
def test_representation_tracking_never_affects_physical_dynamics():
    """Reading self.winner/dynamic_state()/causal_story heavily between steps
    must not change spike timing or learned weights -- it is a pure,
    write-only-for-display side channel."""
    e_quiet = SimulationEngine(seed=3, **DASHBOARD_PRESET)
    e_polled = SimulationEngine(seed=3, **DASHBOARD_PRESET)
    winners_quiet, winners_polled = [], []
    for _ in range(4):
        for name in PATTERNS:
            e_quiet.set_pattern(name)
            e_polled.set_pattern(name)
            for _ in range(20):
                dq = e_quiet.step()
                _ = e_polled.dynamic_state()   # heavy read between steps
                _ = e_polled.winner
                _ = e_polled.pathway_influence_report()
                dp = e_polled.step()
                winners_quiet.append(dq['winner'])
                winners_polled.append(dp['winner'])
    assert winners_quiet == winners_polled
    assert e_quiet._all_weights() == e_polled._all_weights()


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
