# Phase 28A — Local Common-Input Feasibility: NEGATIVE RESULT

**Status: measured, analyzed against pre-registered criteria, GATE FAILS.
Phase 28B is explicitly NOT implemented — no new flag, no code change to
`backend/simulation.py`/`backend/presets.py` in this phase. Branch
`l2-ownership-recovery`, based on Phase 27 (`f09d8fe3`). Nothing pushed.**

## What was tested

A purely local presynaptic activity trace, driven only by physical L1E
spikes, gating only the positive-potentiation half of the existing signed
self-spike rule — never physical transmission, never inactive-input
depression, never L2I loser depression:

```
c_i <- c_i + (s_i - c_i) / tau_c          (s_i = physical L1E_i spike, 0/1)
g_i = max(g_min, 1 - c_i)                  (applied only to potentiation)
```

Implemented entirely offline via monkeypatches on top of a real
`SimulationEngine` (`phase28a_local_common_input_feasibility.py`,
`CausalTracer`-style, same technique as Phase 27) — no engine flag exists
yet, by design, pending this feasibility gate.

**Conditions**: baseline (unmodified), oracle (hardcoded freeze of the
pattern set's own universal pixel — an explicit, labeled cheat, upper-bound
reference only, never a candidate), and the gate across `tau_c ∈
{40,80,160,320} × g_min ∈ {0.1,0.25,0.5}` (12 combinations).

**Pattern sets** (never mixed, always compared to their OWN baseline):
`standard` (real `PATTERNS`, universal pixel = 4), `shifted` (pixel 0↔4
swapped — a structure-preserving relabeling, universal pixel moves to 0,
the critical generalization check), `no_universal` (the four existing
`PROBES` used as trainable patterns here only — no pixel active in more
than 2 of 4 patterns, a regression-only control).

**Schedules**: equal-interleaved (`INTERLEAVED_CYCLES=8`, 32 presentations,
20 steps each — reduced from Phase 27's 40 purely for tractability across
this much larger grid, applied identically everywhere) and long-hold
(600-step hold → 200-step hold, chunked into the same 20-step windows).

**Grid**: 30 distinct weight seeds × 1 topology seed (confirmed inert,
Phase 13b/27) × 3 pattern sets × 2 schedules × up to 14 conditions
(baseline + oracle where applicable + 12 gate combos) = **2,460 runs, all
reported below — no per-seed selection, no hidden tuning.** Full grid in
`phase28a_local_common_input_feasibility_results.json` (~11MB).

## Pre-registered stop/go criteria (written BEFORE looking at results)

`phase28a_analyze_results.py` defines, before any result was inspected, six
criteria a `(tau_c, g_min)` pair must pass — checked against BOTH the
`standard` AND `shifted` pattern sets (the generalization requirement) on
BOTH schedules, relative to that pattern set's OWN baseline:

1. Ownership improves (mean distinct_owners +0.5, or persistent-collision
   rate down ≥30% relative).
2. No excessive ambiguity (+0.05 absolute cap on same-step-tie rate).
3. No excessive forgetting (+0.10 absolute cap on the forgetting rate).
4. Peripheral learning retained (≥70% of baseline's mean weight on
   non-universal pixels, restricted to neurons that actually fired).
5. Must hold on BOTH schedules.
6. Must hold on BOTH `standard` and `shifted` with the SAME `(tau_c, g_min)`
   pair (not fitted separately per pattern set).

Plus a regression-only check: must not make `no_universal`'s ownership
meaningfully worse than its own baseline.

## Result: 0/12 gate conditions pass all six criteria

```
                              standard/il  standard/lh  shifted/il  shifted/lh  no_univ/il  no_univ/lh
tau_c=40,  g_min=0.1              OK           x           x           x          OK          OK
tau_c=40,  g_min=0.25              OK           x          OK           x          OK          OK
tau_c=40,  g_min=0.5              OK           x           x           x          OK          OK
tau_c=80,  g_min=0.1              OK           x          OK           x          OK          OK
tau_c=80,  g_min=0.25              OK           x          OK           x          OK          OK
tau_c=80,  g_min=0.5              OK           x           x           x          OK          OK
tau_c=160, g_min=0.1              OK           x           x           x          OK          OK
tau_c=160, g_min=0.25              OK           x           x           x          OK          OK
tau_c=160, g_min=0.5              OK          OK           x           x          OK          OK
tau_c=320, g_min=0.1               x          OK           x           x          OK          OK
tau_c=320, g_min=0.25               x          OK           x           x          OK          OK
tau_c=320, g_min=0.5               x           x           x           x          OK          OK
```
(il = interleaved, lh = long_hold)

**No single `(tau_c, g_min)` pair passes both schedules for both pattern
sets simultaneously.** `no_universal` never regresses under any gate
setting (a genuinely good sign the mechanism is somewhat targeted, not
indiscriminately destructive) — but that alone does not satisfy criterion 6.

## What the numbers actually show (seed-averaged, n=30 each)

