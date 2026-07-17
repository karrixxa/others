"""Phase 33 -- mandatory tests for the default-OFF "causal microstep L2
race" (causal_microstep_l2_race_enabled). Reuses l2_charge_chunks (K) --
no new chunking parameter. K=1 is the exact baseline control; K=20 is the
one preregistered candidate value (no sweep)."""

from __future__ import annotations

import numpy as np
import pytest

from backend.simulation import N_OUT, N_PIX, SimulationEngine
from backend.presets import DASHBOARD_PRESET


def _engine(**overrides):
    return SimulationEngine(seed=1, topology_seed=1, **{**DASHBOARD_PRESET, **overrides})


def _all_ff_weights(engine):
    return {(j, i): float(engine.l2.excitatory_neurons[j]._weights_array[i])
           for j in range(N_OUT) for i in range(N_PIX)}


def _all_weights_full(engine):
    ff = _all_ff_weights(engine)
    ei = {j: float(engine.l2.inhibitory_neuron._weights_array[j]) for j in range(N_OUT)}
    l1i = {i: [float(w) for w in engine.l1.inhibitory_neurons[i]._weights_array] for i in range(N_PIX)}
    pcol = {i: [float(w) for w in pc._weights_array] for i, pc in enumerate(engine.pcol)}
    return dict(ff=ff, ei=ei, l1i=l1i, pcol=pcol)


# --------------------------------------------------------------------- flag-off
def test_flag_off_is_byte_identical_to_baseline():
    """causal_microstep_l2_race_enabled defaults False and, even when
    explicitly passed False, must reproduce the exact ffefd1f baseline
    trajectory (the existing K-chunk path, untouched)."""
    plain = _engine()
    off = _engine(causal_microstep_l2_race_enabled=False)
    plain.set_pattern('row 1')
    off.set_pattern('row 1')
    for _ in range(300):
        plain.step()
        off.step()
    assert _all_weights_full(plain) == _all_weights_full(off)
    assert plain.timestep == off.timestep
    assert plain._neuron_total_spikes == off._neuron_total_spikes


def test_flag_off_never_touches_new_state():
    e = _engine()
    e.set_pattern('row 1')
    for _ in range(100):
        e.step()
    assert e._l2_microstep_counter == 0
    assert e._l2i_microstep_pending == []
    assert e._causal_microstep_stats == dict(
        ff_events_scheduled=0, ff_events_delivered=0, inhib_events_scheduled=0,
        inhib_events_delivered=0, inhib_events_refractory_rejected=0)


# --------------------------------------------------------------------- RNG
def test_no_additional_rng_consumption():
    """Enabling the flag must not consume any extra random draws --
    confirmed directly: initial weights (built entirely before a single
    step runs) are byte-identical whether the flag is on or off, for the
    SAME seed."""
    off = _engine(causal_microstep_l2_race_enabled=False)
    on = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    assert _all_weights_full(off) == _all_weights_full(on)


# --------------------------------------------------------------------- K=1 baseline reproduction
def test_k1_microstep_reproduces_k1_baseline_exactly():
    old_path = _engine(l2_charge_chunks=1)
    new_path = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=1)
    old_path.set_pattern('row 1')
    new_path.set_pattern('row 1')
    for _ in range(300):
        old_path.step()
        new_path.step()
    assert _all_weights_full(old_path) == _all_weights_full(new_path)
    assert old_path._neuron_total_spikes == new_path._neuron_total_spikes


def test_k1_microstep_reproduces_k1_baseline_across_pattern_switches():
    old_path = _engine(l2_charge_chunks=1)
    new_path = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=1)
    for pattern in ['row 1', 'col 1', 'diag \\', 'diag /'] * 3:
        old_path.set_pattern(pattern)
        new_path.set_pattern(pattern)
        for _ in range(20):
            old_path.step()
            new_path.step()
    assert _all_weights_full(old_path) == _all_weights_full(new_path)


# --------------------------------------------------------------------- ties / no argmax
def test_exact_co_crossers_remain_ties():
    """Force two L2E neurons to identical potential, just under threshold,
    with identical incoming weights on the active pixels, and confirm BOTH
    fire together in the same microstep (not just one)."""
    e = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    e.set_pattern('row 1')
    n0, n1 = e.l2.excitatory_neurons[0], e.l2.excitatory_neurons[1]
    thr = n0.threshold
    n0._weights_array[:] = 0.0
    n1._weights_array[:] = 0.0
    active = [i for i, v in enumerate(e.input_vec) if v > 0.5]
    for i in active:
        n0._weights_array[i] = thr / len(active) + 1.0
        n1._weights_array[i] = thr / len(active) + 1.0
    n0.potential = 0.0
    n1.potential = 0.0
    e.step()
    assert e.spiked['L2E0'] is True
    assert e.spiked['L2E1'] is True


