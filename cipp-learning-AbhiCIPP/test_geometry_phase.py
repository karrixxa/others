"""
Regression tests for Phase 3 (seeded engine-owned geometry, july14-integration).

Covers: seed reproduction, fixity across reset/training/probes/apply_config,
spatial bounds (L1E confined to its cell, L1I near its paired L1E, L2E within
the placement radius, L2I fixed at center), irregularity (no accidental
symmetry), minimum separation, serialization (topology geometry descriptor +
per-synapse delivery fields), and the legacy-distance-compat shim's central
guarantee: with it on (the default), switching to the new geometry does not
change neural dynamics at all -- verified against the exact winner sequence
and final weights, not just aggregate diagnostics.
"""

import itertools

import numpy as np

from backend.simulation import (SimulationEngine, PATTERNS, N_PIX, N_OUT, GRID,
                                L2_HOMES, _legacy_l1_xy, L2E_MIN_SEPARATION,
                                L2E_PLACEMENT_RADIUS)
from backend.presets import DASHBOARD_PRESET


def _positions(e):
    return {n['id']: n['pos'] for n in e.topology()['neurons']}


# --------------------------------------------------------------- legacy ablation
def test_symmetric_geometry_reproduces_exact_legacy_positions():
    e = SimulationEngine(seed=1, symmetric_geometry=True)
    pos = _positions(e)
    for j in range(N_OUT):
        assert pos[f'L2E{j}'] == list(L2_HOMES[j])
    legacy_xy = _legacy_l1_xy()
    for i in range(N_PIX):
        assert pos[f'L1E{i}'][:2] == [round(float(legacy_xy[i, 0]), 4), round(float(legacy_xy[i, 1]), 4)]
        assert pos[f'L1E{i}'][2] == 0.0
        assert pos[f'L1I{i}'][:2] == pos[f'L1E{i}'][:2]
        assert pos[f'L1I{i}'][2] == -2.0
    assert pos['L2I'] == [0.0, 0.0, 6.0]


def test_engine_default_is_symmetric_geometry_true():
    """Every existing caller/test that does not pass symmetric_geometry must
    keep getting the exact legacy layout -- this is the legacy-equivalence
    guarantee for every OTHER test file in the repo."""
    e = SimulationEngine(seed=1)
    assert e.params['symmetric_geometry'] is True
    assert e.params['legacy_distance_compat'] is True


# ---------------------------------------------------------- seed reproduction
def test_same_topology_seed_reproduces_identical_positions():
    e1 = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=7)
    e2 = SimulationEngine(seed=99, symmetric_geometry=False, topology_seed=7)  # different WEIGHT seed
    assert _positions(e1) == _positions(e2)


def test_different_topology_seed_gives_different_positions():
    e1 = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=7)
    e2 = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=8)
    assert _positions(e1) != _positions(e2)


# --------------------------------------------------------------- fixity/reset
def test_positions_fixed_across_reset_training_weight_reseed_probe_config():
    e = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=7)
    before = _positions(e)

    e.set_pattern('col 1')
    for _ in range(50):
        e.step()
    assert _positions(e) == before, "positions changed during training"

    e.reset()
    assert _positions(e) == before, "positions changed on reset()"

    e.reseed()   # weight-only reseed
    assert _positions(e) == before, "positions changed on weight reseed()"

    e.present_probe('row 0', steps=10)
    for _ in range(10):
        e.step()
    assert _positions(e) == before, "positions changed across a probe presentation"

    e.apply_config({'l2e_lr_frac': 0.03})
    assert _positions(e) == before, "positions changed on an unrelated apply_config() override"


def test_reseed_topology_changes_positions_but_preserves_learned_weights():
    e = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=7)
    before = _positions(e)
    e.set_pattern('col 1')
    for _ in range(60):
        e.step()
    w_trained = e._all_weights()

    new_seed = e.reseed_topology()
    assert isinstance(new_seed, int)
    assert _positions(e) != before
    assert e._all_weights() == w_trained, "reseed_topology() disturbed learned weights"
    assert e.current_pattern == 'col 1', "reseed_topology() disturbed the current pattern"


def test_reseed_topology_is_a_noop_on_positions_under_symmetric_geometry():
    e = SimulationEngine(seed=1, symmetric_geometry=True)
    before = _positions(e)
    e.reseed_topology()
    assert _positions(e) == before, "the legacy layout has no seed dependence"


# ----------------------------------------------------------------- spatial bounds
def test_l1e_jitter_stays_within_its_own_cell():
    e = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=3)
    legacy = _legacy_l1_xy()
    pos = _positions(e)
    for i in range(N_PIX):
        p = np.array(pos[f'L1E{i}'][:2])
        d = np.linalg.norm(p - legacy[i])
        assert d < GRID / 2, f"L1E{i} crossed out of its assigned cell (d={d})"


def test_l1i_stays_near_its_paired_l1e():
    e = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=3)
    pos = _positions(e)
    for i in range(N_PIX):
        d = np.linalg.norm(np.array(pos[f'L1E{i}'][:2]) - np.array(pos[f'L1I{i}'][:2]))
        assert d < GRID / 2


