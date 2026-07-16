# CLAUDE_HANDOFF.md

## Branch / HEAD

- Branch: `july14-integration` (created from `july14`)
- HEAD at creation: `6195ef8` (july14 was clean, up to date with
  `origin/july14`)
- Phase 0 checkpoint commit: `b02cd9e` (added `CLAUDE.md` +
  `CLAUDE_HANDOFF.md`)
- Phase 1 audit checkpoint commit: `225b8b1` (`Geometric_Influence_Temporal_Winner_Audit.md`)
- Phase 2 Milestone 1 checkpoint commit: `9163da2` (backend observability core)
- Phase 2 END checkpoint commit: `05c17a0` (frontend, phase complete)
- Phase 3 END checkpoint commit: `0e353cd` (seeded engine-owned geometry)
- Phase 4 END checkpoint commit: `586d0f7` (connection distance/influence,
  isolated experimental behavior)
- Phase 5 END checkpoint commit: `ff3048f` (diagnostic interleaved-presentation
  schedule)
- Phase 6 END checkpoint commit: `aa271fc` (representation candidate == first
  physical L2E threshold crossing)
- Phase 7 END checkpoint commit: `d946ff0` (physical L2I competition —
  causal, delayed L2E→L2I→L2E events)
- Phase 8 END checkpoint commit: `c0ac363` (exact local free-energy learning)
- Phase 9 END checkpoint commit: `3dd6f4c` (causal L1I predictive feedback)
- Phase 10 END checkpoint commit: `d333945` (adaptive-threshold ablation)
- Phase 11 END checkpoint commit: `1a59ae8` (controlled multi-seed validation)
- Phase 12 END checkpoint commit: `e4ee1f9` (final local review, DO NOT
  PUBLISH — the last phase of the corrected Phases 6-12 sequence)
- Phase 13 END checkpoint commit: `6655cfe` (dashboard behavior diagnostic,
  measurement only)
- Phase 13b END checkpoint commit: `4457f3b` (corrected and strengthened
  dashboard behavior diagnostic, measurement only)
- Phase 14 END checkpoint commit: `30a8cff` (UI-only observability — display
  controls, spike-raster restoration, terminology/provenance clarity; no
  neural dynamics/parameters/timing/learning/seeds/defaults changed)
- Phase 15 END checkpoint commit: `18bb5f3` (local developmental protection
  from L2I loser depression — new, default-off, NOT promoted)
- Phase 16 END checkpoint commit: `030fffe` (adaptive-threshold x
  developmental-protection factorial + spare-capacity challenge,
  measurement only)
