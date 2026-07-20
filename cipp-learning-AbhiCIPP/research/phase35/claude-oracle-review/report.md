# Read-only review of Codex 2's Phase 35 dendrite oracle

Reviewer: Claude (this session). Target:
`/home/cxiong/codex-runs/codex2-phase35-dendrite-oracle/`. Nothing in that
directory, the production repo, or Codex 1's checkout was modified. All work
product lives under `/home/cxiong/codex-runs/claude-phase35-oracle-review/`.

## Verdict

**`ORACLE_VALID_WITH_COVERAGE_GAPS`**

The oracle's core claim -- that it exhaustively and independently verifies
the physical basal/apical coincidence gate over a 589,824-record two-event
domain -- is genuine and reproduced correctly (see Reproducibility below).
That part is real, not tautological. But several individual requirements in
the review checklist are covered only by tautological checks that cannot
fail by construction, one covered by a golden case whose flag field is
provably dead code, and one (decoder key indexing) uses a convention that
contradicts the governing Phase 35 brief in a way the test suite's topology
can never expose. None of this is `INCONCLUSIVE` -- each gap below is backed
by a specific line number and, where useful, a live reproduction. It is not
`SEMANTIC_CONTRACT_MISMATCH` as an overall verdict either, because the
mismatch is confined to one requirement rather than pervasive; it is called
out explicitly instead so it can be resolved before Codex 1's implementation
is checked against this oracle.

## Reproducibility (positive finding)

The oracle claims to be self-contained and to import no production code.
Confirmed: `reference_oracle.py` has zero imports outside the standard
library. To check the committed JSON artifacts weren't stale or hand-edited,
I copied the script into a scratch directory (never touching the original)
and imported it as a module -- `main()` only runs under
`if __name__ == "__main__"`, so no files were written by this step -- then
recomputed `golden_cases()` and `exhaustive_check()` independently.
`golden_cases.json` reproduced byte-for-byte; `results.json`'s
counterexample count (0) and total simulation count (589,827) both matched.
The oracle is deterministic and its artifacts are current.

## What's genuinely well-verified

Four requirements have real, independent (not self-referential) evidence:

- **Physical delivered-timestep coincidence gate** -- `exhaustive_check()`
  computes an `expected` boolean directly from raw event fields (branch,
  target, delivered_timestep, feedback source, delivery role), independent
  of `simulate()`'s internal control flow, and cross-checks it against
  `simulate()`'s actual output across all 589,824 ordered two-event records.
  Zero counterexamples.
- **Neither branch alone causes charge/firing/learning** -- same exhaustive
  cross-check (`no_effect_without_coincidence`), plus a real negative
  control (`apical_only_max_weight`, apical alone even at `d = d_max`).
- **`d_before_learning` maturity ordering** -- the best-covered requirement
  in the file. `decoder_threshold_crossing` walks the exact crossing
  transition end to end, and a separate independent predicate
  (`bool(spikes) != (before >= maturity)`) is checked at `maturity - eta`,
  `maturity`, and `maturity + eta`.
- **Active-vs-shadow delivery role** -- golden case plus an independent
  exhaustive conjunct requiring both paired events to be `active`.

## Concrete gaps (see `coverage_review.json` for full detail and line numbers)

1. **Decoder key indexes by basal source, not feedback/apical source
   (F1, high).** `semantic_contract.md` states "for each basal source `j`
   ... `d[j,i]`" and the code matches that (`key = f"{b.source}->{target}"`
   uses the *basal* event's source). The governing Phase 35 brief's mapping
   table defines it the other way: `j` is the apical/L2-owner feedback
   source, `i` is the basal-driven pixel. Every test in this oracle
   configures exactly one legitimate feedback source per run, so this
   substitution can never be observed here -- it would only show up once two
   distinct real feedback sources are exercised in the same scenario, which
   never happens in this file. This should be resolved (confirm intended
   convention, then fix the contract or the oracle) before using this oracle
   to validate the production decoder-locality requirement (brief item #12).

2. **"Timestep clearing" and "exactly-once delivery" checks are vacuous by
   construction (F2, F4, both high).** `end_state` is hardcoded to empty
   lists for every record; `delivery_counts` is hardcoded to `{event_id: 1}`
   for every event. Neither can ever fail regardless of what `simulate()`
   does. I confirmed live that `Event.deferred` is read by no code path
   (`deferred=True` vs `deferred=False` produces byte-identical output), so
   `one_time_refractory_deferral` tests nothing about deferral. I also fed
   the oracle two distinct basal events landing on the same target/timestep
   alongside one apical event (simulating a duplicate-delivery bug) and it
   silently applied two separate decoder updates to the same key -- the
   oracle has no notion of a single per-target-per-timestep basal occupancy
   (the brief's `b_i(t)` is a 0/1 indicator, not a count), and neither
   vacuous check would catch this in a real engine.

3. **Queue-carryover classification (`origin_class`) has no independent
   check anywhere (F3, medium).** All golden-case "expected" values,
   including this one, are produced by calling the same `simulate()`/
   `origin_class()` code under test and recording its output -- normal for a
   human-reviewed golden file, but it means `origin_class` correctness rests
   entirely on manual inspection of 3 hand-picked cases, with no exhaustive
   or property-based cross-check the way the gate/maturity/shadow logic has.

4. **Coincidence charge is a fixed config constant, never derived from event
   magnitude (F5, low).** In both parameter sets, `coincidence_charge`
   equals `soma_threshold` exactly, so no case ever exercises "gate opened
   but charge insufficient to cross threshold" as a distinct outcome from
   "gate opened and matured" -- a plausible place for a future off-by-logic
   bug to hide undetected.

## On the checklist's specific tautology/negative-control questions

- **Tautological tests that repeat the oracle's own implementation**: yes,
  two concrete instances (F2, F4), both confirmed to be structurally
  incapable of failing, not merely weak.
- **Golden outputs generated by the same code being tested**: yes, this is
  true of the entire `golden_cases()` mechanism by design (F3) -- the
  saving grace is that four requirements *also* have an independent
  cross-check in `exhaustive_check()`, so they don't rest on golden-file
  self-reference alone. `origin_class` has no such independent backstop.
- **Missing negative controls**: the multi-feedback-source case (F1) and
  the sub-threshold-charge case (F5) are both absent.
- **Ambiguous event ordering**: the two-simultaneous-basal-events case (F4)
  is exactly this, and it is currently under-specified/untested rather than
  ambiguous-but-resolved.
- **Hidden numerical assumptions**: `coincidence_charge == soma_threshold`
  always (F5).
- **Two incorrect behaviors producing the same output**: F1 is precisely
  this shape -- "index by basal source" and "index by feedback source"
  produce identical results under every single-feedback-source test in this
  file, so a wrong implementation of either convention would pass unnoticed.

## Recommendation

Treat the exhaustive-gate, no-effect-without-coincidence, maturity-ordering,
and active/shadow results as trustworthy ground truth now. Before relying on
this oracle for the decoder-locality (F1), timestep-clearing (F2),
exactly-once-delivery (F4), or queue-carryover-classification (F3)
requirements, address the corresponding gap above -- do not treat green
checkmarks on those specific items as evidence yet.
