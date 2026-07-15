# Phase 18b — LPS Lecture 14 Local-Coincidence Prediction Architecture Contract

**Supersedes both prior prediction-architecture documents**:
`Phase18_Lecture14_Prediction_Architecture_Contract.md` (eight-predictor-
per-`L2E`, decoding to all nine `L1E`) and
`Phase18b_Lecture14_Prediction_Architecture_Contract_Corrected.md` (nine
per-column predictors with an all-to-all `L2Ej->Pi` decoder, but no local
lateral connection, and decoder learning gated on `L2Ej`'s own spike). Both
are kept unmodified in git history and both carry a superseded-banner
pointing here; their own implementation attempts are preserved, unmerged,
on `backup/phase19-candidate-a-wip`, `backup/phase19-eight-predictor-wip`,
`backup/phase19a-scaffold-config-ui-wip`, and
`backup/phase19-corrected-prediction`.

A fuller read of the annotated architecture diagram adds two requirements
neither prior document had: a fixed LOCAL lateral `S_i->Pi` coincidence
connection, and decoder learning gated on `Pi`'s OWN spike (crediting only
the `R_j` sources that causally contributed), not on `L2Ej`'s spike.

## Populations

Every pixel column `i` (of nine, one per input pixel) contains three
neurons:

1. **`S_i`** — the existing `L1E_i`. Fires on external pixel activity;
   feeds forward to all eight `R_j`. Unchanged.
2. **`PC_i`** — **new**, one prediction neuron per input column
   (`PC0`..`PC8`). `PC_i` means "pixel `i` is predicted." Not paired 1:1
   with one `R_j` — it receives learned top-down feedback from every `R_j`,
   plus a fixed local lateral connection from its own `S_i` only.
3. **`I_i`** — the existing `L1I_i`. Unchanged as a population in this
   phase; `PC_i -> I_i -> S_i` is the eventual predictive-inhibition path,
   explicitly deferred (see "Deferred" below).

The Layer-2 representation pool (`R_0`..`R_7` = `L2E0`..`L2E7`, shared
`L2I`) is unchanged in this phase.

## Connections

**Purple feedforward — `S_i -> R_j` (existing, unchanged).** Every sensory
`S_i` projects to every `R_j`; the existing learned encoder connections.

**Purple feedback — `R_j -> PC_i` (new, LEARNED, all-to-all).** Every `R_j`
projects to every `PC_i` — an 8x9 positive-bounded feedback matrix, serialized
as `colfb{j}->{i}`. Delivery is queued and arrives exactly
`prediction_feedback_delay` steps later (default 1, never same-step).

**Lime local coincidence — `S_i -> PC_i` (new, FIXED, one-to-one).** One
fixed paired local excitatory connection per column, serialized as
`lat{i}` — `S_0` only projects to `PC_0`, `S_1` only to `PC_1`, and so on.
Delivery is SAME-STEP (a direct local physical connection, never delayed).
Purpose: give `PC_i` physical evidence that pixel `i` is *currently* active,
so it can distinguish "`R_j` fired while my own pixel was active" from
"`R_j` fired but my pixel was absent" — see "Why the lime connection is
necessary" below.

**Deferred — `PC_i -> I_i -> S_i` (fixed/pretrained, NOT built in this
phase).** `PC_i` would excite only its paired local `I_i`; `I_i` would
inhibit only its paired `S_i`. No direct `PC_i -> all-L1E` connection, no
`PC_i -> all-L1I` connection — this is Phase 21's job (selective local
predictive inhibition), gated by a separate flag, not enabled here. **This
phase is SHADOW ONLY**: a `PC_i` spike has zero effect on any other neuron.

**Layer-2 WTA — `R_j -> shared L2I -> R pool` (existing, unchanged in this
phase).** Both recruitment and inhibitory reset stay exactly as they are
today (physical integration, threshold crossing, firing, causal delayed
delivery — no argmax, no owner lock, no same-step software clamp). Making
this pathway pretrained too (per the eventual complete Lecture 14 condition)
is a separate, later, default-off experiment — not implemented here.

## Why the lime connection is necessary

Without `S_i -> PC_i`, every `PC_i` receives the identical `R_j -> PC_i`
broadcast regardless of which pixel it represents — a single `R_j` (e.g. the
middle-row's owner) could eventually make ALL NINE `PC_i` learn to fire,
predicting the entire grid rather than only the pattern's own pixels. The
local lateral connection supplies pixel-specific physical evidence: for the
middle-row pattern, only `S_3`/`S_4`/`S_5` fire, so only `PC_3`/`PC_4`/`PC_5`
receive BOTH the lateral coincidence charge AND the top-down `R_j` feedback;
the other six `PC_i` receive only the top-down broadcast. With a correctly
calibrated coincidence window (see below), only the former three can
physically cross threshold, and — since decoder learning fires only on a
`PC_i`'s own physical spike — only their `R_j -> PC_i` synapses ever learn.
No pattern name or active-pixel array is passed into the learning rule; the
sensory pattern affects learning purely through physical local charge.

## Decoder learning (EXPERIMENTAL CANDIDATE, not a Lecture 14 equation)

On `PC_i`'s own physical spike only (never on a timer, never on `R_j`'s own
spike):

```
delta_w[j] = eta_prediction * (1 - w[j]/w_max)^2     (eligible j only)
```

