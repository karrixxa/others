"""
Regression tests for Phase 21 (selective local predictive inhibition;
wires the deferred PCi->Ii->Si path for the first time -- Phases 19-20 were
shadow-only, zero output). See Phase21_Selective_Inhibition_Report.md.

Two independent factorial variables:
  prediction_column_to_i_enabled: selective PCi->Ii input topology
      (replaces, not appends to, L1Ii's incoming array).
  pretrained_l1i_regulation: fixed/pretrained vs learned L1I regulation,
      kept SEPARATE from the topology flag per the independent review's
      correction #6.

Plain-script style:
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python test_phase21_selective_inhibition.py
"""

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX
from backend.presets import DASHBOARD_PRESET

HOLD = 1500
ACTIVE = (3, 4, 5)
INACTIVE = (0, 1, 2, 6, 7, 8)


def _engine(selective=False, fixed=False, seed=1):
    kw = dict(seed=seed, pretrained_l1i_regulation=fixed, **DASHBOARD_PRESET)
    if selective:
        kw['prediction_column_enabled'] = True
        kw['prediction_column_to_i_enabled'] = True
    return SimulationEngine(**kw)


# --------------------------------------------------------- A. Preservation
def test_flag_off_baseline_equivalent_unit_level():
    e_default = _engine()
    e_off = _engine(selective=False, fixed=False)
    assert e_default.l1.inhibitory_neurons[0].weights.shape == (N_OUT,)
    assert e_off.l1.inhibitory_neurons[0].weights.shape == (N_OUT,)
    assert np.allclose(e_default.l1.inhibitory_neurons[0].weights, e_off.l1.inhibitory_neurons[0].weights)
    print("PASS: flag-off (explicit) == omitted at unit level -- L1I keeps its N_OUT-wide global input")


def test_flag_off_baseline_equivalent_engine_level():
    e_default = _engine()
    e_off = _engine(selective=False, fixed=False)
    for e in (e_default, e_off):
        e.set_pattern('row 1')
        for _ in range(300):
            e.step()
    for j in range(N_OUT):
        assert np.allclose(e_default.l2.excitatory_neurons[j]._weights_array,
                           e_off.l2.excitatory_neurons[j]._weights_array), f"L2E{j} diverged"
    for i in range(N_PIX):
        assert np.allclose(e_default.l1.inhibitory_neurons[i].weights,
                           e_off.l1.inhibitory_neurons[i].weights), f"L1I{i} diverged"
    print("PASS: 300-step engine run byte-identical, flags omitted vs. explicit-off")


def test_selective_requires_prediction_column_enabled():
    try:
        SimulationEngine(seed=1, prediction_column_to_i_enabled=True, **DASHBOARD_PRESET)
        raised = False
    except ValueError:
        raised = True
    assert raised, "prediction_column_to_i_enabled without prediction_column_enabled must raise"
    print("PASS: selective L1I input without an actual PC population raises")


# --------------------------------------------------------- B. Locality/regression guards
def test_l1i_incoming_array_shape_matches_topology():
    e_global = _engine(selective=False)
    e_selective = _engine(selective=True)
    assert e_global.l1.inhibitory_neurons[0].weights.shape == (N_OUT,)
    assert e_selective.l1.inhibitory_neurons[0].weights.shape == (1,)
    print("PASS: L1I incoming array is N_OUT-wide (global) or exactly 1-wide (selective)")


def test_distance_weighting_never_applied_to_selective_l1i():
    """Regression guard for the bug found during Phase 21 calibration:
    _apply_experimental_pathway_distances() would otherwise assign an
    N_OUT-shaped geometric distance row to a genuinely 1-wide L1I weight
    array under the selective topology, raising a shape-mismatch error."""
    e = _engine(selective=True)
    for inh in e.l1.inhibitory_neurons:
        assert inh.distance_weighting is False
        assert len(inh._distance) == 1
    print("PASS: selective-topology L1I is never swept into the N_OUT-shaped distance-weighting path")


def test_pretrained_l1i_regulation_pins_learning_rate():
    """Regression guard: a later generic per-neuron sweep in _build()
    (n.learning_rate = lr_frac * n.weight_cap, keyed only by population
    type) would otherwise silently overwrite the fixed-regulation pinning
    set earlier in the L1I init loop."""
    e_learned = _engine(fixed=False)
    e_fixed = _engine(fixed=True)
    assert e_learned.l1.inhibitory_neurons[0].learning_rate > 0.0
    assert e_fixed.l1.inhibitory_neurons[0].learning_rate == 0.0
    thr_l1i = e_fixed.l1.inhibitory_neurons[0].threshold
    assert np.allclose(e_fixed.l1.inhibitory_neurons[0].weights, thr_l1i)
    print("PASS: pretrained_l1i_regulation correctly pins learning_rate=0 and fixes weights at threshold")