| Pattern set / schedule | baseline distinct_owners | oracle | best gate tried |
|---|---|---|---|
| standard / interleaved | 2.27 (persistent collision 96.7%) | 3.97 (3.3%) | 3.63 @ tau_c=80,g_min=0.1 (33.3%) |
| standard / long_hold | 1.57 (43.3%) | 2.00 (0%) | 1.80 @ tau_c=80,g_min=0.1 (20%) — but peripheral weight 190 vs baseline's 423 (55% retained, fails the 70% floor) |
| shifted / interleaved | 1.37 (100%) | 3.93 (6.7%) | 2.17 @ tau_c=80,g_min=0.1 (86.7%) |
| shifted / long_hold | 1.43 (56.7%) | 1.97 (3.3%) | 1.30 @ tau_c=80,g_min=0.1 (70%) — **worse than baseline** |
| no_universal / interleaved | 3.73 (26.7%) | — | 3.87–3.67 across the grid (no meaningful change either way) |
| no_universal / long_hold | 1.93 (6.7%) | — | 1.67–1.83 (no meaningful change either way) |

**The genuinely interesting, honest picture**: on the **interleaved**
schedule, the gate produces a real, generalizing improvement — it helps
`standard` (pixel 4) AND `shifted` (pixel 0) with the SAME parameters
(`tau_c=80, g_min≤0.25`), which is exactly the property that would matter
(not fitted to a hardcoded index). But on the **long-hold** schedule, the
SAME mechanism either costs too much genuine peripheral learning
(`standard`, weight collapses to 45% of baseline) or actively makes
ownership **worse than doing nothing** (`shifted`, 1.30 vs. baseline's
1.43). This is a real, schedule-dependent failure, not a marginal
near-miss averaged away.

**Why this happens (observation, not yet a tested mechanism)**: the trace
`c_i` is a plain leaky EMA of physical L1E spikes with a FIXED time
constant. Over a 600-step uninterrupted hold, `c_i` climbs much further
toward saturation for EVERY currently-active pixel — including genuinely
pattern-distinguishing ones that just happen to be held a long time — than
it does over a 20-step interleaved window. The gate cannot currently tell
"this pixel is common ACROSS PATTERNS" apart from "this pixel has been on
for a long time in the CURRENT pattern" — the two are conflated by a
same-time-constant trace, and the long-hold schedule is exactly the
condition that exposes the difference.

## Verdict and decision

**The gate does not pass its own pre-registered feasibility bar. Per the
explicit instruction ("if no robust parameter region exists, do not force
an implementation"), Phase 28B is NOT implemented.** No new flag is added
to `backend/simulation.py`. This is a clean, honest, negative result on a
plausible and clearly-testable hypothesis — not a null result from a
broken harness (the oracle condition, in every pattern set/schedule
combination, recovers ownership close to its ceiling, confirming the
harness and the underlying causal story from Phase 27 are both working
correctly; the gate specifically, not the measurement, is what fails to
generalize across hold durations).

## Next smallest falsifiable mechanism (recommendation, not implemented)

The failure is schedule-dependent in a specific, falsifiable way: a
same-time-constant leaky EMA cannot distinguish "common across pattern
switches" from "held a long time within one pattern." The next smallest
testable refinement is a trace that increments **once per presentation
boundary** (a discrete per-presentation commonness counter, incremented at
most once per presentation regardless of how many steps that presentation
lasts) rather than continuously every physical step — this would make the
trace's growth rate schedule-length-INVARIANT by construction, directly
targeting the mechanism identified above as the cause of the long-hold
failure. This is a recommendation for a FUTURE phase's own feasibility
test, not tuned or implemented here.

## Tests

`test_phase28a_local_common_input_feasibility.py` — 18 tests, all passing:
pattern-set structural properties (standard universal at 4, shifted at 0,
no_universal has no common pixel); pattern-swap context manager transparent
and restored even on exception; gate touches only positive potentiation on
participating synapses, never depression, never loser depression; g=1
reproduces the ungated baseline byte-identically; trace reads only
`engine.spiked` (physical L1E), never raw `input_vec`; causal ordering
(gate reflects the PREVIOUS step, verified structurally); oracle freezes
exactly its targeted pixel and no other; no pixel index or pattern-name
literal anywhere in the gate/trace code; deterministic replay; baseline
condition applies zero patches.

## Full test suite

Not re-run in this checkpoint (this phase adds only offline diagnostic
scripts + their own tests; `backend/simulation.py`/`backend/presets.py` are
untouched). Last confirmed clean at Phase 27: 391 passed, 5 pre-existing
failures.

## Files

- `phase28a_local_common_input_feasibility.py` (new) — the harness
  (`CausalTracer`-style monkeypatches, pattern-set swap, gate/oracle
  conditions, full grid runner).
- `phase28a_analyze_results.py` (new) — the pre-registered stop/go
  analysis, written before results were inspected.
- `test_phase28a_local_common_input_feasibility.py` (new) — 18 tests.
- `phase28a_local_common_input_feasibility_results.json` (new, committed,
  ~11MB) — the complete 2,460-run grid, no rows omitted.
- `phase28a_stop_go_analysis.json` (new, committed) — the criteria
  evaluation output (0/12 passing).

## Commit / branch status

Branch `l2-ownership-recovery`, on top of Phase 27 (`f09d8fe3`). Not
pushed. `july14`, `july14-integration`, and every backup branch untouched.
