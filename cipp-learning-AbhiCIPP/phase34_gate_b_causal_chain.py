"""Phase 34 Gate B -- shadow vs. active PCi->Ii causal chain (measurement
only). Verifies that a genuine active-dendrite dendritic spike propagates
through the EXISTING, UNMODIFIED Phase 21 PCi->Ii wiring exactly like any
other PC-firing mechanism would: L2Ej arrival (feedback_arrival_j) + L1Ei
arrival (sensory_arrival_i) -> matured decoder -> dendritic event -> PCi
physical spike -> (only when prediction_column_to_i_enabled is on) paired
L1Ii receives and fires -> L1Ei suppression. Also verifies untrained/
non-coincident columns produce NEITHER a PC spike NOR any L1Ii effect.

Two conditions, same training protocol (Gate A's forced-coincidence method
for the SAME (i, j) pair), differing only in prediction_column_to_i_enabled:

  SHADOW  (False, the Phase 19/20 default): PCi fires but has zero effect
          on any other neuron -- L1Ii must show no reaction at all.
  ACTIVE  (True, Phase 21 wiring + pretrained_l1i_regulation so a single
          PCi spike is deterministically sufficient to cross L1Ii's own
          threshold): PCi fires, and L1Ii must fire on the SAME step.

No parameter is tuned to force a pass."""

from __future__ import annotations

import json

import numpy as np

from backend.simulation import N_OUT, N_PIX, SimulationEngine
from backend.presets import DASHBOARD_PRESET

I, J = 3, 2
OTHER_I = 5   # an untrained, never-coincident PC index used as a negative control
N_TRAIN_STEPS = 3_500   # covers eta=0.15's ~2946-event maturation with margin (see Gate A)


def _engine(prediction_column_to_i_enabled):
    e = SimulationEngine(
        seed=1, topology_seed=1, **{**DASHBOARD_PRESET},
        prediction_column_enabled=True,
        prediction_active_dendrite_enabled=True,
        prediction_column_to_i_enabled=prediction_column_to_i_enabled,
        pretrained_l1i_regulation=prediction_column_to_i_enabled)
    # CORRECTED (Codex preflight review): SimulationEngine always holds SOME
    # real pattern from construction -- silence it so the forced PC-queue
    # delivery below is genuinely isolated from ambient real L1E/L2E/L1I
    # dynamics (the original version of this script was confounded by this;
    # see Phase34_Report.md for the full account).
    e.input_vec = np.zeros(N_PIX)
    return e


def _force_delivery(e, dec_vec, lat_vec):
    e.l2e_to_pcol_queue[0] = np.asarray(dec_vec, dtype=float)
    e.s_to_pcol_queue[0] = np.asarray(lat_vec, dtype=float)


def _train_to_maturity(e, i, j, n_steps=N_TRAIN_STEPS):
    dec = np.zeros(N_OUT); dec[j] = 1.0
    lat = np.zeros(N_PIX); lat[i] = 1.0
    for _ in range(n_steps):
        _force_delivery(e, dec, lat)
        e.step()
    return float(e.pcol[i]._weights_array[j])


def _probe_event(e, i, j):
    """One more genuine coincidence event after training; returns the
    per-neuron spike flags this step for the columns of interest."""
    dec = np.zeros(N_OUT); dec[j] = 1.0
    lat = np.zeros(N_PIX); lat[i] = 1.0
    _force_delivery(e, dec, lat)
    e.step()
    return dict(
        pc_i_spiked=bool(e.spiked[f'PC{i}']),
        l1i_i_spiked=bool(e.spiked[f'L1I{i}']),
        pc_other_spiked=bool(e.spiked[f'PC{OTHER_I}']),
        l1i_other_spiked=bool(e.spiked[f'L1I{OTHER_I}']),
    )


def main():
    results = {}

    # ---- SHADOW: prediction_column_to_i_enabled off.
    shadow = _engine(prediction_column_to_i_enabled=False)
    d_final_shadow = _train_to_maturity(shadow, I, J)
    shadow_probe = _probe_event(shadow, I, J)
    results['shadow'] = dict(d_final=d_final_shadow, **shadow_probe)

    # ---- ACTIVE: prediction_column_to_i_enabled + pretrained_l1i_regulation on.
    active = _engine(prediction_column_to_i_enabled=True)
    d_final_active = _train_to_maturity(active, I, J)
    active_probe = _probe_event(active, I, J)
    results['active'] = dict(d_final=d_final_active, **active_probe)

    req_shadow_pc_fires = shadow_probe['pc_i_spiked'] is True
    req_shadow_no_l1i_effect = shadow_probe['l1i_i_spiked'] is False
    req_active_pc_fires = active_probe['pc_i_spiked'] is True
    req_active_l1i_fires = active_probe['l1i_i_spiked'] is True
    req_active_other_column_silent = (active_probe['pc_other_spiked'] is False
                                       and active_probe['l1i_other_spiked'] is False)
    req_shadow_other_column_silent = (shadow_probe['pc_other_spiked'] is False
                                       and shadow_probe['l1i_other_spiked'] is False)

    requirements = dict(
        shadow_pc_fires_but_has_no_effect=(req_shadow_pc_fires and req_shadow_no_l1i_effect),
        active_pc_fires_and_l1i_reacts_same_step=(req_active_pc_fires and req_active_l1i_fires),
        untrained_column_stays_silent_both_conditions=(req_active_other_column_silent
                                                        and req_shadow_other_column_silent),
    )
    overall_pass = all(requirements.values())
    results['requirements'] = requirements
    results['verdict'] = 'PASS' if overall_pass else 'FAIL'

    with open('phase34_gate_b_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Gate B verdict: {results['verdict']}")
    for k, v in requirements.items():
        print(f"  {k}: {v}")
    print(f"  shadow: {shadow_probe}  d_final={d_final_shadow:.2f}")
    print(f"  active: {active_probe}  d_final={d_final_active:.2f}")
    return results


if __name__ == '__main__':
    main()
