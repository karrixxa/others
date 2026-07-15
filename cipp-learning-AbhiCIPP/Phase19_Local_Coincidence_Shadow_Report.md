# Phase 19 — Local-Coincidence Shadow Prediction Report

**Status: implemented, tested, calibrated, diagnosed. Default OFF
(`prediction_column_enabled=False`). NOT promoted — see promotion-bar
verdict at the end.**

Implements `Phase18b_Lecture14_Local_Coincidence_Architecture_Contract.md`'s
final, transcript-faithful S_i/PC_i/I_i architecture: nine per-input-column
prediction neurons `PC0`–`PC8`, each with a fixed local `S_i->PCi` lateral
coincidence weight and a learned all-to-all `R_j->PCi` feedback matrix.
Supersedes every earlier prediction prototype (eight-predictor-per-`L2E`,
the per-column decoder-only-no-lateral correction, and Phase 19A's
scaffold-only checkpoint), all preserved unmerged on their own backup
branches (see the commit list at the end).

## Corrected timing (this checkpoint's key fix)

An offline feasibility review (exact commit reviewed: `d91e7f7`) found that
a **same-step** `S_i->PCi` lateral connection is not physically available in
this engine's `step()` ordering, and would require routing through
`_apply_stim()` — contaminating the very sensory evidence that produced the
`L2E` response it is supposed to detect coincidence with. The corrected
design instead queues **both** afferents together at the end of the step
that produced them and delivers them **together, one step later**:

- `t`: `S_i` and `L2E_j` may physically spike (existing dynamics, untouched).
- End of `t`: queue BOTH the fixed `S_i->PCi` lateral event and the learned
  `L2E_j->PCi` feedback event, from the SAME originating step, in two
  parallel FIFO queues (`s_to_pcol_queue`, `l2e_to_pcol_queue`).
- `t+1`: both arrive at `PCi` together (one `receive_input` call), `PCi`
  may physically fire.
- No same-step delivery of either term, ever. No routing through
  `_apply_stim()`. `PCi` cannot affect the sensory evidence that produced
  the `L2E` response that reaches it (shadow-only; see below).

This is a **more robust** design than same-step lateral + delayed feedback:
synchronizing both afferents to arrive on the identical step removes a
phase-mismatch that was actively hurting the coincidence signal in the
prior (superseded) attempt. Measured effect: pattern-selective spike counts
roughly **doubled** (e.g. `row 1`: 58 → 113 spikes per 3000-step hold) after
this correction, with precision unchanged at 1.0 (still zero false
positives within a single uninterrupted hold).

## Physical firing vs. decoder learning are separate events

Per the corrected design, `PCi` firing and `PCi` learning are deliberately
decoupled:

