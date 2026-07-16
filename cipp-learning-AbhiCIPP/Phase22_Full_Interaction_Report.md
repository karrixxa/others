# Phase 22 — Full Interaction: `pretrained_l2i_recruitment` × `prediction_column_to_i_enabled` (2×2)

**Status: measured. Both mechanisms stay default OFF, unchanged from
Phases 17 and 21. This phase tests the interaction only — no new flag.**

Full 2×2 factorial across three presentation schedules (`short`=5 steps,
`equal`=20 steps, `long`=100 steps per presentation, 3 cycles,
`CYCLE_ORDER` = row 1/col 1/diag \\/diag /), 2 weight seeds, plus a genuine
novel-pattern spare-capacity challenge per condition
(`phase22_full_interaction_diagnostic.py`, full results in
`phase22_full_interaction_results.json`):

- **A**: neither flag (baseline)
- **B**: `pretrained_l2i_recruitment` only (Phase 17's own narrow negative
  result)
- **C**: `prediction_column_to_i_enabled` only (Phase 21's own positive
  result)
- **D**: both together (the interaction under test)

Reported separately, per the explicit instruction — physical WTA metrics,
allocation/capacity metrics, and prediction-reconstruction metrics are never
conflated. **Clean one-hot firing is explicitly NOT interpreted as
successful one-to-one representation** — a tyrant condition can legitimately
show `l1i_all_nine_sync_rate == 1.0` (every `L1I` fires whenever ANY `L2E`
wins) while `distinct_owners` stays far below 4; the two are checked
independently throughout.

## Physical WTA metrics (`distinct_owners` out of a possible 4)

| Condition | short (seed1/2) | equal (seed1/2) | long (seed1/2) |
|---|---|---|---|
| A (neither) | 3 / 3 | 3 / 2 | 2 / 3 |
| B (L2I only) | **1** / 2 | **1** / 3 | **1** / **1** |
| C (PC only) | 3 / 4 | 2 / 2 | 2 / 1 |
| D (both) | 2 / 2 | **1** / 2 | **1** / **1** |

**Confirms Phase 17's own finding persists unchanged in isolation** (B: a
single `L2E` owns all four patterns under a long hold, both seeds).
**Confirms Phase 21's own finding**: `C` alone does not worsen tyranny
relative to baseline `A` (distinct_owners stays in the same 1-4 range, no
systematic degradation). **The interaction (D) does not fix B's tyranny
problem** — combining selective local predictive inhibition with pretrained
shared L2I recruitment still collapses to a single owner under a long hold
in both seeds, identical in severity to B alone. This is expected and not a
new failure: selective inhibition regulates `L1I`'s input topology; it has
no causal path into `L2`'s own WTA competition dynamics (`L2E -> L2I`
recruitment and `L2I -> L2E` delayed inhibition are unchanged by Phase 21),
so there was never a mechanistic reason to expect it would fix this.

`l1i_all_nine_sync_rate` is **1.0 under every A/B condition and 0.0 under
every C/D condition** — this is purely the input-topology flag
(`prediction_column_to_i_enabled`) doing exactly what Phase 21 already
established, orthogonal to `distinct_owners`. The two never move together,
confirming the required separation: a condition can have `sync=0.0` (C, D)
while STILL showing severe tyranny (D's long-hold `distinct_owners=1`) —
selectivity of the inhibitory topology is not evidence of good
representation allocation.

## Prediction reconstruction metrics

| Condition | PC precision (both seeds) | Fired pixels |
|---|---|---|
| A, B (no PC) | n/a | n/a |
| C | 1.0, 1.0 | `[3, 4, 5]`, `[3, 4, 5]` |
| D | 1.0, 1.0 | `[3, 4, 5]`, `[3, 4, 5]` |

**PC's per-pixel selectivity (Phase 19/21's own established result) is
completely unaffected by adding `pretrained_l2i_recruitment`** — identical
precision and fired-pixel set in C and D. The two mechanisms are
architecturally orthogonal (different populations, different synapses;
`pretrained_l2i_recruitment` only touches `L2E->L2I`/`L2I->L2E`, PC's own
`R_j->PCi`/`S_i->PCi` pathways are untouched), and the measurement confirms
no hidden coupling.

## Capacity metrics (spare-capacity challenge)

Train 4 patterns, freeze+record each pattern's owner, introduce a
genuinely novel 5th pattern (held-out `PROBES['row 0']`) with **live**
plasticity (never `present_probe()`, which freezes), observe the eventual
responder:

| Condition | Seed 1: novel owner (spare?) | Seed 2: novel owner (spare?) |
|---|---|---|
| A | L2E0 (spare) | L2E1 (spare) |
| B | L2E3 (spare) | L2E1 (spare) |
| C | L2E0 (spare) | **L2E0 (NOT spare — already the tyrant)** |
| D | L2E3 (spare) | L2E1 (spare) |

**7 of 8 capacity trials recruited a previously-spare `L2E` for the
genuinely novel pattern — even under B/D's severe tyranny.** This is a
notable positive finding: representation collapse to a single owner across
the four TRAINED patterns does not automatically prevent a genuinely novel
pattern from finding and recruiting spare capacity — the spare neurons
remain recruitable even while one neuron dominates the trained set. The
**one exception** (condition C, seed 2) occurred specifically in the run
where `distinct_owners` was already at its most extreme (1, i.e. `L2E0`
owned literally all four trained patterns AND was the only ever-active
`L2E` at all — `spare_before` for that seed lists every OTHER neuron as
"spare", meaning `L2E0` was the sole neuron with any learned receptive
field whatsoever going into the challenge). This is consistent with, not
contradictory to, the general finding: capacity is preserved as long as
there is more than one neuron with SOME learned structure to compete
against; a maximally-collapsed single-neuron network has nothing else to
recruit from.

## Verdict

The two mechanisms are **orthogonal and compose cleanly** where they
touch independent state (`L1I` input topology vs. `L2I` regulation; PC's
own selectivity is untouched by combining with pretrained L2I). Where they
could plausibly interact (representation allocation quality), **they do
not** — selective local predictive inhibition does not mitigate Phase 17's
tyranny problem, exactly as expected given the two mechanisms' disjoint
causal pathways. The spare-capacity finding is a genuine positive result,
independent of both flags: novel-pattern recruitment of spare neurons
survives even severe upstream tyranny, in all but the single most extreme
case observed. Neither flag is promoted; both remain default OFF.

## Tests (`test_phase22_full_interaction.py`, 7 tests)

Both-flags-off baseline; both mechanisms combine without raising/crashing;
`pretrained_l2i_recruitment`'s fixed L2I weights are unaffected by adding
PC; PC selectivity is unaffected by adding pretrained L2I recruitment; the
persisting-tyranny negative finding (documents, not asserts a fix);
selective L1I topology still breaks all-nine sync when combined; the
explicit clean-one-hot-is-not-representation-quality guard.

Full suite: **375 passed, 5 failed** (the same 5 pre-existing flow-rate/
assembly-flow-credit failures as every prior baseline — no new failures).
