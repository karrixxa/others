"""
Shared engine presets (observability infrastructure). DASHBOARD_PRESET is the
exact configuration the live dashboard (backend/api.py) constructs its engine
with -- previously inline kwargs to one SimulationEngine(...) call, now a named,
importable dict so diagnostics/tests can run (or compare against) the SAME
preset the dashboard uses instead of silently drifting from it (see the Phase 1
audit, "preset parity" finding). No parameter VALUE was changed by this
extraction. Excludes `seed`, which is loaded/persisted separately (see
backend/api.py._load_seed/_save_seed).
"""

from __future__ import annotations

# The currently implemented dashboard runs the MINIMAL SIGNED-SPIKE experiment
# (see Claude_Minimal_Signed_Spike_Learning_Prompt.md and the README section).
# The feedforward rule is the signed one -- on fire, active inputs (+1) potentiate
# and inactive inputs (-1) depress through the direction-aware bounded kernel,
# with no weight budget. The active loop is charge -> fire -> local signed
# update -> unweighted L2I competitive reset/depression -> L1I feedback
# inhibition -> repeat. Uses refractory=0; refractory=1 is reserved for the next
# gate-redistribution architecture and is not active yet.
DASHBOARD_PRESET = dict(
    leak_enabled=False,
    l2i_leak_enabled=False,
    l1i_leak_enabled=False,
    l1i_immediate_relay=False,
    l2e_init_mode='legacy_wide',  # balanced initialization is opt-in
    signed_spike_learning=True,   # signed +1/-1 feedforward learning (the algorithm)
    # Plasticity gate p = (theta - sum(positive afferent weights)) / theta, clamped to
    # [eta_floor, 1] -- the structural free-energy gate. It REPLACES the closeness term
    # (theta/v_pre) in the signed rule, so the basic nonlinear update becomes
    #   dw = eta * p * (1 - (w/w_cap)^2) * signal,   p = max(eta_floor, 1 - sum_w+/theta).
    # An under-built neuron (sum_w+ << theta) is fully plastic (p~1); one whose positive
    # support already covers a threshold crossing (sum_w+ >= theta) gates to the floor
    # (consolidated). Normalized by theta so p stays in [0,1] (raw theta - sum_w+ would
    # be ~1000 in fixed point and blow the weights up). Floor keeps mature neurons from
    # freezing completely; set structural_fe_eta_floor=0 for the pure theta-sum form.
    structural_free_energy=True,
    structural_fe_eta_floor=0.02,
    # Distance factor (toggleable): each L2E feedforward synapse delivers
    # weight * (d_ref/d)^2, where d = euclidean distance between the L2E neuron and
    # its source pixel (set from the 3D layout in _build). The 1/d^2 SHAPE is fixed
    # (power=2): a farther pixel always contributes LESS charge than a nearer one
    # (ratio = 1/d^2, "dissipating along the axon"). d_ref is the reference distance
    # that sets the absolute scale. d_ref = 7.472 is the FARTHEST L2E<->pixel distance
    # in this layout (N_OUT=8 ring), so EVERY factor is >= 1 (nearest ~3.5x .. farthest
    # 1.0x) -- the "floating-point factors greater than one" requirement. This also
    # keeps the network alive: the un-attenuated net barely fires (bootstrap is
    # marginal), so any factor < 1 (e.g. literal 1/d^2 from d_ref=1 -> 0.02..0.06)
    # silences L2E entirely. NB: d_ref tracks the geometry's max distance -- if N_OUT
    # or the layout changes, recompute (grep _apply_l2e_distances). Stored weights are
    # untouched; this scales DELIVERY only.
    distance_weighting=True,
    distance_power=2.0,
    distance_ref=7.472,
    distance_min=1.0,
    l2e_budget=False,             # no positive-weight budget; -1 signal supplies down-pressure
    confidence_consolidation=False,
    # Competitive depression (canonical, default ON): on an L2I hard-reset event
    # each losing L2E depresses only the POSITIVE feedforward weights whose L1E
    # sources participated in its (losing) response, scaled by its own pre-reset
    # charge (p_loss) through the shared bounded kernel -- the structural half of
    # the reset event (see L2_Hard_Reset_Competitive_Depression_Spec.md and
    # Neuron.apply_competitive_reset). No learned inhibitory magnitude; the rate is
    # the L2E's own learning_rate (eta_loss is not used and is removed here).
    loser_depression=True,
    # Assembly-flow credit lets a habitual winner's L2E->L2I synapse climb to
    # self-sufficiency so L2I fires in rhythm -- it removes the last-volley-only
    # credit that stalled the E->I synapse below threshold (the L2I firing deadlock).
    # Runs off L2I's own discharge. See Flow_Credit_Dynamics_Explained.md and
    # Inhibition_And_Consolidation_State.md. ARCHIVED (default OFF): in practice the
    # minimal substrate -- excitatory flow-rate + hard-reset inhibition -- is all
    # that's needed, so flow credit is off by default (still togglable in Advanced).
    assembly_flow_credit=False,   # flow-proportional E->I credit on L2I/L1I fire
    # No down-weighting of the E->I "assembly evidence" synapses: keep the credit
    # (contributors still climb to self-sufficiency) but zero the decay term so a
    # non-contributing L2E->L2I synapse is NOT pushed toward the floor (1). With the
    # old 0.5 decay, training one pattern sank every OTHER pattern's L2E->L2I to the
    # floor, so on a pattern switch the new winner's L2E->L2I was too weak to fire
    # L2I -> no lateral inhibition and competition stalled. (Applies to L1I too.)
    assembly_decay_frac=0.0,
    signed_depression=False,      # superseded by the unified signed rule
    homeostasis=False,
    # L2I hard-reset losers (canonical, default ON;
    # L2_Hard_Reset_Competitive_Depression_Spec.md): once L2I declares a winner,
    # every non-winning L2E receives an UNWEIGHTED competitive-reset event -- its
    # pre-reset charge is captured for competitive depression, then its membrane is
    # clamped back to rest so losers no longer start the next race ahead. There is
    # no learned L2I->L2E gate magnitude; the reset is binary and complete.
    # hard_reset_clear_traces also zeroes the current traces so no residual flow
    # refills the membrane.
    l2i_hard_reset_losers=True,
    hard_reset_clear_traces=True,
    # ARCHIVED: the inhibitory DIFFERENTIATING (turnover) rule is retained only for
    # generic weighted inhibitory synapses and old experiments. Active L2 competition
    # has no L2I->L2E gate, so this setting is inert for the dashboard L2E pool.
    inhibitory_delta_rule=False,
    # SWAP + NEUTER: the trace-based flow-rate delivery is GONE from the active model
    # and chunked charge (K=20) is the new timing mechanism. Instead of rate-limiting
    # charge ARRIVAL through a decaying current trace, deliver each step's L1->L2E
    # feedforward drive in 20 equal chunks (weight_ji/20 per active synapse) WITHIN one
    # frozen outer timestep, re-running the argmax WTA after each chunk and stopping at
    # the first threshold-crosser -- "who would have won as the charge trickles in?".
    # excitatory_flow_rate is passed False here for clarity, but the engine ALSO pins
    # it (and the other trace/flow flags) off in _build, so it can't be re-enabled via
    # config; its dashboard toggle is hidden. The flow-rate/current-trace CODE remains
    # in place (reversible) but is dead on the active path. See SimulationEngine._build.
    excitatory_flow_rate=False,
    l2_charge_chunks=20,
    # L2I delivers charge INSTANTLY (flow off for L2I only): a trained L2E->L2I
    # synapse (weight == L2I threshold) then fires L2I from a SINGLE spike -- the
    # single-source relay. Under flow, one spike's charge spreads over decaying
    # steps while L2I leaks, peaking at only ~0.6x the weight, so no single spike
    # could ever cross (the weight is capped at threshold). L2E keeps flow for its
    # own overshoot control; this override is L2I-only.
    l2i_excitatory_flow_rate=False,
    # (The learned L2I->L2E gate is gone -- L2 competition is the unweighted hard
    # reset + competitive depression above. l2_gate_eq_frac / l2_gate_eta are no
    # longer set here; the constructor still accepts them for old experiments but
    # they build no gate in SimulationEngine.)
    refractory=0,                 # inhibition regulates frequency, not a hard lockout
    # Capacity rule: per-afferent cap = thr/3 so three strong active afferents reach
    # threshold (3-pixel lines); positive floor = 1; each I threshold = its E's / 3.
    l2e_weight_cap_frac=1 / 3,
    pos_weight_floor=1,
    l2i_threshold_frac=1 / 3,     # L2I threshold = threshold_l2 / 3
    l1i_threshold_frac=1.0,       # L1I threshold = L2I threshold
    l2e_lr_frac=0.02,             # L2E feedforward learning rate (fraction of the cap)
    ei_sat_mult=4.0,              # push E->I saturation above the clip so L2E->L2I reaches
                                  # the cap and L2I can sharpen into a single-source relay.
)
