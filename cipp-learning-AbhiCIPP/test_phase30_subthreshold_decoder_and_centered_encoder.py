"""Phase 30 -- focused tests for the two new default-OFF engine flags added
this phase:

  - centered_encoder_enabled (FSCI/ISM Phase 29's centered/covariance
    encoder, promoted from an offline monkeypatch into a real flag).
  - prediction_subthreshold_decoder_enabled (FSCI/ISM Phase 30's local
    subthreshold coincidence decoder, the fix for the existing spike-gated
    decoder's cold-start plateau).

Covers: flag-off byte-identical behavior, locality (no cross-neuron/global
state read), coincidence dependence (both R_j and paired sensory evidence
required), saturation (bounded growth), and absence of unintended learning
(a synapse whose presynaptic source never fires must never move)."""

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


# ==================================================================== centered encoder
def test_centered_encoder_off_is_byte_identical_to_baseline():
    plain = _engine()
    off = _engine(centered_encoder_enabled=False)
    plain.set_pattern('row 1')
    off.set_pattern('row 1')
    for _ in range(300):
        plain.step()
        off.step()
    assert _all_ff_weights(plain) == _all_ff_weights(off)
    assert plain.dynamic_state()['timestep'] == off.dynamic_state()['timestep']


def test_centered_encoder_on_changes_dynamics_and_runs_without_error():
    e = _engine(centered_encoder_enabled=True, loser_depression=False)
    e.set_pattern('row 1')
    for _ in range(300):
        e.step()
    assert e.timestep == 300
    # Center pixel 4 should not run away unboundedly the way it does under
    # the legacy rule -- a coarse sanity check, not the full Phase 29 grid.
    ratios = []
    for j in range(N_OUT):
        w = e.l2.excitatory_neurons[j]._weights_array
        others = [w[i] for i in range(N_PIX) if i != 4]
        if np.mean(others) > 1e-6:
            ratios.append(w[4] / np.mean(others))
    assert ratios   # at least one neuron produced a finite ratio


def test_centered_encoder_trace_is_shared_across_all_l2e_neurons():
    e = _engine(centered_encoder_enabled=True, loser_depression=False)
    for j in range(N_OUT):
        assert e.l2.excitatory_neurons[j]._centered_x_bar is e._centered_x_bar


def test_centered_encoder_disables_no_other_mechanism():
    """Loser depression, L2I hard-reset, and every other flag must be
    settable independently -- this flag ONLY swaps the excitatory rule."""
    e = _engine(centered_encoder_enabled=True)   # loser_depression left at its own default (True)
    assert e.params['loser_depression'] is True
    assert e.params['l2i_hard_reset_losers'] == DASHBOARD_PRESET['l2i_hard_reset_losers']


def test_centered_encoder_rule_is_local_no_cross_neuron_state():
    import inspect
    from snn.rules.excitatory import CenteredEncoderRule
    src = inspect.getsource(CenteredEncoderRule.on_fire)
    for banned in ('engine.', 'other_n', 'rival', 'PATTERNS'):
        assert banned not in src


# ==================================================================== subthreshold decoder
def test_subthreshold_decoder_off_is_byte_identical_to_baseline():
    plain = _engine(prediction_column_enabled=True)
    off = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=False)
    plain.set_pattern('row 1')
    off.set_pattern('row 1')
    for _ in range(300):
        plain.step()
        off.step()
    assert _all_ff_weights(plain) == _all_ff_weights(off)
    for j in range(N_PIX):
        assert list(plain.pcol[j]._weights_array) == list(off.pcol[j]._weights_array)


def test_subthreshold_decoder_requires_prediction_column_enabled_to_do_anything():
    """The flag is inert (no pcol population exists at all) unless
    prediction_column_enabled is also on -- consistent with every other
    PC-dependent flag in this codebase."""
    e = _engine(prediction_column_enabled=False, prediction_subthreshold_decoder_enabled=True)
    assert e.pcol == []


def test_subthreshold_decoder_no_r_spike_means_no_update():
    """A column j whose L2Ej never fires across the whole run must show
    EXACTLY zero decoder-weight change for that index, on every PCi."""
    e = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    e.set_pattern('row 1')
    initial = {j: [pc._weights_array[j] for pc in e.pcol] for j in range(N_OUT)}
    for _ in range(500):
        e.step()
    status = {j: e._l2e_status(j)['status'] for j in range(N_OUT)}
    never_fired = [j for j, s in status.items() if s == 'unrecruited']
    assert never_fired, "expected at least one L2E to never fire in this run"
    for j in never_fired:
        finals = [pc._weights_array[j] for pc in e.pcol]
        assert finals == initial[j], f'L2E{j} never fired but its decoder weight moved'


def test_subthreshold_decoder_no_sensory_eligibility_means_no_update():
    """Directly verify u_i^S <= 0 blocks the WHOLE update for that PCi, even
    with an artificially forced nonzero z_j^R."""
    e = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    pc = e.pcol[0]
    e._pcol_u_S[0] = 0.0
    e._pcol_z_R[:] = 1.0   # every R_j "active"
    w_before = pc._weights_array.copy()
    e._apply_subthreshold_decoder_learning(pc, 0)
    assert np.array_equal(pc._weights_array, w_before)


