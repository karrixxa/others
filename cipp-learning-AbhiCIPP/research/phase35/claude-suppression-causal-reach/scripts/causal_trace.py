"""Phase 35 predictive-suppression causal-reach audit. Measurement-only.

Two analyses, kept explicitly separate because they answer different
questions and must not be conflated:

1. WITHIN-C matched comparison (primary causal-reach evidence): C's own
   L1I does not fire every time PC_i spikes (it needs ~2 accumulated
   deliveries before crossing its own threshold, given
   L1I_FEEDBACK_REFRACTORY=2 and no leak). That gives a natural
   "PC spiked, L1I delivered" vs "PC spiked, L1I did not deliver" split
   INSIDE ONE CONSISTENT ENGINE/REGIME (C), which isolates PC's specific
   causal contribution without needing engine B at all.

2. B-vs-C comparison (secondary, explicitly caveated): B's L1I is not
   silent -- it still receives the full legacy global L2E-winner broadcast
   every step (inh.receive_input(l2e, t=t)), a completely different, much
   more frequent trigger than C's rare PC-driven single-pixel delivery.
   B and C can therefore diverge for reasons that have nothing to do with
   PC's specific spike events -- this comparison answers "does the whole
   selective-vs-global regime differ", not "does this one PC event reach
   L2", and is reported as such, not conflated with analysis 1.

Reuses Stage 1 natural maturation, clone_engine, and make_bc unchanged from
the prior mature-efficacy experiment. No production file touched.
"""
import json
import sys
import time

sys.path.insert(0, "/tmp/claude-275450548/-home-cxiong-others-cipp-learning-AbhiCIPP/55d19a97-a1ec-436c-ada9-dbb060f69996/scratchpad/mature_efficacy_scripts")
import lib
from backend.simulation import N_OUT, N_PIX

HELD_PATTERN = "row 1"
TRACE_WINDOW = 1500


def snap(e, active):
    return dict(
        t=e.timestep,
        l1e_potential={i: float(e.l1.excitatory_neurons[i].potential) for i in active},
        l1e_spiked={i: bool(e.spiked.get(f'L1E{i}', False)) for i in active},
        l1i_potential={i: float(e.l1.inhibitory_neurons[i].potential) for i in active},
        l1i_spiked={i: bool(e.spiked.get(f'L1I{i}', False)) for i in active},
        l1i_feedback_delay_register={i: float(e.l1i_feedback_delay[i]) for i in active},
        pc_spiked={i: bool(e.spiked.get(f'PC{i}', False)) for i in active},
        l2e_potential={j: float(e.l2.excitatory_neurons[j].potential) for j in range(N_OUT)},
        l2e_spiked={j: bool(e.spiked.get(f'L2E{j}', False)) for j in range(N_OUT)},
    )


