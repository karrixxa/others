"""
Regression tests for the observability phase (july14-integration).

Covers the pieces added purely for observability -- shared pattern/probe
metadata, presentation-scoped plasticity freeze, presentation IDs/boundaries,
evidence-based RF status, delivery diagnostics, and serialization -- and
confirms none of it altered the underlying neural dynamics (no probe ever
mutates a weight; the default, non-probe path is byte-identical to the Phase 1
baseline as measured by the existing diagnostics/test suite).
"""

from backend.simulation import SimulationEngine, PATTERNS, PROBES, PATTERN_ROLE, N_OUT
from backend.presets import DASHBOARD_PRESET


# --------------------------------------------------------------- shared metadata
def test_patterns_and_probes_are_disjoint():
    assert set(PATTERNS.keys()).isdisjoint(PROBES.keys())
    assert len(PATTERNS) == 4 and len(PROBES) == 4
    assert set(PATTERN_ROLE.values()) == {'train', 'probe'}
    assert all(PATTERN_ROLE[n] == 'train' for n in PATTERNS)
    assert all(PATTERN_ROLE[n] == 'probe' for n in PROBES)


def test_auto_cycle_order_is_training_patterns_only():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    assert set(e._cycle_order) == set(PATTERNS.keys())
    assert set(e._cycle_order).isdisjoint(PROBES.keys())


# ----------------------------------------------------------------- probe freeze
def test_probe_presentation_never_mutates_a_weight_or_confidence():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    e.set_pattern('col 1')
    for _ in range(60):
        e.step()
    w_before = e._all_weights()
    c_before = e._all_confidence()

    e.present_probe('row 0', steps=25)
    assert e.plasticity_frozen is True
    assert all(n.plasticity_frozen for n in e.neurons.values())
    spikes = 0
    for _ in range(25):
        d = e.step()
        spikes += sum(1 for n in d['neurons'] if n['id'].startswith('L2E') and n['spiked'])

    w_after = e._all_weights()
    c_after = e._all_confidence()
    assert w_after == w_before, "a probe presentation changed a synaptic weight"
    assert c_after == c_before, "a probe presentation changed a confidence value"
    # Physical dynamics must still be live -- a probe is observed, not disabled.
    assert spikes > 0, "no L2E spiked during the probe; physical dynamics look dead"


def test_probe_auto_restores_and_unfreezes():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    e.set_pattern('diag \\')
    e.present_probe('col 0', steps=10)
    for _ in range(9):
        e.step()
    assert e.plasticity_frozen is True   # still inside the window
    e.step()                             # the 10th step crosses probe_steps_total
    assert e.plasticity_frozen is False
    assert e._probe_active is False
    assert e.presentation_pattern == 'diag \\'
    assert e.presentation_role == 'train'
    assert all(not n.plasticity_frozen for n in e.neurons.values())


def test_probe_does_not_corrupt_auto_cycle_bookkeeping():
    e = SimulationEngine(seed=2, **DASHBOARD_PRESET)
    e.set_auto_cycle(True, streak=3, visit_steps=10)
    for _ in range(15):
        e.step()
    pattern_before = e.current_pattern
    visit_step_before = e._visit_step

    e.present_probe('col 2', steps=8)
    for _ in range(8):
        e.step()   # auto-cycle must not tick a probe name into _pattern_streak etc.

    assert e.presentation_pattern == pattern_before
    assert e._visit_step == visit_step_before
    assert set(e._pattern_streak.keys()) == set(PATTERNS.keys())
    assert set(e._pattern_last_winner.keys()) == set(PATTERNS.keys())

    # Auto-cycle keeps working normally afterward (no KeyError, no stuck state).
    for _ in range(300):
        e.step()
    assert e.current_pattern in PATTERNS


def test_manual_input_cancels_an_active_probe_without_restoring():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    e.present_probe('row 2', steps=50)
    assert e.plasticity_frozen is True
    e.toggle_pixel(0)
    assert e.plasticity_frozen is False
    assert e._probe_active is False