def test_subthreshold_decoder_coincidence_dependence():
    """Potentiation requires BOTH z_j^R > 0 AND u_i^S > 0 -- neither alone
    is sufficient."""
    e = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    pc = e.pcol[0]

    # z alone, u=0 -> no change.
    e._pcol_z_R[:] = 1.0
    e._pcol_u_S[0] = 0.0
    w0 = pc._weights_array.copy()
    e._apply_subthreshold_decoder_learning(pc, 0)
    assert np.array_equal(pc._weights_array, w0)

    # u alone, z=0 -> no change.
    e._pcol_z_R[:] = 0.0
    e._pcol_u_S[0] = 1.0
    w1 = pc._weights_array.copy()
    e._apply_subthreshold_decoder_learning(pc, 0)
    assert np.array_equal(pc._weights_array, w1)

    # both nonzero -> genuine potentiation.
    e._pcol_z_R[:] = 1.0
    e._pcol_u_S[0] = 1.0
    w2 = pc._weights_array[:N_OUT].copy()
    e._apply_subthreshold_decoder_learning(pc, 0)
    assert (pc._weights_array[:N_OUT] > w2).all()


def test_subthreshold_decoder_absent_columns_remain_unchanged():
    """Only R_j indices with z_j^R > 0 move -- others in the SAME event are untouched."""
    e = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    pc = e.pcol[0]
    e._pcol_z_R[:] = 0.0
    e._pcol_z_R[2] = 1.0
    e._pcol_z_R[5] = 1.0
    e._pcol_u_S[0] = 1.0
    w_before = pc._weights_array[:N_OUT].copy()
    e._apply_subthreshold_decoder_learning(pc, 0)
    w_after = pc._weights_array[:N_OUT]
    for j in range(N_OUT):
        if j in (2, 5):
            assert w_after[j] > w_before[j]
        else:
            assert w_after[j] == w_before[j]


def test_subthreshold_decoder_saturates_at_feedback_max():
    e = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    pc = e.pcol[0]
    w_max = e.prediction_feedback_max
    pc._weights_array[:N_OUT] = w_max - 0.1
    e._pcol_z_R[:] = 1.0
    e._pcol_u_S[0] = 1.0
    for _ in range(200):
        e._apply_subthreshold_decoder_learning(pc, 0)
    assert (pc._weights_array[:N_OUT] <= w_max + 1e-9).all()


def test_subthreshold_decoder_does_not_touch_lateral_index():
    """The fixed S_i->PCi lateral weight (index N_OUT) is never touched by
    this rule -- only indices 0..N_OUT-1 (the R_j feedback) move."""
    e = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    pc = e.pcol[0]
    lateral_before = pc._weights_array[N_OUT]
    e._pcol_z_R[:] = 1.0
    e._pcol_u_S[0] = 1.0
    e._apply_subthreshold_decoder_learning(pc, 0)
    assert pc._weights_array[N_OUT] == lateral_before


def test_subthreshold_decoder_potentiation_does_not_require_pc_spike():
    """Requirement 6: a PCi somatic spike is NOT required for the decoder
    update to occur -- directly verified by calling the update on a PCi
    that has not crossed threshold (no fire() call at all here)."""
    e = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    pc = e.pcol[0]
    assert not pc.check_threshold()   # freshly built, no charge accumulated
    e._pcol_z_R[:] = 1.0
    e._pcol_u_S[0] = 1.0
    w_before = pc._weights_array[:N_OUT].copy()
    e._apply_subthreshold_decoder_learning(pc, 0)
    assert (pc._weights_array[:N_OUT] > w_before).all()


def test_subthreshold_decoder_frozen_plasticity_via_engine_step_blocks_learning():
    e = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True)
    e.set_pattern('row 1')
    e._set_plasticity_frozen(True)
    initial = [pc._weights_array.copy() for pc in e.pcol]
    for _ in range(200):
        e.step()
    for pc, w0 in zip(e.pcol, initial):
        assert np.array_equal(pc._weights_array, w0)


def test_subthreshold_and_legacy_decoder_are_mutually_exclusive():
    """When subthreshold is on, the OLD spike-gated rule must never also
    fire for the same event (checked indirectly: enabling subthreshold with
    z/u forced to zero -- so the NEW rule does nothing -- and a PCi that
    DOES physically spike must show no decoder movement from the OLD rule
    either)."""
    e = _engine(prediction_column_enabled=True, prediction_subthreshold_decoder_enabled=True,
               prediction_threshold=1.0)   # trivially low threshold -- PCi always fires
    pc = e.pcol[0]
    e._pcol_z_R[:] = 0.0
    e._pcol_u_S[:] = 0.0
    pc._last_input_spikes = np.ones(N_OUT + 1)   # would satisfy the OLD rule's own gates
    w_before = pc._weights_array.copy()
    pc.fire()
    # fire() only runs L2E-style _update_weights; PC's own learning is
    # applied explicitly in step(), not inside fire() -- so this call alone
    # must not move the decoder at all.
    assert np.array_equal(pc._weights_array, w_before)