- Note: origin received a separate direct push (`3a5f158`, "Add files via
  upload" -- the two `LPS_Lecture_14_*.txt` notes) based on `20d6b45`,
  diverging from local `030fffe`. Reconciled with a conflict-free local
  merge (`055b30f`), not pushed, before Phase 17 began.
- This update corresponds to the **Phase 17 END** checkpoint (LPS Lecture
  14 architecture mapping + isolated pre-trained-L2I-recruitment
  experiment -- named Phase 17, not Phase 16, since Phase 16 was already
  taken by the factorial above; new mechanism is default-off and NOT
  promoted -- commit hash filled in after this commit lands, see repo log).
- Phase 18 END checkpoint commit: `3fef508` (LPS Lecture 14 prediction
  architecture contract, docs only -- eight-predictor-per-L2E topology,
  now SUPERSEDED, see below).
- Phase 18b (first correction) END checkpoint commit: `3e43cca` (corrected
  per-input-column contract with an all-to-all L2Ej->Pi decoder but no
  lateral connection, decoder gated on L2Ej's spike -- also now SUPERSEDED).
- Note: origin/HEAD independently advanced to `d91e7f7` ("Phase 19A:
  corrected prediction scaffold" -- a per-column P0..P8 scaffold with a
  stored decoder matrix and fixed Pi->L1Ei replay, no active learning rule)
  from a concurrent session on the same checkout. Preserved as real history
  (not rewritten); its own uncommitted config/UI continuation was found and
  preserved on `backup/phase19a-scaffold-config-ui-wip`.
- This update corresponds to **Phase 18b-v2 / Phase 19-v2**: the final,
  transcript-faithful S_i/PC_i/I_i LOCAL-COINCIDENCE architecture --
  `Phase18b_Lecture14_Local_Coincidence_Architecture_Contract.md` (contract)
  and `Phase19_Local_Coincidence_Shadow_Report.md` (implementation +
  calibration + diagnostic + promotion-bar verdict). New, separate,
  mutually-exclusive-with-every-prior-mechanism flag
  `prediction_column_enabled` (default OFF, not promoted). Pattern
  selectivity within a single hold is clean (precision 1.0, all 4
  patterns); across continuous pattern switching (50-cycle diagnostic,
  `phase19_switch_boundary_diagnostic.py`) a real 2.92% false-prediction
  rate from previous-pattern carryover exists with no gap/clearing (0% with
  either a washout gap or an explicit boundary-clear diagnostic control,
  neither adopted as the primary mechanism) -- promotion bar to `PCi->Ii`
  does NOT fully pass; `PCi->Ii->Si` stays unimplemented. Every prior
  prototype (eight-predictor, Phase 18b's first correction, Phase 19A) is
  preserved unmerged on its own backup branch, never deleted or rewritten --
  see `backup/phase19-candidate-a-wip`, `backup/phase19-eight-predictor-wip`,
  `backup/phase19a-scaffold-config-ui-wip`, `backup/phase19-corrected-prediction`.
- Phase 20 (measurement only, no new flag): `Phase20_Frozen_Reconstruction_
  Report.md` + `test_phase20_frozen_reconstruction.py` +
  `phase20_frozen_reconstruction.py`. Adapted the original decoder->L1E-
  replay spec to the corrected architecture (no such replay path exists by
  design) -- reconstruction is measured directly at the PCi population from
  a cued L2E. HONEST NEGATIVE RESULT: realistic training (60 interleaved
  cycles, or 50,000 steps of a single uninterrupted hold) never matures
  R_j->PCi feedback weights past a ~50-64 plateau reached by step 10,000 --
  far below the ~500 threshold needed for feedback-alone firing, so cueing
  any owner (realistically trained) reconstructs nothing. A manually-
  matured decoder (explicit test control, not normal operation) DOES
  reconstruct correctly with precision/recall 1.0, no center-only collapse,
  no runaway, no false L2E activation -- confirming the architecture/
  cueing mechanism itself is sound; the gap is specifically that Phase 19's
  calibrated learning rate never reaches maturity under realistic training.
- Phase 21 (new flags, default OFF): `prediction_column_to_i_enabled`
  (selective PCi->Ii input topology, replacing L1I's global N_OUT-wide
  feedback with a single paired-PCi input) and `pretrained_l1i_regulation`
  (fixed vs learned L1I regulation, kept as a SEPARATE factorial variable).
  First phase where PCi's own output affects any other neuron (Phases
  19-20 were shadow-only). POSITIVE RESULT: the selective topology breaks
  all-nine L1I synchronization completely (0.42-0.48 -> 0.00) and gives
  EXACT per-pixel selectivity (inactive columns receive precisely zero
  PCi-driven drive over a 3000-step hold) -- works cleanly as intended.
  Honest trade-off: weaker overall suppression than global feedback (PCi
  fires far less often than L2E, so L1E's duty cycle is higher under the
  selective topology) -- a direct, expected consequence of Phase 19/20's
  sparse PCi firing rate. Two regression bugs found and fixed during
  implementation (same class as Phase 19's PC distance-weighting fix): a
  generic per-neuron distance-weighting sweep and a generic learning_rate
  sweep both silently corrupted the new flags' state; both are now guarded
  by dedicated tests. See `Phase21_Selective_Inhibition_Report.md`.
- Phase 22 (measurement only, no new flag): full 2x2 interaction of
  `pretrained_l2i_recruitment` (Phase 17) x `prediction_column_to_i_enabled`
  (Phase 21), across short/equal/long schedules, 2 seeds, plus a novel-
  pattern spare-capacity challenge per condition. Confirms both mechanisms'
  individual findings persist unchanged in combination (Phase 17's tyranny,
  Phase 21's exact selectivity + all-nine-sync=0), and that they are
  otherwise ORTHOGONAL (PC's own precision/fired-set is byte-identical
  whether or not L2I is pretrained). Selective inhibition does NOT fix
  Phase 17's tyranny (no mechanistic reason it should -- disjoint causal
  pathways). POSITIVE finding: novel-pattern spare-capacity recruitment
  survives even severe upstream tyranny in 7/8 trials; the one exception
  was the single most extreme collapse (one L2E as literally the only
  neuron with any learned structure at all). See
  `Phase22_Full_Interaction_Report.md`.
- Phase 23 (measurement only, no new flag, no production code touched):
  L1E frequency across 6 conditions. KEY FINDING: the baseline (no
  prediction at all) sits closest to 0.5 (0.528) -- Phase 17's established
  false positive, reconfirmed; genuine selective PC-driven inhibition sits
  FURTHER from 0.5 (0.834), not closer, because it delivers weaker overall
  suppression (Phase 21's finding). Forcing an INCORRECT (wrong-pixel)
  prediction produces frequency (0.854) statistically indistinguishable
  from CORRECT prediction (0.834) -- frequency alone cannot tell them
  apart. This FAILS Phase 24's explicit gate ("proceed only if Phase 23
  establishes a nontrivial frequency<->correct-prediction relationship").
  See `Phase23_Frequency_Measurement_Report.md`.
- Phase 24: GATED OFF, no implementation. Phase 23 established the
  opposite of what the gate required (frequency near 0.5 is the false-
  positive baseline, not genuine prediction; frequency cannot distinguish
  correct from incorrect prediction at all). See
  `Phase24_Frequency_Learning_Stop_Gate_Report.md`.
- Phase 25: GATED OFF, no implementation. Prediction signal is meaningful
  in DIRECTION (precision=1.0 decoder selectivity, Phases 19-22) but not in
  GROWTH DYNAMICS (Phase 20's weights plateau by step 10,000 because PCi
  stops firing, an upstream bottleneck free-energy has no mechanism to
  address). See `Phase25_Synapse_Free_Energy_Gate_Report.md`.
- Phase 26 (final validation, no code change): full backend suite
  re-confirmed clean -- 379 passed, 5 pre-existing failures (same flow-rate/
  assembly-flow-credit failures present since before this investigation), no
  new failures. Consolidated `Lecture14_Architecture_Validation.md` covering
  Phases 18-26: architecture actually implemented, per-phase outcome table,
  what stays default OFF, what remains conceptual/unresolved, full commit
  list, both regression bugs found/fixed, overall verdict ("partially
  validated" -- coincidence detection and selective inhibition work as
  designed; decoder maturation under realistic training and continuous-
  switching carryover remain open, honestly documented limitations). This
  is the closing checkpoint of the Lecture 14 investigation.
- Base branch `july14` is untouched and remains the protected base.
- `four-pattern` branch exists (checked out in a separate worktree at
  `/home/charisxiong/Documents/others`) and is explicitly NOT merged here —
  see `CLAUDE.md`.
- Phases 6-12 are now driven by the corrected prompt file at
  `/home/charisxiong/Downloads/July14_Phases_6_to_12_Corrected_Claude_Prompts.txt`
  (outside the repo — read it fresh each phase, do not rely on memory of it).
  Confirmed byte-for-byte consistent with what Phase 6/7 already implemented.

## Goal

Port relevant behavior from `four-pattern` into `july14-integration` by hand
(no merge), guided by
`July_14_Geometric_Influence_Temporal_Winner_Brief.txt`, while preserving the
architecture invariants in `CLAUDE.md`: four center-crossing patterns,
`N_OUT=8` (four active + four spare/recruitable L2E cells), no
pattern-to-neuron assignment/argmax/owner-lock/oracle/global
`normalizeW`/fake spikes/UI-side simulation.

**Phase 2 (complete) — Observability only:** added observability infrastructure
— shared pattern/probe metadata and dashboard preset, held-out probes with
presentation-scoped plasticity freeze, backend-driven Causal Story,
presentation IDs/boundaries, evidence-based receptive-field status,
actual-bounds Fit View, delivery/pre-post-integration diagnostics — with **no
neural equation and no preset value** changed.

**Phase 3 (complete) — Seeded engine-owned geometry only:** jittered/irregular
engine-owned positions (L1E jittered within its assigned cell, L1I paired near
its L1E, L2E placed irregularly with a minimum-separation constraint, L2I
fixed near center), seeded and fixed across reset/training/probes, changing
only on an explicit topology reseed, with the legacy symmetric ring/grid
preserved as a selectable ablation. A temporary legacy-distance-compatibility
shim kept `distance_weighting`'s delivered-charge numbers pinned to the legacy
reference geometry, so that phase changed **no neural dynamics**.

**Phase 4 (complete) — Connection distance/influence as isolated experimental
behavior:** adds FOUR NEW, fully independent experimental pathways —
L2E→L2I, L2I→L2E, L2E→L1I, L1I→L1E — each with its own default-OFF ablation
flag and one shared, configurable, safe-by-default power law (inverse-square,
pure attenuation). L1E→L2E's existing legacy pathway (Phase 2/3,
`distance_weighting`/`legacy_distance_compat`) is untouched. Every pathway
exposes source, target, distance, influence, raw weight, effective
transmission, and whether influence was actually applied, via
`pathway_influence_report()`/`GET /api/pathway_influence`. Influence is
applied **exactly once** per pathway, and none of the four new flags is
enabled by default anywhere, so the geometry-off and legacy-distance
baselines from Phases 2/3 are completely unaffected.

**Phase 5 (complete) — Diagnostic-only equal-interleaved presentation
schedule:** a standalone, non-mutating measurement tool (`diagnostic_schedule.py`)
implementing the brief's fixed cycle (row 1 → col 1 → diag \ → diag / →
repeat) with brief, non-saturating presentations, evaluated exclusively on
disposable deep-copies (plus a plasticity-frozen re-test copy). Reports
per-pattern consistency/ambiguity/no-response/distinct-owners/collisions/
forgetting/silent-recruitable-cells/L2I-activity/L1I-selectivity across
seeds. Zero engine/competition code changed — a 5-seed baseline was saved to
`Diagnostic_Schedule_Baseline.md`.

**Phase 6 (complete) — Representation candidate == first
physical L2E threshold crossing, per explicit user instruction:** `self.winner`
(the exposed representation candidate) is now set in EXACTLY one place — the
instant a presentation's first physical L2E threshold crossing occurs — and
never re-derived by argmax, index, hidden charge, weights, geometry, or UI
logic. This retires the Phase 1 audit's headline conflict with the brief (the
old `_resolve_episode()` "latest-spike-wins" mechanism, now fully removed —
confirmed unused by any test, script, or frontend file). A same-step tie
(more than one L2E eligible at the winning step) makes the response ambiguous:
`self.winner` stays `None` for the rest of that presentation, and neither the
evidence-crediting history nor L1I/L2I source attribution names a specific
neuron for it (reported as `'ambiguous'` instead) — while `physicalFirstSpiker`
itself is still recorded as a raw fact (which neuron the legacy tiebreak
physically let fire), kept separately observable from the credit-bearing
`self.winner`, exactly as the brief requires. New fields recorded per
presentation: `earliest_response_set` (the exact tied set, not just a
boolean), `later_responses` (the full ordered later-spike list), and
`latency_to_second_response`. The legacy immediate-reset competition
(`_resolve_l2_competition`'s argmax-over-potential tiebreak, which still
decides which ONE neuron physically fires when several cross threshold in the
same step) is deliberately left UNCHANGED and clearly documented in its own
docstring as the thing Phase 7 is expected to reconsider/replace — this phase
never touches physical dynamics (spike timing, membrane potentials, learning),
confirmed by `sustained_dominance.py`/`ablation_harness.py` reproducing the
exact Phase 1 numbers.

**Current phase (Phase 7, complete) — Physical L2I competition, per explicit
user instruction:** replaced the legacy immediate-reset tiebreak (single
argmax-charge "winner" fires, every other threshold-crosser is hard-reset to
rest in the SAME step) with a causal, delayed L2E→L2I→L2E event chain, per
brief SS9's "investigate the physical dynamics, do not resolve this with a
software exception." Every L2E that crosses threshold in a step now FIRES —
no argmax pick, nobody is denied a spike because another also crossed. Each
firer's event is logged as a contributor to L2I, which accumulates them
toward its OWN threshold exactly as before (unchanged from every prior
phase). Only once L2I itself fires does it SCHEDULE a delayed, uniform
inhibitory delivery — a fixed magnitude (`l2_inhibition_frac * threshold_l2`,
default 1.0) applied to all `N_OUT` L2E targets `l2_inhibition_delay` steps
later (default 1), never fewer, never singling anyone out by ID. Delivery is
a bounded, floor-limited membrane subtraction (`V = max(V - magnitude,
rest)`), not a forced clamp, and is skipped entirely on a target still in its
own post-spike refractory window (`Neuron.apply_delayed_inhibition`, which
replaces the retired `apply_competitive_reset`) — the same convention as
`apply_inhibition`, and the opposite of the retired method's "unconditional
even under refractory" behaviour. A neuron that fired to help trigger L2I
typically escapes its OWN consequence purely because it is still refractory
when the delivery lands — an emergent property of timing, never a software
exemption by index. Every requested fact is directly recorded, never
inferred: contributing sources + arrival times, L2I pre/post charge at its
own threshold crossing, the scheduled delivery record, the delivered
inhibition, and competitor pre/post charge, all exposed via
`dynamic_state()['l2_inhibition']` (`pending`/`last_delivery`/`log`). This
phase deliberately changes physical dynamics (the explicit point of the
instruction) — new baselines were captured and are EXPECTED to differ from
every prior phase's; see Known problems for what changed and why.

**Current phase (Phase 8, complete) — Exact local free-energy learning, per
the corrected Phases 6-12 prompt file:** the already-existing, already-named
`structural_free_energy` mechanism (ported earlier from
`Claude_Structural_Free_Energy_Prompt.md`, which deliberately left its
saturating term as "whatever the local cap/floor behavior is") is now pinned
to the EXACT specified equation when enabled:
`delta_w = LR * FE * (1 - w/w_max)^2 * learn_signal`, where `FE` is this
neuron's own `_structural_free_energy_gate()` (local: only this neuron's
positive-afferent sum vs its own threshold — no rivals, no labels, no
membrane voltage) and `learn_signal` is the existing +1/-1 signed-spike
convention. This REPLACES that branch's previous use of the shared
`bounded_signed_update` reflected kernel (`SignedSpikeRule.on_fire`, in
`snn/rules/excitatory.py`) with a new, separate helper
(`exact_local_free_energy_update`) so the two saturating shapes stay
distinguishable and `bounded_signed_update` itself (still used by the
non-FE signed path and by `apply_delayed_inhibition`'s Phase 7 depression
gain) is completely untouched. The new equation's envelope,
`(1 - w/w_max)^2`, is symmetric and reaches exactly zero at `w_max` in BOTH
directions — a fully-saturated weight cannot move further until it decays,
unlike the old reflected kernel which still permitted downward movement at
the cap. This is the literal, intended consequence of using the equation
exactly as specified, not an oversight. No global normalization,
pattern-to-neuron assignment, hidden-state argmax, or weight-based ownership
was added; the rule is purely per-neuron/event-driven (fires on THIS
neuron's own spike only) and therefore has no representative-specific credit
to withhold on an ambiguous same-step tie in the first place — verified
directly with a forced tie. Frozen probes are unaffected (the existing
`plasticity_frozen` guard at the top of `_update_weights` is unconditional
and was never touched).

**Current phase (Phase 9, complete) — Causal L1I predictive feedback, per the
corrected Phases 6-12 prompt file:** audited the existing L2E→L1I and
L1I→L1E paths before changing anything (documented below). Found and fixed a
genuine correctness gap in the shared `_credit_source` helper: it only
checked whether the presentation's very FIRST L2E spike was an ambiguous
same-step tie, so a LATER step's genuine multi-firer event (which Phase 7
made possible on any step, not just the first) could be mis-attributed to a
single L2E id instead of being reported `'ambiguous'`. `_credit_source` now
reads `self._last_eligible` (this step's actual firer set) directly at the
moment of attribution — fixing L1I attribution (this phase's explicit scope)
and, as a direct consequence of sharing one function, L2I attribution too
(the identical root cause; leaving one fixed and the other stale would have
been an inconsistent half-fix of the same mechanism). Added the requested
causal chain: `l1i_first_source_set` (the raw contributor id list, recorded
even when ambiguous), `l1i_first_arrival_t` (the step a real L2E delivery
reaches L1I — tracked separately from `l1i_first_t`, the step L1I itself
crosses threshold, since the default trainable-integrator mode can take
extra steps to accumulate), `l1i_first_targets` (which L1I units fired), and
`l1i_first_delivery` (the resulting one-step-delayed L1I→L1E pulse's
recorded `_inh_events` effect). None of this is inferred — every field reads
an already-decided physical event, never an index priority, hidden charge,
weight inspection, or oracle. L1I→L1E's spatially-paired (index-matched)
meaning was preserved exactly as-is (not touched); the audit reconfirmed
(and this phase's tests directly assert) that all 9 L1I units currently
share one literal feedback weight vector and receive an identical delivery
by default (`infl_l2e_l1i` off), so their synchrony is an honestly-reported
structural fact, not a fabricated per-unit distinction and not a software
broadcast shortcut (verified: `l1i_immediate_relay` defaults to False, and
the default trainable-integrator mode genuinely requires threshold crossing
— sabotaging L1I's weights/threshold confirms it does not fire).

**Current phase (Phase 10, complete) — Adaptive-threshold ablation, per the
corrected Phases 6-12 prompt file:** a new, separately-named, default-off
L2E-only mechanism (`adaptive_threshold`), fully independent of the existing
synaptic-scaling homeostasis feature (`homeostasis`) and of geometry -- not a
rename or silent reuse of either. Each L2E neuron maintains local state `a_i`
(`Neuron.threshold_adapt`): `effective_threshold = threshold + a_i`; on that
neuron's OWN physical spike, `a_i += delta_threshold` (`fire()`); every step,
`a_i` decays exponentially toward zero with time constant `tau_threshold`
(`update()`, independent of the membrane's own refractory/leak state -- decay
continues even while the neuron itself is refractory, since `a_i` is a
separate local memory). `check_threshold()` delegates straight to the
Membrane's own decision when the flag is off (byte-identical to every
existing caller, verified directly and via a full engine run comparing
`adaptive_threshold=False` explicit vs. the default). `delta_threshold_frac`
(0.05 default) and `tau_threshold` (25 steps default) are documented,
reasonable starting points, deliberately NOT swept or tuned to make any
particular seed succeed -- Phase 11 measures the effect, and Phase 10 does
not pre-judge it. State and trajectory are exposed per-neuron
(`threshold_adapt`/`effective_threshold`) and via a new top-level
`dynamic_state()['adaptive_threshold']` block (config + full per-neuron
history). A probe lets `a_i` evolve internally (real physical spikes during
the probe legitimately move it) but snapshots it beforehand and restores it
UNCONDITIONALLY afterward -- whether the probe elapses naturally or is
cancelled by manual input -- so probe evaluation can never alter subsequent
training. Isolation between neurons and deterministic replay are both
verified directly.

**Current phase (Phase 11, complete) — Controlled multi-seed validation, per
the corrected Phases 6-12 prompt file:** MEASUREMENT ONLY, no neural
parameter tuned. Crossed 4 geometry conditions (symmetric/jittered ×
influence off/on, where "influence" is the original L1E→L2E distance-
weighting pathway; Phase 4's four separate experimental pathways stay off,
per the standing "do not enable every pathway together" rule -- a documented
judgment call) × `adaptive_threshold` off/on (Phase 10) × 3 weight seeds × 2
topology seeds × 2 schedules (short-interleaved / long-saturation) = 96 runs,
all built from `DASHBOARD_PRESET` (not raw constructor defaults -- a real
confound caught and fixed mid-phase before trusting any number: the first,
discarded pass used raw defaults and produced systematically weaker,
non-representative results). `N_OUT` stayed 8 throughout. **The stated
success criterion (four distinct stable owners with spare neurons
recruitable) was not robustly met in any condition** -- the best cell
(short-interleaved, influence off, adaptive threshold on) reached it in 4/6
seed-topology combinations, a real and repeated improvement over the same
condition without adaptive threshold (2/6), but per the instruction's own
"do not count one lucky seed as success," 4/6 is a partial result, not a
pass. Full findings, aggregated tables, and explicit observations-vs-
conclusions sections are in `Phase11_Multiseed_Validation_Report.md`; raw
data in `phase11_validation_report.json` (96 records); the harness itself
(`phase11_validation.py`) and its saved report are both validated by
`test_phase11_validation.py` (6 tests: report shape/no-gaps, `N_OUT`
invariance, a mechanical null-result sanity check, harness determinism, and
a re-derivation of the report's own headline success count from raw data).

**Current phase (Phase 12, complete) — Final local review, per the corrected
Phases 6-12 prompt file. DO NOT PUBLISH:** no new neural mechanism
implemented, nothing tuned around Phase 11's results. Ran the full test
suite (254 passed, same 5 pre-existing failures) plus, for the first time in
this session, REAL end-to-end smoke checks against a live-server-shaped
`TestClient` (REST GET/POST config round-trip that actually changes engine
behavior, and a full WebSocket topology+dynamic exchange) -- closing the
"no httpx available" gap flagged in Phase 7's Known Problems.
**Audited backend/UI configuration agreement and found a real gap:**
`symmetric_geometry`/`legacy_distance_compat` (Phase 3, pre-existing) and
`l2_inhibition_delay`/`l2_inhibition_frac`/`adaptive_threshold`/
`delta_threshold_frac`/`tau_threshold` (Phases 7/10, introduced this
session) were all `TUNABLE` on the engine but absent from
`backend/api.py`'s `CONFIG_SPEC` -- fixed by adding all 7 entries, verified
via the live HTTP round-trip. **Audited for remaining software winner/tie-
break shortcuts:** the default/dashboard competition path
(`_resolve_l2_competition`, `_credit_source`) is clean; found exactly ONE
remaining hidden-charge argmax tiebreak, confined to the non-default,
pre-existing, unexercised `lasting_inhibition` alternate mechanism --
documented, not fixed (fixing it would be a new-mechanism change, barred by
this phase's own scope). Reviewed Phase 11's evidence against its stated
success criteria and reconfirmed: not met in any of 16 conditions across all
6 seed-topology combinations; the central one-to-one-ownership problem
remains open. Wrote `Phase12_Final_Local_Review.md` with all of the above,
plus an honest "Unresolved failures" list and the exact final commit
chain/working-tree status for handoff.

**Current phase (Phase 13, complete) — Dashboard behavior diagnostic,
MEASUREMENT ONLY, requested directly by the user (outside the Phases 6-12
prompt sequence, after observing "only 3 neurons are actively participating
with a tyrant" in the live dashboard):** no neural mechanism changed, no
parameter tuned. Built `dashboard_behavior_diagnostic.py` (new,
non-mutating instrumentation, same discipline as
`diagnostic_schedule.py`/`phase11_validation.py`) that wraps every L2E
neuron's `fire()`/`apply_delayed_inhibition()`/`_homeostatic_scaling()` and
`SimulationEngine.set_feedforward_weight()` to record every feedforward
weight delta with a directly-observed (never inferred) cause, timestep,
pattern, spiked flag, L2I delivery source/time, V_pre/threshold/p_loss,
active inputs, and weight before/delta/after. Ran seed=1 across the
dashboard default and two ablations (A: distance_weighting off, adaptive
off; B: distance_weighting off, adaptive on), both a row-1-then-col-1 hold/
switch and 40 rotations of the brief's 20-step equal-interleaved schedule
(reusing `diagnostic_schedule.CYCLE_ORDER`/`PRESENTATION_STEPS` directly).
Verified `topology()`'s serialized RF weights are byte-identical to the
engine's own `_all_weights()`/raw weight array (0 mismatches, every synapse,
every run). Headline findings: (1) zero non-spiking L2E weight increases in
any config -- every non-spiking delta is `l2i_loser_depression`, the only
non-spiking-triggered weight-mutating path active in these configs; (2) L2E5
does NOT form a union receptive field of row 1/col 1 -- it collapses onto
the one pixel shared by every trained pattern (the center) while its actual
distinguishing pixels decay to the weight floor, because the center pixel
never receives the signed rule's `-1` (depress) signal under any pattern;
(3) the self-spike exact-FE update's `(1-w/w_max)^2` envelope and the loser-
depression `bounded_signed_update` reflected kernel diverge sharply near the
cap (>1000x envelope-value gap at 97% of cap in an extended 150-cycle run),
though no weight fully saturated within the measured run length; (4) legacy
distance amplification of the center pixel is real but modest (~9.6%
relative to the mean of other pixels) -- the center pixel's dominance is
driven far more by its 100% pattern duty cycle than by distance; (5) turning
`distance_weighting` OFF (configs A/B) made recruitment measurably WORSE,
not better (4/8 active neurons in the dashboard default down to 1/8 in A,
3/8 in B) -- config B reproduces the reported "3 active neurons with a
tyrant" symptom almost exactly, ruling out distance-weighting as the fix to
reach for; (6) L2E0/L2E1 stay fully unrecruited (0 spikes) in every config,
consistent with unlucky `legacy_wide` random init plus loser-depression's
rich-get-richer entrenchment and no rescue mechanism for a neuron that never
got an early lead; (7) all nine L1I units remain fully synchronized in every
config (identical weight vectors, 100% all-nine-fire-together rate) --
confirmed structural, unrelated to distance/adaptive-threshold. Full
findings, the exact reproduction method, and every example record are in
`Phase13_Dashboard_Behavior_Diagnostic.md`; the compact aggregate data
backing every number is in `dashboard_behavior_diagnostic_summary.json`
(committed); the full per-event log (tens of MB) is a disposable `/tmp`
artifact, not committed, per this repo's own commit-hygiene rule.

**Current phase (Phase 13b, complete) — Corrected and strengthened
dashboard behavior diagnostic, MEASUREMENT ONLY:** found and fixed a real
methodology bug in Phase 13's own instrumentation -- it tagged loser-
depression weight-delta records with `engine.spiked[nid]` read at the
moment `apply_delayed_inhibition()` is called (the top of `step()`, before
that step's own competition runs), which is last step's result, not this
step's. Replaced with three explicitly-timed fields
(`spiked_previous_step`/`inhibited_at_start_of_step`/
`spiked_later_current_step`), verified by 11 new tracer-timing tests
against independently-reconstructed ground truth. Ran the FULL grid this
time -- weight seeds 1-5 x topology seeds 1-3 x 3 scenarios (20+20 hold/
switch, 600+200 hold/switch, 40-rotation interleaved) x 3 configs (A:
dashboard default distance-on/legacy-pinned; B: raw distance off; C: new,
diagnostic-only spatially-uniform delivery charge-matched to A's mean
influence, built by overriding `.distance` post-construction, no default
touched) = 135 runs, plus a 5-seed Phase-11-style distinct-owners pass for
direct reconciliation. **Corrected several Phase 13 overgeneralizations
drawn from seed=1 alone:** "distance off measurably worsens recruitment" is
WRONG as a general claim (B's mean active-neuron count roughly matches or
beats A across 5 seeds; seed=1 was an unlucky draw for B, not
representative) -- what IS seed-robust is that A trades variance for a
schedule-dependent mean effect that reverses direction (A better in short-
hold, worse in long-hold, roughly even in interleaved); the L2E5-specific
"union receptive field" framing was this session's own prompt's arbitrary
example, not an identified tyrant (L2E5 is tyrant in only 3/45 grid runs) --
but the underlying MECHANISM generalizes perfectly (the tyrant's single
highest weight is the always-active center pixel in 45/45 runs, every
config). New, quantified findings: never-fired neurons receive ~1,400-2,200
loser-depression hits each over a 3,200-step run with zero self-generated
event that could reverse it; `spiked_later_current_step` (a neuron hit by
delayed inhibition still firing later the SAME step) occurs in only 9/135
runs and EXCLUSIVELY under config A, never B or C -- it takes a spatially
concentrated amplification, not just an equal-average one, to rebuild
charge that fast. A genuine methodological finding surfaced by the tracer-
timing tests: `engine._l2_inhibition_log` is a `deque(maxlen=400)`, a
display-oriented rolling window that silently truncates on long runs --
this diagnostic's own exhaustive count, not that log's length, is the
correct "unique delivery events" figure once a run exceeds 400 deliveries.
**Reconciled with Phase 11's schedule-dependent distance/influence
finding:** Phase 11's "influence on" is REAL topology-jittered distance
(`legacy_distance_compat=False`); this phase's config A is the fixed,
legacy-PINNED distance the dashboard actually ships with
(`legacy_distance_compat=True`) -- a third condition Phase 11's own 2x2
geometry grid never tested (and Phase 11's own docstring claim that the
dashboard default sits inside its "influence-off" cell appears imprecise by
its own `_engine_kwargs` code -- flagged for human review, not edited, out
of this phase's scope). The two phases' specific manipulations and even
their schedule lengths differ (Phase 11's short-interleaved is 10 cycles/
800 steps; this phase's `interleaved_40` is 40 cycles/3,200 steps, per this
session's explicit instruction), so they should not be read as agreeing or
disagreeing at face value -- but Phase 13b's OWN axis independently
reproduces the SAME qualitative shape Phase 11 found (a schedule-dependent
reversal, not a uniform verdict), which is a stronger result than either
phase alone. Topology_seed confirmed a complete no-op for all three configs
(byte-identical final weights across topology_seed in {1,2,3} at a fixed
weight seed) since none of Phase 4's real-geometry-consuming pathways are
enabled here. Full findings, the explicit list of corrected Phase 13
claims, and every table are in `Phase13b_Diagnostic_Correction.md`; the
135-run grid plus the reconciliation pass are in
`phase13b_diagnostic_summary.json` (committed); full per-event logs are a
disposable `/tmp` artifact per the standing commit-hygiene rule.

**Current phase (Phase 14, complete) — UI-only observability, per explicit
user instruction: NO neural dynamics, parameters, timing, learning, seeds,
or defaults changed.** All changes are in `frontend/`; no `backend/*.py` or
engine file touched.

- **Network viewport (renderer.js/controls.js/index.html):** independent
  visibility toggles for L1E/L1I/L2E/L2I neurons and independent toggles for
  all five edge kinds (feedforward=L1E→L2E, excitation=L2E→L2I,
  reset_inhibition=L2I→L2E, feedback=L2E→L1I, inhibition=L1I→L1E — mapped
  from the synapse `kind` field via the new pure `edge_filters.js`). Hiding a
  layer hides only its own edges (an edge already hides when either endpoint
  is hidden — no separate bookkeeping needed). Added All/None/
  Excitatory-only/Inhibitory-only presets. Every control calls only
  `renderer.setFilters()` (pure local rendering state, never `/api/config`).
- **Spike raster (raster.js):** restored the older "spikes + charge buildup"
  mode alongside the preserved discrete-only default — a `showCharge` toggle
  ports charge.js's own dim-bar/dashed-threshold-guide/full-height-spike
  rendering verbatim (same source data, same CHARGE_CAP), so both modes read
  the identical recorded `dyn.neurons[].spiked`/`.activation` history; no
  second simulator, no frontend-side spike inference. Added toggles for hide-
  silent-lanes, presentation boundaries, inhibition/reset markers (ported
  from charge.js), first-response markers (new — filled dot = the recorded
  `first_spiker`, hollow ring on every id in `earliest_response_set` = a
  backend-recorded ambiguous same-step tie), and independent L1E/L1I/L2E/L2I
  lane toggles, all in a compact options drawer (the overlay covers the
  sidebar, so raster-only toggles live in the raster's own toolbar). Restored
  the hover tooltip (lane id/timestep/V-θ/SPIKE flag) from the historical
  `four-pattern`-branch raster (re-implemented by hand per `CLAUDE.md`, not
  merged/cherry-picked — that branch's exact commits are documented in the
  Phase 14 exploration notes for reference). Zoom/pan/pattern-label/firing-
  rate-indicator all continue working unchanged; the separate Charge/time
  view (`charge.js`) is completely untouched and still available.
- **Terminology (labels.js + index.html/charts.js/causal.js):** every visible
  "Winner" renamed to "First responder"; when `dyn.winner` is null because
  the current presentation's first response was a same-step tie
  (`causal_story.same_step_tie`), compact widgets show "Ambiguous" and the
  Causal Story tab shows "Ambiguous first response" instead of a generic
  dash — distinguishing that case from "no response yet" (also null). Only
  user-visible text was renamed; internal identifiers (`dyn.winner`,
  `COLORS.winner`, `.rf-winner`, etc.) are untouched since they're not
  user-facing and renaming them would be unnecessary risk.
- **Weight-change provenance (app.js `weightChangeCause()` +
  receptive.js/inspector.js):** RF grid cells and the inspector's synapse
  rows now show a hover/title tag identifying whether a feedforward
  synapse's most recent change was self-spike learning (the target L2E
  spiked this exact step) or L2I loser depression (the target appears in
  `dyn.l2_inhibition.last_delivery` with a nonzero `depressed` count, and
  that delivery's own `deliver_at` matches the current timestep) — both
  facts read straight off already-broadcast backend fields, never
  re-derived from anything the backend didn't already decide. Reports "both"
  when a neuron is hit by delayed inhibition at the top of a step and still
  fires later that same step (see Phase 13b's finding that this is rare and
  config-specific).
- **Config-rebuild warning (controls.js):** `#config-apply` now confirms
  before firing (same `window.confirm` pattern as Reset/Reseed), since
  `apply_config()` has no non-rebuilding path — every override rebuilds the
  network from fresh weights. View Controls' toggles never call
  `/api/config`, so they never trigger this warning.
- **View Controls (index.html/style.css):** the old "Display Filters" panel
  is renamed "View Controls," collapsed by default, and now holds both the
  viewport filters above and is the sole home for the new preset buttons —
  raster-specific toggles live in the raster overlay's own drawer instead
  (the overlay covers the sidebar).
- **Tests:** `frontend/edge_filters.js` and `frontend/labels.js` are new,
  deliberately dependency-free pure-logic modules (no DOM, no three.js)
  extracted specifically so they're testable — `frontend/
  test_phase14_logic.mjs` runs under Node's own built-in test runner
  (`node --test`, zero new dependencies) and covers the layer/edge filter
  mapping and the first-responder/ambiguous-tie label logic (4 tests, all
  passing). `frontend/package.json` (new) only sets `{"type":"module"}` so
  Node's loader treats these `.js` files as ES modules, matching how
  `index.html` already loads them via `<script type="module">` — browsers
  ignore this file entirely. No JS test framework existed in this repo
  before this phase; this is the practical shape of "focused tests" given
  the architecture (no build step, everything else DOM/three.js-coupled).
- **Verified live, not just read** (per this repo's `run` convention):
  launched `uvicorn backend.api:app` and drove it with a headless
  Playwright/Chromium session (installed into the session's throwaway venv;
  no project dependency added). Confirmed: toggling every View Controls/
  raster-options checkbox leaves `GET /api/state`'s synapse weights and the
  engine's timestep progression completely unaffected (fetched state before/
  after a full preset+edge-toggle sequence, byte-compared); the raster's
  hover tooltip and first-response/inhibition markers render correctly once
  real spike history exists; the RF grid's weight-change hover correctly
  shows "self-spike learning" during live training; the config-apply
  confirmation dialog fires with the correct warning text and is dismissable
  without applying; zero browser console errors across the whole sequence.
  Screenshots retained only in `/tmp` scratch space, not committed.
- Full backend suite re-run after all frontend edits (no backend file
  touched, but confirmed no regression anyway): **265 passed, 5 failed** —
  identical pre-existing flow-rate failure set documented since before
  Phase 6, unchanged. Plus the 4 new frontend logic tests (`node --test`),
  all passing.
- Updated `README.md`'s "Dashboard views" paragraph and `docs/DASHBOARD.md`
  (project-structure listing, rendering-pipeline section, and new "Spike
  Raster: two modes" / "Terminology and weight-change provenance"
  subsections) to describe the above — that doc had drifted out of date
  with several already-existing frontend files (raster.js/charge.js/
  weights.js/causal.js/receptive.js were undocumented before this phase;
  fixed opportunistically since this phase's own new files needed the same
  section anyway, not a separate full audit of the whole doc).

**Current phase (Phase 15, complete) — Local developmental protection from
L2I loser depression, the first actual neural-dynamics change since Phase
10 (Phases 11-14 were all measurement/UI-only). New, DEFAULT-OFF flag
`loser_depression_protection` (+ `loser_depression_protection_ca_ref`,
default 0.02), NOT promoted to the dashboard default -- see Conclusions.**

Preserved exactly, per explicit instruction: random `legacy_wide`
initialization (untouched, not balanced/equalized), physical threshold
crossings (Phase 6), delayed causal L2I inhibition (Phase 7), no argmax/
software WTA anywhere, no assigned owners/pattern labels/neuron-index rules/
global comparisons, self-spike learning/distance/leak/adaptive-threshold/L1I
completely untouched (verified directly:
`test_engine_protection_does_not_touch_l1i_or_distance_or_self_spike`).

**Mechanism:** `Neuron._loser_depression_maturity()` (new) = `clamp(self.ca /
loser_depression_protection_ca_ref, 0, 1)`. `self.ca` is the neuron's own
slow EMA of its own physical spiking -- already computed UNCONDITIONALLY
every step in `Neuron.update()` regardless of the `homeostasis` flag, so
this phase reads an existing local signal without changing how it's
computed or touching homeostasis itself. In `apply_delayed_inhibition`, this
`maturity` multiplies into the structural weight-depression gain alongside
the existing `structural_gate`/`p_loss`/`competitive_reset_influence`
factors -- ONLY the plastic weight-depression term; the physical inhibitory
membrane transient (`V = max(V - magnitude, resting_potential)`) is computed
unconditionally, after and independent of the depression branch, and never
reads `maturity` at all. Default off reproduces every prior phase's gain
exactly (gate hardcoded to 1.0).

**Tests (11, all passing, `test_loser_depression_protection.py`):** the
gate formula itself; zero maturity fully suppresses weight depression while
the membrane transient still applies at full magnitude; the membrane
transient is identical across off/immature/mature; depression magnitude
rises MONOTONICALLY and smoothly with ca and matches the unprotected
baseline exactly once ca>=ca_ref ("experienced competitors must still be
depressible"); no ca value ever potentiates; full isolation between
neurons; flag-off is byte-identical to omitted-flag at both unit and
full-150-step-engine-run level; an AST-based locality proof (same technique
as Phase 8's structural-FE test) that the maturity gate's executable body
references nothing but `self.ca`/`self.loser_depression_protection_ca_ref`
-- no rival neuron, no `self.winner`, no pattern identity; L1I weights and
the distance/influence pathway report are byte-identical with the flag on
or off. Full suite: 276 passed, 5 failed (same pre-existing set, unchanged).

**Comparison (`phase15_loser_depression_protection.py`):** weight seeds 1-5
x topology seeds 1-3 x 2 scenarios (20-step equal interleaving/40 rotations;
long row-hold-600-then-col-switch-200) x 2 configs (A=default,
B=protection) = 60 runs. **Honest, mixed, NOT-promoted result:**
- Interleaved schedule: small real improvement in raw recruitment breadth
  (mean active 3.60->3.80, mean unrecruited 2.60->2.00) but a real
  DEGRADATION in stable ownership on Phase 11's own success metric (mean
  distinct_owners 3.6->3.2, collisions 0.40->0.60, forgetting 1.00->1.60,
  ambiguity 0.0312->0.0363) -- recruitment breadth and ownership stability
  move in OPPOSITE directions.
- Long-hold schedule: no improvement, slightly worse (active 1.40->1.20).
- Tyrant share essentially unchanged in both schedules (~0.47/~0.54) --
  protection does not address dominance/tyranny.
- 0 of 75 neurons that had never fired at the row-1 hold's halfway
  checkpoint ever fired by the end of the run, under EITHER config --
  protection alone does not rescue an already-failed-to-recruit neuron
  within this timeframe.
- No increase in same-step multi-firer rate (if anything marginally lower)
  -- protection does not destabilize into excessive simultaneous firing.
- Depression magnitude grouped by maturity bucket (aggregated ~99,000
  events across all 60 runs) shows a clean monotonic ramp (0.0074 mean |dw|
  at maturity 0.00-0.25 up to 2.7817 at 0.75-1.00) -- the gate works exactly
  as designed.
- Physical inhibition event COUNT is byte-identical between A and B in
  ALL 15 long-hold-schedule combinations (the never-fired neurons' reduced
  depression never changes who wins or when L2I fires in that schedule),
  but diverges in ALL 15 interleaved-schedule combinations -- reported as
  EXPECTED, not a violation: the instantaneous transient mechanism is
  unit-proven identical always; the network's downstream trajectory of
  WHEN L2I fires legitimately diverges once repeated interleaved exposure
  gives protection's weight-preservation effect room to compound through
  the closed feedback loop.

**Conclusion: the mechanism does exactly what it was designed to do
mechanically (smooth, local, correctly-scoped, zero side effects on any
other mechanism) but does not solve the recruitment problem it targeted,
and trades a small recruitment gain for real ownership instability in the
one schedule where it has any effect at all. Left as an opt-in, default-off
experiment -- NOT promoted to the dashboard default**, consistent with
every prior phase's finding that the central one-to-one ownership-
consolidation problem remains open. Full findings and every table are in
`Phase15_Loser_Depression_Protection_Report.md`; the 60-run grid is in
`phase15_loser_depression_protection_summary.json` (committed).

**Current phase (Phase 16, complete) — Adaptive-threshold x developmental-
protection factorial + genuine spare-capacity challenge. MEASUREMENT ONLY:
both mechanisms already exist (Phase 10, Phase 15); no new neural rule, no
default changed, nothing tuned per seed, distance/leak/initialization/L1I
untouched.** Conditions A (both off) / B (adaptive on) / C (protection on)
/ D (both on), each mechanism at its own already-documented reference value
(`delta_threshold_frac=0.05`/`tau_threshold=25.0`;
`loser_depression_protection_ca_ref=0.02`), `DASHBOARD_PRESET`'s own legacy
distance config throughout -- only the two booleans toggled.

**Grid (`phase16_factorial_spare_capacity.py`):** weight seeds 1-5 x
topology seeds 1-3 x 2 scenarios (20-step equal interleaving/40 rotations;
long row-hold-600-then-col-switch-200) x 4 conditions = 120 factorial runs,
plus a 60-run spare-capacity challenge extending each condition's own
interleaved-40 trained engine: freeze+record the original four patterns'
owners/consistency -> unfreeze and present ONE declared novel pattern
(`row 0`, an existing held-out `PROBES` entry) 10 times WITH PLASTICITY
LIVE (never `present_probe()`, which freezes -- instead directly drives
`input_vec`+`_start_presentation`, the same public bookkeeping
`set_pattern()`/`present_probe()` already use, zero engine code changed) ->
identify the eventual responder and its PRE-novel status -> freeze again
and re-evaluate the original four. 4 harness-verification tests (all
passing) confirm the novel presentation actually keeps plasticity live, uses
real presentation-tracking, that the retention/collision bookkeeping is
internally consistent, and that the harness itself contains ZERO hardcoded
quiet-neuron-count acceptance assertions. Full suite: 280 passed, 5 failed
(same pre-existing set).

**Key findings:**
- **`adaptive_threshold`, not `loser_depression_protection`, is the
  dominant driver of raw recruitment breadth** -- in the long-hold schedule
  it roughly doubles active count and eliminates the quiet category
  entirely (B/D: active 3.00, quiet 0.00 vs. A/C: ~1.3 active, ~1.7 quiet).
  In the interleaved schedule the COMBINATION (D) reaches the best
  recruitment of any single condition (mean active 5.00/8, unrecruited
  1.20) -- a real, seed-robust improvement over baseline.
- That recruitment win comes at a real cost: D has the LOWEST
  distinct_owners (2.20 vs. A's 3.60) and the HIGHEST collisions/forgetting
  of any condition -- recruitment breadth and ownership stability move in
  opposite directions, sharper under D than under protection alone
  (Phase 15).
- Adaptive threshold (B, D) meaningfully reduces tyrant share in the
  long-hold schedule specifically (0.366/0.353 vs. A's 0.465) but not in
  the interleaved schedule.
- Depression-by-maturity's monotonic ramp (Phase 15's core mechanism proof)
  is preserved identically under D -- the two mechanisms don't interfere
  with each other's own internal math.
- **Spare-capacity challenge -- the most important finding:** under
  baseline A, the novel pattern is captured by an already-active neuron in
  ALL 15 seeds (0 genuine spare-capacity recruitments; 12/15 times by the
  existing tyrant itself). B and C each produce genuine spare-capacity
  recruitment (a previously-UNRECRUITED neuron becomes the novel pattern's
  owner) in 3/15 seeds -- real but modest, and specific to that one
  mechanism. **Combining both (D) ELIMINATES this benefit entirely: 0/15
  genuine recruitments (back to A's baseline), tyrant-capture back to
  12/15, and the WORST retention (0.550) and WORST novel-pattern
  consistency (0.58) of any condition** -- a genuine negative interaction
  between two mechanisms that each individually help a little, found and
  reported as-is, not tuned away.
- A dedicated supplementary within-run checkpoint (same protocol as Phase
  15's own check, extended to all four conditions:
  `phase16_never_fired_checkpoint.json`) confirms 0 of 75
  never-fired-at-halfway neurons ever fire by the end, under EVERY
  condition -- neither mechanism, nor their combination, actively rescues
  an already-fallen-behind competitor within this timeframe.
- No fixed quiet-neuron-count criterion was imposed anywhere in the
  harness (verified by a dedicated test) -- every count above is reported
  as observed.

**Conclusion: consistent with Phase 15, the central one-to-one ownership-
consolidation problem remains open.** This phase maps where two existing,
individually-tested mechanisms land relative to it, alone and combined,
without adjusting anything to make the map look better -- including the
genuinely surprising finding that combining them can erase each one's
individual (modest) benefit rather than compounding it. Full findings and
every table are in `Phase16_Factorial_Spare_Capacity_Report.md`; the
120+60-run grid is in `phase16_factorial_spare_capacity_summary.json`
(committed), and the supplementary never-fired checkpoint is in
`phase16_never_fired_checkpoint.json` (committed).

**Current phase (Phase 17, complete) — LPS Lecture 14 architecture mapping
+ isolated pre-trained L2I recruitment experiment. Named Phase 17 (not
Phase 16, already taken above).** Read `LPS_Lecture_14_Detailed_Summary.txt`/
`LPS_Lecture_14_Expanded_Chronological_Notes.txt` in full as conceptual
research context (not an equation/topology spec). Six proposed hypotheses
classified: pre-trained inhibition is PARTIALLY implemented (L2I's outgoing
side was already fixed since Phase 7, coincidentally, for unrelated
reasons; only the incoming/recruitment side is new here, isolated behind a
flag); "first spike physically recruits inhibition" is ALREADY implemented
(Phase 7's causal chain); the prediction-excitatory population, frequency-
based free energy, synapse-level maturity, and explicit temporal dynamics
are all ABSENT and explicitly DEFERRED, not designed or implemented.

**Audit (measurement only, current baseline):** L2E->L2I learns via
`ChargeBasedRule`; L2I's outgoing side has no learned gate at all (Phase 7);
L2E->L1I learns via `AssemblyFlowCredit` (forced on for all L1I); **L1I's
OWN output inhibition is NOT fixed** -- `NeuronConfig.apply_to()` applies
`inhibitory_delta_rule` uniformly, so L1E's own inhibitory gate (from its
paired L1I) still learns via the legacy saturating rule even under
`DASHBOARD_PRESET`. L2E-first-spike->L2I-fire latency ~0.6-1.1 steps;
L2I-fire->delivery latency exactly 1 step (deterministic); mean 1.4-1.7
contributors per L2I event. **One physical spike already becomes
sufficient to fire L2I by the training MIDPOINT in every one of 5 seeds
tested at baseline** -- the learned system already converges to what
Lecture 14 proposes to hard-code from the start. **Required false-positive
control confirmed directly:** a sustained single-pattern hold converges
L1E frequency to EXACTLY 0.5 via mere synchronized global L1I suppression,
with zero selective prediction -- frequency=0.5 must not be read as
"prediction complete" (verified with a dedicated test that no
weight-mutating code path reads firing frequency at all).

**Mechanism (`pretrained_l2i_recruitment`, new default-off flag):** every
L2E->L2I synapse initializes to exactly `thr_l2i` (the resolved L2I
threshold -- audited: no unit conversion needed, `infl_l2e_l2i` stays off
and untouched) and L2I's own incoming-excitatory `learning_rate` is pinned
to 0. Nothing else touched: L2I still physically integrates and crosses
its own `check_threshold()`/`fire()`; L2I->L2E inhibition remains
scheduled and causally delayed exactly as before; delivery stays uniform;
no winner/pattern/owner/index/cross-neuron state is read anywhere in the
new code. Off reproduces baseline byte-identically (verified at unit and
200-step engine level). 19 new tests (`test_pretrained_l2i_recruitment.py`,
all passing, exceeding the 17 required proofs). Full suite: 299 passed, 5
failed (same pre-existing set, unchanged).

**Multi-seed result (5 weight seeds x 3 topology seeds x 3 schedules:
20+20 short hold/switch, 600+200 long hold/switch, 40-rotation equal
interleaving) -- REJECTED FOR PROMOTION, confirms this phase's own stated
caution:** pre-trained recruitment recruits measurably FEWER neurons in
EVERY schedule tested, and reaches **literal, total single-neuron monopoly
(tyrant_share = 1.000) in EVERY ONE of 15 seed/topology combinations under
the long-hold schedule** -- directly confirming "fixed WTA may make the
first random tyrant stronger." Distinct ownership in the interleaved
schedule is worse (2.00 vs. 3.60 owners), collisions higher. One-hot
firing rate is comparable-to-better under the new mode (simultaneous
same-step firers become nearly impossible once single-spike recruitment is
instant) -- explicitly NOT the same as one-to-one ownership, which gets
worse; the two move in opposite directions, exactly the distinction this
phase's cautions warn against conflating. **A genuine, counter-to-trend
secondary finding in the spare-capacity challenge:** pre-trained
recruitment shows a HIGHER genuine spare-capacity recruitment rate (6/15
vs. 0/15 seeds where the novel pattern's eventual owner had never fired
before) and BETTER original-pattern retention (0.950 vs. 0.750) --
explained as a downstream consequence of training leaving more neurons
genuinely untouched in the first place, not an independent success. Against
the instruction's own explicit promotion bar (must not increase tyrant
capture or dead-neuron count), **this mechanism fails on both of the two
most heavily-weighted criteria** despite passing three secondary ones.

**Decision: `pretrained_l2i_recruitment` remains default OFF, not
promoted, and further testing of this specific mechanism in this form is
not recommended** (though the spare-capacity retention finding is flagged
as a candidate for narrower, separate follow-up). Deferred Lecture 14 work
(prediction-excitatory population, encoder/decoder equation, frequency-
based free energy, synapse-level maturity, explicit temporal dynamics)
remains entirely undesigned. Full findings, every table, and the exact
promotion-bar scorecard are in
`Phase17_Lecture14_Mapping_and_Pretrained_L2I_Report.md`; raw data is in
`phase17_lecture14_audit.json` and `phase17_controlled_comparison_summary.json`
(both committed).

**Current phase (Phase 19A, corrected scaffold checkpoint) — Per-input-column
prediction population with delayed local replay, default OFF.** This
explicitly supersedes the abandoned "one predictor per L2E, broadcast to all
9 L1E" main-line topology. The implemented scaffold now matches the corrected
Lecture 14 contract's first reconstruction milestone:

- exactly nine prediction neurons `P0..P8`, each permanently mapped to one
  input column / pixel;
- stored positive-bounded `L2Ej -> Pi` decoder matrix (`decoder{j}->{i}`),
  exposed/serialized but **not learned** in Phase 19A;
- fixed local `Pi -> L1Ei` replay only (`pred{i}->{i}`), no `P -> L1I`, no
  `P -> P`, no broadcast `P -> all L1E`;
- causal delay preserved end-to-end: `L2E@t -> P@t+1 -> L1E@t+2`, with no
  same-step `L2E -> P -> L1E` shortcut;
- backend observability added for prediction neuron state, stored/effective
  decoder matrices, control mode (`normal` / `disabled` / `shuffled`), and
  queued/arrived/integrated/delivered prediction events.

**Important explicit boundary:** no active `L2E -> P` plasticity equation is
implemented in this checkpoint. The earlier candidate rule was removed from the
runtime path. The unresolved local-learning requirement is now documented
directly in code and in `Phase19A_Corrected_Prediction_Scaffold.md`: a future
decoder rule needs a pixel-local teaching signal telling `Pi` whether *pixel i*
was truly present when a causal `L2E` event arrived, without labels, owner
tables, argmax routing, or global reconstruction error.

**Verification:** focused corrected-topology tests in
`test_prediction_phase19.py` pass `11/11` (feature-off baseline equivalence,
exactly nine `P` neurons, full `8x9` decoder connectivity, strict local replay,
no `P -> L1I`, no same-step `L2E -> P` or `P -> L1E`, frozen replay does not
mutate weights/confidence/specialization state, disabled/shuffled controls do
not mutate the stored matrix, legacy L1I/L2I causal behavior unchanged when
prediction is inert). Full script-style suite re-run under the available local
virtualenv passed `29/30`; the lone non-pass,
`test_phase13b_tracer_timing.py`, failed to start because that environment
does not have `pytest` installed (`ModuleNotFoundError: No module named
'pytest'`), not because of a new Phase 19A neural-dynamics regression.

## Completed (this session)

Phase 0 (branch/docs setup):
- Ran git diagnostics: root, remote, branch, status, branch list, recent log.
- Confirmed `july14` was clean and `july14-integration` did not yet exist.
- Created `july14-integration` from `july14` (no other branch changes).
- Authored `CLAUDE.md` with the permanent rules for this repo.
- Authored this file, `CLAUDE_HANDOFF.md`. Committed as `b02cd9e`.

Phase 1 (required audit, brief §14 + §20 — read-only, no mechanisms changed):
- Full read of `July_14_Geometric_Influence_Temporal_Winner_Brief.txt`.
- Audited `backend/simulation.py`, `neuron_flexible.py`, `layers.py`,
  `snn/rules/*.py`, `backend/api.py`, `backend/serializer.py`,
  `backend/websocket.py`, and all of `frontend/*.js` against every item in
  brief §14 and §20.
- Wrote up findings in `Geometric_Influence_Temporal_Winner_Audit.md` —
  read that file for full detail with file:line citations. Six headline
  findings, most importantly: (1) the dashboard's exposed "winner" is
  latest-spike-wins, not first-spike-wins, contradicting the brief's core
  thesis; (2) L2E geometry is a perfect ring (only a 2-way, not 8-way,
  geometric signature); (3) all 9 L1I units share one literal weight vector
  and threshold, so their synchrony is structural, not a serializer bug; (4)
  `distance_weighting=True` is live in `backend/api.py`, not an inert
  default, but starved of symmetry-breaking effect by finding (2); (5) no
  literal influence-squaring bug for the winner's own learning, but a
  two-stage reuse of one distance-derived quantity in the loser depression
  path; (6) no fake raster spikes, no UI-side simulation, no coordinate
  ownership conflict — the frontend audited clean apart from one client-side
  "dead neuron" label that could diverge from the backend's own notion.
- Ran the unmodified baseline test suite and two unmodified diagnostics (see
  Tests below) to anchor these findings against actual current behavior.

Phase 2 (observability infrastructure; see "Files changed" and commits
`9163da2`/`05c17a0` for full detail): shared pattern/probe metadata + dashboard
preset, held-out probes with presentation-scoped plasticity freeze, backend-
driven Causal Story/presentation tracking, evidence-based RF status,
delivery/pre-post-integration diagnostics, and the matching frontend
(probe controls, Causal Story tab, evidence-based status display, Fit View,
presentation-boundary markers, distance/influence display). No neural
equation or preset value changed.

Phase 3 (seeded engine-owned geometry; see commit `0e353cd`): jittered
L1E-in-cell / paired L1I / irregular-with-min-separation L2E / centered L2I
positions, seeded and fixed except on explicit topology reseed, legacy
ring/grid preserved as a selectable ablation, and a temporary
legacy-distance-compatibility shim that keeps that phase's dynamics
byte-identical to before it while clearly labeling the pinned numbers
wherever they're shown.

Phase 4 (connection distance/influence as isolated experimental behavior; see
commit `586d0f7`): rather than removing Phase 3's legacy-distance-compat shim
(the plan anticipated at the end of that phase), the ACTUAL instruction for
this phase was narrower and safer -- add FOUR NEW, independently-ablated
experimental pathways (L2E→L2I, L2I→L2E, L2E→L1I, L1I→L1E) beside the
untouched legacy L1E→L2E pathway, each default-off, each fully audited
(source/target/distance/influence/raw weight/effective transmission/applied),
using one shared safe-by-default power law. The legacy-distance-compat shim
and the L1E→L2E pathway it governs are completely UNCHANGED by this phase.

Phase 5 (diagnostic equal-interleaved presentation schedule; see commit
`ff3048f`): a standalone, non-mutating diagnostic tool implementing the
brief's fixed cycle (row 1 → col 1 → diag \ → diag / → repeat) with brief,
non-saturating presentations, evaluated exclusively on disposable deep-copies
(plus a plasticity-frozen re-test copy) so nothing outside the tool is ever
touched. Records every requested per-presentation field and reports
consistency/ambiguity/no-response/distinct-owners/collisions/forgetting/
silent-recruitable-cells/L2I-activity/L1I-selectivity across seeds. Zero
engine/competition code changed -- purely additive, with a 5-seed baseline
saved to `Diagnostic_Schedule_Baseline.md`.

Phase 6 (representation candidate == first physical L2E threshold crossing;
see "Files changed" below): retired the latest-spike-wins `_resolve_episode()`
mechanism (the Phase 1 audit's headline conflict with the brief) and replaced
it with direct, presentation-scoped tracking of the first physical L2E
threshold crossing. Added `earliest_response_set` (exact tied set),
`later_responses` (full ordered later-spike list), and
`latency_to_second_response`. A same-step tie makes `self.winner` (and any
L1I/L2I source attribution that would otherwise name the tied neuron)
ambiguous for the whole presentation -- no winner-specific credit or feedback
-- while `physicalFirstSpiker` itself remains a separately-recorded raw fact.
The legacy immediate-reset competition tiebreak in `_resolve_l2_competition`
is unchanged, clearly documented in its own docstring as a Phase 7 candidate.
Along the way, found and fixed a latent, pre-existing non-determinism bug in
Phase 5's `diagnostic_schedule.py::_modal()` (tie-breaking depended on
Python's per-process string hash randomization) -- confirmed NOT a Phase 6
regression (the underlying spike counts were identical before and after; only
the tie-break's displayed label was unstable).

Phase 7 (physical L2I competition; see "Files changed" below): retired
`Neuron.apply_competitive_reset` (unconditional clamp-to-rest, ignored
refractory) and replaced it with `Neuron.apply_delayed_inhibition(magnitude)`
(bounded floor-limited subtraction, skips a refractory target entirely).
Rewrote `_resolve_l2_competition()` so every threshold-crosser fires and only
contributes to L2I's own accumulation; added `_deliver_scheduled_l2_inhibition()`
and the `_l2i_pending`/`_l2i_contributors`/`_last_l2_inhibition_delivery`/
`_l2_inhibition_log` state to schedule and later apply delayed, uniform
delivery. New config: `l2_inhibition_delay`/`l2_inhibition_frac` (constructor
+ live `apply_config`/`TUNABLE`). New diagnostics:
`dynamic_state()['l2_inhibition']`. Updated 13 pre-existing tests across five
files that directly exercised the retired mechanism's semantics (immediate
reset, unconditional-under-refractory, argmax winner exemption) to match the
new causal/bounded/refractory-skipping design; added
`test_l2i_causal_inhibition.py` (15 new tests) asserting directly on the
newly-exposed facts. Captured new `sustained_dominance.py`/
`ablation_harness.py`/`diagnostic_schedule.py` baselines — all show real,
expected declines in distinct-owner/pool-participation metrics (see Known
problems), which is the anticipated cost of removing the same-step immediate
mutual exclusion, not a bug.

Phase 8 (exact local free-energy learning; see "Files changed" below): pinned
the `structural_free_energy`-gated branch of `SignedSpikeRule` (in
`snn/rules/excitatory.py`) to the literal equation
`delta_w = LR * FE * (1 - w/w_max)^2 * learn_signal` via a new helper
`exact_local_free_energy_update`, replacing that branch's previous use of
`bounded_signed_update`. `bounded_signed_update` itself is untouched (still
used by the non-FE signed-spike path and by Phase 7's
`apply_delayed_inhibition` depression gain — a different call site/purpose,
out of this phase's scope). Updated one pre-existing test
(`test_gate_replaces_p`) that pinned the OLD formula; added 8 new focused
tests covering the exact equation, both-direction saturation at `w_max`,
purely-numerical clamping, voltage-independence (FE fully replaces `p`, no
leakage), code-level locality (AST-verified: the helper's executable body
references no name beyond its own five arguments), same-step-tie
non-discrimination, and probe non-mutation.

Phase 9 (causal L1I predictive feedback; see "Files changed" below): fixed
`_credit_source` to check `self._last_eligible` (this step's actual firer
set) directly instead of only the presentation-level first-spike tie flag —
closing a real gap where a genuine same-step multi-firer event on a LATER
step could be mis-attributed to a single L2E id for BOTH L1I and L2I source
reporting. Added the full causal chain requested: `l1i_first_source_set`,
`l1i_first_arrival_t` (separate from the existing `l1i_first_t` threshold-
crossing step), `l1i_first_targets`, `l1i_first_delivery` (the resulting
L1I→L1E pulse's `_inh_events` effect, captured one step later via a
one-shot pending-capture flag). L1I→L1E's spatially-paired meaning and the
L2E→L1I delivery mechanism itself are UNCHANGED — this phase is
observability plus a targeted attribution-logic fix, not a rewiring of
connectivity. Added `test_l1i_causal_feedback.py` (12 new tests).

Phase 10 (adaptive-threshold ablation; see "Files changed" below): added
`Neuron.adaptive_threshold`/`delta_threshold`/`tau_threshold`/`threshold_adapt`
(a_i) and `effective_threshold`; `check_threshold()` uses the elevated
threshold only when the flag is on, else delegates unchanged to the
Membrane. L2E-only wiring in `_build()`, new engine constructor params
(`adaptive_threshold`, `delta_threshold_frac`, `tau_threshold`), new
`dynamic_state()['adaptive_threshold']` block plus per-neuron
`threshold_adapt`/`effective_threshold` fields, and probe snapshot/restore
in `present_probe`/`_end_probe` (unconditional restore regardless of how the
probe ends). Added `test_adaptive_threshold.py` (16 new tests).

Phase 11 (controlled multi-seed validation; see "Files changed" below):
built `phase11_validation.py` (a new, self-contained measurement harness,
reusing `diagnostic_schedule.py`'s already-tested per-presentation recording
function for the short-interleaved schedule rather than reimplementing it)
and ran the full 96-run cross (4 geometry x 2 adaptive_threshold x 3 weight
seeds x 2 topology seeds x 2 schedules). Caught and fixed a real confound
mid-phase (engines were being built from raw constructor defaults instead of
`DASHBOARD_PRESET`) before trusting any result -- the corrected, final sweep
is the one reported. Wrote up full findings with explicit observations vs.
conclusions sections and a failures-recorded-honestly section in
`Phase11_Multiseed_Validation_Report.md`. Added `test_phase11_validation.py`
(6 tests) validating the saved report's shape, `N_OUT` invariance, a
mechanical sanity check, and harness determinism.

Phase 12 (final local review; see "Files changed" below): full test suite +
real end-to-end smoke checks (REST + WebSocket, via a newly-installed
`httpx2` in the session venv) against `backend.api.app`; found and fixed a
backend/UI `CONFIG_SPEC` gap for `symmetric_geometry`/`legacy_distance_compat`
(Phase 3) and `l2_inhibition_delay`/`l2_inhibition_frac`/`adaptive_threshold`/
`delta_threshold_frac`/`tau_threshold` (Phases 7/10); audited the whole
engine for remaining software winner/tie-break shortcuts and found exactly
one, confined to the non-default `lasting_inhibition` mechanism (documented,
not fixed -- out of this phase's "no new mechanisms" scope); reconfirmed
Phase 11's success-criteria evaluation; wrote
`Phase12_Final_Local_Review.md` as the final handoff document for this
session's work.

## In progress

**Phase 12 (final local review) is COMPLETE — this is the final phase of
the corrected Phases 6-12 sequence.** No further phase is queued in this
session. The branch is ready for human review; see
`Phase12_Final_Local_Review.md` for the exact commit chain and working-tree
status.

## Files changed (Phase 12 — final local review, this checkpoint)

- `backend/api.py`: added 7 `CONFIG_SPEC` entries (`symmetric_geometry`,
  `legacy_distance_compat`, `l2_inhibition_delay`, `l2_inhibition_frac`,
  `adaptive_threshold`, `delta_threshold_frac`, `tau_threshold`) closing the
  backend/UI agreement gap found in this phase's audit (see §3 of
  `Phase12_Final_Local_Review.md`). All left `advanced: true` (not added to
  `_MAIN_CONFIG_KEYS`), consistent with how Phase 4's `infl_*` pathways were
  treated. No engine file (`backend/simulation.py`, `neuron_flexible.py`,
  `snn/*`) was touched this phase.
- `Phase12_Final_Local_Review.md` (new) — the final review document: full
  test suite result, end-to-end smoke check results (REST + WebSocket),
  the backend/UI agreement audit (found/fixed + confirmed-out-of-scope
  gaps), the no-software-tiebreak audit (one remaining instance, documented),
  the Phase 11 success-criteria re-confirmation, an "Unresolved failures"
  section, and the exact final commit chain / working-tree status for
  handoff.

### Phase 11 (prior checkpoint `1a59ae8`)

- `phase11_validation.py` (new) — the measurement harness. Defines the 4
  `GEOMETRY_CONDITIONS`, crosses them with `adaptive_threshold`,
  `WEIGHT_SEEDS=[1,2,3]`, `TOPOLOGY_SEEDS=[1,2]`, and the two schedules.
  `_engine_kwargs()` builds every engine from `DASHBOARD_PRESET` with only
  the tested dimensions overridden (the mid-phase fix). Short-interleaved
  reuses `diagnostic_schedule._present_and_record`/`summarize` directly;
  long-saturation is a scaled-down version of `sustained_dominance.py`'s
  honest per-cycle-winner protocol. Per-run helpers compute receptive-field
  cosine similarity, the adaptive-threshold final-state summary, L2I causal-
  timing snapshot, and the L1E->L2E influence distribution (with an explicit
  `applied` flag, since distance/influence VALUES are computed from geometry
  regardless of whether the pathway is actually consumed by delivery).
  `--quick` mode (2 seeds, 1 topology seed, 4 cycles) is for fast
  smoke-testing script changes only -- NOT the data behind the saved report.
- `phase11_validation_report.json` (new, generated, tracked) — the 96 raw
  records from the full (non-quick) run.
- `Phase11_Multiseed_Validation_Report.md` (new) — the written report: method
  (including the `DASHBOARD_PRESET` fix, documented as a correction, not
  hidden), the success-criterion table per condition, aggregated observation
  tables, a clearly separate "Conclusions (interpretive)" section, and a
  "Failures recorded (not glossed over)" section.
- `test_phase11_validation.py` (new) — 6 tests: the saved report file exists
  and parses; every expected (schedule, geometry, adaptive_threshold,
  weight_seed, topology_seed) combination is present exactly once (96, no
  duplicates, no gaps); `N_OUT` stayed 8 in every record; geometry alone
  (symmetric vs. jittered) produces byte-identical metrics when influence is
  off (a direct proof of the report's own mechanical null-result finding);
  the harness itself is deterministic (same condition/seed/steps run twice
  -> identical measurements); and the report's stated best-cell success
  count (4/6) is independently re-derived from the raw JSON, not hand-typed.

### Phase 10 (prior checkpoint `d333945`)

- `neuron_flexible.py`:
  - New `__init__` state: `adaptive_threshold` (bool, default False),
    `delta_threshold` (float, default 0.0), `tau_threshold` (float, default
    1.0, guarded > 0 wherever divided), `threshold_adapt` (a_i, default 0.0).
  - `fire()`: when `adaptive_threshold` is on, `threshold_adapt +=
    delta_threshold` on THIS neuron's own spike only (no cross-neuron
    coupling) — placed right after the membrane discharge.
  - `update()`: when `adaptive_threshold` is on, `threshold_adapt *=
    exp(-1/tau_threshold)` every step, unconditionally (independent of the
    membrane's own refractory/leak branch — a_i is a separate local memory
    that keeps decaying even while the neuron is refractory).
  - `check_threshold()`: delegates straight to `self._membrane.check_threshold()`
    when the flag is off (byte-identical to every existing caller); when on,
    compares `potential` against the new `effective_threshold` property
    directly (still respecting the refractory gate).
  - New `effective_threshold` property: `threshold + threshold_adapt` when on,
    else exactly `threshold`.
- `backend/simulation.py`:
  - New constructor params `adaptive_threshold: bool = False`,
    `delta_threshold_frac: float = 0.05`, `tau_threshold: float = 25.0`
    (both in `TUNABLE`/live `apply_config`). Documented as reasonable,
    non-adversarial defaults, not swept to make any seed succeed (Phase 11
    measures the effect).
  - `_build()`: wires `adaptive_threshold`/`delta_threshold` (scaled by
    `thr_l2`, scale-invariant)/`tau_threshold` onto L2E neurons ONLY, in the
    same L2E-only branch as `structural_free_energy` etc. — every other
    population's `adaptive_threshold` stays at the class default (False).
  - New `self.threshold_adapt_history` (per-L2E bounded deque, same
    `FREQ_WINDOW` convention as `self.freq`), appended once per step right
    after `_record_spikes`.
  - `dynamic_state()`: per-neuron `threshold_adapt`/`effective_threshold`
    (L2E only); new top-level `adaptive_threshold` block (`enabled`,
    `delta_threshold`, `tau_threshold`, per-neuron `state`,
    `effective_threshold`, and `history`).
  - `present_probe()`/`_end_probe()`: snapshot every L2E's `threshold_adapt`
    before the probe starts (`_probe_threshold_adapt_snapshot`); restore it
    UNCONDITIONALLY in `_end_probe` (both `restore=True` — the probe elapsed
    — and `restore=False` — the probe was cancelled by manual input) so
    probe evaluation can never alter subsequent training. Physical dynamics
    (spike-local increments, per-step decay) stay fully live DURING the
    probe window — only the pre/post values are protected, not frozen live.
- `test_adaptive_threshold.py` (new) — 16 tests: spike-local increment;
  exponential decay toward zero (including the exact hand-computed value
  after one step); decay continues during refractory; the effective-
  threshold equation (and that it collapses to exactly `threshold` when
  off); `check_threshold` actually compares against the elevated threshold;
  a stray nonzero `a_i` is fully ignored when the flag is off; isolation
  between two neurons; `adaptive_threshold` and `homeostasis` are fully
  independent flags; the engine defaults to off and an explicit
  `adaptive_threshold=False` is byte-identical to the default (same winner
  sequence and final weights over a real 60-step run); `delta_threshold_frac`
  scales with `threshold_l2`; every non-L2E population never gets the flag;
  state/trajectory are exposed correctly end-to-end; deterministic replay
  (identical seed -> identical `a_i` trajectory); the probe restores `a_i`
  whether it elapses naturally or is cancelled; and a_i genuinely evolves
  DURING an open probe window (not frozen live, only protected afterward).

### Phase 9 (prior checkpoint `3dd6f4c`)

- `backend/simulation.py`:
  - `_credit_source(idx)`: now returns `'ambiguous'` whenever
    `len(self._last_eligible) > 1` at the moment of attribution (this step's
    actual firer set), replacing the old check against
    `self._presentation_tie`/`self._presentation_first_spiker` (which only
    covered a presentation's very first spike). Applies to BOTH L1I and L2I
    source attribution, since both share this one function.
  - New presentation-scoped state (init in `_build()`, reset in
    `_start_presentation()`, archived into `presentation_log` entries):
    `_presentation_l1i_first_source_set`, `_presentation_l1i_first_arrival_t`,
    `_presentation_l1i_first_targets`, `_presentation_l1i_first_delivery`,
    and a one-shot `_l1i_delivery_capture_pending` flag.
  - `_track_presentation()`: records ARRIVAL (`step_winner_idx is not None`,
    i.e. a real nonzero `l2e` was just delivered to L1I this step) with its
    source SET (`self._last_eligible`), independently of whether L1I has
    fired yet; on L1I's actual fire, records `l1i_first_targets` (which L1I
    ids fired) and sets the one-shot delivery-capture flag.
  - `step()`: right after the top-of-step L1E/`apply_inhibition` loop
    populates `self._inh_events` for this step (the delivery/effect of
    WHATEVER L1I fired last step, per the one-step `l1i_feedback_delay`
    register), checks the pending-capture flag and — if set — snapshots
    `_inh_events` into `_presentation_l1i_first_delivery` (with the step
    number) and clears the flag. This correctly captures the FIRST L1I fire's
    resulting delivery on the very next step, no re-derivation needed since
    the delay is a fixed, known one-step register.
  - `dynamic_state()['causal_story']`: added `l1i_first_source_set`,
    `l1i_first_arrival_t`, `l1i_first_targets`, `l1i_first_delivery`.
- `test_l1i_causal_feedback.py` (new) — 12 tests: arrival never happens after
  threshold crossing; source set is recorded at arrival and lists only L2E
  ids; targets are the actual firing L1I ids; delivery lands exactly one step
  after threshold crossing and its events reference L1E with `v_pre`/`v_post`;
  a forced same-step multi-firer set is reported in `l1i_first_source_set`;
  a same-step tie on a LATER (non-first) step is now correctly reported
  `'ambiguous'` for both L1I and L2I attribution (the Phase 9 fix, exercised
  end-to-end through the real engine, not just the unit-level helper); a
  direct unit test of the fixed `_credit_source`; the default (non-relay)
  mode genuinely requires threshold crossing (sabotage test, mirroring
  `test_l1i_immediate_relay.py`'s technique) so units never fire merely by
  duplication; an audit-confirming test that all 9 L1I still share one
  literal weight vector by default (honestly reported, not hidden); probe
  non-mutation for the new bookkeeping; presentation-boundary reset of the
  new fields; and a proof that reading the new diagnostics heavily between
  steps has zero effect on physical dynamics.

### Phase 8 (prior checkpoint `c0ac363`)

- `snn/rules/excitatory.py`: added `exact_local_free_energy_update(w, w_min,
  w_max, lr, fe, learn_signal)` — the literal Phase 8 equation, clamped only
  for numerical bounds `[w_min, w_max]`. `SignedSpikeRule.on_fire`'s
  `structural_free_energy` branch now calls this helper instead of
  `bounded_signed_update`; the non-FE branch (plain `p`-scaled signed-spike
  learning) is byte-for-byte unchanged.
- `snn/rules/__init__.py`: exported `exact_local_free_energy_update`.
- `test_structural_free_energy.py`: updated `test_gate_replaces_p` to build
  its reference via `exact_local_free_energy_update` instead of
  `bounded_signed_update`; added `test_exact_equation_matches_the_literal_formula`,
  `test_saturation_envelope_zero_at_w_max_both_directions`,
  `test_saturation_envelope_maximal_at_w_min`, `test_clamp_is_purely_numerical`,
  `test_fe_gate_and_envelope_are_the_only_two_factors` (voltage-independence),
  `test_fe_update_uses_only_this_neurons_own_state` (AST-based locality proof),
  `test_same_step_tie_gives_no_special_credit_either_side` (drives a real
  forced same-step tie through the full engine and confirms both firers still
  apply their own local FE update, with no asymmetric winner/loser treatment),
  and `test_frozen_probe_does_not_mutate_weights_or_confidence_under_fe`.
- No changes to `neuron_flexible.py`, `backend/simulation.py`, or any Phase
  4-7 mechanism — `_structural_free_energy_gate()`/`structural_fe_eta_floor`/
  the `apply_delayed_inhibition` depression-gain consumer of the same gate
  function are all unchanged; only `SignedSpikeRule`'s OWN use of the gate
  value changed.

### Phase 7 (prior checkpoint `d946ff0`)

- `neuron_flexible.py`:
  - **Retired** `apply_competitive_reset()`. **Added**
    `apply_delayed_inhibition(magnitude)`: skips entirely (`applied=False`, no
    transient, no depression, no record) when `refractory_timer > 0` (matching
    `apply_inhibition`'s convention — the OPPOSITE of the retired method,
    which was unconditional even under refractory); otherwise `V = max(V -
    magnitude, resting_potential)` (a bounded, floor-limited subtraction, never
    a forced clamp) plus the SAME structural depression as before (gain =
    `learning_rate * gate * p_loss * competitive_reset_influence`, guarded by
    `plasticity_frozen`/`loser_depression`). Dropped the unconditional
    trace-clearing the retired method did (`exc_trace`/`inh_trace` are
    confirmed always inert in this engine — see `_build()`'s neutering block —
    so a delivery event has nothing physically meaningful left to drain).
  - Updated the `competitive_reset_influence`/`plasticity_frozen` docstrings
    that referenced the retired method by name.
- `cortical_column_flexible.py` / `backend/presets.py`: updated comments that
  named `apply_competitive_reset` to name the new method/mechanism.
- `backend/simulation.py`:
  - New constructor params `l2_inhibition_delay: int = 1` and
    `l2_inhibition_frac: float = 1.0` (both in `TUNABLE`/live `apply_config`).
    Default `frac=1.0` (a full-`threshold_l2` magnitude) reproduces the
    retired method's net DISCHARGE magnitude for any target below
    `threshold_l2` — only the CAUSALITY changes (delayed, accumulate-then-
    cross-own-threshold, no ID-based exemption, refractory-skip) by default.
  - New state: `_l2i_pending` (scheduled deliveries), `_l2i_contributors`
    (running `(t, id)` list since L2I's last fire), `_last_l2_inhibition_delivery`,
    `_l2_inhibition_log` (bounded history, same `LOG_MAX` convention as
    `event_log`/`presentation_log`).
  - `_resolve_l2_competition()` REWRITTEN: every `eligible` L2E now calls its
    own `.fire()` (mutates `l2e` in place with a 1 for EACH firer, not one);
    each firer is appended to `_l2i_contributors`. L2I's `receive_input` now
    gets the full multi-hot vector (previously always one-hot). If L2I
    crosses ITS OWN threshold (unchanged check), it fires (unchanged) and a
    delayed delivery record is appended to `_l2i_pending`
    (`fire_t`/`deliver_at`/`contributors`/`l2i_v_pre`/`l2i_v_post`/`magnitude`)
    instead of an immediate reset loop. `inhibited` is now always `[]` and
    `_reset_events` is never touched by this method — populated later, at
    delivery time. `self._last_eligible` (Phase 6's same-step-tie source) is
    still set exactly the same way, so `self.winner`/`earliest_response_set`
    semantics are UNCHANGED.
  - New `_deliver_scheduled_l2_inhibition(t)`: applies every pending record
    whose `deliver_at <= t`, uniformly across ALL `N_OUT` L2E (no ID-based
    exemption — a target still refractory from its own recent spike is simply
    skipped by `apply_delayed_inhibition` itself). Builds `_reset_events`
    (same tuple shape as before, `(nid, record)` — kept for compatibility with
    the pre-existing standalone diagnostics `hard_reset_experiment.py`/
    `report_competitive_depression.py`, which read it directly and needed no
    changes), `l2_inh_phase_debug` (per-target `id`/`applied`/`v_pre`/`v_post`/
    `p_loss`/`depressed`), and a `_l2_inhibition_log` entry.
  - `step()`: calls `_deliver_scheduled_l2_inhibition(t)` at the very top,
    BEFORE this step's own L1E/L2E processing — the same one-step-register
    precedent as `l1i_feedback_delay` (a due delivery lands on the membrane
    before new charge accumulates this step). The `reset->{j}` edge-flash list
    is now built from the delivery's actually-applied target list, not from
    an immediate per-step `inhibited` list. Removed the now-superseded
    `_check_l2_reset_phases()` invariant check (it asserted every reset
    reached EXACT rest, which no longer holds in general for a bounded,
    partial-magnitude delivery — `l2_inh_phase_debug` is now built directly
    at delivery time instead).
  - `dynamic_state()`: added `l2_inhibition` block (`delay`, `magnitude`,
    `pending`, `last_delivery`, `log`) exposing every requested fact —
    contributing sources + arrival times, L2I pre/post charge at its own
    threshold crossing, the scheduled delivery record, delivered inhibition,
    and competitor pre/post charge — directly, never inferred from neuron IDs
    or final spike counts.
  - Updated stale docstrings/comments across the file (module-level L2E_FANIN
    comment, `_build()`'s L2E config block, `event_driven`/`l2_charge_chunks`
    constructor docs, `step()`'s 2b/2c comment block,
    `pathway_influence_report()`'s L2I→L2E docstring, `_track_presentation()`'s
    docstring) that named the retired argmax/hard-reset mechanism.
- `test_competitive_reset.py`, `test_refractory_gating.py`,
  `test_influence_phase.py`, `test_hard_reset_inhibition.py`,
  `test_l2_competition.py`: 13 tests updated across these five files — each
  directly exercised the retired mechanism's specific semantics (unconditional
  clamp regardless of magnitude, ignoring refractory, a single-winner
  ID-exemption from `inhibited`/`_reset_events`) and needed to change to
  match the new bounded/refractory-skipping/uniform-delivery design. Every
  other test in these files (the bounded weight kernel, topology/serialization,
  depression-only-participating-positive math, `apply_inhibition`'s own
  independent refractory gating, etc.) is UNCHANGED — only assertions that
  actually depended on the retired mechanism's specific behavior were touched.
- `test_l2i_causal_inhibition.py` (new) — 15 tests: every threshold-crosser
  fires (not just one); a later response before delivery arrives is never
  erased; L2I fire schedules a delayed record, never an immediate reset;
  contributing sources + arrival times are exact recorded `(t, id)` events;
  L2I's own pre/post charge at threshold crossing is recorded, not inferred;
  a scheduled delivery applies at exactly `deliver_at`, not before, and is
  consumed (not re-delivered); delivered inhibition exposes competitor
  pre/post charge; a refractory target is skipped, verified directly against
  `refractory_timer`; `dynamic_state()['l2_inhibition']` exposes the full
  structure; pending entries carry every recorded field; a scheduled delivery
  is NOT cancelled by a pattern switch (matching the `l1i_feedback_delay`
  precedent); a probe's plasticity freeze blocks depression learning but not
  the physical delivery discharge; `l2_inhibition_delay`/`l2_inhibition_frac`
  are live-configurable both at construction and via `apply_config`; delivery
  lands exactly `delay` steps after L2I fires; and a direct proof that
  reading `dynamic_state()['l2_inhibition']` heavily between steps has zero
  effect on spike timing or learned weights.

### Phase 6 (prior checkpoint `aa271fc`)

- `backend/simulation.py`:
  - **Retired** the entire "episode" latest-spike-wins mechanism: `EPISODE_QUIET_K`/
    `EPISODE_MAX_LEN` constants, `self.episode_active`/`episode_timer`/
    `episode_last_spike_time`/`episode_l2_spikes` state, `_update_episode()`/
    `_resolve_episode()` methods, the `_update_episode(l2e, t)` call in
    `step()`, and the `episode=dict(...)` key in `dynamic_state()`. Confirmed
    unused by any test, script, or frontend file before removing (grepped the
    whole repo) -- this was dead weight once decoupled from `self.winner`, not
    kept as an unused shim.
  - `_resolve_l2_competition()`: docstring extended with a PHASE 6/7 note
    documenting that its `max(eligible, key=potential)` tiebreak is a LEGACY
    immediate-reset mechanism that decides which ONE neuron physically fires
    when several cross threshold in the same step -- deliberately unchanged,
    flagged for Phase 7. `_last_eligible`'s comment updated to name it as
    `earliestResponseSet`'s source.
  - `_start_presentation()`: now also resets/archives `earliest_response_set`/
    `later_responses`/`latency_to_second_response`; resets `self.winner = None`
    at the start of every new presentation (no stale carryover credit); the
    evidence-crediting history (`_pattern_first_responder_log`/
    `_neuron_first_responder_counts`) now skips a presentation whose first
    response was a same-step tie.
  - `_credit_source(idx)` (new): returns the L2E id for `idx`, UNLESS it is
    the presentation's own ambiguous same-step-tied first responder, in which
    case it returns `'ambiguous'` -- used for both L1I and L2I first-source
    attribution so a tie's "no winner-specific credit or feedback" extends to
    those fields too, not just `self.winner`.
  - `_track_presentation()`: `self.winner` is now set in EXACTLY this one
    method, the instant `step_winner_idx` is non-None for the first time in a
    presentation -- to that neuron's id, UNLESS `self._last_eligible` (the
    eligible set at that exact step, already computed by
    `_resolve_l2_competition`) has more than one member, in which case
    `self.winner` stays `None`. Later spikes (any spike after the first,
    including a repeat of the same neuron) are appended to
    `_presentation_later_responses`; `_presentation_latency_to_second` is set
    once, on the first DISTINCT later identity.
  - `dynamic_state()`'s `causal_story`: added `earliest_response_set`,
    `later_responses`, `latency_to_second_response`.
- `diagnostic_schedule.py`: `_modal()` fixed to break exact count-ties
  deterministically (sorted-first, via `Counter` + `min` over the tied
  candidates) instead of `max(set(...), key=count)`, whose tie-break depended
  on Python's per-process string hash randomization. No change to what is
  counted or how consistency/ambiguity/etc. are computed -- only which label
  is reported on a genuine exact tie is now stable across process launches.
- `test_representation_candidate.py` (new) — 13 tests: winner equals the raw
  first-spiker fact when not tied; a forced same-step tie produces
  `winner=None` while `earliest_response_set`/`first_spiker` still record the
  raw facts; the None persists for the rest of that presentation even after a
  later unambiguous spike; no evidence credit is logged for a tied
  presentation; L1I/L2I source attribution reports `'ambiguous'` when it would
  otherwise credit the tied first responder; later responses are recorded in
  chronological order; latency-to-second only counts a distinct identity;
  winner resets to `None` at every new presentation; the retired episode
  machinery is confirmed fully gone (`dynamic_state()` has no `episode` key,
  the four `episode_*` attributes and both retired methods no longer exist on
  the engine); probe non-mutation still holds (weights/confidence
  byte-identical across a probe, real spikes still occur, a probe can still
  report a winner while frozen); and a direct proof that reading
  `dynamic_state()`/`winner`/`pathway_influence_report()` heavily between
  steps has ZERO effect on spike timing or learned weights (a pure,
  write-only-for-display side channel).

### Phase 5 (prior checkpoint `ff3048f`)

- `diagnostic_schedule.py` (new) — standalone script, no changes to any
  existing file. `run_diagnostic(seed, engine=None, cycles=15,
  presentation_steps=20, consistency_reps=5)`: builds (or deep-copies) an
  engine, runs the fixed cycle `row 1 -> col 1 -> diag \ -> diag / -> repeat`
  with each presentation a BRIEF 20-step window (never saturating), recording
  every requested field per presentation via `_present_and_record()` — which
  reads ONLY pre-existing engine state (`engine.spiked`, `engine.l2_drive`/
  `l2_charge`, `engine.dynamic_state()['causal_story']`, `engine._all_weights()`)
  and touches no engine internals beyond that. After the live pass, a FURTHER
  deep copy has its plasticity frozen (`engine._set_plasticity_frozen(True)`,
  reusing Phase 2's already-proven mechanism) and each pattern is
  re-presented `consistency_reps` times with learning off, for a clean
  first-responder-consistency re-test isolated from weight drift.
  `summarize(run)` computes the full report (per-pattern consistency/
  ambiguity/no-response, distinct owners, collisions, forgetting — first-half
  vs. second-half modal owner within the same run, silent/recruitable cells,
  L2I activity, L1I all-nine-sync rate, and the frozen pass's own consistency
  + zero-weight-drift check) purely from the recorded records — no engine
  access. `main()` provides a CLI (`--seeds`, `--cycles`,
  `--presentation-steps`) matching the style of `ablation_harness.py`/
  `sustained_dominance.py`.
- `test_diagnostic_schedule.py` (new) — 13 tests: fixed cycle order, brief
  (non-saturating) presentation length, the non-mutating-evaluation guarantee
  (a live engine handed in is provably untouched — weights/timestep/
  presentation_id/input all identical before and after), every requested
  field is present and correctly typed, presentation IDs strictly increase,
  `latency_margin_to_second` is `None` exactly when there's no second distinct
  responder, the frozen pass shows exactly zero weight drift while the live
  pass shows real learning, and the summary report's structure/sanity
  (including the L1I-all-nine-sync empirical confirmation of the Phase 1
  audit's finding).
- `Diagnostic_Schedule_Baseline.md` (new) — the saved baseline: a 5-seed run
  (`--seeds 1 2 3 4 5`, defaults) against `DASHBOARD_PRESET`, with full
  per-seed tables and the aggregate findings (see Tests below for the
  headline numbers).

No file in `backend/`, `neuron_flexible.py`, `snn/`, or `frontend/` was
touched — confirmed by `git status` showing only new, untracked files for
this checkpoint.

### Phase 4 (prior checkpoint `586d0f7`)

- `neuron_flexible.py`:
  - `Neuron.competitive_reset_influence` (new, default `1.0` = neutral): the
    ONLY place the L2I→L2E pathway's influence can enter, since that path has
    no learned weight/delivery step. `apply_competitive_reset()`'s depression
    `gain` is now `learning_rate * gate * p_loss * competitive_reset_influence`
    — the UNCONDITIONAL membrane reset itself is never touched by it.
  - `apply_inhibition()`: when the target neuron's `distance_weighting` is on
    (used here by the NEW L1I→L1E pathway), the DELIVERED discharge magnitude
    is scaled by `(distance_ref/max(distance,distance_min))^distance_power`
    (mirroring `effective_weights()` in `snn/rules/delivery.py`, but for this
    negative/inhibitory path, which delivers via `apply_inhibition` rather
    than `receive_input`). The per-discharge LEARNING call keeps using the
    RAW, unscaled gate magnitude — influence is applied exactly once, at
    delivery, never again in the learning update.
- `backend/simulation.py`:
  - New module-level Phase 4 section: `INFLUENCE_SAFE_MAX=4.0`,
    `_power_law_influence(d, ref, d_min, power)` (the shared, configurable
    power law — defaults `ref==d_min` make it pure attenuation, never
    amplifying), `_summarize_pathway(entries)` (min/median/max influence + a
    `safe` flag).
  - Seven new constructor params, all defaulting to neutral/off:
    `infl_power=2.0` (inverse-square), `infl_ref=1.0`, `infl_min=1.0`
    (ref==min by default), and `infl_l2e_l2i`/`infl_l2i_l2e`/`infl_l2e_l1i`/
    `infl_l1i_l1e` (all `False`).
  - `_apply_experimental_pathway_distances()`: computes real-geometry
    distances for the four new pathways from `self._geometry_xy` and sets
    `distance_weighting`/`distance_power`/`distance_ref`/`distance_min`/
    `.distance` on the target neuron(s) for each — reusing the SAME generic
    per-neuron delivery machinery the legacy L1E→L2E pathway already uses
    (`effective_weights()` in `snn/rules/delivery.py`), since L2I/L1I/L1E's
    distance fields were completely dormant before this phase (confirmed via
    `NeuronConfig.apply_to()`, which explicitly forces `distance_weighting`
    off for every non-L2E neuron — this method must run, and does run, AFTER
    that). L1I→L1E neutralizes L1E's abstract external-pixel channel
    (`distance[1] = infl_ref`, giving factor `1.0` exactly) so the sensory
    input is never accidentally attenuated. Called from both `_build()` and
    `reseed_topology()`.
  - `pathway_influence_report()` (new): the full per-connection audit across
    all FIVE pathways — source, target, distance, influence, raw weight,
    effective transmission, `applied` — reusing `_delivery_diagnostics()` for
    the untouched legacy L1E→L2E pathway.
  - `TUNABLE`/`apply_config()`: the seven new params are dashboard-configurable
    (bool-coerced flags, float-coerced power law).
- `backend/api.py`: new `GET /api/pathway_influence` endpoint (returns
  `pathway_influence_report()`); seven new `CONFIG_SPEC` entries (all
  `advanced=True`, so they render in the collapsed "Advanced" panel, not the
  main one — matching "isolated experimental", not a new default experience).
- `test_influence_phase.py` (new) — 18 tests: all four new flags default off;
  `DASHBOARD_PRESET` doesn't enable any of them; the legacy L1E→L2E pathway
  and both Phase 2/3 baselines untouched; disabled-config byte-equivalence;
  each pathway's flag is independent of the others; close-vs-distant delivery
  for all four new pathways (L2E→L2I and L2E→L1I via `effective_weights()`
  directly, L1I→L1E via a direct `apply_inhibition()` call since its effect
  isn't reliably observable in L1E's spike outcome -- see Known problems,
  L2I→L2E via a direct `apply_competitive_reset()` comparison confirming the
  depression gain scales with distance while the reset itself stays exact);
  influence fixed across steps/training/probes and only changes on
  `reseed_topology()`; no-influence-squared checks (delivery uses
  `influence**1` exactly, not `influence**2`); learning uses the raw
  unscaled weight; no reported influence exceeds 1.0 under the default law;
  full `pathway_influence_report()` structure and `applied`-flag correctness.

### Phase 3 (prior checkpoint `0e353cd`)

- `backend/simulation.py`:
  - New geometry constants + helpers: `L1_JITTER_FRAC`, `L1I_PAIR_JITTER_FRAC`,
    `L2E_PLACEMENT_RADIUS`, `L2E_MIN_SEPARATION`,
    `L2E_PLACEMENT_MAX_TRIES/_RESTARTS`, `_legacy_l1_xy()` (the deterministic
    legacy grid, factored out and reused as both the `symmetric_geometry=True`
    source and the `legacy_distance_compat` reference), `_jittered_l1e_xy()`,
    `_paired_l1i_xy()`, `_irregular_l2e_xy()` (seeded rejection-sampling
    placement with a minimum-separation constraint).
  - Three new constructor params, all defaulting to the exact legacy behavior
    so every existing caller/test is unaffected: `topology_seed=1`,
    `symmetric_geometry=True`, `legacy_distance_compat=True`.
  - `_compute_geometry()`: returns legacy positions verbatim when
    `symmetric_geometry=True`, else draws jittered/irregular positions from
    `topology_seed` via a dedicated RNG stream (independent of the weight-init
    `seed`).
  - `_register_neurons()` now calls `_compute_geometry()` and caches the result
    on `self._geometry_xy`; positions are recomputed identically on every
    `_build()` (deterministic given `topology_seed`), which is exactly what
    keeps them FIXED across `reset()`/`apply_config()`/`reseed()` (weight)/
    probes — none of those change `topology_seed`.
  - `_apply_l2e_distances()`: when `legacy_distance_compat=True` (default), the
    per-L2E delivery distances come from the legacy reference geometry
    regardless of `symmetric_geometry`; when `False`, they come from the real
    `self._geometry_xy` positions (the Phase 4 path).
  - `reseed_topology()`: the ONLY thing that changes `topology_seed` (a new
    dedicated verb, deliberately NOT in `TUNABLE`/the generic config panel) —
    regenerates positions in place WITHOUT calling `_build()`, so every learned
    weight/confidence value and the current pattern/probe/auto-cycle state
    survive untouched.
  - `TUNABLE`/`apply_config()`: added `symmetric_geometry`/
    `legacy_distance_compat` as bool-coerced dashboard ablation toggles
    (rebuilds the network, like every other config toggle); `topology_seed`
    deliberately excluded.
  - `topology()`: new `geometry` descriptor (`symmetric`, `topology_seed`,
    `legacy_distance_compat`, `legacy_distance_compat_active`) so the UI can
    clearly label when distance/influence numbers are the temporary pinned
    placeholder rather than computed from the visible coordinates.
- `backend/api.py`: new `POST /api/reseed_topology` endpoint.
- `backend/presets.py`: `DASHBOARD_PRESET` now sets `symmetric_geometry=False`
  (the live dashboard shows the new jittered/irregular geometry) and
  `legacy_distance_compat=True` (dynamics stay pinned to the legacy baseline),
  with an explicit comment flagging Phase 4 as where this is expected to flip.
- `frontend/inspector.js`: a visible "legacy-distance compat active" notice
  card plus a `⚠`-marked, differently-colored delivery readout on every
  synapse row when `topology.geometry.legacy_distance_compat_active` is true —
  the pinned numbers are never shown as if computed from the displayed
  coordinates.
- `frontend/index.html` / `frontend/controls.js`: a "Reseed Topology" button
  (geometry-only; no confirmation dialog, since unlike Reseed/Reset it does
  not wipe learned state) so the feature — and Fit View reacting to new
  positions — is actually exercisable from the dashboard.
- `test_geometry_phase.py` (new) — 19 tests: legacy-ablation exact
  reproduction, seed reproduction (same/different topology_seed), fixity
  across reset/training/weight-reseed/probe/apply_config, `reseed_topology()`
  changes positions but preserves weights (and is a no-op under
  `symmetric_geometry=True`), spatial bounds (L1E cell confinement, L1I
  pairing, L2E placement radius, L2I center, z-coordinates unchanged),
  irregularity (>10 distinct pairwise L2E distances vs. the legacy ring's 6),
  minimum separation across 5 seeds, serialization (`geometry` descriptor +
  per-synapse delivery fields under the new geometry), the compat shim's
  distance-pinning in both directions, and the phase's central guarantee —
  `DASHBOARD_PRESET`'s new geometry produces a byte-identical winner sequence
  and final weights to what it would have produced before this phase.

### Phase 2 (prior checkpoints `9163da2`/`05c17a0`)

#### Milestone 2 — frontend

- `frontend/index.html` — "Presentation" top-bar stat pill; "Held-out Probes"
  sidebar section (`#probe-buttons`, `#probe-status`); `#fit-view` button in
  the viewport; new "Causal Story" bottom-panel tab (`#causal-current` /
  `#causal-history`). Explicitly did **not** add an "Input Weights" tab.
- `frontend/style.css` — styling for the above (`.probe-btn`, `.probe-status`,
  `#fit-view`, `.causal-*`).
- `frontend/controls.js` — `buildProbeButtons()` (mirrors
  `buildPatternButtons()`, posts to `/api/probe`); `_updateProbeStatus()`
  reflecting `dyn.probe`/`dyn.causal_story` (frozen state, steps elapsed).
- `frontend/app.js` — top-bar "Presentation" readout from `dyn.causal_story`;
  wires the new `CausalStory` module; wires `#fit-view` to `renderer.fitView()`.
- `frontend/receptive.js` — **removed** the client-side top-3-weight-ratio
  "dead" guess (the audit-flagged divergence risk); now reads
  `state.rf_status.status` (`unrecruited`/`active`/`quiet`) straight from the
  backend.
- `frontend/raster.js` / `frontend/charge.js` — presentation-boundary vertical
  markers (solid = training pattern, dashed = probe), driven purely by
  watching `dyn.causal_story.presentation_id` change (backend-computed value;
  the frontend does no detection/inference of its own, only bookkeeping of
  already-known state). Both remain continuous rolling-history, real-spike-only
  views (`raster.js`) and threshold-normalized-charge views (`charge.js`,
  `activation` = V/θ) — these were already correct per the Phase 1 audit and
  are unchanged in that respect.
- `frontend/renderer.js` — `fitView()`: computes the actual bounding box from
  `this.pos` (built only from `topology.neurons[i].pos`, i.e. real engine
  coordinates — verified non-degenerate: x∈[-3.2,3.2], y∈[-3.2,3.2],
  z∈[-2.0,6.0] across all 27 neurons on the live server), then repositions the
  camera/target with 20% padding along the SAME default viewing direction. The
  default camera pose and the rest of the 3D view are untouched.
- `frontend/inspector.js` — synapse rows now show `distance`/`influence`/
  `effective` (from `backend/_delivery_diagnostics`) when present.
- `frontend/causal.js` (new) — pure renderer of `dyn.causal_story`; computes
  nothing itself (no first-spike/tie/source detection client-side).

All new/changed JS files pass `node --input-type=module --check` (syntax-only;
no bundler in this project). No file in `frontend/` steps or mutates engine
state — every action is still an HTTP POST, exactly as before.

#### Milestone 1 — backend core (prior checkpoint `9163da2`)

- `backend/presets.py` (new) — `DASHBOARD_PRESET`, the exact kwargs
  `backend/api.py` used to construct inline, now named/importable (no values
  changed; addresses the audit's "preset parity" gap for future diagnostics).
- `backend/api.py` — engine construction now `SimulationEngine(seed=_load_seed(),
  **DASHBOARD_PRESET)`; added `ProbeBody` + `POST /api/probe`.
- `backend/simulation.py`:
  - `PROBES` (row 0/row 2/col 0/col 2, held-out) + `PATTERN_ROLE` shared
    metadata. `PATTERNS` and `_cycle_order` (auto-cycle) are untouched, so
    auto-cycle remains training-patterns-only by construction.
  - Presentation tracking: `presentation_id`/`_start_presentation`/
    `_track_presentation`/`presentation_log`, capturing brief §9's fields
    (first physical L2E responder, first-spike step, same-step tie, first
    L1I/L2I source+step) from already-decided physical events only.
  - `present_probe`/`_end_probe`/`_cancel_probe_if_active`: presentation-scoped
    plasticity freeze via `Neuron.plasticity_frozen`, auto-restores the prior
    pattern/input after `steps` (default: `visit_steps`), never touches
    auto-cycle's paused `_visit_step`/`_visit_spikes`/`_pattern_streak`.
  - Evidence bookkeeping: `_neuron_total_spikes`, `_neuron_last_fired_t`,
    `_neuron_first_responder_counts`, `_pattern_first_responder_log`, and
    `_l2e_status(j)` — replaces the audit-flagged client-side weight-sum
    "dead" guess with an observed-behavior status (`unrecruited`/`active`/`quiet`).
  - `_delivery_diagnostics()` — per-feedforward-synapse distance/influence/
    effective-transmission, always computed (not gated on `distance_weighting`),
    closing the audit's "distance/influence absent end-to-end" gap.
  - `topology()`/`dynamic_state()` extended: `probes`, `probe_vectors`,
    `pattern_roles`, per-synapse `distance`/`influence`/`effective`,
    `causal_story`, `probe`, `rf_status` per L2E, `l2_drive`, `l2_charge`
    (previously computed internally but never serialized), `inh_events`.
- `neuron_flexible.py` — added `Neuron.plasticity_frozen` (default `False`,
  every existing caller unaffected) and guarded it in the only three
  weight-mutating call sites (`_update_weights`, `apply_competitive_reset`'s
  depression, `apply_inhibition`'s gate-plasticity/loser-depression) plus
  `_homeostatic_scaling`; all PHYSICAL effects (membrane integration,
  threshold crossing, firing, the unconditional reset/discharge) are
  untouched by the flag.
- `test_observability_phase.py` (new) — 14 tests: pattern/probe metadata,
  auto-cycle training-only, probe immutability (weights AND confidence
  byte-identical across a probe presentation, with real spikes still
  occurring), probe auto-restore/unfreeze, probe-vs-auto-cycle bookkeeping
  safety, manual-input cancels a probe, presentation ID increments +
  history, first-responder evidence accumulation, serialization contents,
  evidence-based status semantics, legacy-equivalence checks.

No neural equation and no preset VALUE was changed. `CLAUDE_HANDOFF.md`
(this file) is also part of this checkpoint's commit.

## Tests

### Phase 12 (this checkpoint)

- `pytest -q` (full suite, final run of this session): **254 passed, 5
  failed** — identical count and identical failing test names to the Phase
  11 checkpoint (no test file was added or changed this phase; only
  `backend/api.py`'s `CONFIG_SPEC` was touched, and it is not exercised by
  the unit suite's collection count, only by the new smoke checks below).
- **New this phase — real end-to-end smoke checks** (not part of `pytest -q`,
  run directly via `fastapi.testclient.TestClient` after installing `httpx2`
  into the session venv): `GET /api/state`, `GET /api/config`, `POST
  /api/config` (round-trip verified to actually change engine behavior, not
  just accepted), `POST /api/step`, `GET /api/pathway_influence` all return
  200 with the expected Phase 7/9/10 fields present; a full WebSocket
  `topology` → `step` → `dynamic` exchange over `/ws` also carries
  `l2_inhibition`/`adaptive_threshold` in the streamed payload. This is the
  first checkpoint in this session where a live-server-shaped check (as
  opposed to direct `SimulationEngine` construction) was possible.
- **Backend/UI agreement, verified programmatically:** a direct set-difference
  between `SimulationEngine.TUNABLE` and `backend.api.CONFIG_SPEC` (plus
  `_HIDDEN_CONFIG_KEYS`) confirmed zero orphaned UI controls (every served
  key is engine-`TUNABLE`) and enumerated the 7 previously-missing keys
  (now fixed) plus the 9 remaining, confirmed-pre-existing, out-of-scope
  gaps (see `Phase12_Final_Local_Review.md` §3).
- **No-software-tiebreak audit:** `grep`-based sweep of `backend/simulation.py`
  for `argmax`/`key=lambda` patterns, with every hit individually reviewed
  and classified (competition-deciding vs. UI/logging-only vs. raw-fact-
  labeling-only vs. the one remaining `lasting_inhibition` exception) —
  documented in `Phase12_Final_Local_Review.md` §6, not just asserted.

### Phase 11 (prior checkpoint `1a59ae8`)

- `test_phase11_validation.py` (new, focused): **6/6 passed**.
- `pytest -q` (full suite): **254 passed, 5 failed** (248 prior + 6 new =
  254; same 5 pre-existing `test_flow_rate.py`/`test_assembly_flow_credit.py`
  failures as every prior checkpoint, untouched).
- **The report's own inputs were validated, not just generated:**
  `test_report_has_every_expected_combination_with_no_gaps` confirms all 96
  expected (schedule, geometry, adaptive_threshold, weight_seed,
  topology_seed) combinations are present exactly once -- no run silently
  dropped or duplicated; `test_success_criterion_evaluation_matches_recorded_data`
  independently re-derives the report's headline "4/6" best-cell number
  straight from the raw JSON, catching any hand-typo between the data and
  the written report.
- **The mid-phase confound fix is directly tested:**
  `test_geometry_alone_is_a_null_result_when_influence_is_off` proves, via a
  real (if small) run, that symmetric and jittered geometry are byte-
  identical in every measured metric when influence is off -- the mechanical
  finding the full report's Conclusion 3 depends on.
- **Harness determinism:** `test_harness_is_deterministic` runs the identical
  condition/seed/steps twice and confirms bit-identical measurements -- no
  hidden RNG in the measurement code itself (separate from the engine's own,
  already-covered determinism).
- **No engine/mechanism code was touched this phase** -- `phase11_validation.py`
  and its test file are the only new files; `git status` confirms zero
  modified `.py` files outside them.

### Phase 10 (prior checkpoint `d333945`)

- `test_adaptive_threshold.py` (new, focused): **16/16 passed**.
- `pytest -q` (full suite): **248 passed, 5 failed** (232 prior + 16 new =
  248; same 5 pre-existing `test_flow_rate.py`/`test_assembly_flow_credit.py`
  failures as every prior checkpoint, untouched).
- **Toggle-off equivalence, verified at both levels:**
  `test_toggle_off_is_baseline_equivalent` (unit) confirms a stray nonzero
  `a_i` is fully ignored when the flag is off; `test_engine_default_is_off_and_baseline_equivalent`
  (engine) runs an explicit `adaptive_threshold=False` engine side-by-side
  with the default over 60 real steps and confirms an identical winner
  sequence AND identical final weights.
- **Equation exactness:** `test_decay_toward_zero` compares the post-update
  `a_i` against a hand-computed `10.0 * exp(-1/5)` after one step, then
  confirms convergence to ~0 after 200 steps; `test_effective_threshold_equation`
  and `test_check_threshold_uses_effective_threshold_when_on` confirm the
  elevated threshold is actually what gates firing, not just computed and
  ignored.
- **Independence from homeostasis/geometry:**
  `test_separate_from_homeostasis_flag` confirms toggling one flag never
  implies the other; `test_non_l2e_populations_never_get_adaptive_threshold`
  confirms the L2E-only scope.
- **Isolation and determinism:** `test_isolation_between_neurons` fires one
  neuron and confirms a sibling's `a_i` stays exactly 0;
  `test_deterministic_replay` runs the identical seed/steps twice and
  confirms a bit-identical `a_i` trajectory.
- **Probe restoration, both exit paths:**
  `test_probe_restores_pre_probe_threshold_adapt` (natural elapse) and
  `test_probe_cancellation_also_restores_threshold_adapt` (cancelled via
  `clear_input()`) both confirm `a_i` returns to its exact pre-probe value;
  `test_probe_lets_a_i_evolve_internally_during_the_window` confirms it is
  NOT frozen live (real spikes during the probe do move it) -- only the
  before/after values are protected.
- **No parameter tuning to force a result:** defaults
  (`delta_threshold_frac=0.05`, `tau_threshold=25.0`) are used as-is across
  every test; no seed-specific override was introduced to make a particular
  test pass.

### Phase 9 (prior checkpoint `3dd6f4c`)

- `test_l1i_causal_feedback.py` (new, focused): **12/12 passed**.
- `pytest -q` (full suite): **232 passed, 5 failed** (220 prior + 12 new =
  232; same 5 pre-existing `test_flow_rate.py`/`test_assembly_flow_credit.py`
  failures as every prior checkpoint, untouched).
- **The correctness fix, verified directly:**
  `test_l1i_source_is_ambiguous_on_any_step_not_just_the_first_spike` drives
  a real forced same-step multi-firer event on a LATER step (well after the
  presentation's first spike) through the full engine and confirms both
  `l1i_first_source`/`l2i_first_source` report `'ambiguous'` when that step
  is the one being attributed; `test_credit_source_directly_checks_this_steps_firer_set`
  is a direct unit-level proof of the fixed helper's exact contract.
- **Causal chain ordering:** `test_arrival_precedes_or_equals_threshold_crossing`
  and `test_delivery_effect_lands_one_step_after_threshold_crossing` confirm
  the three-hop timing (arrival <= threshold crossing < delivery, with
  delivery exactly `+1`) under `DASHBOARD_PRESET`'s live config.
- **No fabricated per-unit distinction:**
  `test_l2e_l1i_delivery_is_currently_identical_across_units_by_default`
  re-confirms the Phase 1 audit finding (one shared literal weight vector)
  is still true and reported honestly, not hidden.
- **No software-broadcast duplication:**
  `test_default_mode_l1i_does_not_fire_without_real_threshold_crossing`
  reuses `test_l1i_immediate_relay.py`'s sabotage technique (zeroed weights,
  impossibly high threshold) under the DEFAULT (non-relay) config and
  confirms L1I does not fire despite a real L2E winner appearing.
- **Probe non-mutation and presentation-boundary reset** re-verified under
  the new bookkeeping specifically (not just inherited from Phase 2/6's
  existing tests).
- **No collateral:** all pre-existing L1I/L2I-attribution-adjacent tests
  (`test_representation_candidate.py`'s tie tests,
  `test_l1i_immediate_relay.py` in full) pass unchanged.

### Phase 8 (prior checkpoint `c0ac363`)

- `test_structural_free_energy.py`: **13/13 passed** (5 pre-existing + 8 new).
- `pytest -q` (full suite): **220 passed, 5 failed** (212 prior + 8 new = 220;
  same 5 pre-existing `test_flow_rate.py`/`test_assembly_flow_credit.py`
  failures as every prior checkpoint, untouched — unrelated to this phase).
- **Equation exactness:** `test_exact_equation_matches_the_literal_formula`
  computes the reference by hand from the literal spec string and checks
  bit-for-bit; `test_gate_replaces_p` re-derives the same reference inline
  inside the full `_update_weights` call path (not just the bare helper).
- **Saturation:** `test_saturation_envelope_zero_at_w_max_both_directions`
  confirms a weight sitting exactly at `w_max` cannot move in EITHER
  direction (the intended, literal consequence of the symmetric envelope —
  contrasted explicitly with the OLD reflected kernel, which still permitted
  downward movement at the cap); `test_saturation_envelope_maximal_at_w_min`
  confirms envelope=1 at w=0; `test_clamp_is_purely_numerical` confirms an
  oversized update lands exactly on the bound rather than overshooting.
- **No duplicated capacity/influence factor:**
  `test_fe_gate_and_envelope_are_the_only_two_factors` fires the SAME neuron
  at two wildly different `v_pre` values (which would change `p` by ~100x)
  and confirms the FE-gated update is bit-identical either way — proving `p`
  has been fully replaced, not blended in.
- **Locality, verified structurally (not just by convention):**
  `test_fe_update_uses_only_this_neurons_own_state` parses
  `exact_local_free_energy_update`'s AST and asserts its executable body
  (docstring excluded) references no name beyond its own five parameters —
  a stronger guarantee than a docstring claim.
- **Ambiguity (same-step tie):**
  `test_same_step_tie_gives_no_special_credit_either_side` forces a real
  same-step tie through the full engine (`structural_free_energy=True`) and
  confirms both firers independently apply their own local FE update
  regardless of `self.winner`/tie status — the rule never referenced
  `self.winner` in the first place, so there was no representative-specific
  credit to withhold, and this test proves that absence rather than assuming it.
- **Probe non-mutation:**
  `test_frozen_probe_does_not_mutate_weights_or_confidence_under_fe` re-runs
  Phase 2's guarantee under `DASHBOARD_PRESET` with `structural_free_energy=True`
  layered on top — weights and confidence are byte-identical across the probe.
- **No collateral:** all four other pre-existing tests in the file
  (`test_gate_monotonic_in_sum`, `test_negative_gate_ignored`,
  `test_flag_off_identical`, `test_only_signed_path`) pass unchanged — the
  gate VALUE computation, the flag-off path, and the legacy-charge-path
  inertness are all untouched by this phase.

### Phase 7 (prior checkpoint `d946ff0`)

- `test_l2i_causal_inhibition.py` (new, focused): **15/15 passed**.
- 13 pre-existing tests updated across `test_competitive_reset.py`,
  `test_refractory_gating.py`, `test_influence_phase.py`,
  `test_hard_reset_inhibition.py`, `test_l2_competition.py` (see Files
  changed): **all pass** with the new bounded/refractory-skipping/
  delayed-delivery semantics.
- `pytest -q` (full suite): **212 passed, 5 failed** (197 prior + 15 new = 212;
  same 5 pre-existing `test_flow_rate.py`/`test_assembly_flow_credit.py`
  failures as every prior checkpoint, untouched — flow-rate is permanently
  neutered in `_build()`, confirmed unrelated to this phase).
- **Probe non-mutation preserved:**
  `test_probe_plasticity_freeze_does_not_block_delivery_discharge` confirms a
  probe's frozen plasticity blocks the structural-depression learning a
  delivery can trigger while the physical membrane discharge still happens —
  and that no weight changes across the probe regardless.
- **Direct engine-level verification, not inferred:**
  `test_every_threshold_crosser_fires_not_just_one` forces two L2E above
  threshold in the same step and confirms BOTH physically spike (`e.spiked`);
  `test_l2i_fire_schedules_a_delayed_delivery_not_an_immediate_reset` confirms
  `_resolve_l2_competition` never populates `_reset_events`/`inhibited` and
  only schedules; `test_refractory_target_is_skipped_not_forced` confirms
  delivery is attempted uniformly but a refractory target is excluded from
  the applied-targets list; `test_pending_delivery_is_not_cancelled_by_a_pattern_switch`
  confirms a scheduled delivery survives `set_pattern` (an in-flight physical
  signal, matching the `l1i_feedback_delay` precedent).
- **This phase deliberately changes physical dynamics** (the explicit point of
  the instruction), so `sustained_dominance.py`/`ablation_harness.py`/
  `diagnostic_schedule.py` were re-run to capture NEW baselines rather than
  reproduce old ones — see Known problems for the numbers and why they
  differ. This is the FIRST phase where a changed number is expected and
  correct, not a regression.
- **Full-stack smoke test:** direct engine construction + `step()` loop
  confirmed `dynamic_state()['l2_inhibition']` is well-formed and non-empty
  after a real run under `DASHBOARD_PRESET`; `backend.api` still imports and
  builds its module-level `engine` cleanly (exercised via
  `test_constant_input_feedback.py`, which imports `backend.api`, inside the
  same `pytest -q` run — no separate httpx-based HTTP smoke test was possible
  in this environment, see Known problems).

### Phase 6 (prior checkpoint `aa271fc`)

- `test_representation_candidate.py` (new, focused): **13/13 passed**.
- `pytest -q` (full suite): **194 passed, 5 failed** (181 prior + 13 new =
  194; same 5 pre-existing failures as every prior checkpoint, untouched).
- **Physical dynamics completely unchanged, verified three ways:**
  1. `sustained_dominance.py`/`ablation_harness.py` (unmodified) reproduce the
     exact Phase 1 numbers.
  2. `test_representation_tracking_never_affects_physical_dynamics` runs two
     identical-seed engines side by side, one read heavily
     (`dynamic_state()`/`winner`/`pathway_influence_report()` between every
     step) and one left alone, and asserts identical winner sequences AND
     identical final weights — proving the representation-tracking layer is a
     pure, write-only-for-display side channel with zero feedback into the
     simulation.
  3. While validating with `diagnostic_schedule.py`, found a col-1/seed-1
     discrepancy that looked like a dynamics change but was NOT: the
     first-spiker counts for `L2E3`/`L2E4` were an EXACT 7-7 tie, and
     `_modal()`'s `max(set(...), key=count)` breaks such ties by Python's
     per-process string hash randomization, not the data. Fixed to a
     deterministic sorted tiebreak (see Files changed); re-ran three times —
     stable now, and the underlying counts (0.47 consistency either way) were
     identical throughout, confirming no dynamics changed.
- **The central semantic guarantee, verified directly:**
  `test_winner_is_none_during_a_same_step_tie` forces two L2E neurons above
  threshold in the same step and confirms `winner is None` while
  `earliest_response_set` correctly contains both ids and `first_spiker`
  (the raw fact) still names whichever one the legacy tiebreak let fire;
  `test_winner_stays_none_for_rest_of_presentation_after_a_tie` confirms a
  LATER, unambiguous spike does not retroactively become the winner;
  `test_no_evidence_credit_for_a_tied_first_response` confirms neither
  `_pattern_first_responder_log` nor `_neuron_first_responder_counts` records
  a tied presentation; `test_l1i_l2i_source_is_ambiguous_when_it_would_credit_the_tied_first_spiker`
  confirms L1I/L2I source attribution reports `'ambiguous'` rather than
  naming the tied neuron when the two coincide on the same step.
- **Non-tied case:** `test_winner_equals_first_physical_spiker_when_not_tied`
  and `test_earliest_response_set_is_singleton_when_not_tied` confirm the
  ordinary path is exactly `winner == first_spiker` with a one-element
  earliest-response set.
- **Later responses / latency:** `test_later_responses_recorded_in_chronological_order`
  and `test_latency_to_second_response_only_counts_a_distinct_identity` confirm
  the ordered list and the distinct-identity-only latency computation.
- **Retired mechanism confirmed gone:**
  `test_latest_spike_wins_episode_machinery_is_fully_removed` checks
  `dynamic_state()` has no `episode` key and that all four `episode_*`
  attributes and both retired methods no longer exist on the engine object.
- **Probe non-mutation preserved** (explicit instruction):
  `test_probe_non_mutation_still_holds` re-verifies weights/confidence are
  byte-identical across a probe presentation with real spikes still
  occurring (Phase 2's guarantee, re-confirmed under the new winner logic);
  `test_probe_presentation_can_still_report_a_winner_while_frozen` confirms a
  probe can still have a representation candidate (physics stay live even
  though plasticity is frozen).
- **Full-stack smoke test (real server):** confirmed via a direct
  `GET /api/state` read that `dynamic.causal_story` carries all three new
  fields and that the `episode` key is genuinely absent from the live
  payload, not just from unit tests.

### Phase 5 (prior checkpoint `ff3048f`)

- `test_diagnostic_schedule.py` (new, focused): **13/13 passed**.
- `pytest -q` (full suite): **181 passed, 5 failed** (168 prior + 13 new =
  181; same 5 pre-existing failures as every prior checkpoint, untouched).
  Zero engine files were modified this phase, so this is a trivial re-run —
  confirmed via `git status` showing only new, untracked files.
- **Legacy/baseline equivalence:** `sustained_dominance.py`/
  `ablation_harness.py` (unmodified) still reproduce the exact Phase 1
  numbers — expected and confirmed, since no engine code changed.
- **Non-mutating evaluation, the phase's central guarantee, verified
  directly:** `test_run_diagnostic_never_mutates_a_passed_in_live_engine`
  builds a live engine, trains it for 40 steps, snapshots its weights/
  timestep/presentation_id/input vector, runs a full diagnostic sweep against
  it via `engine=live`, and asserts all four are bit-for-bit identical
  afterward — plus a separate live manual check (outside pytest) confirming
  the same on a `DASHBOARD_PRESET` engine.
- **Brief, non-saturating presentations:** `PRESENTATION_STEPS=20` (asserted
  in-range, 5-40, matching the scale of every other diagnostic in the repo);
  `test_live_pass_visits_patterns_in_fixed_cycle_order` confirms the exact
  `row 1 -> col 1 -> diag \ -> diag / -> repeat` sequence, never holding one
  pattern before the others.
- **Frozen-copy correctness:** `test_frozen_pass_produces_zero_weight_drift`
  confirms every frozen-pass presentation has `plasticity_frozen=True` and
  literally zero weight change, while `test_live_pass_actually_learns`
  confirms the (non-frozen) live pass does show real weight changes
  somewhere — together proving the freeze mechanism is doing real work, not
  silently absent.
- **Every requested field recorded, correctly:** presentation ID/pattern/
  plasticity, first spiker + step, same-step tie, the full ordered spike
  list, latency margin to the second DISTINCT responder (asserted `None`
  exactly when fewer than 2 distinct L2E identities fired — not a bogus
  number), L2I spike steps/count, L1I fired positions per step, pre/post-
  inhibition charge snapshots (one per step, count matches the window),
  receptive fields (9 values per L2E), and weight-change deltas.
- **Report sanity:** consistency/ambiguity/no-response bounded in `[0,1]`;
  silent and recruitable cell sets are disjoint subsets of the 8 L2E ids;
  every reported collision is internally consistent with the owners list;
  distinct-owner count matches the deduplicated owner set exactly.
- **5-seed baseline saved** to `Diagnostic_Schedule_Baseline.md` (see that
  file for full tables): distinct owners 2.20/4 mean; L1I all-nine-sync rate
  **1.0 in every single seed with zero exceptions** — an empirical,
  quantitative confirmation of the Phase 1 audit's L1I-lockstep finding;
  frozen-replay zero-weight-drift confirmed in all 5 seeds, with
  first-responder consistency high but not always 1.0 even under a fully
  frozen network (isolating genuine physical/temporal variability from
  weight drift).

### Phase 4 (prior checkpoint `586d0f7`)

- `test_influence_phase.py` (new, focused): **18/18 passed**.
- `pytest -q` (full suite): **168 passed, 5 failed** (150 prior + 18 new =
  168; same 5 pre-existing failures as every prior checkpoint, untouched).
- **Legacy/baseline equivalence:** `sustained_dominance.py`/
  `ablation_harness.py` (unmodified) still reproduce the Phase 1 numbers
  exactly; `test_disabled_equivalence_dashboard_preset_unaffected_by_new_params_existing`
  confirms `DASHBOARD_PRESET` (which does not set any of the four new flags)
  produces byte-identical winners/weights across a fresh 600-step run;
  `test_dashboard_preset_does_not_enable_any_new_pathway` asserts this
  directly against the preset dict, not just observed behavior.
- **Close vs. distant delivery, per pathway** (brief requirement, tested
  precisely, not just qualitatively):
  - L2E→L2I / L2E→L1I: `effective_weights()` at `d==ref==min` returns the RAW
    weight exactly (influence==1.0); at `d==5×ref` returns strictly less.
  - L1I→L1E: tested via a **direct** `apply_inhibition()` call (not the full
    engine loop) because L1E's pixel drive delivers exactly its own threshold
    with zero margin — ANY nonzero inhibition already fully suppresses firing
    regardless of magnitude, so the pathway's real, correctly-applied effect
    is not reliably observable in whether L1E ends up spiking (see Known
    problems). Direct test: close (`d==ref`) delivers the full discharge
    (potential → 0 exactly); distant (`d==2×ref`, power=2) delivers exactly
    25% (potential → 750.0 exactly) — confirming both the scaling AND that it
    is not squared (would be 6.25% / potential → 937.5 if it were).
  - L2I→L2E: `apply_competitive_reset()` compared directly at
    `competitive_reset_influence=1.0` vs. `0.25` — the depression magnitude
    scales down accordingly while `v_post` (the unconditional reset) is
    `resting_potential` in BOTH cases, confirming the reset invariant survives
    untouched.
- **No influence-squared bug**, verified two ways: (1) direct numeric
  comparison of `effective_weights()`'s output against `raw*influence**1`
  (matches) and `raw*influence**2` (does not match); (2) the L1I→L1E
  close/distant test above, where a squared factor would have produced a
  visibly different (937.5, not 750.0) result.
- **Learning uses the raw, unscaled weight**, not the distance-scaled
  delivered value — verified for the E→I feedforward rule directly (heavy
  distance attenuation on the delivery side does not gate whether/how much
  the raw weight learns).
- **Reset stability / fixed influence:** per-connection distances (hence
  influence) are identical before/after 60 steps of training plus a 10-step
  probe, and only change on an explicit `reseed_topology()` call — mirroring
  Phase 3's positional-fixity guarantee, now re-verified at the influence
  level for all three geometry-dependent new pathways.
- **Avoid extreme amplification:** with all four new pathways simultaneously
  enabled (deliberately stress-testing the "don't enable together" guidance
  rather than avoiding it), every reported `influence_max` is `<= 1.0` and
  every pathway's `safe` flag is `True`.
- **Full-stack smoke test (real server):** ran `uvicorn backend.api:app`,
  confirmed `GET /api/pathway_influence` returns all five pathways with
  correct entry counts (72/8/8/72/9) and sane values, and that the seven new
  `infl_*` config keys appear in `GET /api/config` under `advanced: true`
  (collapsed "Advanced" panel — not surfaced as a new default control).

### Phase 3 (prior checkpoint `0e353cd`)

- `test_geometry_phase.py` (new, focused): **19/19 passed** — legacy-ablation
  exact reproduction, seed reproduction, fixity across reset/training/
  weight-reseed/probe/apply_config, `reseed_topology()` semantics, spatial
  bounds, irregularity, minimum separation (5 seeds), serialization, and the
  compat shim in both directions.
- `pytest -q` (full suite): **150 passed, 5 failed** (131 prior + 19 new =
  150; same 5 pre-existing failures as every prior checkpoint, untouched).
- **Legacy equivalence — the central guarantee of this phase, verified at
  three levels:**
  1. `sustained_dominance.py` / `ablation_harness.py --seeds 1 2 --epochs 3`
     (unmodified; never pass the new geometry kwargs) reproduce the Phase 1
     numbers exactly, unchanged since Phase 2.
  2. Per-L2E `distance` arrays are `np.array_equal` between
     `symmetric_geometry=True` and `symmetric_geometry=False,
     legacy_distance_compat=True` — the geometry-derived input to the neural
     equations is provably identical regardless of displayed layout.
  3. `test_dashboard_preset_with_new_geometry_is_dynamically_identical_to_pre_phase3`
     runs `DASHBOARD_PRESET` (new geometry) against an otherwise-identical
     config forced back to `symmetric_geometry=True` (what it would have been
     before this phase) for 600 steps across all 4 training patterns: the
     **exact winner-sequence and final learned weights are identical**, not
     just aggregate statistics.
- Irregularity/separation verified numerically, not just by construction: a
  live-instance check found 27 of 28 possible pairwise L2E distances distinct
  (vs. the legacy ring's 6), with the enforced 1.3 minimum comfortably cleared
  (observed minimum 1.81 at `topology_seed=42`).
- **Full-stack smoke test (real server):** ran `uvicorn backend.api:app`,
  confirmed `topology.geometry` reports the new seeded state
  (`symmetric: false, legacy_distance_compat_active: true`) with genuinely
  irregular L2E positions (e.g. `L2E0 [1.663, 0.506, 4.0]`, nothing on a
  ring), and that `POST /api/reseed_topology` redraws positions live (new
  `topology_seed` returned, new coordinates on the next `/api/state` read)
  without disturbing the running network.
- Fit View's actual on-screen camera motion was not screenshotted (no browser
  in this environment, same limitation as Phase 2) — but its only input
  (`topology.neurons[i].pos`) was confirmed to carry real, varied, non-ring
  coordinates from the live server, and `renderer.fitView()` itself is
  unchanged code from Phase 2 (already reviewed).

### Phase 2 (prior checkpoints, unchanged by this phase)

- `test_observability_phase.py` (new, focused): **14/14 passed**.
- `pytest -q` (full suite): **131 passed, 5 failed** (117 pre-existing + 14
  new = 131; same 5 pre-existing `test_flow_rate.py`/
  `test_assembly_flow_credit.py` failures as the Phase 1 baseline, unrelated
  to this work, not touched).
- **Legacy equivalence, verified two ways:**
  1. `sustained_dominance.py` and `ablation_harness.py --seeds 1 2 --epochs 3`
     (both unmodified) reproduce the Phase 1 audit's recorded numbers
     exactly: `distinct=2.00/4, sustained_dominance=0.497, dead=5.00` and
     `dom=0.39±0.015, distinct=2/4, collisions=2, dead=5, rf_cos
     0.915->0.904` respectively.
  2. `test_plasticity_frozen_defaults_false_and_learning_is_unaffected` in the
     new test file asserts weights actually change over 80 steps under the
     (untouched) default `plasticity_frozen=False` path.
- Probe immutability verified directly: `test_probe_presentation_never_mutates_a_weight_or_confidence`
  hashes every synapse weight and every confidence value before/after a
  25-step probe and asserts equality, while also asserting `spikes > 0`
  during the probe (physical dynamics stay live).
- **Full-stack smoke test (real server, not just unit tests):** ran
  `uvicorn backend.api:app` in the background and drove it with an actual
  websocket client (the runner only steps while a client is connected —
  confirmed by reading `backend/websocket.py`, pre-existing behavior, not a
  regression). Verified over the wire:
  - `topology`/`dynamic` messages contain `probes`, `pattern_roles`,
    per-synapse `distance`/`influence`/`effective`, `causal_story`, `probe`,
    `rf_status`.
  - `POST /api/probe {"name": "col 0", "steps": 20}` → `causal_story.role`
    flips to `probe` and `plasticity_frozen`/`probe.active` read `True` for
    exactly the requested 20 frames, then both flip back to `False` and the
    engine auto-restores the prior training pattern — `presentation_log`
    history shows both presentations in order.
  - Topology neuron positions are real, non-degenerate 3D coordinates (see
    Fit View note above), confirming `renderer.fitView()` has genuine engine
    geometry to compute a bounding box from.
- Raster/charge boundary-marker *rendering* and Fit View's on-screen camera
  motion were verified by code review + confirmed correct upstream data (the
  `causal_story.presentation_id` transitions and real topology bounds above),
  not by literally opening a browser (none available in this environment). If
  the user wants a visual check, the dashboard now runs correctly
  end-to-end (`uvicorn backend.api:app`, verified above) and can be opened at
  `http://127.0.0.1:8000`.

## Known problems

- **RESOLVED (Phase 12): backend/UI `CONFIG_SPEC` gap for 7 keys.**
  `symmetric_geometry`/`legacy_distance_compat` (Phase 3) and
  `l2_inhibition_delay`/`l2_inhibition_frac`/`adaptive_threshold`/
  `delta_threshold_frac`/`tau_threshold` (Phases 7/10) were `TUNABLE` on the
  engine but unreachable from the dashboard config panel. Fixed; verified
  via a live HTTP round-trip (see `Phase12_Final_Local_Review.md` §2-3).
- **One software winner/tie-break shortcut remains, found in Phase 12's
  audit and NOT fixed** (out of Phase 12's "no new mechanisms" scope):
  `lasting_inhibition`'s branch in `step()` (~line 2034) still picks a
  single physical firer via `max(eligible, key=potential)` -- a genuine
  hidden-charge argmax. It is a pre-existing, `default=False`, opt-in
  ALTERNATE competition mechanism, never touched by Phase 7 (which targeted
  only `_resolve_l2_competition`), not enabled by `DASHBOARD_PRESET`, and
  not exercised by any of Phase 11's 96 runs. The default/dashboard
  competition path itself has zero remaining shortcuts. Flagged for a
  future phase if `lasting_inhibition` is ever meant to become a supported,
  non-experimental path.
- **Nine legacy `TUNABLE` keys remain unexposed in `CONFIG_SPEC`**
  (`conf_cap_frac`, `eta_min`, `hard_reset_clear_traces`,
  `inhibitory_delta_eta`, `inhibitory_margin_frac`, `inhibitory_rule_mode`,
  `l2i_excitatory_flow_rate`, `l2i_hard_reset_losers`, `seed`) -- confirmed
  pre-existing (predate Phase 6), confirmed NOT touched by Phases 6-11,
  deliberately left alone in Phase 12 (bundling nine unrelated legacy-knob
  decisions into a final-review commit would obscure what Phases 6-12
  actually changed) -- candidate for a future, explicitly-scoped cleanup.
- **RESOLVED (measured, Phase 11): `adaptive_threshold`'s effect is now
  characterized, and it is a MIXED result, not a clean win.** It raised mean
  distinct_owners in 6 of 8 condition-pairs (most in long-saturation:
  1.67->3.00), left one nearly flat, and actively REDUCED it in one
  (short-interleaved, symmetric geometry + influence on: 2.33->2.00). Its
  Phase 10 defaults (`delta_threshold_frac=0.05`/`tau_threshold=25`) were
  used as-is throughout Phase 11 -- still not tuned/recommended values, now
  with actual measured behavior attached rather than "unmeasured." See
  `Phase11_Multiseed_Validation_Report.md` for the full breakdown.
- **The central ownership-consolidation problem remains open.** Phase 11's
  96-run sweep found NO condition (of 16 schedule x geometry x
  adaptive-threshold combinations) that robustly meets "four distinct stable
  owners with spare neurons recruitable" across all 6 seed-topology
  combinations. The best cell (short-interleaved, influence off, adaptive
  threshold on) reaches it in 4/6 -- a real, repeated improvement over the
  same condition without adaptive threshold (2/6), but explicitly NOT counted
  as a pass per the phase's own "do not count one lucky seed" instruction.
  This is the same central failure the Phase 1 audit first identified,
  narrowed down across six intervening phases of causal-dynamics work
  (Phases 6-10) without being solved by any of them individually or in
  combination -- consistent with each of those phases' own scope (none of
  them claimed to solve one-to-one ownership; each replaced a specific
  mechanism with a more physically-grounded one).
- **Distance-weighting "influence" has a schedule-DEPENDENT effect, not a
  uniform one.** Turning it on REDUCED distinct_owners in short-interleaved
  (3.33->2.33 symmetric, 3.33->1.50 jittered) but modestly INCREASED it in
  long-saturation (1.67->2.33 symmetric, 1.67->2.17 jittered), both at
  adaptive_threshold=False. Reported as-observed; not resolved or tuned
  toward either direction.
- **Geometry alone (symmetric vs. jittered) has ZERO measured effect on any
  metric unless an influence pathway is actively consuming it** -- confirmed
  bit-identical across every metric in Phase 11's data whenever
  `distance_weighting` is off. This reconfirms (does not newly discover) the
  Phase 3/4 architecture: position is purely structural/cosmetic until a
  distance-weighted delivery pathway reads it.
- **L1I still has no real per-unit geometric/causal differentiation by
  default.** All 9 units share one literal feedback weight vector and
  receive an identical `l2e` delivery, so their synchrony (confirmed again
  by this phase's own tests, and by Phase 5's `L1I all-nine-sync rate: 1.0`)
  is structural, not fixed. Phase 4's `infl_l2e_l1i` pathway is a real,
  already-audited, geometrically-grounded per-unit distance differentiator
  and IS a "demonstrated physical path" -- but it is default OFF (an isolated
  Phase 4 ablation, deliberately not enabled together with other pathways),
  so it was NOT turned on here. Phase 9's scope was the causal
  attribution/recording layer (source/set/arrival/threshold/target/delivery/
  effect) and a targeted `_credit_source` correctness fix, not a rewiring of
  L2E->L1I connectivity or enabling a Phase 4 pathway by default -- flagged
  as a candidate for a future phase if genuine per-unit L1I differentiation
  is wanted as a default behavior.
- **`structural_free_energy` is still default OFF** (`DASHBOARD_PRESET` does
  not set it) -- Phase 8 corrected the equation used WHEN it is enabled, but
  did not turn it on by default or measure its effect on distinct-owner/
  pool-participation metrics against the new Phase 7 baseline. The original
  ported prompt's own "Expected Effect"/"Measurements" sections (multi-seed
  consolidation/retention comparisons) were explicitly NOT part of the
  corrected Phase 8 prompt's narrower scope (equation + tests + validation +
  handoff only) and were deliberately not run here -- a future phase could
  sweep `structural_free_energy`/`structural_fe_eta_floor` against the Phase 7
  baseline if the user wants that experiment revisited.
- **The exact envelope's both-directions-zero-at-cap property is a real
  behavioral difference from the old reflected kernel**, worth remembering if
  `structural_free_energy` is ever enabled together with `loser_depression`'s
  OWN structural-FE-gated depression path in `apply_delayed_inhibition`
  (unaffected by this phase, still uses `bounded_signed_update`) -- the two
  call sites now use DIFFERENT saturating shapes for what is nominally "the
  same" FE gate value, which is intentional (Phase 8 only pins the
  potentiation/signed-learning path) but should be kept in mind if the two
  are ever meant to be unified later.
- **The "central failure" is now measured through an honest first-spike lens,
  and it's still unsolved.** With `self.winner` correctly tracking the first
  physical responder (not latest-spike), re-running
  `diagnostic_schedule.py --seeds 1 2 3 4 5` (same defaults as the saved
  Phase 5 baseline) after this phase's change would be the natural next
  validation step -- not yet done as a NEW saved baseline in this checkpoint
  (the existing `Diagnostic_Schedule_Baseline.md` numbers are unaffected,
  since that script computes `first_l2e_spiker` from its own raw stepping,
  not from `engine.winner` -- see Files changed for the confirmation this
  produced no change). Phase 7 re-ran this exact diagnostic and its numbers
  DID change (see below) -- this bullet's "not yet done" framing is now
  superseded by Phase 7's own findings.
- **RESOLVED (Phase 6 -> Phase 7): the legacy immediate-reset competition is
  gone.** `_resolve_l2_competition` no longer picks a single physical
  "resetter" via hidden membrane charge -- every threshold-crosser fires, and
  L2I's own threshold crossing schedules a delayed, uniform delivery instead
  of an immediate reset. See Files changed/Goal above for the full design.
- **Phase 7 measurably reduces distinct-owner/pool-participation metrics --
  expected, and worth tracking closely.** Re-running
  `diagnostic_schedule.py --seeds 1 2 3 4 5` (identical protocol to the saved
  Phase 5 baseline) after this phase's change gives **distinct_owners =
  1.60/4** (down from the Phase 5 baseline's 2.20/4) with per-pattern
  consistency in a similar range (0.667-0.813 vs. the baseline's 0.680-0.813).
  `sustained_dominance.py`/`ablation_harness.py` (held-pattern protocol) show
  a much larger effect: **distinct=1/4, sustained_dominance=1.000, dead=7**
  (vs. the long-standing confirmed baseline `distinct=2.00/4,
  sustained_dominance=0.497, dead=5.00`) -- under a single HELD pattern for
  many cycles, one specialist now wins EVERY cycle, and the SAME specialist
  wins across all four DIFFERENT held patterns. This is the expected physical
  consequence of removing the same-step immediate mutual exclusion: the old
  design forced a fresh competition every single step (any step with 2+
  crossers immediately reset everyone but one), which is what drove rotation;
  the new design only corrects the pool every few steps (whenever L2I's OWN
  accumulated evidence crosses its threshold), so a fast/confident specialist
  can keep firing largely unimpeded between corrections and entrenches
  further each pattern-hold. Per brief SS9 ("do not resolve this with a
  software exception") this was NOT tuned away by adjusting
  `l2_inhibition_frac`/`l2_inhibition_delay` to force a particular outcome --
  it is reported as a real, measured consequence for the user to weigh. Not
  yet investigated: whether this is specific to the `sustained_dominance`/
  `ablation_harness` HELD-pattern protocol (a regime the brief's own
  equal-interleaved schedule does not exercise) or a broader effect; a future
  phase could look at this directly if the user wants pool utilization
  addressed further.
- **No adaptive/learned L2I->L2E gate was reintroduced.** The delayed
  delivery's magnitude is a FIXED, configurable constant
  (`l2_inhibition_frac * threshold_l2`), not something that learns per-target
  over time -- an explicit, documented simplification (out of scope for this
  phase; the instruction asked for causal timing/accumulation, not a new
  learning rule).
- **No httpx-based live-server HTTP smoke test was possible in this
  environment** (`starlette.testclient` requires `httpx2`, not installed) --
  verified instead via direct engine construction/stepping and via
  `test_constant_input_feedback.py` (which imports `backend.api` and its
  module-level `engine` inside the same `pytest -q` run). Flagged in case a
  human or a differently-provisioned session wants to eyeball the live
  websocket/API surface directly.
- L1I/L2I source attribution's "no winner-specific credit" guard
  (`_credit_source`) only nulls out a source when it would otherwise name the
  presentation's own tied FIRST responder on the exact same step it fired.
  A later (non-first) L2E win that happens to itself be part of a same-step
  tie at a LATER point in the presentation is not specially flagged --
  `self.winner` is unaffected either way (it was decided once, at the first
  spike), but a future phase could extend `same_step_tie`-style ambiguity
  tracking to every step, not just the presentation's first one, if that
  finer-grained signal turns out to matter.
- **This diagnostic (Phase 5) confirms, quantitatively, that the "central
  failure" remains unsolved under the live `DASHBOARD_PRESET` config:** the
  5-seed baseline (`Diagnostic_Schedule_Baseline.md`) shows 2.20/4 mean
  distinct owners under the brief's own equal-interleaved schedule (not just
  under the ad hoc windows earlier diagnostics used), with collisions in
  every single seed and "forgetting" (a pattern's modal owner changing within
  one run) in 3 of 5 seeds. This is a measurement, not a fix — "do not change
  competition yet" was followed exactly (zero engine files touched).
- **Forgetting and consistency now have a saved, reproducible baseline
  number** to compare against for any future competition change:
  per-pattern consistency 0.68-0.81 under brief presentations; once
  plasticity is frozen, first-responder consistency is high (mostly 1.0) but
  NOT always 1.0 (as low as 0.6 in a few pattern/seed combinations) — meaning
  some of the instability is genuine physical/temporal variability at
  presentation boundaries, not purely weight drift during training. Any
  future competition change should be checked against BOTH numbers.
- Per `AGENT_HANDOFF.md`/the Phase 1 audit, true one-to-one L2E ownership is
  still unsolved and NEITHER Phase 2, 3, nor 4 fix it by default — the four
  new Phase 4 pathways are all off in `DASHBOARD_PRESET`, so the live
  dashboard's actual behavior is unchanged from Phase 3. See
  `Geometric_Influence_Temporal_Winner_Audit.md` for the full list of
  confirmed conflicts still awaiting a decision. Finding (2)'s
  perfect-ring-geometry concern is addressed for placement/rendering (Phase 3)
  and now has REAL, audited, opt-in influence pathways available for L2E→L2I/
  L2I→L2E/L2E→L1I/L1I→L1E (Phase 4) — but L1E→L2E itself (the pathway that
  concern was originally about) still runs under the `legacy_distance_compat`
  shim by default, so IT still hasn't been flipped over to the real new
  geometry. That flip was the original Phase 4 plan anticipated at the end of
  Phase 3; the ACTUAL Phase 4 instruction took a narrower, additive path
  instead (new isolated pathways, legacy pathway untouched) — flagged here so
  future work knows that flip is still on the table, separately, if wanted.
- **L1I→L1E's influence is real and correctly applied, but not reliably
  observable in whether L1E fires.** L1E's external-pixel drive delivers
  EXACTLY its own threshold with zero headroom (`e.weights=[-1,+1]*UNIT`,
  `thr_l1=1*UNIT` — "one pixel spike... fires the encoder in one hit," per
  the original module docstring). Any nonzero inhibitory discharge — scaled
  by distance-influence or not — already drops the post-inhibition potential
  below threshold, so L1E fails to fire either way. The pathway is verified
  correct at the mechanism level (`apply_inhibition`'s delivered magnitude
  provably scales with distance — see Tests), just not at the emergent
  spike/L2E level under the current L1 fixed-point design. If this pathway is
  meant to visibly change L1 spiking, L1E's threshold margin would need
  revisiting separately — out of scope for "isolated experimental behavior."
- `four-pattern` branch carries diagnostic/tracer work not yet reviewed for
  porting.
- The four new pathways currently share ONE power-law configuration
  (`infl_power`/`infl_ref`/`infl_min`), not independently tunable per pathway.
  A scope decision for simplicity/parameter-surface reasons — easy to split
  into per-pathway triples later if independent tuning turns out to matter.
- `pathway_influence_report()`/`GET /api/pathway_influence` is diagnostic-only
  (on-demand GET), not pushed with every `dynamic_state()` frame or surfaced
  in any frontend view yet — no UI change was made this phase (the
  instruction was backend/audit-focused; the existing generic config panel
  already exposes the four new toggles + power-law sliders under "Advanced"
  with no frontend code changes needed).
- Presentation boundaries are scoped to NAMED pattern/probe switches only
  (`set_pattern`/`present_probe`); raw pixel/random/noise edits do not start a
  new presentation record. Documented, not a bug — free-form manual input was
  never part of the brief's presentation protocol.
- Tie detection (`same_step_tie`) is validated against the default
  event-driven/chunked-charge path (what the live dashboard actually runs);
  the legacy `lasting_inhibition`/`event_driven=False` branches are wired
  (`_last_eligible` is set in both) but not separately tested here.
- No literal browser was opened for Phase 2 or Phase 3 (none available in
  this environment); Fit View / boundary-marker visuals were verified by code
  review plus confirmed-correct upstream data, not a screenshot. Flagged for a
  human or a browser-capable session to eyeball if desired.
- `topology_seed` is NOT persisted across a server restart (unlike the
  weight-init `seed`, which is deliberately persisted to `.claude/dashboard_seed.txt`
  — see `_load_seed`/`_save_seed`). A restart currently returns to
  `topology_seed=1`'s geometry. This was a deliberate scope decision (the
  instruction only required fixity across reset/training/probes, not across
  restarts) — flagged in case the user wants restart-persistence added later.
- `L2E_PLACEMENT_RADIUS=3.6` / `L2E_MIN_SEPARATION=1.3` were chosen to keep
  the new layout roughly the same visual scale as the legacy ring (radius 3.2)
  while giving the rejection sampler comfortable room (observed min separation
  well above the floor across the seeds tested) — not derived from any brief
  requirement beyond "bounded" and "minimum separation enforced". Revisit if a
  tighter/looser packing is wanted.

## Next action

**Phase 12 is closed. This was the final phase of the corrected Phases 6-12
prompt file.** No further phase is queued in this session. The branch
(`july14-integration`, HEAD at this checkpoint) is ready for human review;
see `Phase12_Final_Local_Review.md` for the complete final commit chain and
working-tree status. Per that file's "LATER PUSH PROMPT" section, any push
requires its own separate, explicit human confirmation after review --
nothing in Phases 7-12 pushed, merged, or opened a PR.

Candidates for a future phase, none started, all needing their own explicit
go-ahead (compiled across Phases 7-12, still open at this checkpoint):
- Redesign `lasting_inhibition`'s competition mechanism (Phase 12 audit,
  Known Problems) to remove its remaining hidden-charge argmax tiebreak, if
  that alternate mechanism is ever meant to become a supported path rather
  than an unexercised, default-off legacy ablation.
- Explicitly-scoped cleanup pass exposing the 9 remaining legacy `TUNABLE`
  keys in `CONFIG_SPEC` (or formally deprecating/removing them if truly
  dead) -- deliberately not bundled into Phase 12's final-review commit.
- Investigate the central ownership-consolidation problem directly (Phase
  11's 96-run sweep confirms it is still open in every configuration tested)
  -- NOT by tuning `l2_inhibition_frac`/`delta_threshold_frac`/etc. to force
  a metric, per the standing "no software exception" guidance that has
  shaped every phase since Phase 7.
- Investigate the schedule-dependent direction-flip of distance-weighting
  influence on distinct_owners (helps long-saturation, hurts
  short-interleaved) -- Phase 11 measured it but did not investigate why.
- Enable Phase 4's `infl_l2e_l1i` pathway (a real, demonstrated, geometric
  per-unit differentiator for L1I) as a default/canonical behavior, if
  genuine per-unit L1I differentiation is wanted rather than the current
  honestly-reported structural sameness -- explicitly out of Phase 9's scope.
- Sweep `structural_free_energy`/`structural_fe_eta_floor` (now Phase
  8-corrected) against the Phase 7 competition baseline, per the original
  ported prompt's multi-seed consolidation/retention measurements -- not run
  in Phase 8 (out of its narrower corrected scope).
- Investigating the measured distinct-owner/pool-participation decline from
  Phase 7 (especially the `sustained_dominance.py`/`ablation_harness.py`
  HELD-pattern collapse to `distinct=1/4`) if the user wants that addressed;
  should NOT be resolved by tuning `l2_inhibition_frac`/`l2_inhibition_delay`
  to force a particular metric (brief SS9).
- Investigate why `sustained_dominance.py`/`ablation_harness.py`'s HELD-pattern
  protocol now collapses to one specialist dominating all four patterns
  (`distinct=1/4`, `dead=7`) while the brief's own equal-interleaved schedule
  (`diagnostic_schedule.py`) shows a smaller decline (2.20/4 -> 1.60/4) --
  whether this is protocol-specific or a broader Phase 7 consequence.
- Whether a learned/adaptive L2I->L2E delivery magnitude (rather than the
  current fixed `l2_inhibition_frac * threshold_l2`) is wanted -- explicitly
  out of scope for Phase 7.
- DONE (Phase 7): re-ran `diagnostic_schedule.py --seeds 1 2 3 4 5` now that
  `self.winner` correctly tracks the first physical responder AND now that
  competition itself is causal/delayed -- see Known problems for the numbers.
  `Diagnostic_Schedule_Baseline.md` itself was left unmodified (it documents
  the Phase 5 snapshot); a future phase could save a new dated baseline file
  if a stable reference point post-Phase-7 is wanted.
- Use `diagnostic_schedule.py` to actually experiment with the four Phase 4
  distance/influence pathways ONE AT A TIME (per "do not enable every pathway
  together"), comparing each run's `summarize()` output against the saved
  baseline to see whether any pathway measurably improves distinct-owner
  count, collisions, or consistency — the infrastructure is ready; no
  experiment has been run yet.
- Revisit whether to flip `legacy_distance_compat=False` for the ORIGINAL
  L1E→L2E pathway (the plan anticipated at the end of Phase 3) — this is the
  one change in this whole area still expected to alter baseline dynamics
  when it happens, so it should stay a deliberate, separately-approved step.
- Whether `topology_seed` should persist across a server restart like the
  weight-init `seed` does (currently does not — see Known problems from
  Phase 3, still applicable).
- Whether the four Phase 4 pathways should get independent per-pathway
  power-law configs instead of the current shared one.
- Whether `same_step_tie`-style ambiguity tracking should extend beyond just
  the presentation's first response (see Known problems).
