# Phase 34: Active-Dendrite Local Coincidence Prediction — Report

**Branch `phase34-active-dendrite-coincidence`, based on `ffefd1f` (the FSCI/ISM
final consolidated report commit) — deliberately NOT built on Phase 33's
commit `a51b4e4` on `l2-ownership-recovery`, per explicit instruction. That
commit remains preserved as an unpromoted negative experiment.**

## Motivation

Phase 33's causal microstep L2 race investigation (on `l2-ownership-recovery`,
a sibling of this branch) reconfirmed the standing finding from Phase 27 and
the Gate 1 saturation/compression audit: ownership collisions in this network
are decided early by dynamical/competitive-timing factors, not by weight
saturation or L2 competition granularity. Separately, Codex 1/Codex 2's
preflight review of the existing Phase 19/21/30 prediction architecture
identified that the additive PCi somatic-integration model (`pc.receive_input`
summing decayed feedback and lateral traces) allows PCi to fire from strong
feedback alone once the decoder matures, even with zero real sensory evidence
— a false-positive reconstruction mode, not a genuine coincidence detector.

This phase implements a coincidence-GATED alternative: an "active dendrite"
that can never fire from either afferent alone, only from a genuine physical
coincidence of a real sensory arrival and a real feedback arrival in the same
step, against an already-matured decoder synapse.

## Contract correction (mid-implementation)

The original Phase 34 contract specified the dendritic-fire condition as
`u_i^S * z_j^R >= 0.7`, using the DECAYED traces as the coincidence gate (a
soft ~1-step tolerance). Before any code was written, this was corrected:

> Bound both learning traces: `z_j^R <- min(1, 0.7*z_j^R + feedback_arrival_j)`,
> `u_i^S <- min(1, 0.7*u_i^S + sensory_arrival_i)`. Use these traces for
> decoder learning only. A physical dendritic spike must require CURRENT-STEP
> delivered events: `sensory_arrival_i(t) == 1`, `feedback_arrival_j(t) == 1`,
> `d_ji_before_learning >= 350`. Do not permit residual traces alone to
> generate the dendritic spike. Evaluate dendritic firing using d_ji before
> this step's learning update. If the current event raises d_ji across 350,
> the next coincident event may fire.

The implementation below is built to this corrected contract from the start
(never implemented, then patched, per the original spec).

## What was implemented

New default-OFF flag `prediction_active_dendrite_enabled` in
`backend/simulation.py` (plus `prediction_active_dendrite_learning_rate`,
`prediction_active_dendrite_trace_retention`, `prediction_active_dendrite_
coincidence_weight`). When on, it REPLACES the additive `pc.receive_input`
somatic path entirely for every PCi:

- **Decoder learning** (`_apply_active_dendrite_decoder_learning`, runs every
  step regardless of PCi's own spike): bounded, decaying traces
  `_pcol_ad_z`/`_pcol_ad_u` (retention 0.7, clipped to `[0, 1]`) feed
  `delta_d_ji = eta * z_j^R * u_i^S * (1 - d_ji/d_max)^2` — monotonic,
  saturating, positive-only, same two-gate structure as the existing Phase 30
  subthreshold rule.
- **Physical dendritic spike** (`_active_dendrite_event`): reads the RAW,
  undecayed this-step arrival vectors only (never the traces) — fires iff
  `sensory_arrival_i(t)==1 AND feedback_arrival_j(t)==1` for some `j`, AND
  `d_ji` captured BEFORE this step's own learning update is
  `>= prediction_active_dendrite_coincidence_weight` (350). Multiple
  qualifying sources still produce exactly one bounded injection of
  `prediction_threshold` directly into the membrane — never additive, never
  routed through `receive_input`.
- Mutually exclusive with `prediction_subthreshold_decoder_enabled` (raises
  `ValueError` at build time if both are on). Flag-off is byte-identical to
  `ffefd1f` (verified over 300+ steps and by the full regression suite) and
  consumes no additional RNG.
- Topology preserved unchanged: `sensory E_i -> local sensory branch of PC_i`,
  `L2E_j -> learned distal feedback branch of PC_i` (via the existing delayed
  `l2e_to_pcol_queue`/`s_to_pcol_queue`), `PC_i -> paired I_i` (Phase 21's
  existing `prediction_column_to_i_enabled` wiring, completely untouched by
  this phase — `pcol_spiked[i]` feeds it identically regardless of which PC
  firing mechanism produced the spike).

## Bugs found and fixed during this phase's own validation

1. **Test-isolation confound (not a production-code bug).** `SimulationEngine`
   always holds SOME real pattern from construction (`current_pattern`
   defaults to the first entry in `PATTERNS`; there is no "no pattern" state).
   The first versions of Gate A and Gate B built engines from
   `DASHBOARD_PRESET` and manipulated the PC delayed-delivery queues directly
   without ever silencing that default-held pattern — so genuine L1E/L2E/L1I
   dynamics ran the ENTIRE time alongside the forced delivery. This produced a
   spurious Gate B **FAIL** (shadow-mode L1I appeared to react to nothing;
   active-mode L1I appeared not to react to a genuine PCi spike) that traced
   entirely to the REAL, ambient row-1-pattern-driven L2E->L1I broadcast
   pathway, unrelated to the Phase 34 mechanism. Fixed by explicitly zeroing
   `e.input_vec` after construction in both isolated gates (verified
   separately to produce zero L1E/L2E activity over 300 steps). Gate B PASSED
   cleanly once isolated correctly.
2. **eta correction (Codex preflight).** `prediction_active_dendrite_learning_
   rate`'s initial default (0.01, chosen only by loose analogy to the
   existing subthreshold-decoder rate) was replaced with **0.15** — the value
   that makes the closed-form saturating-growth solution
   (`dw/dt = eta*(1-w/w_max)^2` => `1/u = 1/u0 + (eta/w_max)*t`) land EXACTLY
   on the required reproduction target of "approximately 2946 coincidence
   events" to mature a synapse from `d=50` to `d=350`. Verified: Gate A's
   isolated logic test reproduces `first_fire_step=2946` exactly at this eta.
   0.15 is also simply the existing `prediction_learning_rate` constant
   already used by the Phase 19 spike-gated rule, reused rather than a new
   untested value.

