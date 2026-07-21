from __future__ import annotations

import numpy as np

from backend.simulation import (
    EDGE_DETECTOR_CANDIDATE_MEAN,
    N_OUT,
    N_PIX,
    SimulationEngine,
)


def _ff_matrix(engine: SimulationEngine) -> np.ndarray:
    return np.array([
        [engine._all_weights()[f'ff{i}->{j}'] for i in range(N_PIX)]
        for j in range(N_OUT)
    ], dtype=float)


def test_edge_detector_candidate_rescales_the_same_legacy_draw():
    legacy = SimulationEngine(seed=11, l2e_init_mode='legacy_wide', pos_weight_floor=1)
    candidate = SimulationEngine(seed=11, l2e_init_mode='edge_detector_candidate', pos_weight_floor=1)
    base = _ff_matrix(legacy)
    scaled = _ff_matrix(candidate)

    factor = EDGE_DETECTOR_CANDIDATE_MEAN / float(base.mean())
    assert np.allclose(scaled, base * factor)
    assert np.isclose(float(scaled.mean()), EDGE_DETECTOR_CANDIDATE_MEAN)
    assert legacy.params['l2e_init_mode'] == 'legacy_wide'
    assert candidate.params['l2e_init_mode'] == 'edge_detector_candidate'


def test_simulator_status_reports_candidate_prediction_state_cleanly():
    engine = SimulationEngine(
        seed=3,
        l2e_init_mode='edge_detector_candidate',
        prediction_column_enabled=True,
        prediction_column_to_i_enabled=True,
        prediction_column_to_i_delivery_enabled=True,
        prediction_column_persistent_conductance_enabled=False,
        pos_weight_floor=1,
    )
    status = engine.simulator_status()
    assert status['prediction_output_state'] == 'instantaneous'
    assert status['detected_pattern'] in {'row 1', 'col 1', 'diag /', 'diag \\'}
    assert status['exact_zero_feedforward'] == 0
