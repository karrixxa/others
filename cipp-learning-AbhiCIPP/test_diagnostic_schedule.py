"""
Regression tests for the diagnostic-only equal-interleaved presentation
schedule (july14-integration).

Covers: fixed cycle order, brief (non-saturating) presentations, the
non-mutating-evaluation guarantee (a live engine passed in is NEVER touched),
every requested per-presentation field is recorded, the frozen re-test pass
shows exactly zero weight drift, and the summary report's structure/sanity
(per-pattern consistency/ambiguity/no-response, distinct owners, collisions,
forgetting, silent/recruitable cells, L2I activity, L1I selectivity).

Deliberately no changes to backend/simulation.py or neuron_flexible.py in this
phase -- this file only imports and exercises the existing public/semi-public
engine surface.
"""

from backend.simulation import SimulationEngine, N_OUT, N_PIX
from backend.presets import DASHBOARD_PRESET
from diagnostic_schedule import CYCLE_ORDER, run_diagnostic, summarize, PRESENTATION_STEPS


# ------------------------------------------------------------------- schedule
def test_cycle_order_matches_the_brief_exactly():
    assert CYCLE_ORDER == ['row 1', 'col 1', 'diag \\', 'diag /']


def test_presentations_are_brief_not_saturating():
    """PRESENTATION_STEPS must be a short window, not a long saturating hold
    (repo convention for other diagnostics is 15-40 steps)."""
    assert 5 <= PRESENTATION_STEPS <= 40


def test_live_pass_visits_patterns_in_fixed_cycle_order():
    run = run_diagnostic(seed=1, cycles=3, presentation_steps=6)
    patterns_seen = [r['pattern'] for r in run['live']]
    expected = CYCLE_ORDER * 3
    assert patterns_seen == expected


# --------------------------------------------------------- non-mutating eval
def test_run_diagnostic_never_mutates_a_passed_in_live_engine():
    live = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    live.set_pattern('col 1')
    for _ in range(40):
        live.step()
    w_before = live._all_weights()
    t_before = live.timestep
    pid_before = live.presentation_id
    input_before = live.input_vec.copy()

    run_diagnostic(seed=1, engine=live, cycles=4, presentation_steps=6)

    assert live._all_weights() == w_before
    assert live.timestep == t_before
    assert live.presentation_id == pid_before
    assert (live.input_vec == input_before).all()


def test_run_diagnostic_builds_a_fresh_engine_when_none_given():
    run = run_diagnostic(seed=7, cycles=2, presentation_steps=5)
    assert run['seed'] == 7
    assert len(run['live']) == 2 * len(CYCLE_ORDER)


def test_frozen_pass_produces_zero_weight_drift():
    run = run_diagnostic(seed=1, cycles=4, presentation_steps=8)
    for r in run['frozen']:
        assert r['plasticity_frozen'] is True
        assert all(abs(v) < 1e-9 for v in r['weight_changes'].values())


def test_live_pass_actually_learns():
    """Sanity: the LIVE pass (not frozen) must show real weight changes
    somewhere, or the whole exercise measures nothing."""
    run = run_diagnostic(seed=1, cycles=6, presentation_steps=10)
    any_change = any(abs(v) > 1e-9 for r in run['live'] for v in r['weight_changes'].values())
    assert any_change


# ------------------------------------------------------------- recorded fields
def test_every_requested_field_is_recorded_per_presentation():
    run = run_diagnostic(seed=1, cycles=3, presentation_steps=8)
    required = {'presentation_id', 'pattern', 'plasticity_frozen',
               'first_l2e_spiker', 'first_l2e_spike_t', 'same_step_tie',
               'all_l2e_spikes', 'latency_margin_to_second',
               'l2i_spike_steps', 'l2i_spike_count', 'l1i_fired_positions',
               'pre_inhibition_charge', 'post_inhibition_charge',
               'receptive_fields', 'weight_changes'}
    for r in run['live']:
        assert required <= r.keys()
        assert len(r['receptive_fields']) == N_OUT
        assert all(len(rf) == N_PIX for rf in r['receptive_fields'].values())
        assert len(r['pre_inhibition_charge']) == 8   # presentation_steps used above
        assert len(r['post_inhibition_charge']) == 8


def test_presentation_ids_strictly_increase_across_the_live_pass():
    run = run_diagnostic(seed=1, cycles=3, presentation_steps=6)
    ids = [r['presentation_id'] for r in run['live']]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_latency_margin_is_none_when_no_second_distinct_responder():
    """A presentation with 0 or 1 distinct L2E identity firing must report
    latency_margin_to_second as None, never a bogus number."""
    run = run_diagnostic(seed=1, cycles=3, presentation_steps=8)
    for r in run['live']:
        distinct = {nid for _t, nid in r['all_l2e_spikes']}
        if len(distinct) < 2:
            assert r['latency_margin_to_second'] is None
        else:
            assert r['latency_margin_to_second'] is not None
            assert r['latency_margin_to_second'] >= 0


# --------------------------------------------------------------------- report
def test_summary_report_structure_and_sanity():
    run = run_diagnostic(seed=2, cycles=8, presentation_steps=10)
    s = summarize(run)
    assert set(s['per_pattern'].keys()) == set(CYCLE_ORDER)
    for p, pp in s['per_pattern'].items():
        assert 0.0 <= pp['consistency'] <= 1.0
        assert 0.0 <= pp['ambiguity_rate'] <= 1.0
        assert 0.0 <= pp['no_response_rate'] <= 1.0
        assert pp['n_presentations'] == 8

    assert 0 <= s['distinct_owners'] <= 4
    all_l2e = {f'L2E{j}' for j in range(N_OUT)}
    assert set(s['silent_cells']) <= all_l2e
    assert set(s['recruitable_cells']) <= all_l2e
    assert set(s['silent_cells']).isdisjoint(s['recruitable_cells'])
    assert set(s['forgetting'].keys()) == set(CYCLE_ORDER)
    assert s['l2i_activity']['total'] >= 0
    assert s['l1i_all_nine_sync_rate'] is None or 0.0 <= s['l1i_all_nine_sync_rate'] <= 1.0
    assert isinstance(s['frozen_replay_zero_weight_drift'], bool)
    assert s['frozen_replay_zero_weight_drift'] is True
    assert set(s['frozen_first_responder_consistency'].keys()) == set(CYCLE_ORDER)


def test_collisions_and_distinct_owners_are_consistent():
    run = run_diagnostic(seed=3, cycles=8, presentation_steps=10)
    s = summarize(run)
    owners = [pp['modal_owner'] for pp in s['per_pattern'].values() if pp['modal_owner']]
    # Every collision key must actually be a repeated owner across >=2 patterns.
    for owner, patterns in s['collisions'].items():
        assert len(patterns) >= 2
        assert owners.count(owner) == len(patterns)
    assert s['distinct_owners'] == len(set(owners))


# ----------------------------------------------------------- L1I lockstep finding
def test_l1i_all_nine_sync_rate_matches_phase1_audit_finding():
    """The Phase 1 audit found all 9 L1I units share one literal weight vector
    and always fire in lockstep. This diagnostic should empirically confirm
    that (rate == 1.0, or None if L1I never fired in this short run)."""
    run = run_diagnostic(seed=1, cycles=6, presentation_steps=15)
    s = summarize(run)
    if s['l1i_all_nine_sync_rate'] is not None:
        assert s['l1i_all_nine_sync_rate'] == 1.0


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
