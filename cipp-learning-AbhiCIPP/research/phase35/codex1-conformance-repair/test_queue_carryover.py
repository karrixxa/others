"""Phase 35 conformance regression: scheduled events survive presentation switches."""

from collections import deque

import numpy as np

from backend.simulation import N_OUT, N_PIX, SimulationEngine


def test_scheduled_pair_survives_pattern_switch_and_delivers_once():
    engine = SimulationEngine(seed=1, prediction_column_enabled=True,
                              prediction_feedback_delay=1,
                              prediction_feedback_init=400.0,
                              prediction_lateral_weight=150.0,
                              prediction_threshold=500.0,
                              prediction_learning_rate=0.0,
                              refractory=0)
    apical = np.zeros(N_OUT); apical[0] = 1.0
    basal = np.zeros(N_PIX); basal[4] = 1.0
    engine.l2e_to_pcol_queue = deque([apical])
    engine.s_to_pcol_queue = deque([basal])
    engine.pcol_delivery_metadata_queue = deque([[
        dict(source="L2E0", target="PC4", target_compartment="apical",
             scheduled_step=engine.timestep - 1, arrival_step=engine.timestep,
             origin_pattern="row 1"),
        dict(source="L1E4", target="PC4", target_compartment="basal",
             scheduled_step=engine.timestep - 1, arrival_step=engine.timestep,
             origin_pattern="row 1"),
    ]])

    engine.set_pattern("col 1")
    assert np.array_equal(engine.l2e_to_pcol_queue[0], apical)
    assert np.array_equal(engine.s_to_pcol_queue[0], basal)

    engine.input_vec[:] = 0.0
    engine.step()
    assert engine.spiked["PC4"]
    delivered_step = engine.pcol[4].last_coincidence_step
    deliveries = engine.dynamic_state()["prediction_column"]["last_deliveries"]
    assert len(deliveries) == 2
    assert {record["origin_class"] for record in deliveries} == {"stale-same-pixel"}
    for record in deliveries:
        assert record["scheduled_step"] == -1
        assert record["arrival_step"] == 0
        assert record["delivered_step"] == 0
        assert record["source"] in {"L2E0", "L1E4"}
        assert record["target"] == "PC4"

    engine.input_vec[:] = 0.0
    engine.step()
    assert not engine.spiked["PC4"]
    assert engine.pcol[4].last_coincidence_step == delivered_step
    assert engine.dynamic_state()["prediction_column"]["last_deliveries"] == []


def test_origin_classification_is_passive_and_complete():
    engine = SimulationEngine(seed=1, prediction_column_enabled=True)
    cases = [
        ([dict(origin_pattern="col 1")], 4, "current-correct"),
        ([dict(origin_pattern="row 1")], 4, "stale-same-pixel"),
        ([dict(origin_pattern="row 1")], 3, "stale-wrong-pixel"),
        ([dict(origin_pattern="row 1"), dict(origin_pattern="col 1")], 4, "mixed"),
    ]
    engine.current_pattern = "col 1"
    for records, pixel, expected in cases:
        assert engine._prediction_column_origin_class(records, pixel) == expected


if __name__ == "__main__":
    test_scheduled_pair_survives_pattern_switch_and_delivers_once()
    test_origin_classification_is_passive_and_complete()
    print("QUEUE_CARRYOVER_PASS")
