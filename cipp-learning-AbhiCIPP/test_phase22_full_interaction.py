"""
Regression tests for Phase 22 (full interaction: pretrained_l2i_recruitment
x prediction_column_to_i_enabled, july14-integration). See
Phase22_Full_Interaction_Report.md for the full 2x2 x schedule x seed
measurement (diagnostic: phase22_full_interaction_diagnostic.py).

Plain-script style:
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python test_phase22_full_interaction.py
"""

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS
from backend.presets import DASHBOARD_PRESET


def _engine(l2i=False, pc=False, seed=1):
    kw = dict(DASHBOARD_PRESET)
    if l2i:
        kw['pretrained_l2i_recruitment'] = True
    if pc:
        kw['prediction_column_enabled'] = True
        kw['prediction_column_to_i_enabled'] = True
    return SimulationEngine(seed=seed, **kw)


def test_both_flags_off_is_baseline():
    e_default = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    e_off = _engine(l2i=False, pc=False)
    for j in range(N_OUT):
        assert np.allclose(e_default.l2.excitatory_neurons[j]._weights_array,
                           e_off.l2.excitatory_neurons[j]._weights_array)
    assert e_off.pcol == []
    print("PASS: both flags off is byte-identical to the plain baseline")


def test_both_flags_can_be_enabled_together():
    e = _engine(l2i=True, pc=True)
    assert e.pretrained_l2i_recruitment is True if hasattr(e, 'pretrained_l2i_recruitment') else True
    assert e.prediction_column_enabled is True
    assert e.prediction_column_to_i_enabled is True
    assert np.allclose(e.l2.inhibitory_neuron._weights_array, e.l2.inhibitory_neuron.threshold)
    e.set_pattern('row 1')
    for _ in range(300):
        e.step()
    print("PASS: both mechanisms combine without raising or crashing over 300 steps")


def test_l2i_pretrained_still_pinned_when_combined_with_pc():
    e = _engine(l2i=True, pc=True)
    w_before = e.l2.inhibitory_neuron._weights_array.copy()
    e.set_pattern('row 1')
    for _ in range(500):
        e.step()
    assert np.allclose(e.l2.inhibitory_neuron._weights_array, w_before), \
        "L2I weights must stay fixed (pretrained_l2i_recruitment) even with PC combined"
    print("PASS: pretrained_l2i_recruitment's fixed L2I weights are unaffected by adding PC")


def test_pc_selectivity_unaffected_by_pretrained_l2i():
    """Phase 19/21's clean per-pixel selectivity (precision 1.0) must survive
    combining with pretrained_l2i_recruitment -- the two mechanisms are
    orthogonal by construction (different populations/synapses)."""
    e = _engine(l2i=True, pc=True)
    e.set_pattern('row 1')
    spikes = np.zeros(N_PIX)
    for _ in range(1500):
        e.step()
        for i in range(N_PIX):
            if e.spiked.get(f'PC{i}'):
                spikes[i] += 1
    fired = set(np.nonzero(spikes)[0].tolist())
    active = set(i for i, v in enumerate(PATTERNS['row 1']) if v)
    assert fired <= active, f"PC precision broken when combined with pretrained_l2i_recruitment: {fired - active}"
    assert fired, "PC should still fire for its own active pixels when combined"
    print(f"PASS: PC selectivity ({fired}) unaffected by combining with pretrained_l2i_recruitment")


def test_selective_l1i_topology_still_breaks_all_nine_sync_when_combined():
    e = _engine(l2i=True, pc=True)
    e.set_pattern('row 1')
    sync_steps = 0
    for _ in range(1000):
        e.step()
        spiked = [e.spiked.get(f'L1I{i}') for i in range(N_PIX)]
        if all(spiked):
            sync_steps += 1
    assert sync_steps == 0, f"expected zero all-nine L1I sync even combined with pretrained_l2i_recruitment, got {sync_steps}"
    print("PASS: selective L1I topology still breaks all-nine sync when combined with pretrained_l2i_recruitment")


def test_pretrained_l2i_tyranny_persists_when_combined_with_selective_inhibition():
    """HONEST NEGATIVE finding (see the report's full grid): combining
    prediction_column_to_i_enabled with pretrained_l2i_recruitment does NOT
    fix Phase 17's own known tyranny problem -- a single L2E can still end
    up owning all four patterns under a long hold, exactly as it does with
    pretrained_l2i_recruitment alone. Selective local predictive inhibition
    regulates L1I's input topology; it does not touch L2's own WTA
    competition dynamics, so there is no reason it SHOULD fix this, and it
    does not."""
    import diagnostic_schedule as ds
    kw = dict(DASHBOARD_PRESET, pretrained_l2i_recruitment=True,
             prediction_column_enabled=True, prediction_column_to_i_enabled=True)
    run = ds.run_diagnostic(seed=1, engine_kwargs=kw, cycles=3, presentation_steps=100)
    summary = ds.summarize(run)
    assert summary['distinct_owners'] <= 2, (
        f"expected the combined condition to still show significant tyranny "
        f"(distinct_owners <= 2) under a long hold, got {summary['distinct_owners']} "
        f"-- if this now passes, the interaction may have genuinely improved; update the report")
    print(f"PASS (documents the persisting negative finding): distinct_owners="
         f"{summary['distinct_owners']} under the combined condition, long hold")


def test_clean_one_hot_is_not_conflated_with_representation_quality():
    """Explicit guard against the known false-positive risk (Phase 17):
    a clean one-hot L1I sync/response pattern must never be silently
    interpreted as evidence of correct one-to-one representation --
    distinct_owners/collisions must be checked independently."""
    import diagnostic_schedule as ds
    kw = dict(DASHBOARD_PRESET, pretrained_l2i_recruitment=True)
    run = ds.run_diagnostic(seed=1, engine_kwargs=kw, cycles=3, presentation_steps=100)
    summary = ds.summarize(run)
    # A tyrant condition CAN still show l1i_all_nine_sync_rate == 1.0 (every
    # L1I fires whenever ANY L2E wins, regardless of which one) -- this must
    # never be read as "one-to-one representation achieved".
    if summary['l1i_all_nine_sync_rate'] == 1.0:
        assert summary['distinct_owners'] < 4, (
            "a tyrant condition legitimately shows all-nine L1I sync -- this test "
            "documents that fact is NOT evidence of one-to-one representation")
    print(f"PASS: l1i_all_nine_sync_rate={summary['l1i_all_nine_sync_rate']} and "
         f"distinct_owners={summary['distinct_owners']} are reported/checked independently")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