- **Firing** requires only that the combined membrane charge (retained
  leak + this step's arriving lateral + feedback terms) cross
  `prediction_threshold` — this is allowed to happen from feedback alone
  once a synapse is mature (see "mature feedback-only firing" below), which
  is the intended eventual input-free-reconstruction capability.
- **Learning** additionally requires THIS delivery's own lateral
  (`S_i`) component to have been active (`_last_input_spikes[N_OUT] > 0.5`).
  If it was 0 — including on a step where `PCi` fired purely from mature
  feedback with no sensory evidence at all — **no decoder weight moves**,
  for any `R_j` index, this event. Among the eight feedback indices, only
  those the queued delivery actually carried a 1 for (`_last_input_spikes[:8]`)
  are credited (per-synapse eligibility, unchanged from before).

This directly implements the requirement that mature feedback-only firing
must remain possible (Part 7's eventual reconstruction) while NOT letting
that same feedback-only event be mistaken for evidence that pixel `i` was
truly present.

## Calibration (empirical, not merely derived)

`DASHBOARD_PRESET`'s actual dynamics: `S_i` fires on ~90% of steps
(`refractory=0`); `L2E_j` fires on ~50% of steps once a stable winner
emerges. A leaky integrator receiving a duty-cycled input settles at a
steady state of roughly `duty * weight / leak_rate` — this, not just a
single retained sample, is the binding constraint.

| `prediction_threshold` | Result (pre-timing-fix sweep) |
|---|---|
| 1000 | Nothing ever fires. |
| 300 | Fires almost every cycle — dominated by LATERAL-ALONE steady state, not genuine coincidence (the exact failure the lime connection exists to prevent). |
| **500 (chosen default)** | Pattern-selective, genuinely coincidence-gated. |
| 600+ | Nothing fires. |

Defaults locked in: `prediction_lateral_weight=150`,
`prediction_feedback_init=50` (small, nonzero — enables the no-leak
diagnostic below), `prediction_feedback_max=1200`,
`prediction_learning_rate=0.15`, `prediction_threshold=500`,
`prediction_leak=0.3`, `prediction_feedback_delay=1`.

**No-leak diagnostic** (`prediction_leak_diagnostic_disable=True`): with
leak forced to 0, inactive columns (pixels never part of the current
pattern) fire repeatedly and without bound (200/3000 steps) from
accumulated feedback-only charge that never decays. With the real leak,
the same inactive columns never fire once in 20,000 steps. This is the
direct, reproduced demonstration of why a real, separately-tunable
`prediction_leak` is necessary.

**A genuine bug found and fixed during calibration**: `NeuronConfig.
apply_to()`'s classification (`is_l2e = not (is_l1e or is_l1i or is_l2i)`,
`snn/config.py`) silently swept every `PCi` into the legacy `L1E->L2E`
distance-weighting path (since a `PC{i}` id matches none of the three named
checks), inflating delivered charge by ~55x via a stale `distance_ref`
value meant for a completely different pathway. Fixed locally in `_build()`
(explicitly resetting `pc.distance_weighting = False` after the generic
sweep runs) rather than touching the shared classification logic, which is
out of scope for this phase. A regression test
(`test_distance_weighting_never_applied_to_pc`) guards this.

## Pattern selectivity (single uninterrupted hold, post-timing-fix)

3000-step hold per pattern, seed 1:

| Pattern | Active pixels | Spike counts (all 9 columns) |
|---|---|---|
| `row 1` | 3, 4, 5 | `[0,0,0,113,113,113,0,0,0]` |
| `col 1` | 1, 4, 7 | `[0,102,0,0,102,0,0,102,0]` |
| `diag \` | 0, 4, 8 | `[127,0,0,0,127,0,0,0,127]` |
| `diag /` | 2, 4, 6 | `[0,0,99,0,99,0,99,0,0]` |

**Precision is exactly 1.0 for every pattern** — zero false positives on
any pixel not part of that pattern, in every one of the four cases. Center
pixel 4 fires for all four patterns (expected — it is genuinely active in
every one; not itself a failure signature). No center-only collapse: every
pattern's peripheral pixels also fire. Never all nine columns fire together.

## Switch-boundary diagnostic (continuous operation, the real test)

A single uninterrupted hold cannot reveal carryover between DIFFERENT
patterns. Ran the standard 20-step equal-interleaved schedule
(`CYCLE_ORDER = ['row 1', 'col 1', 'diag \\', 'diag /']`,
`PRESENTATION_STEPS=20`, matching `diagnostic_schedule.py`'s convention)
continuously for 50 full cycles (4000+ steps), under three conditions
(`phase19_switch_boundary_diagnostic.py`, full records in
`phase19_switch_boundary_results.json`):

| Condition | Total PC spikes | Coincidence | Inactive-pixel | Carryover | **False-prediction rate** |
|---|---|---|---|---|---|
| **1. Continuous leak** (the real mechanism, no clearing) | 513 | 498 | 6 | 9 | **2.92%** |
| **2. Washout-gap** (5-step blank between presentations, diagnostic) | 482 (+7 during the blank itself) | 475 | — | — | **0%** in-pattern (7 spikes occur during the blank, tracked separately) |
| **3. Explicit boundary-clearing** (PCi potential + both queues forced to zero at every switch — DIAGNOSTIC CONTROL ONLY, never the primary mechanism) | 463 | 463 | 0 | 0 | **0%** |

**Selectivity does NOT perfectly survive continuous pattern switches
without any gap or clearing.** Under pure continuous operation, ~2.9% of
`PCi` spikes are false predictions — some firing on a pixel not active in
the current pattern at all (`inactive_pixel`, 6/513), and some caused by a
stale `S`/`R` event queued during the PREVIOUS presentation arriving just
after the switch and being (wrongly) treated as current-pattern evidence
(`carryover`, 9/513). This is reported honestly as the real, measured
number — not smoothed over. Both mitigations tested (a natural blank gap,
or forcibly clearing state at the switch) eliminate it entirely in this
run, but per the explicit instruction, boundary-clearing is documented here
as a **diagnostic control**, not adopted as the primary biological
mechanism — the underlying tension (queued events crossing a presentation
boundary) is a real property of the corrected architecture, not an
implementation accident to be silently patched away by a reset.

**Most dangerous failure mode, confirmed empirically**: previous-pattern
carryover masquerading as current-pattern prediction. It is real, it is
small (~3%) at these settings, and it is fully attributable to the queued-
delivery boundary crossing a presentation switch — exactly the risk flagged
before this diagnostic was run.

## Tests (`test_prediction_column_phase19.py`, 37 tests)

Covers: flag-off baseline equivalence (unit + engine level); shadow-mode
non-perturbation of every existing population; no RNG consumption by PC
construction; lateral reaches only its own paired column, feedback reaches
every column; no pattern/owner/rival state read by the learning rule; no
same-step delivery for EITHER pathway (corrected — previously only the
feedback path was delayed); both pathways arrive together exactly one step
later; no-spike-means-no-weight-change; only the causally-eligible `R_j`
index is credited; **the S_i-eligibility gate blocks ALL learning when the
lateral component is absent, even with eligible R_j indices and even if PCi
physically fired**; **mature feedback alone (no lateral input at all) can
still physically fire PCi** (decoupled firing/learning, verified directly);
single lateral/immature-feedback events alone stay subthreshold; genuine
coincidence fires the correct columns; repeated feedback-only stays
subthreshold for inactive columns over 3000 steps; no false spike from a
prior pattern's leftover charge (single-switch case); the no-leak diagnostic
reproduces the accumulation failure and the real leak prevents it; pattern
selectivity for all four patterns (precision exactly 1.0); center-pixel
handling; never-all-nine-firing; only-fired-synapses-change; monotonic
weight growth; mixed-decoder-during-unconsolidated-ownership is measured,
not asserted as pass/fail; determinism; `topology()` observability;
mutual exclusion with `prediction_excitatory_enabled` raises; the
distance-weighting regression guard; PC has no synapse where it is the
SOURCE (dynamically disconnected from I and S); no further growth on a
column's weights once its pixel leaves the active pattern.

Full suite: **347 passed, 5 failed** (the same 5 pre-existing flow-rate/
assembly-flow-credit failures as every prior baseline in this repo — no new
failures introduced by this phase).

## Promotion-bar verdict

Per the required bar for moving to `PCi -> Ii` inhibition:

- Inactive `PCi` do not accumulate to threshold under normal operation:
  **PASS** (0 spikes/20,000 steps within a single hold; 6 inactive-pixel
  false spikes out of 513 total across a full continuous-switching run —
  small but nonzero).
- `PCi` firing is pattern-selective across a single hold: **PASS**
  (precision 1.0 for all four patterns).
- Only physically fired `PCi` learn: **PASS** (directly verified).
- Correct feedback structure includes peripheral pixels, not just center:
  **PASS** (no center-only collapse).
- Shadow mode leaves every existing neural trajectory unchanged: **PASS**
  (500-step run byte-identical, PC on vs. off).
- No same-step contamination: **PASS** (corrected in this checkpoint).
- No labels or global routing: **PASS** (AST-verified).
- **Selectivity survives continuous, uninterrupted pattern switching: FAIL
  outright — it does not, cleanly.** A real, measured 2.92% false-
  prediction rate exists under continuous operation with no gap or
  clearing, driven by previous-pattern carryover and occasional inactive-
  pixel spikes.

**Verdict: the promotion bar does NOT fully pass.** `prediction_column_
enabled` stays default OFF. This is not silently patched by adopting
boundary-clearing as the real mechanism (explicitly disallowed) — the
carryover risk is a genuine, structural property of queuing physical events
across a presentation boundary in this architecture, and remains open for a
future phase to address (e.g. an explicit local discharge tied to a
physical event rather than a software presentation-boundary hook, or a
tighter coincidence window that reduces how long a stale event can remain
queued relative to how fast patterns change). `PCi -> Ii -> Si` is NOT
enabled. This report documents a genuine, partial, honestly-scoped result:
the coincidence mechanism itself works and is pattern-selective within a
hold; it is not yet robust across continuous, rapid pattern switching.

## Commits / branches

- Backup preservation (verified intact, not touched this session):
  `backup/phase19-candidate-a-wip`, `backup/phase19-eight-predictor-wip`,
  `backup/phase19a-scaffold-config-ui-wip`,
  `backup/phase19-corrected-prediction`.
- `Phase 18b: correct Lecture 14 topology with local sensory-feedback coincidence`
  — docs + `CLAUDE_HANDOFF.md` only.
- This commit: Phase 19 implementation (corrected timing), tests, both
  diagnostic scripts + results, this report.
- `july14-integration`, not pushed.
