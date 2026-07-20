"""Exact Phase 35 Gate B contract. Run from the repository source directory."""

from collections import deque
import struct

import numpy as np

from backend.presets import DASHBOARD_PRESET
from backend.simulation import N_OUT, N_PIX, SimulationEngine


def engine(**overrides):
    params = {**DASHBOARD_PRESET, "prediction_feedback_init": 349.9,
              "prediction_lateral_weight": 150.0,
              "prediction_threshold": 500.0,
              "prediction_learning_rate": 100.0, "refractory": 0,
              **overrides}
    return SimulationEngine(seed=37, prediction_column_enabled=True, **params)


def queued_step(e, source, basal_targets):
    apical = np.zeros(N_OUT); apical[source] = 1.0
    basal = np.zeros(N_PIX); basal[list(basal_targets)] = 1.0
    e.l2e_to_pcol_queue = deque([apical])
    e.s_to_pcol_queue = deque([basal])
    e.input_vec[:] = 0.0
    return e.step()


def packed(values):
    return b"".join(struct.pack("!d", float(value)) for value in values)


def test_fanout_selective_learning_and_locality():
    e = engine()
    source, targets = 4, {1, 4, 7}
    before = [packed(pc.decoder_weights) for pc in e.pcol]
    queued_step(e, source, targets)
    assert all(pc.last_apical_sources == (f"L2E{source}",) for pc in e.pcol)
    for i, pc in enumerate(e.pcol):
        assert pc.basal_connection.source == f"L1E{i}"
        assert pc.apical_connections[source].source == f"L2E{source}"
        changed = packed(pc.decoder_weights) != before[i]
        assert changed is (i in targets)
        for j in range(N_OUT):
            if i in targets and j == source:
                assert pc.decoder_weights[j] > 349.9
            else:
                assert struct.pack("!d", pc.decoder_weights[j]) == struct.pack("!d", 349.9)


def test_d_before_learning_and_next_coincidence_fire():
    e = engine()
    state = queued_step(e, 2, {3})
    pc = e.pcol[3]
    assert pc.last_d_before_learning == 349.9
    assert pc.decoder_weights[2] > 350.0
    assert not state["prediction_column"]["spiked"]["PC3"] if "prediction_column" in state else not e.spiked["PC3"]
    state = queued_step(e, 2, {3})
    assert e.spiked["PC3"], "weight crossing affects only the next physical coincidence"


def test_no_duplicate_or_deferred_delivery():
    e = engine(prediction_feedback_init=400.0, prediction_learning_rate=0.0)
    queued_step(e, 1, {2})
    assert e.spiked["PC2"]
    first_step = e.pcol[2].last_coincidence_step
    e.l2e_to_pcol_queue = deque([np.zeros(N_OUT)])
    e.s_to_pcol_queue = deque([np.zeros(N_PIX)])
    e.step()
    assert not e.spiked["PC2"]
    assert e.pcol[2].last_coincidence_step == first_step
    assert e.pcol[2].basal.delivery_step is None and e.pcol[2].apical.delivery_step is None


def test_paired_output_route():
    e = engine(prediction_feedback_init=400.0, prediction_learning_rate=0.0,
               prediction_column_to_i_enabled=True, pretrained_l1i_regulation=True)
    queued_step(e, 0, {5})
    assert e.spiked["PC5"] and e.spiked["L1I5"]
    assert not any(e.spiked[f"L1I{i}"] for i in range(N_PIX) if i != 5)
    assert e.l1i_feedback_delay[5] == 1.0


def test_pattern_switch_discards_queued_compartment_events():
    e = engine(prediction_feedback_init=400.0, prediction_learning_rate=0.0)
    apical = np.zeros(N_OUT); apical[0] = 1.0
    basal = np.zeros(N_PIX); basal[4] = 1.0
    e.l2e_to_pcol_queue = deque([apical])
    e.s_to_pcol_queue = deque([basal])
    e.set_pattern("col 1")
    e.step()
    assert not any(e.spiked[f"PC{i}"] for i in range(N_PIX))


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests: test(); print("PASS", test.__name__)
    print(f"GATE_B_PASS {len(tests)}")