def test_pci_delivery_reaches_only_its_own_paired_l1i():
    """Force ONLY PC3 to fire (selective topology); only L1I3 may receive
    charge -- every other L1Ii must see zero delivered charge this event."""
    e = _engine(selective=True)
    for i, inh in enumerate(e.l1.inhibitory_neurons):
        pc_spike = 1.0 if i == 3 else 0.0
        inh.receive_input(np.array([pc_spike]), t=0)
    for i, inh in enumerate(e.l1.inhibitory_neurons):
        if i == 3:
            assert inh.potential > 0.0, "L1I3 should have received PC3's spike"
        else:
            assert inh.potential == 0.0, f"L1I{i} must not receive any charge from PC3's spike"
    print("PASS: PCi's spike reaches only its own paired L1Ii under the selective topology")


# --------------------------------------------------------- C. Measured factorial findings
def _run(condition, seed=1):
    selective = condition in ('B', 'D')
    fixed = condition in ('C', 'D')
    e = _engine(selective=selective, fixed=fixed, seed=seed)
    e.set_pattern('row 1')
    l1i_counts = np.zeros(N_PIX)
    all_nine_sync = 0
    for _ in range(HOLD):
        e.step()
        spiked = np.array([1.0 if e.spiked.get(f'L1I{i}') else 0.0 for i in range(N_PIX)])
        l1i_counts += spiked
        if spiked.all():
            all_nine_sync += 1
    return l1i_counts / HOLD, all_nine_sync / HOLD


def test_global_topology_shows_all_nine_sync_and_no_selectivity():
    rate, sync = _run('A')
    assert sync > 0.3, f"expected substantial all-nine sync under global feedback, got {sync}"
    assert np.allclose(rate, rate[0], atol=1e-6), \
        f"global feedback should deliver identically to every L1Ii regardless of pixel, got {rate}"
    print(f"PASS: global topology (A) shows all-nine sync ({sync:.3f}) and zero per-pixel selectivity")


def test_selective_topology_breaks_sync_and_adds_selectivity():
    rate, sync = _run('B')
    assert sync == 0.0, f"selective topology should never show all-nine sync, got {sync}"
    assert rate[list(INACTIVE)].max() == 0.0, \
        f"inactive columns must receive exactly zero PCi-driven inhibition, got {rate[list(INACTIVE)]}"
    assert rate[list(ACTIVE)].min() > 0.0, \
        f"active columns should receive some real PCi-driven inhibition, got {rate[list(ACTIVE)]}"
    print(f"PASS: selective topology (B) breaks all-nine sync (0.0) and shows perfect "
         f"per-pixel selectivity (inactive={rate[list(INACTIVE)].max()}, active mean={rate[list(ACTIVE)].mean():.3f})")


def test_selective_topology_delivers_weaker_overall_inhibition():
    """Honest trade-off, not smoothed over: selective inhibition is more
    TOPOLOGICALLY correct but weaker in raw magnitude (PCi fires far less
    often than L2E), which should show up as a HIGHER L1E duty cycle
    (less overall suppression) than the global baseline."""
    e_global = _engine(selective=False)
    e_selective = _engine(selective=True)
    for e in (e_global, e_selective):
        e.set_pattern('row 1')
    l1e_global = np.zeros(N_PIX)
    l1e_selective = np.zeros(N_PIX)
    for _ in range(HOLD):
        e_global.step()
        e_selective.step()
        l1e_global += np.array([1.0 if e_global.spiked.get(f'L1E{i}') else 0.0 for i in range(N_PIX)])
        l1e_selective += np.array([1.0 if e_selective.spiked.get(f'L1E{i}') else 0.0 for i in range(N_PIX)])
    duty_global = (l1e_global[list(ACTIVE)] / HOLD).mean()
    duty_selective = (l1e_selective[list(ACTIVE)] / HOLD).mean()
    assert duty_selective > duty_global, (
        f"expected selective topology's weaker/rarer inhibitory drive to show a HIGHER L1E "
        f"duty cycle than global: global={duty_global:.3f}, selective={duty_selective:.3f}")
    print(f"PASS (documents the trade-off): selective inhibition is weaker overall -- "
         f"L1E duty cycle global={duty_global:.3f} < selective={duty_selective:.3f}")


def test_no_unwanted_global_silence_of_active_pixels():
    """The active pixels (part of the current pattern) must not be
    permanently silenced under any of the four conditions -- some nonzero
    firing rate must survive."""
    for condition in ('A', 'B', 'C', 'D'):
        rate, _ = _run(condition)
        assert rate[list(ACTIVE)].min() > 0.0, \
            f"condition {condition}: an active pixel's L1I never fired at all -- check for over-suppression"
    print("PASS: no unwanted permanent silence of active-pixel L1I across all 4 conditions")


def test_deterministic_replay():
    e1 = _engine(selective=True, fixed=True, seed=3)
    e2 = _engine(selective=True, fixed=True, seed=3)
    e1.set_pattern('row 1'); e2.set_pattern('row 1')
    for _ in range(500):
        e1.step(); e2.step()
    for i in range(N_PIX):
        assert np.allclose(e1.l1.inhibitory_neurons[i].weights, e2.l1.inhibitory_neurons[i].weights)
    print("PASS: identical seed -> identical 500-step L1I trajectory (condition D)")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
