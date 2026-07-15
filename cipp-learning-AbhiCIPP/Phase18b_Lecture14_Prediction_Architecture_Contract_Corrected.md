# Phase 18b — Corrected LPS Lecture 14 Prediction Architecture Contract

**No neural-dynamics change. No topology change. No runtime behavior added.**
This document supersedes `Phase18_Lecture14_Prediction_Architecture_Contract.md`'s
eight-predictor topology (one `L2Pk` per `L2Ek`, decoding to all nine `L1Ei`).
That document remains in git history unmodified at `3fef508` and is not
deleted — its uncommitted implementation attempt is preserved, unmerged, on
local backup branches (`backup/phase19-candidate-a-wip`,
`backup/phase19-eight-predictor-wip`). A banner has been added to the top of
the original file pointing here. Everything numeric below is this project's
own candidate unless explicitly attributed to Lecture 14; every such
candidate is marked **[EXPERIMENTAL CANDIDATE]**.

## Why this correction

A closer, full read of the Lecture 14 transcript (not just the summary
documents) indicates the prediction neuron is described as living
**per input column**, not as one neuron per L2E representation. Each of
the nine lower/input cortical columns is described as containing a
sensory excitatory neuron, a prediction excitatory neuron, and a
(pretrained) local inhibitory neuron — three neurons per column, all
locally coupled — with the *upper* L2E representation layer projecting
down to the prediction neurons via learned excitatory feedback. This is
architecturally inverted from the superseded Phase 18 contract, which put
the one-to-one pairing at the L2 (representation) level and fanned each
predictor out to all nine L1 pixels. The corrected topology instead puts
one predictor per L1 pixel, fed by all eight L2E neurons through a learned
decoder matrix. This also better matches Lecture 14's actual claim: it is
the upper representation that has learned to predict a *specific* lower
column's activity, not a representation-indexed neuron broadcasting a
guess about every pixel independently.

## Architecture

### Populations

- **`L1E0`–`L1E8`** — existing sensory excitatory neurons, one per input
  pixel. Unchanged.
- **`L1P0`–`L1P8`** — **new**, one prediction excitatory neuron per input
  column, co-located with its paired `L1Ei`/`L1Ii`. `type='P'`, `layer='L1'`
  (distinct from the superseded contract's `L2`-layer `L2Pk`), so existing
  per-population UI toggles are unaffected until explicitly extended.
- **`L1I0`–`L1I8`** — existing local inhibitory neurons, one per input
  column. Unchanged as a population; see "All-I rule" below for what
  changes about their *plasticity*, not their existence.
- **`L2E0`–`L2E7`** — existing representation excitatory neurons. Unchanged.
- **`L2I`** (shared) — existing single shared inhibitory neuron. Unchanged
  as a population; see "All-I rule" below.

### Connections

**1. `L1Ei → L2Ej`: existing learned feedforward encoder.** Unchanged —
this is the current `ff{i}->{j}` weight array, already learned via
`SignedSpikeRule`. Nothing about this pathway changes in this contract.

**2. `L2Ej → L1Pi`: new learned positive-bounded decoder matrix.** This is
the actual prediction/reconstruction pathway and the only newly-learned
connection. Each `L1Pi` has eight independent afferent decoder weights, one
per `L2Ej` — the mirror of `L2Ej`'s own nine feedforward encoder weights,
but transposed (indexed by target pixel, source representation) and never
aliased to them. Naming convention: `decoder{j}->{i}` for the synapse from
`L2Ej` to `L1Pi`. Weights are bounded to `[0, w_cap_pred]`
**[EXPERIMENTAL CANDIDATE: exact cap]**, positive only (no inhibitory
decoder in this milestone). Direction: `source=L2Ej, target=L1Pi`.

**3. `L1Pi → L1Ei`: fixed local excitatory replay path (first
reconstruction experiment only).** One-to-one, **fixed, never learned** —
this pairing's job is delivering a column's own predicted evidence back to
its own sensory neuron; there is nothing to learn in a same-column,
one-to-one identity link. Fixed value candidate: `L1Ei`'s own threshold
(same "one physical spike alone is sufficient" reasoning used for every
other fixed recruitment synapse in this codebase — Phase 17's
`pretrained_l2i_recruitment`, the superseded contract's `L2Ek→L2Pk`)
**[EXPERIMENTAL CANDIDATE: exact fixed value]**.

**4. `L1Pi → L1Ii`: intended fixed local predictive-regulation path,
deferred.** Not built in Phase 18b/19/20. This is explicitly Phase 21's
job (selective local predictive inhibition) and must not be conflated with
connection 3 — a decoder that excites `L1Ei` and one that regulates
`L1Ii` are architecturally and functionally separate, gated by separate
flags, tested separately.

**5. `L2Ej → L2I` and `L2I → L2Ej`: fixed/pretrained in the Lecture 14
condition.** In the full Lecture 14 experimental condition (a specific,
separately-flagged configuration — not the codebase default), these
recruitment/return synapses use Phase 17's already-implemented
`pretrained_l2i_recruitment` mechanism (fixed recruitment weight, `L2I`'s
own learning rate pinned to 0). That flag already exists, already defaults
off, already carries its own documented negative result in isolation
(`Phase17_Lecture14_Mapping_and_Pretrained_L2I_Report.md`) — Phase 22 tests
its *interaction* with the corrected prediction pathway; this contract does
not change the flag's default or behavior.

**6. All `L1I` recruitment/output pathways: fixed/pretrained in the full
Lecture 14 condition.** Same posture as (5): the full Lecture 14 condition
is described as treating *all* inhibitory neurons as already trained —
no `L1I` synapse (recruitment in, output out) learns in that specific
condition. This is a **new, separate, default-off flag**, not yet named or
implemented (tentatively `pretrained_l1i_regulation` in a later phase). It
must not reuse or repurpose Phase 15's `loser_depression_protection` flag
or any existing L1I learning-rate parameter.

### Important unresolved / local-learning requirement

Decoder learning (connection 2) needs local sensory evidence from `L1Ei`
in order to know what each column's true target activity is — the decoder
lives on the `L2Ej→L1Pi` synapse, but the *training signal* for "was this
column actually active" is `L1Ei`'s own state, not `L1Pi`'s. Initial
experimental candidate, explicitly **not** a Lecture 14 equation:

```
delta_w_ji = eta_pred * s_L2Ej * (x_i - w_ji)     [EXPERIMENTAL CANDIDATE]
```

where `w_ji` is the decoder weight from `L2Ej` to `L1Pi`, `s_L2Ej` is
`L2Ej`'s own binary spike indicator (update gated on `L2Ej`'s own physical
spike — this is the "on its own spike only" plasticity event, analogous to
the superseded contract's `s_Pj`-gated rule but now keyed to the
representation neuron's spike rather than the predictor's), and `x_i` is
`L1Ei`'s own local sensory activity: **[EXPERIMENTAL CANDIDATE: exact
form]** either `L1Ei`'s own current binary spike state, or a short causal
eligibility trace of it (e.g. an EMA over the last few steps, to bridge
the one-step-plus delay between `L2Ej`'s spike and the arrival of any
downstream consequence) — which of these two is used must be decided and
documented explicitly before Phase 19 implementation begins, not left
implicit in code. Bounds: `w_ji` clamped to `[0, w_cap_pred]` (same cap as
connection 2). `eta_pred` is a new, separately-named rate, never aliased
to `learning_rate`/`l2e_lr_frac`.

