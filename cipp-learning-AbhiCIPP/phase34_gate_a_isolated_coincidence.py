"""Phase 34 Gate A -- isolated learned coincidence (measurement only).

CORRECTED after the Codex preflight review, in two ways:

  1. Isolation bug fixed: SimulationEngine always holds SOME real pattern
     from construction (current_pattern defaults to the first entry in
     PATTERNS; there is no "no pattern" state). The original version of
     this script built engines from DASHBOARD_PRESET without ever silencing
     that default-held pattern, so genuine L1E/L2E/L1I dynamics ran the
     whole time alongside the forced PC-queue delivery below -- confounding
     Gate B's causal-chain measurement (see Phase34_Report.md). Fixed here
     by explicitly zeroing `e.input_vec` after construction, verified
     separately to produce zero L1E/L2E activity over 300 steps.
  2. eta corrected: prediction_active_dendrite_learning_rate's default was
     wrongly 0.01; Codex's independent reproduction target ("~2946
     coincidence events" to reach d=350 from d=50) is exact ONLY at
     eta=0.15 (verified against the closed-form saturating-growth solution
     dw/dt = eta*(1-w/w_max)^2 => 1/u = 1/u0 + (eta/w_max)*t). The engine
     default is now 0.15; this script reads it from the engine rather than
     assuming a number, so it stays correct if the default ever changes.

PART 1 -- isolated logic verification: drives a SINGLE PC_i/L2E_j pair with
a repeated, genuine same-step coincidence delivery (using the exact
dec_vec_pcol/lat_vec_pcol queue mechanism step() itself pops from -- not a
synthetic shortcut) against a silenced (all-zero input) engine, and records
the full trajectory of d_ji, PCi's membrane potential, and its physical
spike flag: immature phase (zero spikes), the exact pre-update transition
step, mature phase (always fires), and feedback-alone failure at
near-d_max.

PART 2 -- natural coincidence-rate measurement (Codex requirement: "Gate A
must run long enough to observe natural decoder maturation or establish
from the measured physical coincidence rate how many outer steps are
required. Do not reuse the earlier 15-cycle window and interpret
non-maturation as failure."): runs a REAL, unforced engine on a REAL
pattern, identifies the pattern's own actual causal first-responder L2Ej
(read off the engine's own spike history, no assignment), and measures how
often a genuine same-step coincidence (sensory_arrival_i(t)==1 AND
feedback_arrival_j(t)==1, exactly the condition _active_dendrite_event
checks) actually occurs per outer step under REAL, unmanipulated dynamics.
From that measured rate, projects how many real outer steps natural
maturation would require, and -- only if that projection is small enough to
run within this script's own budget -- actually runs it and reports whether
natural maturation was observed within that window. If the projection is
too large to run here, this is reported honestly as a scale estimate, NOT
interpreted as a failure (per the explicit instruction above).

No parameter is tuned to force a pass anywhere in this script."""

from __future__ import annotations

import json

import numpy as np

from backend.simulation import N_OUT, N_PIX, SimulationEngine
from backend.presets import DASHBOARD_PRESET

I, J = 3, 2   # the one PCi/L2Ej pair under test for Part 1 -- arbitrary, fixed before running
N_FEEDBACK_ALONE_STEPS = 200
NATURAL_PILOT_STEPS = 4_000            # real, unforced dynamics measurement window
NATURAL_RUN_BUDGET_STEPS = 200_000     # only actually run Part 2's full maturation if projected <= this


