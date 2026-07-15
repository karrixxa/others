# Phase 16 — Adaptive-Threshold × Developmental-Protection Factorial and Spare-Capacity Challenge

**MEASUREMENT ONLY.** Both mechanisms already exist (Phase 10's
`adaptive_threshold`, Phase 15's `loser_depression_protection`). No new
neural rule added, no default changed, nothing tuned per seed, distance/
leak/initialization/L1I untouched. Every condition uses
`DASHBOARD_PRESET`'s own legacy distance configuration and each mechanism's
already-documented reference values (`delta_threshold_frac=0.05`,
`tau_threshold=25.0`, `loser_depression_protection_ca_ref=0.02`) — only the
two boolean flags are toggled.

## Conditions

| | adaptive_threshold | loser_depression_protection |
|---|---|---|
| **A** | off | off |
| **B** | on | off |
| **C** | off | on |
| **D** | on | on |

## Method

`phase16_factorial_spare_capacity.py` — weight seeds 1–5 × topology seeds
1–3 (15 combinations) × 2 scenarios × 4 conditions = **120 factorial runs**,
plus a **60-run spare-capacity challenge** (one per condition/seed/topology,
extending each condition's own interleaved-40 trained engine).

Scenarios: 20-step equal interleaving (40 rotations, `diagnostic_schedule`
precedent) and long row-hold (600 steps) → column switch (200 steps).

4 harness-verification tests (`test_phase16_harness.py`, all passing):
confirm the novel-pattern presentation actually keeps plasticity live
(unlike `present_probe()`), goes through the same presentation-tracking
bookkeeping `set_pattern()` already uses, that the spare-capacity report's
own retention/collision logic is internally consistent, and that the
measurement harness itself contains **zero** hardcoded acceptance
assertions (no "must have exactly N quiet neurons" gate anywhere).

Full backend suite: **280 passed, 5 failed** (same pre-existing flow-rate
failures documented since before Phase 6, unaffected).

## Factorial findings

### Recruitment breadth (mean active/quiet/unrecruited over 15 combos)

| Scenario | Condition | active | quiet | unrecruited |
|---|---|---|---|---|
| long_hold_switch | A | 1.40 | 1.60 | 5.00 |
| long_hold_switch | B | **3.00** | **0.00** | 5.00 |
| long_hold_switch | C | 1.20 | 1.80 | 5.00 |
| long_hold_switch | D | **3.00** | **0.00** | 5.00 |
| interleaved_40 | A | 3.60 | 1.80 | 2.60 |
| interleaved_40 | B | 3.40 | 2.60 | 2.00 |
| interleaved_40 | C | 3.80 | 2.20 | 2.00 |
| interleaved_40 | D | **5.00** | 1.80 | **1.20** |

**`adaptive_threshold` (B, D) is the dominant driver of raw recruitment
breadth**, not protection: in the long-hold schedule it roughly doubles
active count and eliminates the "quiet" category entirely, regardless of
whether protection is also on. In the interleaved schedule, the
**combination (D) reaches the best recruitment of any single condition**
(5/8 active, only 1.2 unrecruited on average) — a real, seed-robust
improvement over baseline A.

### Distinct, stable ownership (interleaved_40, Phase-11-style)

| Condition | distinct_owners | tyrant_share (interleaved) | tyrant_share (long-hold) | collisions | forgetting | ambiguity |
|---|---|---|---|---|---|---|
| A | 3.60 | 0.538 | 0.465 | 0.40 | 1.00 | 0.0312 |
| B | 2.60 | 0.565 | 0.366 | 0.60 | 0.60 | 0.0113 |
| C | 3.20 | 0.553 | 0.468 | 0.60 | 1.60 | 0.0363 |
| D | **2.20** | 0.486 | **0.353** | **1.00** | **2.20** | 0.0138 |

**The recruitment-breadth win under D comes at a real cost to stable
ownership** — distinct_owners drops to the lowest of any condition (2.20 of
4), collisions and forgetting are both the worst of any condition. This
mirrors Phase 15's own finding for protection alone (recruitment breadth and
ownership stability move in opposite directions) and shows the same
tension **persists, even sharpens, when combined with adaptive threshold**.
Tyrant share in the **long-hold** schedule specifically is meaningfully
lower under both B and D (0.366/0.353 vs. A's 0.465) — adaptive threshold
does measurably reduce single-neuron dominance in that schedule, even
though it does not reduce it (and D even increases collisions) in the
interleaved schedule.

### Loser-depression magnitude grouped by local maturity (C and D, aggregated)

| Condition | 0.00–0.25 | 0.25–0.50 | 0.50–0.75 | 0.75–1.00 |
|---|---|---|---|---|
| C (protection only) | n=59,961, mean\|Δw\|=0.0074 | n=864, 0.7813 | n=558, 1.5277 | n=37,668, 2.7817 |
| D (both on) | n=37,725, mean\|Δw\|=0.0059 | n=465, 0.822 | n=333, 1.7763 | n=43,233, 3.0801 |

The maturity gate's monotonic ramp is preserved identically under D — the
adaptive-threshold mechanism does not interfere with the depression-scaling
gate's own shape.

### Adaptive-threshold trajectories

Mean count of L2E neurons with nonzero final `a_i` (interleaved_40): B=3.4,
D=5.0 — consistent with D's larger active-neuron count (more neurons ever
fire, so more accumulate nonzero threshold elevation).

### Whether any never-fired neuron becomes active (within-run checkpoint)

Dedicated supplementary check (same protocol as Phase 15's own checkpoint,
extended to all four conditions): for each of the 15 weight/topology
combinations, record each L2E's status after 600 steps of `row 1` (the
halfway point), then continue 200 more steps of `col 1` and check whether
any neuron that was `unrecruited` at the checkpoint ever fires by the end.

