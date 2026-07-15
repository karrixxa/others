"""
Regression tests for Phase 20 (frozen reconstruction; adapted to the
corrected S_i/PCi/Ii local-coincidence architecture, july14-integration).
See Phase20_Frozen_Reconstruction_Report.md for the full measurement.

The original Phase 20 spec (cue one L2E/decoder, measure reconstruction
INTO L1E) was written against a superseded decoder->L1E-replay topology.
The corrected architecture has no such replay path by design (Pi->Ii is
inhibitory-only, never excitatory replay into Si) -- "the P grid itself is
the reconstructed pattern" (Phase18b's contract). These tests therefore
measure reconstruction directly at the PCi population when one L2E is cued
via an explicit experimental control (forced potential, never a software
pass-through), with plasticity frozen and external input removed.

Plain-script style:
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python test_phase20_frozen_reconstruction.py
"""

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS
from backend.presets import DASHBOARD_PRESET

CUE_STEPS = 5
OBSERVE_STEPS = 10


def _engine(seed=1):
    return SimulationEngine(seed=seed, prediction_column_enabled=True, **DASHBOARD_PRESET)


def _cue(e, cue_j, steps=CUE_STEPS + OBSERVE_STEPS):
    e._set_plasticity_frozen(True)
    e.input_vec = np.zeros(N_PIX)
    fired = np.zeros(N_PIX)
    for step_i in range(steps):
        if cue_j is not None and step_i < CUE_STEPS:
            e.l2.excitatory_neurons[cue_j].potential = e.l2.excitatory_neurons[cue_j].threshold + 10_000
        e.step()
        for i in range(N_PIX):
            if e.spiked.get(f'PC{i}'):
                fired[i] += 1
    return fired


def test_no_cue_produces_no_reconstruction():
    """With plasticity frozen, no external input, and no cue at all, PCi
    must never fire -- a clean negative-control baseline."""
    e = _engine()
    fired = _cue(e, cue_j=None)
    assert not fired.any(), f"PC fired with no cue at all: {fired}"
    print("PASS: no-cue control produces zero PC activity")


def test_frozen_plasticity_blocks_any_weight_change_during_cueing():
    e = _engine()
    e.set_pattern('row 1')
    for _ in range(500):
        e.step()
    w_before = [pc._weights_array.copy() for pc in e.pcol]
    _cue(e, cue_j=4)
    for i in range(N_PIX):
        assert np.array_equal(e.pcol[i]._weights_array, w_before[i]), \
            f"PC{i} weights changed during a frozen-plasticity cue -- freeze is not being honored"
    print("PASS: plasticity_frozen blocks all decoder weight changes during cueing")


def test_cueing_never_causes_false_l2e_activation_from_pc():
    """Isolates PC's OWN causal effect (not the cue's normal, expected L2I-
    competition side effects on other L2E from cueing L2Ej itself): forcing
    every PCi to fire directly must never change any L2E potential -- PC has
    zero output wiring in this phase (reproduces Phase 19's shadow-mode
    guarantee as an explicit Phase 20 check)."""
    e = _engine()
    e.set_pattern('row 1')
    for _ in range(500):
        e.step()
    _cue(e, cue_j=4)
    l2e_before = [n.potential for n in e.l2.excitatory_neurons]
    for pc in e.pcol:
        pc.potential = pc.threshold + 10_000
        if pc.check_threshold():
            pc.fire()
    l2e_after = [n.potential for n in e.l2.excitatory_neurons]
    assert l2e_before == l2e_after, "forcing every PC to fire must never change any L2E potential"
    print("PASS: forcing every PC to fire causes zero L2E potential change (no false L2E activation)")


def test_immature_decoder_does_not_reconstruct_from_a_single_cue():
    """HONEST NEGATIVE RESULT (see the Phase 20 report): after a realistic
    training budget (interleaved schedule, tens of cycles), R_j->PCi
    feedback weights remain far below the ~500 threshold needed for
    feedback-alone firing (they plateau around 50-65, see the report's 50k-
    step trajectory). Cueing the correct owner alone (no lateral input)
    must therefore NOT reconstruct the pattern at this training scale --
    this test documents the current, real limitation rather than asserting
    a reconstruction capability that has not been demonstrated."""
    e = _engine()
    e.set_pattern('row 1')
    for _ in range(3000):
        e.step()
    owner = int(np.argmax([e.pcol[4]._weights_array[j] for j in range(N_OUT)]))
    fired = _cue(e, cue_j=owner)
    assert not fired.any(), (
        f"expected NO reconstruction from an immature decoder (weights plateau well below "
        f"threshold at this training scale) -- got {fired}. If this now fires, decoder "
        f"weights have matured further than previously measured; update the report.")
    print(f"PASS (documents current limitation): cueing the mature-est owner (L2E{owner}) "
         f"alone does not yet reconstruct the pattern -- decoder weights have not matured "
         f"enough at this training scale (see Phase20_Frozen_Reconstruction_Report.md)")