## Documented, not fixed (out of this phase's scope)

The `CenteredEncoderRule`/`SignedSpikeRule` `w_max` inconsistency documented
in every prior phase since the Gate 1 audit remains unchanged and unfixed
here (irrelevant to this phase's own mechanism, which operates entirely on
PC decoder weights capped by `prediction_feedback_max`, not L2E feedforward
weights).

## Passive queue-origin telemetry (Codex preflight request)

Added, purely observational, verified to never alter scheduling, delivery,
potentials, weights, or RNG (see the mandatory tests below):

- Parallel origin-timestamp deques (`_pcol_feedback_origin_t`,
  `_pcol_sensory_origin_t`) tracking which real outer step produced each
  queued delivery vector.
- `_last_pattern_switch_t`: detected reactively at the top of `step()` by
  comparing `self.input_vec` against a snapshot from the previous step —
  covers every mutation path (`set_pattern`, auto-cycle, probes, `set_input`,
  `toggle_pixel`) uniformly without hooking each call site individually.
- Per-PCi, per-step dense probe (`_active_dendrite_last_probe`, overwritten
  every step) and a sparse log (`active_dendrite_event_log`, appended ONLY on
  an actual dendritic-spike event) recording: origin timestamps, whether the
  event used pre-switch ("stale") queue data, whether the paired sensory
  target is currently active (`self.input_vec[i]`), and a three-way
  suppression classification — `current-correct` (non-stale), `stale-but-
  same-pixel` (stale, but the target happens to still be active), or
  `stale-wrong-pixel` (stale and the target is not currently active).

## Mandatory tests

`test_phase34_active_dendrite_coincidence.py` — **35 tests, all passing.**
Covers: flag-off byte-identical behavior and RNG; trace-source isolation
(z only from feedback, u only from sensory); exact trace-decay/bound
formula verification; bounded-trace saturation under repeated arrivals;
sensory-alone/feedback-alone never fire (unit and engine level); temporal
separation (one step apart) never fires; residual-saturated-trace-alone
never fires; sub-coincidence-weight coincidence learns but never spikes;
genuine post-maturity coincidence fires; multiple qualifying sources still
produce one bounded injection; never calls `receive_input`; organic
maturation from real coincidences; frozen-plasticity blocks learning but not
physical firing; absent/untrained columns neither learn nor fire; PCi->Ii
wiring untouched; no pattern-boundary reset; locality (no argmax/owner/
pattern-name/cross-neuron state); determinism; mutual exclusivity with the
Phase 30 subthreshold decoder; the eta=0.15/2946-event reproduction target;
and the full passive-telemetry suite (non-mutation, origin-timestep
correctness, switch detection, all three suppression classifications, sparse
log semantics, disabled-when-flag-off).

## Full regression suite