"Eligible" means the specific `R_j` index whose delayed delivery actually
arrived and contributed to THIS spike — read directly off `PC_i`'s own
`_last_input_spikes` (indices 0..7), the same physical record `receive_input`
already populates; no separate bookkeeping, no pattern name, no owner table,
no cross-neuron comparison, no argmax. Monotonic, saturating, POSITIVE-ONLY
growth — this rule never depresses a synapse; a synapse that never
causally contributed to a real `PC_i` spike simply never changes, which is
also why an "inactive" `PC_i` (whose own pixel is never part of the current
pattern) can never accidentally learn: it never receives lateral
coincidence charge for that pattern, so it essentially never crosses
threshold from that pattern's presentations, so its `R_j -> PC_i` weights
for that pattern's owner(s) stay at `prediction_feedback_init` forever.

## Coincidence / leak requirements and the actual calibration

`PC_i` is a genuine integrate-and-fire neuron: `V <- decay(V) + w_lateral *
spike(S_i) [same-step] + sum_j w_feedback[j] * spike(R_j) [delayed]`, firing
only at `V >= prediction_threshold`.

The naive constraint list (single lateral event subthreshold; single
immature feedback event subthreshold; repeated feedback-only settles below
threshold; retained lateral + fresh feedback together can cross threshold)
undersells the real difficulty here, and this is worth stating plainly: in
`DASHBOARD_PRESET`, `S_i`'s own duty cycle is very high (empirically ~90%
of steps, because `refractory=0` in this preset) and `R_j`'s duty cycle is
moderate (empirically ~50%, roughly every 2-3 steps once a stable winner
emerges). A leaky integrator receiving the SAME fixed weight on
(nearly-)every step settles at a STEADY STATE of roughly `duty * weight /
leak_rate` — not just a single retained sample. This means:

- **Lateral-alone steady state** (an "active" `PC_i`, no feedback
  contribution at all) is *itself* large enough to threaten firing on its
  own, purely from `S_i`'s own high duty cycle — this is a real, load-bearing
  failure mode the naive constraint list does not name explicitly, but that
  this project's calibration run hit directly (see below).
- **Feedback-alone steady state** (an "inactive" `PC_i`) is smaller (lower
  duty cycle) but still nonzero, and — critically — is UNBOUNDED without a
  real leak (see the no-leak diagnostic below).

**Empirical calibration** (measured directly against this codebase's actual
dynamics, not derived in the abstract — see
`Phase19_Local_Coincidence_Shadow_Report.md` for the full sweep):

| `prediction_threshold` | Result |
|---|---|
| 1000 (naive guess, same scale as `threshold_l1`) | Nothing ever fires — coincidence charge never reaches it. |
| 300 | Pattern-selective, but fires almost every cycle (453/2000 steps) — later shown to be dominated by LATERAL-ALONE steady state (~416-500), not genuine coincidence: this is exactly the "sensory alone can fire `PC_i`" failure the lime connection exists to prevent. |
| 500 (chosen default) | Pattern-selective, genuinely coincidence-gated (learning only occurs on events with real `R_j` eligibility), but the firing rate is LOW and FRONT-LOADED — bursts during the early, unconverged competition phase, then stops almost entirely once `L2E` ownership settles into a regular rhythm whose phase no longer reliably overlaps the retained lateral charge. |
| 600+ | Nothing fires — window closed. |

The feasible window is real but **narrow and phase-sensitive**, not a
comfortable margin. This is reported honestly rather than tuned until it
looks clean: **this architecture, as specified, has a demonstrated tension
between "sensory alone must never fire `PC_i`" and "coincidence must
reliably fire `PC_i`" that a single global leak/threshold does not fully
resolve** — exactly the concern raised independently before this
calibration was run. Pattern selectivity (never firing on the wrong pixels)
holds cleanly across all four patterns even at the narrow default; SUSTAINED
learning throughout a long hold does not.

**No-leak diagnostic** (`prediction_leak_diagnostic_disable=True`, Part 5's
required control): with the leak forced to 0, INACTIVE `PC_i` (pixels never
part of the current pattern) fire repeatedly and without bound (200/3000
steps in the calibration run) purely from accumulated feedback-only charge
that never decays — directly reproducing the failure mode that motivates
having a real, nonzero, separately-tunable `prediction_leak` at all. With
the real leak (0.3 default), the same inactive columns never fire once in
20,000 steps.

## What this architecture may still fail to do

Per this project's established discipline of not overclaiming: even where
`PC_i` firing is pattern-selective, nothing here yet prevents a single
tyrant `R_j` from eventually being the sole learned contributor across
MULTIPLE patterns' `PC_i` populations (the familiar upstream Layer-2
ownership-collapse risk from Phases 11/13b/15/16/17, entirely orthogonal to
this decoder rule). A mixed decoder belonging to one tyrant is evidence of
upstream representation collapse, not necessarily decoder-rule failure —
Phase 19's diagnostic reports representation ownership, decoder quality
conditional on owner, and mixed-pattern reconstruction as separate findings,
never conflated (per the independent LPS14 review's correction #7, carried
over from the prior architecture's contract).

## What this phase does NOT implement

- `PC_i -> I_i -> S_i` (deferred to Phase 21).
- The all-inhibition-pretrained final Lecture 14 condition (a later,
  separate, default-off flag — the existing inhibitory-learning code path
  is preserved as the default baseline, untouched).
- Frequency-based learning-stop / synapse-level free-energy (Phases 23-25).
- Any change to the existing feedforward encoder rule, Layer-2 physical
  competition, distance/geometry, adaptive threshold, Phase 15 protection,
  leak of EXISTING populations, or current dashboard preset.

## Baseline verification

Full backend suite re-run after implementation: see
`Phase19_Local_Coincidence_Shadow_Report.md` for the exact pass/fail count.
