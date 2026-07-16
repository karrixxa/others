# Phase 21 — Selective Local Predictive Inhibition (2×2 Factorial)

**Status: implemented, tested, measured. Default OFF
(`prediction_column_to_i_enabled=False`, `pretrained_l1i_regulation=False`).
This is the first phase where `PCi`'s own output affects any other neuron
— Phases 19–20 were shadow-only (zero output).**

Wires the deferred `PCi -> Ii -> Si` path from `Phase18b_Lecture14_Local_
Coincidence_Architecture_Contract.md`. Two independent factorial variables,
kept separate per the independent review's correction #6 (never change
input topology and inhibitory plasticity simultaneously without isolated
controls):

- **Input topology**: `prediction_column_to_i_enabled` — OFF (A/C) keeps
  the existing global `L2E -> all-L1I` broadcast (every `L1Ii` receives the
  identical N_OUT-dimensional feedback vector); ON (B/D) **replaces** it
  (not appends to it) with a single input from `L1Ii`'s own paired `PCi`
  only.
- **Regulation**: `pretrained_l1i_regulation` — OFF (A/B) keeps the
  existing learned random-init regulation; ON (C/D) fixes every incoming
  L1I weight at L1I's own resolved threshold and pins `learning_rate=0`
  (the Phase 17 `pretrained_l2i_recruitment` pattern, applied to L1I).

## Two regression bugs found and fixed during implementation

1. **Distance-weighting misclassification** (same class of bug as Phase
   19's `PCi` fix): `_apply_experimental_pathway_distances()`'s own L1I
   loop unconditionally assigns an N_OUT-shaped geometric distance row to
   every `L1Ii`, which raised a shape-mismatch error the instant `L1Ii`'s
   incoming array became genuinely 1-wide under the selective topology.
   Fixed by skipping that assignment for L1I when
   `prediction_column_to_i_enabled` is on (that geometric concept simply
   doesn't apply to a single same-column connection).
2. **`learning_rate` silently overwritten**: a later, generic per-neuron
   sweep in `_build()` (`n.learning_rate = lr_frac * n.weight_cap`, keyed
   only by population type via `nid.startswith(...)`) ran *after* the L1I
   init loop and unconditionally reset `learning_rate` back to the learned
   value — silently undoing `pretrained_l1i_regulation`'s own
   `learning_rate=0` pinning. Fixed by skipping that line for L1I when
   `pretrained_l1i_regulation` is on.

Both are the same underlying failure mode: a broad, generic per-neuron
sweep written before this phase's new populations/flags existed, applied
uniformly without knowing about them. Both are now guarded by dedicated
regression tests (`test_distance_weighting_never_applied_to_selective_l1i`,
`test_pretrained_l1i_regulation_pins_learning_rate`).

## Measured result: the mechanism works exactly as intended for its stated purpose

3000-step single-pattern hold (`row 1`, active pixels 3/4/5), seed 1:

| Condition | Topology | Regulation | All-nine sync rate | L1I rate, active pixels | L1I rate, inactive pixels | L1E duty cycle (active) |
|---|---|---|---|---|---|---|
| **A** | global | learned | **0.4613** | 0.4613 | 0.4613 (identical) | 0.1796 |
| **B** | selective | learned | **0.0000** | 0.1810 | **0.0000** | 0.2731 |
| **C** | global | fixed | **0.4843** | 0.4843 | 0.4843 (identical) | 0.1720 |
| **D** | selective | fixed | **0.0000** | 0.2117 | **0.0000** | 0.2628 |

**All-nine synchronization is completely broken by the selective topology**
(0.46 → 0.00 for A→B, 0.48 → 0.00 for C→D) — under global feedback, every
`L1Ii` fires in perfect lockstep regardless of which pixel it regulates
(identical rate across all nine columns, by construction: the same
N_OUT-dimensional vector is delivered to every `L1Ii`). Under the selective
topology, **per-pixel selectivity is exact**: inactive columns (0,1,2,6,7,8)
receive precisely zero `PCi`-driven inhibitory drive across the entire
3000-step hold, while active columns (3,4,5) receive real, nonzero drive.
This is exactly the qualitative behavior "selective local predictive
inhibition" is meant to produce, and it is not a partial or fragile effect
— it holds cleanly across the full run, in both the learned and
fixed-regulation conditions.

## Honest trade-off: selectivity costs raw suppression strength

The selective topology's L1I firing rate on active columns (0.181-0.212)
is noticeably lower than global feedback's rate (0.461-0.484) — expected,
since `PCi` fires far less often than `L2E` (per Phase 19/20's own
findings: `PC`'s coincidence-triggered firing is front-loaded and much
sparser than `L2E`'s regular competition rhythm). This shows up directly as
a **higher L1E duty cycle under the selective topology** (0.27-0.27 vs.
0.17-0.18 under global) — weaker, rarer inhibitory drive suppresses L1E
less overall. This is reported as a genuine, real trade-off: selective
inhibition is more topologically correct (per-pixel, not all-nine) but
delivers less total suppression strength than the global baseline, a
direct consequence of `PCi`'s own sparser firing rate documented in
Phase 19/20 — not a new, independent finding, but the predictable
downstream consequence of it.

No unwanted global silence was observed in any of the four conditions —
every active pixel's `L1I` fired at a nonzero rate throughout every hold.

## Tests (`test_phase21_selective_inhibition.py`, 10 tests)

Flag-off byte-identical baseline (unit + engine level); the mutual-
exclusion guard (`prediction_column_to_i_enabled` without
`prediction_column_enabled` raises); `L1I`'s incoming array shape matches
the active topology (N_OUT vs. exactly 1); both regression guards for the
bugs found above; `PCi`'s spike reaches only its own paired `L1Ii`, never
any other column; the measured all-nine-sync-vs-selectivity finding for
global (A) and selective (B) topologies; the honest weaker-overall-
suppression trade-off; no unwanted permanent silence of active-pixel `L1I`
across all four conditions; deterministic replay.

Full suite: **368 passed, 5 failed** (the same 5 pre-existing flow-rate/
assembly-flow-credit failures as every prior baseline — no new failures
from Phase 21's changes).

## Verdict

The selective `PCi -> Ii` mechanism does exactly what it is designed to
do — break all-nine synchronization and deliver genuinely per-pixel
selective inhibition — cleanly and reliably within a single held pattern.
It remains default OFF pending Phase 22's interaction test with
`pretrained_l2i_recruitment` and a genuine novel-pattern spare-capacity
challenge, and pending resolution of the weaker-overall-suppression
trade-off (a direct, expected consequence of Phase 19/20's sparse `PCi`
firing rate, not a new problem). `Si` suppression itself (the actual
`Ii -> Si` inhibitory delivery) is unchanged existing machinery — this
phase only changes WHAT drives `Ii`, not how `Ii` inhibits `Si`.