def test_manually_matured_decoder_can_reconstruct_from_a_single_cue():
    """Positive control proving the CUEING MECHANISM ITSELF works correctly
    once a decoder is mature -- isolates "the cue/measurement harness is
    correct" from "realistic training reaches maturity" (which the
    preceding test shows it currently does not)."""
    e = _engine()
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()   # just enough for the network to settle; weights untouched below
    active = [i for i, v in enumerate(PATTERNS['row 1']) if v]
    for i in active:
        e.pcol[i]._weights_array[4] = e.prediction_feedback_max   # manually mature R4->PCi
    fired = _cue(e, cue_j=4)
    fired_set = set(np.nonzero(fired)[0].tolist())
    assert fired_set == set(active), \
        f"a manually-matured decoder should reconstruct exactly the active set {active}, got {fired_set}"
    print(f"PASS: a manually-matured decoder correctly reconstructs {active} from a single cue "
         f"(proves the cueing/measurement mechanism itself is correct)")


def test_reconstruction_center_vs_peripheral_reported_separately():
    e = _engine()
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    active = [i for i, v in enumerate(PATTERNS['row 1']) if v]
    for i in active:
        e.pcol[i]._weights_array[4] = e.prediction_feedback_max
    fired = _cue(e, cue_j=4)
    center_fired = bool(fired[4] > 0)
    peripheral = [i for i in active if i != 4]
    peripheral_fired = [i for i in peripheral if fired[i] > 0]
    assert center_fired, "center pixel should reconstruct (legitimately shared across all patterns)"
    assert set(peripheral_fired) == set(peripheral), \
        f"peripheral pixels {peripheral} should also reconstruct, not just center: got {peripheral_fired}"
    print(f"PASS: center ({center_fired}) and peripheral ({peripheral_fired}) reconstruction reported separately")


def test_persistence_no_runaway_after_cue_removed():
    """After the cue window ends, PCi's own potential must decay under the
    normal leak, not run away / stay latched forever."""
    e = _engine()
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    active = [i for i, v in enumerate(PATTERNS['row 1']) if v]
    for i in active:
        e.pcol[i]._weights_array[4] = e.prediction_feedback_max
    e._set_plasticity_frozen(True)
    e.input_vec = np.zeros(N_PIX)
    for step_i in range(CUE_STEPS):
        e.l2.excitatory_neurons[4].potential = e.l2.excitatory_neurons[4].threshold + 10_000
        e.step()
    # Cue removed -- run many more steps with no further cueing.
    for _ in range(200):
        e.step()
    for i in active:
        assert e.pcol[i].potential < e.pcol[i].threshold, \
            f"PC{i} potential did not decay after cue removal -- possible runaway"
    print("PASS: PC potential decays under the normal leak after the cue is removed (no runaway)")


def test_wrong_owner_cue_does_not_reconstruct_a_different_pattern():
    e = _engine()
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    row1_active = [i for i, v in enumerate(PATTERNS['row 1']) if v]
    for i in row1_active:
        e.pcol[i]._weights_array[4] = e.prediction_feedback_max   # R4 matured for row 1 only
    # Cue a DIFFERENT, never-trained source (R7) -- should reconstruct nothing.
    fired = _cue(e, cue_j=7)
    assert not fired.any(), f"an untrained R7 cue should not reconstruct anything, got {fired}"
    print("PASS: cueing an untrained source reconstructs nothing (no spurious generalization)")


def test_shuffled_decoder_breaks_correct_reconstruction():
    """Sanity check that reconstruction quality is a property of the
    LEARNED structure, not an artifact of the cueing mechanism: permuting
    which pixel each decoder row targets must break correct reconstruction."""
    e = _engine()
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    active = [i for i, v in enumerate(PATTERNS['row 1']) if v]
    for i in active:
        e.pcol[i]._weights_array[4] = e.prediction_feedback_max
    perm = list(np.roll(np.arange(N_PIX), 1))   # shift every column's decoder row by one
    rows = [pc._weights_array[:N_OUT].copy() for pc in e.pcol]
    for i, pc in enumerate(e.pcol):
        pc._weights_array[:N_OUT] = rows[perm[i]]
    fired = _cue(e, cue_j=4)
    fired_set = set(np.nonzero(fired)[0].tolist())
    assert fired_set != set(active), \
        f"shuffling the decoder should change which pixels reconstruct, but got the same set {active}"
    print(f"PASS: shuffling the learned decoder changes reconstruction ({fired_set} != {set(active)})")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
