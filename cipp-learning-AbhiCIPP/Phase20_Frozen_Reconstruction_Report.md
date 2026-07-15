# Phase 20 — Frozen Reconstruction (measurement only)

**Status: measured. `prediction_column_enabled` stays default OFF (unchanged
from Phase 19). This phase is measurement-only against the existing Phase
19 mechanism — no new persistent flags added.**

## Scope adapted from the original spec

The original Phase 20 spec (written earlier in this session, against a
now-superseded decoder-directly-to-`L1E` topology) asked to cue one
`L2E`/decoder and measure reconstruction *into* `L1E`. The corrected S_i/
PC_i/I_i architecture (`Phase18b_Lecture14_Local_Coincidence_Architecture_
Contract.md`) has no such replay path by design — the annotated diagram
shows `PC_i -> I_i` (inhibitory-only, deferred to Phase 21), never
`PC_i -> excitatory replay into S_i`. Per that contract: **"the P grid
itself is the reconstructed pattern."** This phase therefore measures
reconstruction directly at the `PCi` population when one `L2Ej` is cued
via an explicit experimental control (forced potential, never a software
pass-through — `PCi` still integrates and crosses its own threshold for
real), with plasticity frozen and external input removed.

## Protocol

1. Train normally (`prediction_column_enabled=True`, equal-interleaved
   20-step schedule, `CYCLE_ORDER`) for 60 full cycles (4800 steps).
2. Identify each pattern's owner `L2E` (most frequent firer during that
   pattern's presentations).
3. Freeze plasticity (`_set_plasticity_frozen(True)`), zero `input_vec`,
   cue one `L2Ej` for 5 steps (forced potential above its own threshold,
   physical `check_threshold`/`fire`), then observe 10 further steps.
4. Measure which `PCi` fire: precision/recall against the pattern's true
   active-pixel set, center vs. peripheral separately, persistence/decay
   after the cue stops, and confirm zero false `L2E` activation from `PCi`
   itself (isolated from the cue's own, expected, unrelated `L2I`-
   competition side effects on other `L2E`s).

Controls: no cue; correct-owner cue (all four patterns); wrong-owner cue;
shuffled-decoder cue (decoder rows permuted across columns).

## Result 1 — realistic training does not mature the decoder enough to reconstruct

After 60 interleaved cycles (4800 steps) **every** control — no cue,
correct-owner cue for all four patterns, wrong-owner cue, shuffled decoder
— produced **zero PCi firing**. This is not a bug in the cueing mechanism
(see Result 3 below, which proves the mechanism works correctly once a
decoder is actually mature); it is a direct, measured consequence of the
decoder-weight trajectory documented in Phase 19: PCi's own physical firing
(and therefore its learning event) is front-loaded and stops almost
entirely once L2 competition consolidates into a regular rhythm.

**Weight-maturation trajectory** (`PC4`'s row-1 decoder weights, single
uninterrupted `row 1` hold, seed 1):

| Step | `PC4` weights (indices 0-7) |
|---|---|
| 10,000 | `[50, 50, 50, 58.1, 56.9, 63.6, 50, 50]` |
| 20,000 | `[50, 50, 50, 58.1, 56.9, 63.6, 50, 50]` |
| 30,000 | `[50, 50, 50, 58.1, 56.9, 63.6, 50, 50]` |
| 40,000 | `[50, 50, 50, 58.1, 56.9, 63.6, 50, 50]` |
| 50,000 | `[50, 50, 50, 58.1, 56.9, 63.6, 50, 50]` |

**Weights plateau completely by step 10,000 and do not move again through
step 50,000.** The mechanism does not "eventually" mature given more time
at these settings — it stops learning entirely once `PCi` stops physically
firing, and `PCi` stops firing once the upstream `L2E` competition settles
into a fixed rhythm whose phase no longer reliably re-creates the narrow
coincidence window (exactly the phase-sensitivity documented in Phase 19's
report). The plateaued values (~50-64) are far below the ~500 threshold a
single feedback delivery needs to fire `PCi` alone.