| Condition | never-fired-at-halfway instances | rescued by end |
|---|---|---|
| A | 75 | **0** |
| B | 75 | **0** |
| C | 75 | **0** |
| D | 75 | **0** |

**Zero rescues under every condition, alone or combined.** Neither
mechanism — nor their combination — rescues a neuron that has already
fallen behind within this specific long-hold timeframe. This generalizes
Phase 15's own finding (0/75 under A/C) to B and D as well: raising the
threshold adaptively, protecting depression, or both together, do not by
themselves constitute an active recruitment signal strong enough to revive
an already-failed competitor within 200 steps once it has fallen behind.

## Spare-capacity challenge

Protocol: train the original four patterns (the interleaved-40 run itself)
→ freeze and record owners/consistency → unfreeze and present one declared
novel pattern (**`row 0`**, an existing held-out `PROBES` entry, never in
the training rotation) 10 times with **plasticity live** (never
`present_probe()`, which freezes) → identify the eventual (modal)
responder and its PRE-novel-exposure status → freeze again and re-evaluate
the original four.

| Condition | novel captured (n/15) | responder was unrecruited | responder was quiet | responder was active | captured by an existing tyrant | mean retention of original-4 owners | mean novel-pattern consistency |
|---|---|---|---|---|---|---|---|
| A | 15/15 | 0 | 0 | 15 | **12/15** | 0.750 | 0.86 |
| B | 15/15 | **3** | 0 | 12 | 9/15 | 0.700 | 0.86 |
| C | 15/15 | **3** | 0 | 12 | 6/15 | 0.750 | 0.74 |
| D | 15/15 | **0** | 0 | 15 | **12/15** | **0.550** | **0.58** |

**Genuine spare capacity (a previously-unrecruited neuron becoming the
novel pattern's owner) is real but modest under B or C alone (3/15 seeds
each) — and under the baseline (A) it never happens at all (0/15): the
novel pattern is always absorbed by an already-active neuron, most often
the existing tyrant itself (12/15).** Per this phase's own instruction, a
silent neuron is called "recruitable" here **only** for those 3/15 seeds
under B and the 3/15 under C where it actually won the challenge — not as a
blanket property of either mechanism.

**The most important, non-obvious finding: combining both mechanisms (D)
does not add their individual benefits — it erases them.** D shows **zero**
genuine spare-capacity recruitments (back to A's 0/15), tyrant capture back
up to A's own 12/15, and **the worst retention (0.550) and worst novel-
pattern consistency (0.58) of any condition** — meaning the original four
patterns' ownership is *less* stable after novel exposure under D than
under any other condition, and the novel pattern's own responder is itself
the least consistently identified. Two mechanisms that each individually
show a small positive spare-capacity signal **interact negatively** when
combined, at this reference parameter setting. This is reported as found —
not tuned away, not one seed cherry-picked.

## Conclusions

1. **`adaptive_threshold` (not `loser_depression_protection`) is the
   dominant driver of raw recruitment breadth**, and the combination (D)
   reaches the best recruitment of any single condition in the interleaved
   schedule — but at a real, measurable cost to ownership stability
   (lowest distinct_owners, highest collisions/forgetting).
2. Genuine, challenge-proven spare capacity (not just "ever fired once") is
   real but rare under either mechanism alone (3/15 seeds each), never
   observed under baseline, and **eliminated entirely when both mechanisms
   are combined** — a genuine negative interaction, not a tuning artifact.
3. Neither mechanism, alone or combined, prevents the novel pattern from
   most often being captured by an existing tyrant rather than a spare
   neuron (6–12 of 15 seeds across all four conditions).
4. No condition satisfies, or was expected to satisfy, any fixed
   quiet-neuron-count criterion — none was imposed, per instruction; the
   silent/quiet/active counts are reported as observed, not gated.
5. Consistent with every prior phase's finding: the central one-to-one
   ownership-consolidation problem remains open. This phase maps where two
   existing, individually-tested mechanisms land relative to it — alone and
   combined — without adjusting anything to make the map look better.

## Files

- `phase16_factorial_spare_capacity.py` (new) — the factorial + spare-
  capacity harness.
- `test_phase16_harness.py` (new) — 4 harness-verification tests.
- `phase16_factorial_spare_capacity_summary.json` (new, committed) — the
  120-run factorial grid + 60-run spare-capacity grid backing every table.
- No engine file changed — both mechanisms (Phase 10, Phase 15) are
  reused exactly as they already exist.