This rule reads exactly two already-decided physical facts (`L2Ej` fired;
`L1Ei`'s own current or short-trace activation) and one own-synapse value
(`w_ji`) — **no pattern name, no owner table, no argmax, no cross-neuron
comparison, and no global reconstruction error** are read or computed
anywhere in this rule, matching the locality discipline already audited in
Phases 8, 15, and 17.

### Causal timing

- **`t`**: sensory processing and physical `L2Ej` spike (existing
  feedforward competition, unchanged).
- **`t+1`**: queued `L2Ej → L1Pi` decoder events arrive; `L1Pi` neurons
  integrate and may cross their own threshold and fire for real
  (`receive_input`/`check_threshold`/`fire()` — never a software pass-
  through of `L2Ej`'s spike flag).
- **`t+2`**: queued `L1Pi → L1Ei` replay (connection 3) arrives; `L1Ei`
  integrates and may fire for real.
- **No same-step routing through `_apply_stim()`.** Every new pathway uses
  the existing one-step-delayed-register pattern already established for
  `l1i_feedback_delay` — never a same-step direct write into another
  neuron's membrane within a single `step()` call.

### Two distinguished tests

**1. Local relay test.** Cue exactly one `L1Pi` through an explicit
experimental control (never by writing `input_vec` pixels directly).
Verify that *only* the paired `L1Ei` receives replay (connection 3 is
strictly one-to-one) — no other `L1Ej` (`j != i`) should show any physical
excitation from this cue. This isolates connection 3 alone, with the
decoder matrix (connection 2) not exercised at all.

**2. Full reconstruction test.** Cue exactly one `L2Ej` through an
explicit experimental control. Verify that its learned decoder (connection
2) activates the appropriate *subset* of `L1Pi` — the columns belonging to
whichever pattern `L2Ej` has come to represent — which then, via
connection 3, recreates the complete pattern's active pixel set in `L1E`.
This exercises the full chain (2)→(3) together and is the actual
reconstruction claim under test. Center pixel 4's strong reconstruction
across all four patterns is expected and is not itself failure; failure is
center-only reconstruction or poor pattern-specific peripheral recall —
center and peripheral performance must be reported separately, per the
independent review.

### All-I rule

The final Lecture 14 experimental condition disables **all** inhibitory
plasticity — every `L1Ii` and `L2I` synapse (recruitment and output) is
treated as already trained, none of it learns during that specific run.
This is implemented as a new, separate, default-off configuration (an
`L1I`-side counterpart to Phase 17's `pretrained_l2i_recruitment`), not by
modifying or deleting the existing inhibitory-learning code path. The
current `ChargeBasedRule`-driven L1I/L2I learning remains the default
baseline for every run that does not explicitly opt into the Lecture 14
all-pretrained-inhibition condition. Input topology (connections 2-4
above) and inhibitory plasticity (this flag) are kept as separate
factorial variables — per the independent review's correction #6, they
must not be changed simultaneously without isolated controls comparing
each in turn.

### What this phase does NOT do

- No code in `backend/simulation.py`, `neuron_flexible.py`, `layers.py`,
  or `cortical_column_flexible.py` is modified, beyond the superseded-
  banner addition to the original Phase 18 document.
- No new flag, no new neuron, no new synapse exists yet after this commit.
- No equation above is adopted as final — every one is marked
  **[EXPERIMENTAL CANDIDATE]** and subject to revision once Phase 19
  (rebuilt against this corrected topology) produces actual measurements.
- The superseded eight-predictor prototype is not deleted, not merged, not
  cherry-picked back in — it remains isolated on
  `backup/phase19-candidate-a-wip` / `backup/phase19-eight-predictor-wip`.

## Baseline verification

Full backend suite re-run after this documentation-only commit, to confirm
this phase truly added zero runtime behavior.