**This is reported as a genuine, honest negative finding, not smoothed
over**: at the current calibration, **frozen/input-free reconstruction
from a realistically-trained decoder does not work** — not because the
cueing mechanism is broken, but because the decoder itself never
accumulates enough weight under normal operation.

## Result 2 — the underlying representation-ownership problem persists

Owners identified after training: `{'row 1': 4, 'col 1': 5, 'diag \': 7,
'diag /': 5}`. `L2E5` is the owner of BOTH `col 1` and `diag /` — the
same familiar upstream Layer-2 ownership-collapse risk from Phases 11/13b/
15/16/17, entirely orthogonal to the decoder-learning rule itself, and
explicitly flagged as a known open risk in `Phase18b_Lecture14_Local_
Coincidence_Architecture_Contract.md`'s "What this architecture may still
fail to do" section.

## Result 3 — the cueing/measurement mechanism itself is correct (positive control)

To isolate "does the harness work" from "does realistic training reach
maturity" (Result 1 shows it currently does not), decoder weights for
`row 1`'s active pixels (3, 4, 5) were **manually** set to
`prediction_feedback_max` (bypassing the learning rule entirely — an
explicit test control, not a claim about normal operation) before cueing
`L2E4` alone, with zero lateral input:

- **Reconstruction is exact**: `PC3`, `PC4`, `PC5` fire; no other column
  fires. Precision and recall both 1.0.
- **Center vs. peripheral, reported separately**: `PC4` (center) fires, and
  ALL peripheral pixels (`PC3`, `PC5`) also fire — no center-only collapse.
- **Persistence / no runaway**: after the 5-step cue window ends, every
  `PCi`'s potential decays back below threshold under the normal leak
  within the following 200 steps — no latching, no runaway recurrence.
- **No false `L2E` activation**: forcing every `PCi` to fire directly
  causes zero change in any `L2E` potential (PC has no output wiring in
  this phase — reproduces Phase 19's shadow-mode guarantee).
- **Wrong-owner / untrained cue**: cueing an untrained source (`L2E7`, no
  matured weights for `row 1`) reconstructs nothing.
- **Shuffled decoder**: permuting which pixel each decoder row targets
  changes the reconstructed set away from the true active pixels,
  confirming reconstruction quality is a property of the learned decoder
  structure, not an artifact of the cueing mechanism.

This confirms the **architecture and cueing mechanism are sound** — the
gap is specifically that Phase 19's calibrated learning rate/threshold/leak
combination does not, in practice, mature decoder weights far enough under
realistic training to reach the regime Result 3 exercises manually.

## Tests (`test_phase20_frozen_reconstruction.py`, 9 tests)

Covers: no-cue baseline; frozen plasticity blocks all weight changes during
cueing; no false `L2E` activation from `PCi` (isolated from the cue's own
normal `L2I`-competition side effects); the honest negative result (an
immature, realistically-trained decoder does not reconstruct); a positive
control proving the mechanism itself works once a decoder is manually
matured; center-vs-peripheral reported separately; persistence/no-runaway
after cue removal; wrong-owner/untrained cue reconstructs nothing; shuffled
decoder breaks correct reconstruction.

Full suite: **356 passed, 5 failed** (the same 5 pre-existing flow-rate/
assembly-flow-credit failures as every prior baseline — no new failures
from Phase 20's test file).

## Verdict

Frozen reconstruction is **architecturally sound but not yet achievable
under realistic training** at Phase 19's calibrated defaults — the decoder
weight trajectory plateaus early and never reaches the maturity needed.
This does not block later phases that measure frequency or test the
inhibition path in isolation (Phases 21/23), but any phase that assumes a
mature, input-free-capable decoder must either train far longer with a
different schedule, or increase `prediction_learning_rate`/lower
`prediction_threshold` further (both of which risk reopening the false-
positive failure modes Phase 19 fought to avoid) — a tuning trade-off
explicitly flagged for a later, separately-approved experiment, not
resolved here. No new default-off flag was added in this phase; nothing is
promoted.
