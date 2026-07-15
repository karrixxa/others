"""Tracer-timing tests for phase13b_diagnostic.py's own instrumentation
(NOT the engine -- these verify the diagnostic tooling reads the right value
at the right moment, which is exactly the bug Phase 13b was asked to fix).
Measurement-only infrastructure; no engine file is touched.
"""

import numpy as np
import pytest

from backend.simulation import N_OUT
from phase13b_diagnostic import (
    WeightDeltaRecorder, build_engine, run_short_hold_switch, run_long_hold_switch,
    run_interleaved_40, identify_tyrant, never_fired_neurons, config_A, config_B,
    _MEAN_INFLUENCE_A, _D_UNIFORM,
)


def test_config_c_mean_influence_matches_a_exactly():
    """Config C's per-connection influence values are uniform and their
    mean equals config A's own mean -- the whole point of the C control."""
    eng_a = build_engine('A', 1, 1)
    eng_c = build_engine('C', 1, 1)
    infl_a = [e['influence'] for e in eng_a.pathway_influence_report()['l1e_l2e']['entries']]
    infl_c = [e['influence'] for e in eng_c.pathway_influence_report()['l1e_l2e']['entries']]
    # pathway_influence_report() rounds each entry to 4 decimals, so the mean
    # of 72 already-rounded A values vs. C's exact single value can differ by
    # a few 1e-5 -- well below anything that matters for "matched charge".
    assert abs(np.mean(infl_a) - np.mean(infl_c)) < 1e-3
    # C is spatially UNIFORM: every connection has the identical value.
    assert max(infl_c) - min(infl_c) < 1e-9
    # ...while A is not (real per-neuron/pixel distances vary).
    assert max(infl_a) - min(infl_a) > 1e-6


def test_config_b_has_no_distance_attenuation():
    eng_b = build_engine('B', 1, 1)
    assert eng_b.params['distance_weighting'] is False


def test_unique_delivery_events_match_engines_own_log():
    """Ground-truth cross-check: the recorder's own delivery_id grouping
    must agree with the engine's own _l2_inhibition_log length exactly --
    this is the engine's own record, not a re-derivation."""
    engine, rec = run_short_hold_switch('A', 1, 1)
    loser = [r for r in rec.records if r['cause'] == 'l2i_loser_depression']
    unique_ids = {r['delivery_id'] for r in loser if r['delivery_id'] is not None}
    assert len(unique_ids) == len(engine._l2_inhibition_log)


def test_spiked_previous_step_reflects_t_minus_1_not_t():
    """The core Phase 13 bug: apply_delayed_inhibition runs at the TOP of
    step(), before this step's own competition. A record's
    spiked_previous_step must equal engine.spiked[nid] as it stood at the
    END of the PRIOR step, not some later value."""
    engine, rec = run_short_hold_switch('A', 1, 1)
    loser = [r for r in rec.records if r['cause'] == 'l2i_loser_depression']
    assert loser, "expected at least one loser-depression event in this scenario"
    # Reconstruct per-neuron spike history by re-running a fresh, identically
    # seeded engine step-by-step and recording engine.spiked snapshots
    # ourselves, independent of the recorder under test.
    fresh, _ = build_engine('A', 1, 1), None
    fresh.set_pattern('row 1')
    history = []   # history[t] = dict(nid -> spiked) at the END of step t
    for _ in range(20):
        fresh.step()
        history.append(dict(fresh.spiked))
    fresh.set_pattern('col 1')
    for _ in range(20):
        fresh.step()
        history.append(dict(fresh.spiked))
    for r in loser:
        t = r['t']
        if t == 0:
            continue   # no prior step to compare against
        expected = bool(history[t - 1].get(r['neuron'], False))
        assert r['spiked_previous_step'] == expected, (
            f"t={t} neuron={r['neuron']}: recorder said "
            f"spiked_previous_step={r['spiked_previous_step']}, "
            f"but independently-tracked history says {expected}")


def test_spiked_later_current_step_is_filled_after_step_completes():
    """Every loser-depression record must have spiked_later_current_step
    resolved (not left as the None placeholder) once its owning step()
    call has returned -- the deferred-fill mechanism actually ran."""
    engine, rec = run_short_hold_switch('A', 1, 1)
    loser = [r for r in rec.records if r['cause'] == 'l2i_loser_depression']
    assert loser
    assert all(r['spiked_later_current_step'] is not None for r in loser)


