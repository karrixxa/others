"""Regression entry point for the Phase 35 conformance repair."""

from collections import deque
from types import SimpleNamespace

import numpy as np

from backend.simulation import N_OUT, N_PIX, SimulationEngine
from neuron_flexible import Neuron
from snn.dendrite import CoincidencePyramidalCell


def test_switch_preserves_scheduled_physical_pair_and_metadata():
    engine = SimulationEngine(seed=1, prediction_column_enabled=True,
                              prediction_feedback_init=400.0,
                              prediction_lateral_weight=150.0,
                              prediction_threshold=500.0,
                              prediction_learning_rate=0.0, refractory=0)
    apical = np.zeros(N_OUT); apical[0] = 1.0
    basal = np.zeros(N_PIX); basal[4] = 1.0
    engine.l2e_to_pcol_queue = deque([apical])
    engine.s_to_pcol_queue = deque([basal])
    engine.pcol_delivery_metadata_queue = deque([[
        dict(source='L2E0', target='PC4', target_compartment='apical',
             scheduled_step=-1, arrival_step=0, origin_pattern='row 1'),
        dict(source='L1E4', target='PC4', target_compartment='basal',
             scheduled_step=-1, arrival_step=0, origin_pattern='row 1')]])
    engine.set_pattern('col 1')
    engine.input_vec[:] = 0.0
    engine.step()
    assert engine.spiked['PC4']
    records = engine.dynamic_state()['prediction_column']['last_deliveries']
    assert len(records) == 2
    assert {record['origin_class'] for record in records} == {'stale-same-pixel'}
    engine.step()
    assert not engine.spiked['PC4']
    assert engine.dynamic_state()['prediction_column']['last_deliveries'] == []


def test_saturating_update_crosses_then_fires_on_following_coincidence():
    soma = Neuron(n_inputs=1, threshold=5.0, refractory_period=0,
                  learning_rate=0.0, weight_cap=11.0, leak_rate=0.0)
    soma._weights_array = np.array([1.0])
    cell = CoincidencePyramidalCell(soma, 'input', ['feedback'], 0.0, [4.0], 5.0)
    harness = SimpleNamespace(prediction_feedback_max=11.0,
                              prediction_learning_rate=1.0)
    fired = []
    before = []
    for step in range(4):
        cell.deliver_basal(1.0, step); cell.deliver_apical(0, 1.0, step)
        before.append(cell.decoder_weights[0])
        current = cell.resolve_coincidence(step)
        SimulationEngine._apply_prediction_column_learning(harness, cell)
        fired.append(bool(current))
        if current: cell.fire()
        cell.update()
    assert before[2] < 5.0 < cell.decoder_weights[0]
    assert fired == [False, False, False, True]


if __name__ == '__main__':
    tests = [value for name, value in sorted(globals().items()) if name.startswith('test_')]
    for test in tests: test(); print('PASS', test.__name__)
    print(f'CONFORMANCE_REPAIR_PASS {len(tests)}')