def test_l2e_stays_within_the_placement_radius():
    e = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=3)
    pos = _positions(e)
    for j in range(N_OUT):
        r = np.linalg.norm(pos[f'L2E{j}'][:2])
        assert r <= L2E_PLACEMENT_RADIUS + 1e-9


def test_l2i_is_fixed_at_center_regardless_of_geometry_mode():
    for symmetric in (True, False):
        e = SimulationEngine(seed=1, symmetric_geometry=symmetric, topology_seed=3)
        assert _positions(e)['L2I'] == [0.0, 0.0, 6.0]


def test_z_coordinates_unchanged_by_jitter():
    """Only (x,y) is jittered -- z stays per-population, matching the legacy
    layout (0.0 / -2.0 / _Z / 6.0)."""
    e = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=3)
    pos = _positions(e)
    for i in range(N_PIX):
        assert pos[f'L1E{i}'][2] == 0.0
        assert pos[f'L1I{i}'][2] == -2.0
    for j in range(N_OUT):
        assert pos[f'L2E{j}'][2] == L2_HOMES[0][2]   # _Z


# ------------------------------------------------------------------ irregularity
def test_l2e_placement_is_irregular_not_symmetric():
    e = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=3)
    pos = _positions(e)
    l2e_ids = [f'L2E{j}' for j in range(N_OUT)]
    dists = [round(float(np.linalg.norm(np.array(pos[a][:2]) - np.array(pos[b][:2]))), 3)
             for a, b in itertools.combinations(l2e_ids, 2)]
    # The legacy ring collapses to only 6 distinct pairwise distances (8-fold
    # symmetry); irregular placement should look nothing like that.
    assert len(set(dists)) > 10, f"placement looks too symmetric: only {len(set(dists))} distinct distances"


def test_minimum_separation_is_enforced_across_several_seeds():
    for seed in (1, 2, 3, 4, 5):
        e = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=seed)
        pos = _positions(e)
        l2e_ids = [f'L2E{j}' for j in range(N_OUT)]
        for a, b in itertools.combinations(l2e_ids, 2):
            d = np.linalg.norm(np.array(pos[a][:2]) - np.array(pos[b][:2]))
            assert d >= L2E_MIN_SEPARATION - 1e-9, f"seed {seed}: {a}/{b} violate min separation (d={d})"


# --------------------------------------------------------------- serialization
def test_topology_geometry_descriptor():
    e_compat = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=7,
                                legacy_distance_compat=True)
    g = e_compat.topology()['geometry']
    assert g == dict(symmetric=False, topology_seed=7, legacy_distance_compat=True,
                     legacy_distance_compat_active=True)

    e_legacy = SimulationEngine(seed=1, symmetric_geometry=True)
    g2 = e_legacy.topology()['geometry']
    assert g2['legacy_distance_compat_active'] is False   # nothing can diverge when symmetric


def test_topology_synapses_still_expose_delivery_diagnostics_under_new_geometry():
    e = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=7)
    ff = next(s for s in e.topology()['synapses'] if s['kind'] == 'feedforward')
    assert {'distance', 'influence', 'effective'} <= ff.keys()
    assert ff['distance'] > 0


# ------------------------------------------------- legacy-distance-compat shim
def test_legacy_distance_compat_pins_distances_to_the_legacy_reference():
    e_compat = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=7,
                                legacy_distance_compat=True)
    e_legacy = SimulationEngine(seed=1, symmetric_geometry=True)
    for j in range(N_OUT):
        assert np.array_equal(e_compat.l2.excitatory_neurons[j].distance,
                              e_legacy.l2.excitatory_neurons[j].distance)


def test_legacy_distance_compat_false_uses_the_real_new_geometry():
    e_compat = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=7,
                                legacy_distance_compat=True)
    e_real = SimulationEngine(seed=1, symmetric_geometry=False, topology_seed=7,
                              legacy_distance_compat=False)
    differs = any(not np.array_equal(e_compat.l2.excitatory_neurons[j].distance,
                                     e_real.l2.excitatory_neurons[j].distance)
                  for j in range(N_OUT))
    assert differs, "legacy_distance_compat=False should use the real (different) geometry"


def test_dashboard_preset_with_new_geometry_is_dynamically_identical_to_pre_phase3():
    """The central guarantee of this phase: DASHBOARD_PRESET's new
    symmetric_geometry=False (jittered display) must not change a single
    spike, winner, or learned weight versus what it would have been before
    Phase 3 (symmetric_geometry=True), because legacy_distance_compat=True
    pins the only geometry-derived input (distance) to the same legacy
    reference in both cases."""
    pre_phase3 = dict(DASHBOARD_PRESET)
    pre_phase3['symmetric_geometry'] = True

    e_new = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    e_old = SimulationEngine(seed=1, **pre_phase3)

    for j in range(N_OUT):
        assert np.array_equal(e_new.l2.excitatory_neurons[j].distance,
                              e_old.l2.excitatory_neurons[j].distance)

    winners_new, winners_old = [], []
    for _ in range(4):
        for name in PATTERNS:
            e_new.set_pattern(name)
            e_old.set_pattern(name)
            for _ in range(25):
                dn = e_new.step()
                do = e_old.step()
                winners_new.append(dn['winner'])
                winners_old.append(do['winner'])
    assert winners_new == winners_old
    assert e_new._all_weights() == e_old._all_weights()


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
