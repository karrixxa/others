"""Focused regression tests for Phase 19A's corrected per-input-column
prediction scaffold.

The feature is default-off and must leave the existing network behavior
unchanged. When enabled, it adds exactly nine prediction neurons P0..P8,
an 8x9 stored L2E->P decoder matrix, and a fixed local P_i->L1E_i replay
path with delayed queued delivery only.
"""

from __future__ import annotations

import copy

from backend.simulation import (
    N_OUT,
    N_PIX,
    PRED_CONTROL_DISABLED,
    PRED_CONTROL_SHUFFLED,
    SimulationEngine,
)
from backend.presets import DASHBOARD_PRESET


def _make(**overrides):
    return SimulationEngine(seed=1, **{**DASHBOARD_PRESET, **overrides})


def _spike_snapshot(engine):
    return dict(engine.spiked)


def _l1e_spikes(engine):
    return [bool(engine.spiked[f'L1E{i}']) for i in range(N_PIX)]


def _stored_decoder(engine):
    return copy.deepcopy(engine.dynamic_state()['prediction']['stored_decoder'])


def _legacy_weight_subset(weights):
    return {k: v for k, v in weights.items() if not (k.startswith('decoder') or k.startswith('pred'))}


def test_prediction_flag_off_matches_legacy_baseline():
    a = SimulationEngine(seed=3, **DASHBOARD_PRESET)
    b = SimulationEngine(seed=3, **{**DASHBOARD_PRESET, 'prediction_excitatory_enabled': False})
    for _ in range(40):
        da = a.step()
        db = b.step()
        assert da['winner'] == db['winner']
        assert da['causal_story']['l1i_first_t'] == db['causal_story']['l1i_first_t']
        assert da['causal_story']['l2i_first_t'] == db['causal_story']['l2i_first_t']
        assert _spike_snapshot(a) == _spike_snapshot(b)
    assert a._all_weights() == b._all_weights()
    assert a._all_confidence() == b._all_confidence()


def test_corrected_topology_contains_exactly_nine_prediction_neurons():
    e = _make(prediction_excitatory_enabled=True)
    p_ids = [n['id'] for n in e.dynamic_state()['neurons'] if n['id'].startswith('P')]
    assert p_ids == [f'P{i}' for i in range(N_PIX)]


def test_every_l2e_connects_to_every_prediction_column():
    e = _make(prediction_excitatory_enabled=True)
    topo = e.topology()
    dec = [s for s in topo['synapses'] if s['kind'] == 'decoder']
    assert len(dec) == N_OUT * N_PIX
    assert set((s['source'], s['target']) for s in dec) == {
        (f'L2E{j}', f'P{i}') for j in range(N_OUT) for i in range(N_PIX)
    }


def test_prediction_replay_is_strictly_local_to_matching_l1e():
    e = _make(prediction_excitatory_enabled=True)
    topo = e.topology()
    replay = [s for s in topo['synapses'] if s['kind'] == 'prediction_replay']
    assert len(replay) == N_PIX
    assert set((s['source'], s['target']) for s in replay) == {
        (f'P{i}', f'L1E{i}') for i in range(N_PIX)
    }


def test_no_prediction_neuron_connects_to_l1i():
    e = _make(prediction_excitatory_enabled=True)
    topo = e.topology()
    assert not [s for s in topo['synapses']
                if s['source'].startswith('P') and s['target'].startswith('L1I')]


def test_l2e_activity_cannot_affect_prediction_in_the_same_step():
    e = _make(prediction_excitatory_enabled=True)
    e.clear_input()
    e.set_prediction_decoder_weight(0, 0, e.prediction_weight_cap)
    e.stimulate('L2E0', magnitude=e.l2.excitatory_neurons[0].threshold)
    e.step()
    assert e.spiked['L2E0'] is True
    assert e.spiked['P0'] is False
    pred = e.dynamic_state()['prediction']
    assert any(rec['source'] == 'L2E0' for rec in pred['pending']['decoder'])
    e.step()
    assert e.spiked['P0'] is True


def test_prediction_spike_cannot_affect_l1e_in_the_same_step():
    e = _make(prediction_excitatory_enabled=True)
    e.clear_input()
    e.stimulate('P0', magnitude=e.neurons['P0'].threshold)
    e.step()
    assert e.spiked['P0'] is True
    assert e.spiked['L1E0'] is False
    e.step()
    assert e.spiked['L1E0'] is True


def test_replay_reaches_only_the_matching_l1e_column():
    e = _make(prediction_excitatory_enabled=True)
    e.clear_input()
    e.stimulate('P3', magnitude=e.neurons['P3'].threshold)
    e.step()
    e.step()
    spikes = _l1e_spikes(e)
    assert spikes[3] is True
    assert sum(spikes) == 1


def test_frozen_replay_does_not_mutate_weights_confidence_or_specialization_state():
    e = _make(prediction_excitatory_enabled=True)
    e.set_prediction_decoder_weight(0, 4, e.prediction_weight_cap)
    w_before = e._all_weights()
    c_before = e._all_confidence()
    counts_before = copy.deepcopy(e._neuron_first_responder_counts)
    history_before = copy.deepcopy(e._pattern_first_responder_log)
    e._set_plasticity_frozen(True)
    e.clear_input()
    e.stimulate('P4', magnitude=e.neurons['P4'].threshold)
    e.step()
    e.step()
    assert e._all_weights() == w_before
    assert e._all_confidence() == c_before
    assert e._neuron_first_responder_counts == counts_before
    assert e._pattern_first_responder_log == history_before


def test_decoder_controls_do_not_modify_the_stored_matrix():
    e = _make(prediction_excitatory_enabled=True)
    e.set_prediction_decoder_weight(0, 0, e.prediction_weight_cap)
    stored = _stored_decoder(e)
    e.set_prediction_decoder_control(PRED_CONTROL_DISABLED)
    e.clear_input()
    e.stimulate('L2E0', magnitude=e.l2.excitatory_neurons[0].threshold)
    e.step()
    assert _stored_decoder(e) == stored
    dyn = e.dynamic_state()['prediction']
    assert dyn['decoder_control'] == PRED_CONTROL_DISABLED
    assert all(v == 0.0 for v in dyn['effective_decoder']['L2E0'])

    e.set_prediction_decoder_control(PRED_CONTROL_SHUFFLED)
    e.step()
    assert _stored_decoder(e) == stored
    assert e.dynamic_state()['prediction']['decoder_control'] == PRED_CONTROL_SHUFFLED


def test_existing_l2i_and_l1i_causal_behavior_remains_unchanged_when_prediction_is_inert():
    off = _make()
    on = _make(prediction_excitatory_enabled=True)
    for _ in range(60):
        doff = off.step()
        don = on.step()
        assert doff['winner'] == don['winner']
        assert doff['causal_story']['l1i_first_t'] == don['causal_story']['l1i_first_t']
        assert doff['causal_story']['l2i_first_t'] == don['causal_story']['l2i_first_t']
        for nid in [f'L2E{j}' for j in range(N_OUT)] + ['L2I'] + [f'L1I{i}' for i in range(N_PIX)]:
            assert off.spiked[nid] == on.spiked[nid]
    assert _legacy_weight_subset(off._all_weights()) == _legacy_weight_subset(on._all_weights())
    assert off._all_confidence() == on._all_confidence()


if __name__ == '__main__':
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