def _engine(**overrides):
    e = SimulationEngine(seed=1, topology_seed=1, **{**DASHBOARD_PRESET, **overrides},
                          prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.input_vec = np.zeros(N_PIX)   # silence the default-held pattern -- true isolation
    return e


def _force_delivery(e, dec_vec, lat_vec):
    e.l2e_to_pcol_queue[0] = np.asarray(dec_vec, dtype=float)
    e.s_to_pcol_queue[0] = np.asarray(lat_vec, dtype=float)


def part1_isolated_logic():
    e = _engine()
    coincidence_weight = e.prediction_active_dendrite_coincidence_weight
    d_max = e.prediction_feedback_max
    d_init = e.prediction_feedback_init
    eta = e.prediction_active_dendrite_learning_rate

    # Closed-form projection (saturating growth, verified below against the
    # actual simulated trajectory): dw/dt = eta*(1-w/w_max)^2 =>
    # 1/(1-w/w_max) = 1/(1-w0/w_max) + (eta/w_max)*t
    u0 = 1.0 - d_init / d_max
    u_target = 1.0 - coincidence_weight / d_max
    projected_events = (1.0 / u_target - 1.0 / u0) / (eta / d_max)
    n_train_steps = int(projected_events * 1.15) + 50   # 15% margin + small floor

    dec = np.zeros(N_OUT); dec[J] = 1.0
    lat = np.zeros(N_PIX); lat[I] = 1.0

    trajectory = []
    first_fire_step = None
    immature_fire_count = 0
    for step_idx in range(n_train_steps):
        d_before = float(e.pcol[I]._weights_array[J])
        was_immature = d_before < coincidence_weight
        _force_delivery(e, dec, lat)
        e.step()
        fired = bool(e.spiked[f'PC{I}'])
        d_after = float(e.pcol[I]._weights_array[J])
        trajectory.append(dict(step=step_idx, d_before=d_before, d_after=d_after,
                                fired=fired, potential_post_step=float(e.pcol[I].potential)))
        if was_immature and fired:
            immature_fire_count += 1
        if fired and first_fire_step is None:
            first_fire_step = step_idx

    req1_pass = (immature_fire_count == 0)

    req2_pass = False
    transition_detail = None
    if first_fire_step is not None and first_fire_step > 0:
        prev = trajectory[first_fire_step - 1]
        cur = trajectory[first_fire_step]
        req2_pass = (cur['d_before'] >= coincidence_weight
                     and prev['d_after'] >= coincidence_weight
                     and not prev['fired'])
        transition_detail = dict(
            crossing_step=first_fire_step - 1, crossing_step_d_after=prev['d_after'],
            crossing_step_fired=prev['fired'], first_fire_step=first_fire_step,
            first_fire_step_d_before=cur['d_before'])

    req3_pass = False
    if first_fire_step is not None:
        req3_pass = all(row['fired'] for row in trajectory[first_fire_step:])

    d_final = float(e.pcol[I]._weights_array[J])
    feedback_alone_fires = 0
    feedback_alone_trajectory = []
    for step_idx in range(N_FEEDBACK_ALONE_STEPS):
        _force_delivery(e, dec, np.zeros(N_PIX))
        e.step()
        fired = bool(e.spiked[f'PC{I}'])
        feedback_alone_trajectory.append(dict(step=step_idx, fired=fired,
                                               d_ji=float(e.pcol[I]._weights_array[J])))
        if fired:
            feedback_alone_fires += 1
    req4_pass = (feedback_alone_fires == 0)

    overall_pass = req1_pass and req2_pass and req3_pass and req4_pass
    coarse = trajectory[::50]
    dense_window = []
    if first_fire_step is not None:
        lo = max(0, first_fire_step - 25)
        hi = min(len(trajectory), first_fire_step + 25)
        dense_window = trajectory[lo:hi]

    return dict(
        pair=dict(pc_i=I, l2e_j=J),
        config=dict(coincidence_weight=coincidence_weight, d_max=d_max, d_init=d_init,
                    eta=eta, n_train_steps=n_train_steps, projected_events=projected_events,
                    n_feedback_alone_steps=N_FEEDBACK_ALONE_STEPS,
                    trace_retention=e.prediction_active_dendrite_trace_retention,
                    prediction_threshold=e.prediction_threshold),
        requirements=dict(
            req1_immature_phase_zero_spikes=req1_pass,
            req2_transition_matches_pre_update_semantics=req2_pass,
            req3_mature_phase_always_fires=req3_pass,
            req4_feedback_alone_never_fires=req4_pass),
        immature_fire_count=immature_fire_count,
        first_fire_step=first_fire_step,
        transition_detail=transition_detail,
        d_final=d_final,
        feedback_alone_fires=feedback_alone_fires,
        feedback_alone_trajectory=feedback_alone_trajectory,
        train_trajectory_coarse_every_50_steps=coarse,
        train_trajectory_dense_around_transition=dense_window,
        verdict='PASS' if overall_pass else 'FAIL',
    )


def part2_natural_rate():
    """Real, unforced engine on a real pattern ('row 1') -- measures the
    ACTUAL physical same-step coincidence rate for the pattern's own causal
    first-responder, with no forced delivery anywhere in this function."""
    e = SimulationEngine(seed=1, topology_seed=1, **DASHBOARD_PRESET,
                          prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
    e.set_pattern('row 1')

    responder_counts = np.zeros(N_OUT)
    pixel_counts = np.zeros(N_PIX)
    for _ in range(NATURAL_PILOT_STEPS):
        e.step()
        for j in range(N_OUT):
            if e.spiked.get(f'L2E{j}'):
                responder_counts[j] += 1
        for i in range(N_PIX):
            if e.spiked.get(f'L1E{i}'):
                pixel_counts[i] += 1

    responder_j = int(np.argmax(responder_counts))
    # Direct measurement: replay with a trivially-low coincidence weight (0)
    # so _active_dendrite_event's own same-step AND-gate becomes a pure
    # coincidence detector (the weight-maturity clause is satisfied
    # unconditionally) -- reads the SAME production code path (the real
    # _active_dendrite_event method and its telemetry), no detection logic
    # duplicated here. Fresh engine/seed so Part 1's forced delivery never
    # contaminates this pilot.
    e3 = SimulationEngine(seed=1, topology_seed=1, **DASHBOARD_PRESET,
                           prediction_column_enabled=True, prediction_active_dendrite_enabled=True,
                           prediction_active_dendrite_coincidence_weight=0.0)
    e3.set_pattern('row 1')
    coincidence_count_per_pixel = np.zeros(N_PIX)
    for _ in range(NATURAL_PILOT_STEPS):
        e3.step()
        for i in range(N_PIX):
            rec = e3._active_dendrite_last_probe.get(i)
            if rec is not None and rec['fired']:
                coincidence_count_per_pixel[i] += 1

    target_i = int(np.argmax(coincidence_count_per_pixel))
    rate = float(coincidence_count_per_pixel[target_i]) / NATURAL_PILOT_STEPS

    eta = e.prediction_active_dendrite_learning_rate
    d_max = e.prediction_feedback_max
    d_init = e.prediction_feedback_init
    coincidence_weight = e.prediction_active_dendrite_coincidence_weight
    u0 = 1.0 - d_init / d_max
    u_target = 1.0 - coincidence_weight / d_max
    projected_events = (1.0 / u_target - 1.0 / u0) / (eta / d_max)
    projected_real_steps = (projected_events / rate) if rate > 0 else float('inf')

    result = dict(
        pilot_steps=NATURAL_PILOT_STEPS,
        causal_first_responder_l2e_j=responder_j,
        responder_counts=responder_counts.tolist(),
        target_pixel_i=target_i,
        measured_coincidences_in_pilot=float(coincidence_count_per_pixel[target_i]),
        measured_coincidence_rate_per_step=rate,
        projected_events_needed=projected_events,
        projected_real_outer_steps_needed=projected_real_steps,
        note=("Projection only, per the explicit instruction not to reuse a short "
              "window and interpret non-maturation as failure. Actually run below "
              "only if within this script's own budget."),
    )

    if rate > 0 and projected_real_steps <= NATURAL_RUN_BUDGET_STEPS:
        e4 = SimulationEngine(seed=1, topology_seed=1, **DASHBOARD_PRESET,
                               prediction_column_enabled=True, prediction_active_dendrite_enabled=True)
        e4.set_pattern('row 1')
        n_run = int(projected_real_steps * 1.2) + 100
        matured_at = None
        for step_idx in range(n_run):
            e4.step()
            if e4.pcol[target_i]._weights_array[responder_j] >= coincidence_weight:
                matured_at = step_idx
                break
        result['actually_ran_steps'] = n_run
        result['natural_maturation_observed'] = matured_at is not None
        result['natural_maturation_step'] = matured_at
    else:
        result['actually_ran_steps'] = None
        result['natural_maturation_observed'] = None
        result['natural_maturation_step'] = None
        result['reason_not_run'] = ('zero measured coincidence rate' if rate == 0
                                    else f'projected {projected_real_steps:.0f} steps exceeds budget {NATURAL_RUN_BUDGET_STEPS}')

    return result


def main():
    part1 = part1_isolated_logic()
    part2 = part2_natural_rate()

    results = dict(part1_isolated_logic=part1, part2_natural_rate=part2,
                   verdict=part1['verdict'])

    with open('phase34_gate_a_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Gate A Part 1 (isolated logic) verdict: {part1['verdict']}")
    for k, v in part1['requirements'].items():
        print(f"  {k}: {v}")
    print(f"  first_fire_step={part1['first_fire_step']}  eta={part1['config']['eta']}  "
          f"projected_events={part1['config']['projected_events']:.1f}  n_train_steps={part1['config']['n_train_steps']}")
    print(f"  transition_detail={part1['transition_detail']}")
    print()
    print("Gate A Part 2 (natural coincidence-rate measurement):")
    print(f"  causal_first_responder_l2e_j={part2['causal_first_responder_l2e_j']}  "
          f"target_pixel_i={part2['target_pixel_i']}")
    print(f"  measured_coincidence_rate_per_step={part2['measured_coincidence_rate_per_step']:.6f}")
    print(f"  projected_real_outer_steps_needed={part2['projected_real_outer_steps_needed']:.1f}")
    print(f"  natural_maturation_observed={part2['natural_maturation_observed']}  "
          f"natural_maturation_step={part2['natural_maturation_step']}")
    return results


if __name__ == '__main__':
    main()