`pytest -q`: **470 passed, 5 failed** — the same 5 pre-existing failures
documented across every prior phase in `CLAUDE_HANDOFF.md`
(`test_assembly_flow_credit.py::test_integration_four_pattern_regime_is_
active_and_bounded`, `test_flow_rate.py`'s four flow-rate tests); both files
date to the repository's initial commit. **Zero new regressions.**

## Gate results

### Gate A — isolated learned coincidence: **PASS**

Two parts, both against a silenced (all-zero `input_vec`) engine or a real
one, as appropriate:

**Part 1 (isolated logic, forced every-step coincidence for one fixed
PCi/L2Ej pair):**

| Requirement | Result |
|---|---|
| Immature phase (`d < 350`) produces zero spikes | PASS |
| Transition matches the corrected pre-update semantics (crossing step does not fire; the next coincident event, whose pre-update `d_ji` is already `>=350`, does) | PASS — crossing step 2945 (`d_after=350.0008`, did not fire); first fire at step 2946 |
| Mature phase always fires thereafter | PASS |
| Feedback-alone never fires, even at near-`d_max` | PASS (0/200) |

`first_fire_step = 2946`, matching the required reproduction target exactly.

**Part 2 (natural coincidence-rate measurement, per the explicit instruction
not to reuse a short window and interpret non-maturation as failure):** a
real, unforced engine presenting `'row 1'` alone was measured for its actual
physical same-step coincidence rate for the pattern's own causal
first-responder (`L2E4`, pixel 3): **0.505 coincidences/step**. Projected
natural maturation: ~5,831 real outer steps. Actually run for real (no
forcing) for 7,097 steps: **natural maturation was observed at step 4,239** —
organic, unforced decoder maturation under real network dynamics, confirming
Part 1's isolated result is not an artifact of the forced-delivery method.

### Gate B — shadow vs. active causal chain: **PASS**

Both conditions trained to maturity (`d_final ≈ 389.75`) via the same
isolated forced-coincidence protocol (corrected for input isolation):

| Requirement | Result |
|---|---|
| Shadow (`prediction_column_to_i_enabled=False`): PCi fires but has zero effect on L1Ii | PASS |
| Active (`=True`, `pretrained_l1i_regulation=True`): PCi fires and paired L1Ii reacts the SAME step | PASS |
| An untrained, non-coincident PC column (index 5) stays silent — neither it nor its paired L1I fires — in BOTH conditions | PASS |

### Gate C — exploratory two-pattern integration: **NEGATIVE (honestly reported)**

All 3 seeds organically matured the row-1 responder's decoder for all three
of row 1's own pixels within the training budget (no manual weight
assignment anywhere in this gate). First measurement pass used a binary
"did the pixel fire at all in the 20-step window" activity metric, which
trivially saturated to 1.0 for every pixel in every condition (a
continuously-held pixel almost always fires at least once in 20 steps, even
under transient inhibition) — a test-methodology bug, not a finding; fixed
to measure per-presentation firing RATE (fraction of steps within the
window) instead, then rerun:

| Measurement | off | on |
|---|---|---|
| Row-only pixels (3, 5), during 'row 1' | 0.500 | 0.698 |
| Column-only pixels (1, 7), during 'col 1' | 0.500 | 1.000 |

**Neither pre-registered observation holds**: row-only activity during 'row
1' INCREASED under prediction (not suppressed), and column-only activity
during 'col 1' also increased sharply (not preserved near baseline) —
`row_pixels_show_suppression_trend=False`, `col_pixels_remain_largely_
unaffected=False`.

A plausible mechanistic explanation (labeled as a hypothesis, not verified
further — outside this exploratory gate's own scope): enabling
`prediction_column_to_i_enabled` REPLACES L1Ii's default, frequent
L2E-broadcast-driven input with the sparser, coincidence-gated PCi-driven
input for ALL nine L1Ii, uniformly. Only row 1's own decoder was trained;
column 1's decoder never matured, so column pixels' L1Ii receives
essentially no drive under this routing and provides almost no suppression
at all (consistent with column activity saturating to 1.0). Row pixels'
L1Ii does receive occasional drive from the now-organically-firing PCi, but
only on a genuine same-step coincidence (no tolerance, no memory) — rarer
than the default broadcast's own firing frequency — so it suppresses LESS
than the mechanism it replaced, not more, explaining the row-only INCREASE
relative to the off baseline.

This is an honest negative result for the specific two-pattern integration
question asked, consistent with (and does not contradict) the explicit
caveat that this phase makes no claim that prediction solves four-pattern
ownership. It suggests that the selective PCi->Ii routing (Phase 21),
useful for isolating a clean causal chain in Gate B, may need to
SUPPLEMENT rather than REPLACE the existing broadcast-driven L1I
regulation to show a net suppressive effect at the population level — a
question for a future phase, not resolved here.

## Configuration

`prediction_active_dendrite_enabled=True`, `prediction_active_dendrite_
learning_rate=0.15`, `prediction_active_dendrite_trace_retention=0.7`,
`prediction_active_dendrite_coincidence_weight=350.0`. `prediction_threshold
=500`, `prediction_feedback_init=50`, `prediction_feedback_max=1200` (all
pre-existing Phase 19 defaults, unchanged).

## Files

- `backend/simulation.py` — the engine change (flag, methods, `step()`
  wiring, passive telemetry).
- `test_phase34_active_dendrite_coincidence.py` — 35 mandatory tests.
- `phase34_gate_a_isolated_coincidence.py` / `phase34_gate_a_results.json`.
- `phase34_gate_b_causal_chain.py` / `phase34_gate_b_results.json`.
- `phase34_gate_c_two_pattern_integration.py` / `phase34_gate_c_results.json`.
- `CLAUDE_HANDOFF.md` — updated per the established per-phase convention.

## Commit / branch status

Branch `phase34-active-dendrite-coincidence`, based on `ffefd1f`. Not pushed.
`l2-ownership-recovery` (HEAD `a51b4e4`, Phase 33) remains untouched and
preserved as a separate, unpromoted negative experiment.
