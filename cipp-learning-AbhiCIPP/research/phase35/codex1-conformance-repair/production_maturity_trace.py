"""Direct production-only maturity trace; no oracle or adapter imports."""

import json
from types import SimpleNamespace

import numpy as np

from backend.simulation import SimulationEngine
from neuron_flexible import Neuron
from snn.dendrite import CoincidencePyramidalCell


def make_cell(weight=4.0):
    soma = Neuron(n_inputs=1, threshold=5.0, refractory_period=0,
                  learning_rate=0.0, weight_cap=11.0, leak_rate=0.0)
    soma._weights_array = np.array([1.0])
    return CoincidencePyramidalCell(soma, "input", ["feedback"], 0.0,
                                    [weight], 5.0)


def event(cell, step):
    cell.deliver_basal(1.0, step)
    cell.deliver_apical(0, 1.0, step)
    connection = cell.apical_connections[0]
    d_before = connection.weight
    eta, d_max = 1.0, 11.0
    remaining = 1.0 - d_before / d_max
    capacity = remaining ** 2
    delta_unrounded = eta * capacity
    somatic_charge = cell.basal.charge + cell.apical.charge
    current_fire = cell.resolve_coincidence(step)
    SimulationEngine._apply_prediction_column_learning(
        SimpleNamespace(prediction_feedback_max=d_max,
                        prediction_learning_rate=eta), cell)
    d_after = connection.weight
    row = {
        "step": step,
        "d_before_learning": d_before,
        "eta": eta,
        "d_max": d_max,
        "remaining_capacity_factor": remaining,
        "squared_capacity_factor": capacity,
        "unrounded_delta": delta_unrounded,
        "stored_delta": d_after - d_before,
        "d_after_learning": d_after,
        "maturity_threshold": cell.coincidence_threshold,
        "coincidence_status": cell.last_coincidence_step == step,
        "somatic_charge": somatic_charge,
        "current_event_firing_result": bool(current_fire),
    }
    if current_fire:
        cell.fire()
    cell.update()
    return row


def main():
    cell = make_cell()
    rows = [event(cell, step) for step in range(4)]
    for index in range(len(rows) - 1):
        rows[index]["next_valid_coincidence_firing_result"] = rows[index + 1]["current_event_firing_result"]
    rows[-1]["next_valid_coincidence_firing_result"] = None
    print(json.dumps({"classification": "oracle expectation mismatch", "events": rows},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