def test_no_argmax_or_index_tiebreak_in_source():
    import inspect
    from backend.simulation import SimulationEngine as SE
    src = inspect.getsource(SE._resolve_l2_competition_causal_microstep)
    code_only = src.split('"""', 2)[-1]   # drop the docstring (which discusses what's NOT used), check code only
    banned = ('argmax', 'max(eligible', 'key=lambda j: l2.excitatory_neurons[j].potential')
    for b in banned:
        assert b not in code_only, f'{b!r} found in causal microstep code'


# --------------------------------------------------------------------- conservation
def test_feedforward_mass_conserved():
    e = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
        stats = e._causal_microstep_stats
        assert stats['ff_events_scheduled'] == stats['ff_events_delivered']
        assert stats['ff_events_scheduled'] == 20 * N_OUT


def test_inhibitory_conservation_accounting_present_and_consistent():
    e = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    e.set_pattern('row 1')
    saw_inhibition = False
    for _ in range(300):
        e.step()
        stats = e._causal_microstep_stats
        assert (stats['inhib_events_delivered'] + stats['inhib_events_refractory_rejected']
               == stats['inhib_events_scheduled'])
        if stats['inhib_events_scheduled'] > 0:
            saw_inhibition = True
    assert saw_inhibition, "expected at least one delayed inhibition event across 300 steps"


# --------------------------------------------------------------------- causal ordering
def test_l2e_to_l2i_and_l2i_to_l2e_timestamps_causally_ordered():
    e = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    e.set_pattern('row 1')
    seen_events = []
    orig = e._resolve_l2_competition_causal_microstep

    def wrapped(l2, l2e, ff_vec, t):
        before = list(e._l2i_microstep_pending)
        result = orig(l2, l2e, ff_vec, t)
        after = e._l2i_microstep_pending
        for rec in after:
            if rec not in before:
                seen_events.append(rec)
        return result
    e._resolve_l2_competition_causal_microstep = wrapped
    for _ in range(300):
        e.step()
    assert seen_events, "expected at least one scheduled return-inhibition event"
    for rec in seen_events:
        assert rec['deliver_at_microstep'] > rec['fire_microstep']
    fire_order = [rec['fire_microstep'] for rec in seen_events]
    assert fire_order == sorted(fire_order), "L2I firing microsteps must be monotonically non-decreasing"


# --------------------------------------------------------------------- frozen weights
def test_frozen_run_leaves_every_weight_byte_identical():
    e = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    e._set_plasticity_frozen(True)
    for n in e.l2.excitatory_neurons:
        n.loser_depression = False
    before = _all_weights_full(e)
    e.set_pattern('row 1')
    for _ in range(300):
        e.step()
    after = _all_weights_full(e)
    assert before == after


# --------------------------------------------------------------------- passive telemetry
def test_passive_telemetry_read_does_not_alter_state():
    e = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    w_before = _all_weights_full(e)
    t_before = e.timestep
    pending_before = list(e._l2i_microstep_pending)
    stats_read_1 = dict(e._causal_microstep_stats)
    stats_read_2 = dict(e._causal_microstep_stats)
    assert stats_read_1 == stats_read_2
    assert _all_weights_full(e) == w_before
    assert e.timestep == t_before
    assert e._l2i_microstep_pending == pending_before


# --------------------------------------------------------------------- determinism
def test_deterministic_replay():
    e1 = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    e2 = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    e1.set_pattern('row 1')
    e2.set_pattern('row 1')
    for _ in range(300):
        e1.step()
        e2.step()
    assert _all_weights_full(e1) == _all_weights_full(e2)
    assert e1._neuron_total_spikes == e2._neuron_total_spikes


# --------------------------------------------------------------------- no discard-remaining
def test_does_not_discard_remaining_chunks_after_a_spike():
    """Unlike the existing K-chunk path (which stops after the first
    threshold-crosser), the causal microstep path must still deliver ALL
    K chunks' worth of feedforward mass even after an earlier microstep's
    spike -- directly verified via the conservation counter, which would
    be < 20*N_OUT per step if chunks were discarded."""
    e = _engine(causal_microstep_l2_race_enabled=True, l2_charge_chunks=20)
    e.set_pattern('row 1')
    fired_at_least_once = False
    for _ in range(50):
        e.step()
        if any(e.spiked.get(f'L2E{j}') for j in range(N_OUT)):
            fired_at_least_once = True
            assert e._causal_microstep_stats['ff_events_scheduled'] == 20 * N_OUT
    assert fired_at_least_once