def trace_one_seed(seed):
    active = lib.active_pixels(HELD_PATTERN)
    stage1_result, checkpoint = lib.run_stage1(seed, pattern=HELD_PATTERN)
    if checkpoint is None:
        return dict(seed=seed, verdict="NATURAL_THREE_PIXEL_MATURITY_NOT_REACHED")

    ok, detail = lib.verify_engine_independence(checkpoint)
    b, c, l1i_reshape_log = lib.make_bc(checkpoint)

    traj_b, traj_c = [], []
    for _ in range(TRACE_WINDOW):
        before_b, before_c = snap(b, active), snap(c, active)
        b.step()
        c.step()
        after_b, after_c = snap(b, active), snap(c, active)
        traj_b.append(dict(before=before_b, after=after_b))
        traj_c.append(dict(before=before_c, after=after_c))

    # -------------------- Analysis 1: within-C matched comparison --------
    pc_events = []  # every PC_i spike event in C
    for idx, rec in enumerate(traj_c):
        t = rec['before']['t']
        for i in active:
            if rec['after']['pc_spiked'][i]:
                pc_events.append(dict(
                    pixel=i, idx=idx, pc_spike_t=t,
                    l1i_before=rec['before']['l1i_potential'][i],
                    l1i_after=rec['after']['l1i_potential'][i],
                    local_i_delivered=rec['after']['l1i_spiked'][i],
                ))

    # For each event where L1I delivered (fired) this step, look at t+1:
    # did L1E_i fire, and did L2's spike set that step contain the natural
    # leader / differ from the OTHER (undelivered) group's typical outcome.
    delivered = [e for e in pc_events if e['local_i_delivered']]
    undelivered = [e for e in pc_events if not e['local_i_delivered']]

    def outcome_at_next_step(e, active):
        nxt = e['idx'] + 1
        if nxt >= len(traj_c):
            return None
        rec = traj_c[nxt]
        i = e['pixel']
        return dict(
            t=rec['before']['t'],
            register_active=rec['before']['l1i_feedback_delay_register'][i] > 0.5,
            l1e_fired=rec['after']['l1e_spiked'][i],
            l2e_spike_set=sorted(j for j in range(N_OUT) if rec['after']['l2e_spiked'][j]),
            l2e_potential=rec['after']['l2e_potential'],
        )

    delivered_outcomes = [o for e in delivered if (o := outcome_at_next_step(e, active)) is not None]
    undelivered_outcomes = [o for e in undelivered if (o := outcome_at_next_step(e, active)) is not None]

    def rate(outcomes, key_fn):
        if not outcomes:
            return None
        return round(sum(1 for o in outcomes if key_fn(o)) / len(outcomes), 4)

    leader = stage1_result['final_leader']
    within_c = dict(
        total_pc_events=len(pc_events),
        delivered_events=len(delivered),
        undelivered_events=len(undelivered),
        delivery_rate=round(len(delivered) / len(pc_events), 4) if pc_events else None,
        l1e_fire_rate_given_delivered=rate(delivered_outcomes, lambda o: o['l1e_fired']),
        l1e_fire_rate_given_undelivered=rate(undelivered_outcomes, lambda o: o['l1e_fired']),
        leader_l2e_fire_rate_given_delivered=rate(delivered_outcomes, lambda o: leader in o['l2e_spike_set']),
        leader_l2e_fire_rate_given_undelivered=rate(undelivered_outcomes, lambda o: leader in o['l2e_spike_set']),
        any_l2e_fire_rate_given_delivered=rate(delivered_outcomes, lambda o: len(o['l2e_spike_set']) > 0),
        any_l2e_fire_rate_given_undelivered=rate(undelivered_outcomes, lambda o: len(o['l2e_spike_set']) > 0),
    )

    # -------------------- Analysis 2: B vs C, explicitly caveated ---------
    b_l1i_total_fires = sum(1 for rec in traj_b for i in active if rec['after']['l1i_spiked'][i])
    c_l1i_total_fires = sum(1 for rec in traj_c for i in active if rec['after']['l1i_spiked'][i])
    b_l1e_fire_counts = {i: sum(1 for rec in traj_b if rec['after']['l1e_spiked'][i]) for i in active}
    c_l1e_fire_counts = {i: sum(1 for rec in traj_c if rec['after']['l1e_spiked'][i]) for i in active}

    leader_b, tied_b, totals_b = lib.find_leader(b, active)
    leader_c, tied_c, totals_c = lib.find_leader(c, active)

    b_vs_c = dict(
        b_l1i_total_fires_across_3_pixels=b_l1i_total_fires,
        c_l1i_total_fires_across_3_pixels=c_l1i_total_fires,
        note="B's L1I fires from the LEGACY GLOBAL broadcast (every step some L2E wins), NOT from PC -- "
             "this is why b_l1i_total_fires is not simply 0; it is a different mechanism entirely, "
             "not the absence of one.",
        b_l1e_fire_counts=b_l1e_fire_counts,
        c_l1e_fire_counts=c_l1e_fire_counts,
        ownership_leader_b=f"L2E{leader_b}", ownership_leader_c=f"L2E{leader_c}",
        ownership_changed=(leader_b != leader_c),
    )

    result = dict(
        seed=seed,
        stage1_leader=leader,
        stage1_matured_step=stage1_result['matured_step'],
        independence_ok=ok,
        trace_window=TRACE_WINDOW,
        within_c_matched_comparison=within_c,
        b_vs_c_whole_regime_comparison=b_vs_c,
        sample_pc_events=pc_events[:40],
    )
    return result


if __name__ == "__main__":
    seed = int(sys.argv[1])
    out_path = sys.argv[2]
    t0 = time.time()
    result = trace_one_seed(seed)
    result["wall_seconds"] = round(time.time() - t0, 2)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"seed={seed} done in {result['wall_seconds']}s -> {out_path}")