# ------------------------------------------------------------- presentation IDs
def test_presentation_id_increments_on_every_named_switch_and_logs_history():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    start_id = e.presentation_id
    e.set_pattern('col 1')
    for _ in range(15):
        e.step()
    e.set_pattern('row 1')
    assert e.presentation_id == start_id + 2
    assert len(e.presentation_log) >= 1
    last = e.presentation_log[-1]
    assert last['pattern'] == 'col 1'
    assert last['role'] == 'train'
    assert last['end_t'] >= last['start_t']


def test_first_responder_evidence_accumulates_across_presentations():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    for _ in range(8):
        for name in PATTERNS:
            e.set_pattern(name)
            for _ in range(15):
                e.step()
    # At least one L2E neuron should have been recorded as a first responder for
    # at least one pattern by now (evidence-based, not a hardcoded owner).
    assert e._neuron_first_responder_counts, "no first-responder evidence recorded"
    total_counts = sum(sum(v.values()) for v in e._neuron_first_responder_counts.values())
    assert total_counts > 0


# --------------------------------------------------------------- serialization
def test_topology_exposes_probes_and_delivery_diagnostics():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    for _ in range(3):
        e.step()
    topo = e.topology()
    assert sorted(topo['probes']) == sorted(PROBES.keys())
    assert set(topo['probe_vectors'].keys()) == set(PROBES.keys())
    assert topo['pattern_roles'] == PATTERN_ROLE
    ff_syn = next(s for s in topo['synapses'] if s['kind'] == 'feedforward')
    assert {'distance', 'influence', 'effective'} <= ff_syn.keys()
    assert ff_syn['distance'] > 0


def test_dynamic_state_exposes_causal_story_and_rf_status():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    for _ in range(20):
        e.step()
    dyn = e.dynamic_state()
    assert 'causal_story' in dyn and 'probe' in dyn
    story = dyn['causal_story']
    for key in ('presentation_id', 'pattern', 'role', 'plasticity_frozen',
                'first_spiker', 'first_spike_t', 'same_step_tie',
                'l1i_first_source', 'l2i_first_source', 'history'):
        assert key in story
    l2e0 = next(n for n in dyn['neurons'] if n['id'] == 'L2E0')
    assert 'rf_status' in l2e0
    assert l2e0['rf_status']['status'] in ('unrecruited', 'active', 'quiet')
    assert 'l2_drive' in dyn and 'l2_charge' in dyn and 'inh_events' in dyn


def test_probe_endpoint_rejects_unknown_name():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    try:
        e.present_probe('not a real probe')
        assert False, "expected KeyError"
    except KeyError:
        pass


# ---------------------------------------------------------------- rf status
def test_l2e_status_is_evidence_based_not_a_weight_guess():
    """A neuron with strong weights but that has never fired must read
    'unrecruited', not 'dead' (the old client-side weight-sum heuristic) --
    status is purely about OBSERVED spikes."""
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    status = e._l2e_status(0)
    assert status['status'] == 'unrecruited'
    assert status['spikes_total'] == 0
    assert status['last_fired_step'] is None
    assert status['first_responder_counts'] == {}


# ----------------------------------------------------------- legacy equivalence
def test_default_engine_construction_unchanged_by_dashboard_preset_extraction():
    """backend.presets.DASHBOARD_PRESET must reproduce byte-identical params to
    what backend/api.py constructed inline before the extraction."""
    e = SimulationEngine(seed=7, **DASHBOARD_PRESET)
    p = e.params
    assert p['distance_weighting'] is True
    assert p['distance_ref'] == 7.472
    assert p['structural_free_energy'] is True
    assert p['loser_depression'] is True
    assert p['l2i_hard_reset_losers'] is True
    assert p['refractory'] == 0
    assert p['l2_charge_chunks'] == 20


def test_plasticity_frozen_defaults_false_and_learning_is_unaffected():
    """With plasticity_frozen never touched (the default for every pre-existing
    caller/test), a fire() call must still update weights exactly as before."""
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    assert all(not n.plasticity_frozen for n in e.neurons.values())
    e.set_pattern('row 1')
    w_before = e._all_weights()
    for _ in range(80):
        e.step()
    w_after = e._all_weights()
    assert w_after != w_before, "learning did not happen with plasticity_frozen at its default (False)"


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