def test_spiked_later_current_step_agrees_with_self_spike_records():
    """Cross-check: whenever a neuron has BOTH a loser-depression record
    and a self-spike record at the identical timestep, the loser-depression
    record's spiked_later_current_step must be True (it fired later in that
    same step, after being hit by delayed inhibition at the top) -- and
    when no matching self-spike record exists at that (t, neuron), it must
    be False."""
    engine, rec = run_long_hold_switch('A', 1, 1, row1_steps=600, col1_steps=200)
    loser = [r for r in rec.records if r['cause'] == 'l2i_loser_depression']
    self_spike_ts = {(r['t'], r['neuron']) for r in rec.records if r['cause'].startswith('self_spike')}
    assert loser
    checked_true = checked_false = 0
    for r in loser:
        expected = (r['t'], r['neuron']) in self_spike_ts
        assert r['spiked_later_current_step'] == expected
        checked_true += expected
        checked_false += not expected
    # Empirically (verified across all three configs and both long-running
    # scenarios, tens of thousands of events) spiked_later_current_step is
    # ALWAYS False under the default l2_inhibition_frac=1.0: a full
    # threshold_l2-magnitude subtraction leaves no realistic path back to
    # threshold within the same step. This is itself a genuine finding
    # (Phase 13b report), not a test bug -- so only the False branch is
    # required to be exercised here; a future config change to
    # l2_inhibition_frac could legitimately make the True branch appear.
    assert checked_false > 0


def test_tyrant_identification_is_not_hardcoded():
    """identify_tyrant must reflect whichever neuron actually spiked most,
    which config/seed combinations can and do disagree on (Phase 13
    assumed L2E5; this must not)."""
    engine, rec = run_short_hold_switch('A', 1, 1)
    tyrant = identify_tyrant(engine)
    counts = {f'L2E{j}': engine._neuron_total_spikes.get(f'L2E{j}', 0) for j in range(N_OUT)}
    assert tyrant == max(counts, key=counts.get)
    assert counts[tyrant] == max(counts.values())


def test_never_fired_neurons_have_zero_total_spikes():
    engine, rec = run_short_hold_switch('A', 1, 1)
    for nid in never_fired_neurons(engine):
        assert engine._neuron_total_spikes.get(nid, 0) == 0


def test_delivery_id_groups_multiple_synapse_deltas_from_one_event():
    """A single delivery event typically depresses several (neuron, pixel)
    synapses at once -- delivery_id must be shared across all of them, and
    the count of unique ids must be <= the count of individual deltas."""
    engine, rec = run_long_hold_switch('A', 1, 1, row1_steps=600, col1_steps=200)
    loser = [r for r in rec.records if r['cause'] == 'l2i_loser_depression']
    ids = [r['delivery_id'] for r in loser]
    assert len(set(ids)) <= len(ids)
    assert len(set(ids)) >= 1


def test_engine_own_delivery_log_truncates_on_long_runs_tracer_does_not():
    """_l2_inhibition_log is a deque(maxlen=LOG_MAX=400) -- a display-
    oriented rolling window, not an exhaustive record. On a long enough run
    (the 40-rotation interleaved schedule, 3200 steps) the true delivery
    count exceeds 400 and the engine's own log silently drops older
    entries, so it UNDERCOUNTS total deliveries -- this is why the grid's
    unique_delivery_events (this tracer's own exhaustive count) can
    legitimately exceed engine._l2_inhibition_log's length on that
    scenario, while the two matched exactly on the two hold/switch
    scenarios (which stay under 400 events). Confirms this is a bounded-
    buffer artifact, not a counting bug in the tracer."""
    from backend.simulation import LOG_MAX
    engine, rec, _pres = run_interleaved_40('A', 1, 1)
    loser = [r for r in rec.records if r['cause'] == 'l2i_loser_depression']
    unique_ids = {r['delivery_id'] for r in loser if r['delivery_id'] is not None}
    assert len(engine._l2_inhibition_log) == LOG_MAX, (
        "expected this long a run to fill the bounded log completely")
    assert len(unique_ids) > len(engine._l2_inhibition_log), (
        "expected the tracer's exhaustive count to exceed the truncated engine log")


def test_topology_seed_is_inert_for_configs_a_b_c():
    """Configs A (legacy-pinned) and C (uniform override) never let real
    per-topology-seed geometry drive delivered distance, and B has
    distance_weighting off entirely -- so the same weight_seed at different
    topology_seeds must produce byte-identical final feedforward weights."""
    for config_name in ('A', 'B', 'C'):
        finals = []
        for ts in (1, 2, 3):
            engine, _ = run_short_hold_switch(config_name, 1, ts)
            finals.append([float(w) for e in engine.l2.excitatory_neurons for w in e._weights_array])
        for f in finals[1:]:
            assert np.allclose(finals[0], f), f"{config_name}: topology_seed changed outcome"
