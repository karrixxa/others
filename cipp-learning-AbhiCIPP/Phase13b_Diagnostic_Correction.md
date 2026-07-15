# Phase 13b — Corrected and Strengthened Dashboard Behavior Diagnostic

**MEASUREMENT ONLY.** No neural mechanism, parameter, timing, learning rule,
seed convention, or default changed. Continues from the Phase 13 checkpoint
(`6655cfe`); corrects a real methodology bug found in that phase's own
instrumentation and generalizes every seed=1-only claim across a full seed
grid before trusting it.

## What was wrong with Phase 13

Phase 13's `dashboard_behavior_diagnostic.py` tagged every loser-depression
weight-delta record with `spiked=engine.spiked[nid]` read **at the moment
`apply_delayed_inhibition()` is called** — which is at the very top of
`step()`, before that step's own L1E/L2E competition has run. At that point
`engine.spiked[nid]` still holds **last step's** result, not "did this
neuron spike this step." Separately, every one of Phase 13's headline claims
(the "3 active neurons" match, "distance off makes things worse," the
L2E5-specific union claim) was drawn from **a single seed** (seed=1). Both
problems are fixed here.

## Corrected instrumentation (`phase13b_diagnostic.py`)

Three explicitly-timed facts replace the old ambiguous `spiked` field on
every loser-depression record:
- **`spiked_previous_step`** — `engine.spiked[nid]` snapshotted *before*
  `_deliver_scheduled_l2_inhibition` runs this step (this neuron's real,
  finished result from t−1).
- **`inhibited_at_start_of_step`** — `apply_delayed_inhibition`'s own
  `applied` flag.
- **`spiked_later_current_step`** — `engine.spiked[nid]` read *after* the
  owning `step()` call fully completes (this neuron's real, finished result
  for the CURRENT step). Filled via a bounded per-step pending list, not a
  full-history rescan (the first draft of this fix had an O(steps × total
  records) rescan that made the full grid run take 9.5 minutes instead of
  the expected ~1; fixed to O(events this step) before this data was
  trusted).

Also added: **unique L2I delivery-event counts** (grouped by the delivery's
own `fire_t`) alongside the **individual synapse-delta count** Phase 13
already had; dynamic **tyrant identification** (most total spikes this run,
never assumed); **tyrant-vs-pattern-specific weight** comparison generalized
to whichever neuron that is; a **never-fired-neuron loser-depression
count**; and a third config, **C** (see below). 11 tracer-timing tests
(`test_phase13b_tracer_timing.py`) verify the instrumentation itself against
independently-reconstructed ground truth — not the engine, the diagnostic
tooling.

**A genuine methodological finding surfaced by these tests:**
`engine._l2_inhibition_log` is a `deque(maxlen=LOG_MAX=400)` — a
display-oriented rolling window, not an exhaustive record. On the
3,200-step interleaved scenario the true delivery count exceeds 400 and the
engine's own log silently drops older entries, so **this tracer's own
exhaustive count is the correct "unique delivery events" figure for long
runs, not `len(engine._l2_inhibition_log)`** (confirmed:
`unique_delivery_events` > `engine_l2_inhibition_log_len` in all 45
`interleaved_40` grid runs, by exactly the amount truncated; the two matched
exactly in all 90 short/long hold-switch runs, which never reach 400
events). Worth knowing for anyone reading `dynamic_state()['l2_inhibition']['log']`
directly off a long-running dashboard session.

## Method

**Grid:** weight seeds 1–5 × topology seeds 1–3 (15 combinations) × 3
scenarios × 3 configs = 135 runs, plus a 5-seed Phase-11-style
distinct-owners pass (topology_seed=1) for direct reconciliation, plus a
dedicated topology-seed-inertness check.

**Scenarios:**
1. `short_hold_switch` — row 1 for 20 steps → col 1 for 20 (Phase 13's
   original scenario).
2. `long_hold_switch` — row 1 for 600 steps → col 1 for 200.
3. `interleaved_40` — the brief's equal cycle, 20 steps/pattern, 40
   rotations (3,200 steps) — reuses `diagnostic_schedule.CYCLE_ORDER`/
   `_present_and_record`/`summarize` directly, same as Phase 13.

**Configs:**
- **A** — the literal dashboard default (`distance_weighting=True`,
  `legacy_distance_compat=True`; delivery distances pinned to the fixed
  legacy reference geometry, independent of topology_seed).
- **B** — raw distance off (`distance_weighting=False`; no per-connection
  attenuation/amplification at all).
- **C** — diagnostic-only: `distance_weighting=True` with every L1E→L2E
  connection's distance overridden, after construction, to one uniform
  scalar solved so the delivered influence factor equals config A's own
  mean (1.9621, computed once from A's real geometry) for every
  connection. Same total/mean amplification budget as A, but spatially
  flat — isolates "does the AMOUNT of amplification matter" from "does
  WHICH pixel gets more of it matter." Built via the same `.distance`
  property every existing test already uses to set per-afferent distances;
  no default in `backend/presets.py`/`backend/simulation.py` touched.

**Topology-seed inertness — verified, not assumed:** none of A/B/C let real
per-topology-seed geometry drive delivered distance (A/C are legacy-pinned
or uniform-overridden; B has no distance factor at all). Confirmed directly:
final feedforward weights are byte-identical across topology_seed∈{1,2,3}
at a fixed weight_seed, for all three configs
(`topology_seed_inertness` in the summary JSON, all `True`). This is why the
grid below reports per-config numbers pooled across all 15 seed/topology
combinations without a separate topology axis — topology_seed is a
confirmed no-op for these three configs specifically (Phase 4's
`infl_l2e_l2i`/`infl_l2e_l1i`/etc. pathways, which WOULD respond to real
topology, stay off in all three, per the standing "do not enable every
pathway together" rule).

## Corrected findings

### 1. Recruitment breadth (`active_count`, mean over 15 seed/topology combos)

| Scenario | A (distance on) | B (distance off) | C (uniform, matched) |
|---|---|---|---|
| short_hold_switch | **4.80** (min 4, max 6) | 4.00 (min 3, max 5) | 4.40 (min 3, max 5) |
| long_hold_switch | 1.40 (min 1, max 2) | **2.00** (min 1, max 3) | **2.40** (min 2, max 3) |
| interleaved_40 | 3.60 (min 3, max 4) | 4.00 (min 1, max 6) | 3.80 (min 3, max 5) |

**Phase 13's claim that "turning distance_weighting off measurably WORSENS
recruitment" does NOT hold up across seeds and must be corrected.** It was
true for seed=1 specifically (B: 1/8 active) but seed=1 was an unlucky draw
for B, not a representative one — averaged over 5 seeds, B's recruitment is
about the same as A in the interleaved schedule (4.00 vs 3.60) and clearly
BETTER in the long-hold schedule (2.00 vs 1.40). What IS true and
seed-robust: **A is more consistent (narrow min–max spread) while B is more
variable (can do much better or much worse depending on seed)** — B's
interleaved-schedule range (1–6) is far wider than A's (3–4). The correct,
corrected statement is "distance-on trades variance for a schedule-dependent
mean effect that reverses direction — better in short/interleaved, worse in
long-hold — not a uniform improvement," which is a materially different and
more defensible claim than Phase 13's.

### 2. Distinct, stable ownership (Phase-11-style metric, interleaved schedule, 5 seeds)

| Config | distinct_owners per seed | mean |
|---|---|---|
| A | 4, 4, 3, 4, 3 | **3.6** |
| B | 1, 1, 4, 1, 1 | 1.6 |
| C | 1, 4, 4, 1, 1 | 2.2 |

Here A is clearly, robustly better than B on the metric Phase 11 actually
used (not just "some neuron spiked at least once," but "a consistent,
stable per-pattern first-responder"). This is the more important corrected
picture: **distance-on (A) doesn't necessarily recruit more neurons overall,
but the neurons it does recruit hold their pattern identity far more
consistently than under distance-off.**

### 3. Reconciliation with Phase 11's schedule-dependent distance finding

Phase 11 found: turning distance/influence ON *reduced* distinct owners in
the short-interleaved schedule (3.33→2.33 symmetric, 3.33→1.50 jittered) but
*increased* it in long-saturation (1.67→2.33/2.17) — a real,
schedule-dependent reversal, not a uniform effect.

**This is NOT the same manipulation as Phase 13/13b's A-vs-B axis, and the
two should not be read as agreeing or disagreeing at face value:**
- Phase 11's "influence on" = `distance_weighting=True` **with
  `legacy_distance_compat=False`** — REAL, topology-seed-varying,
  jittered-geometry-driven distances (`_engine_kwargs`,
  `phase11_validation.py:106-107`).
- Phase 13b's config A = `distance_weighting=True` **with
  `legacy_distance_compat=True`** — a FIXED, topology-seed-independent
  legacy reference. This is a third condition Phase 11's own 2×2 geometry
  grid never tested. (Phase 11's own docstring claims the literal dashboard
  default "sits inside the jittered/influence-off cell" of its grid — by
  its own `_engine_kwargs` code, that cell requires `distance_weighting=
  False`, which the dashboard's actual `distance_weighting=True` doesn't
  satisfy. That docstring claim appears to be imprecise; flagged here for a
  human to confirm, not corrected in Phase 11's own file, which is out of
  this phase's scope.)
- Phase 11's "short-interleaved" is 10 cycles (800 steps); this phase's
  `interleaved_40` is 40 cycles (3,200 steps) — 4x longer, per this
  session's explicit instruction, not a replication of Phase 11's exact
  schedule length.

**What DOES generalize, and is the genuinely useful reconciliation:** Phase
13b's OWN axis (legacy-pinned distance on vs. off) shows the same
QUALITATIVE pattern Phase 11 found on its different axis — **a schedule-
dependent reversal, not a uniform verdict.** By `active_count`: A beats B in
`short_hold_switch` (4.80 vs 4.00) and loses to B in `long_hold_switch`
(1.40 vs 2.00). By `distinct_owners` in `interleaved_40` specifically: A
beats B (3.6 vs 1.6), the opposite polarity from Phase 11's short-
interleaved result for its OWN (real-geometry) manipulation. Two
independent distance-related manipulations, two different specific
directions, but the SAME shape of finding: **"does distance information
help" has no single answer independent of the presentation schedule.** This
is Phase 11's core lesson, now independently reproduced on a different
mechanism, which is a stronger result than either phase's finding alone —
and a caution against extending either phase's specific polarity to a
manipulation it didn't test.

### 4. The tyrant is not, and was never necessarily, L2E5

Tyrant identity (`interleaved_40`, 15 seed/topology combos per config):
- A: `L2E3` (9/15), `L2E5` (3/15), `L2E1` (3/15)
- B: `L2E0` (6/15), `L2E3` (6/15), `L2E4` (3/15)
- C: `L2E4`, `L2E0`, `L2E5`, `L2E1`, `L2E7` (3/15 each)

L2E5 was the tyrant in only 3/45 runs across all three configs. Phase 13's
specific focus on L2E5 came directly from that phase's own prompt (which
named it as the example to check), not from any actual identification
process — Phase 13's report should have been read as "an illustration using
one particular seed's tyrant," not "L2E5 is special." This phase corrects
that framing explicitly.

**What DOES generalize, robustly, regardless of which neuron is tyrant:**
in **all 45 runs, across all three configs**, the tyrant's single highest
feedforward weight is on **pixel 4 (the center)** — the one pixel active in
every trained pattern. The union-vs-other-pixel weight ratio (tyrant's mean
weight on row1∪col1 pixels vs. the rest):

| Config | union mean | other mean | ratio |
|---|---|---|---|
| A | 452.3 | 106.9 | 4.23x |
| B | 458.1 | 72.2 | **6.35x** |
| C | 470.4 | 92.8 | 5.07x |

The mechanism from Phase 13 (the center pixel never receives the signed
rule's depress signal under any pattern, so it climbs unopposed while
genuinely distinguishing pixels get depressed whenever a DIFFERENT pattern
fires) is confirmed to be general, not an L2E5 artifact. **Turning distance
off does not fix this — it makes the winner's own receptive-field
degeneracy WORSE** (6.35x vs 4.23x concentration), even though (per finding
1) it doesn't clearly change how many neurons participate overall. Combined
with finding 2 (lower distinct_owners under B), the corrected picture is:
distance-off doesn't fix the underlying "collapse onto the shared pixel"
pathology — it just makes which neuron ends up doing it, and how
consistently, less predictable.

### 5. Never-fired neurons and loser depression — quantified, not just observed

Across the 15-seed `interleaved_40` grid, aggregating every never-fired
neuron encountered:

| Config | never-fired neuron-instances (of 120 possible) | mean depression events received, each |
|---|---|---|
| A | 39 | **2,222** |
| B | 27 | 1,388 |
| C | 36 | 2,161 |

A neuron that never fires once in a 3,200-step run still gets its
currently-active-pixel weights depressed on the order of **1,400–2,200+
times** by loser depression alone — continuous, one-directional erosion
with no self-generated event that could ever reverse it (Phase 13's finding
1–2, that 100% of non-spiking-previous-step weight changes are
`l2i_loser_depression`, is reconfirmed here: max over all 135 runs is
exactly 0 non-spiking-previous-step increases). This is Phase 13's
"rich-get-richer, no rescue mechanism" claim, now with an actual magnitude
attached instead of just a direction.

### 6. `spiked_later_current_step` — rare, and config-A-specific

Out of all 135 runs, only **9** show any occurrence of a neuron being hit by
delayed inhibition at the start of a step and still crossing threshold
later that SAME step — and every one of those 9 is in **config A**
(6/15 `long_hold_switch`, 3/15 `interleaved_40`; values 9, 18, or 39 events
per run). **Zero occurrences in configs B or C, ever.** This is a genuinely
new, precise mechanistic finding: it takes a strong, spatially-CONCENTRATED
amplification (config A's up-to-2.13x boost concentrated on specific
pixels) to let a neuron's charge rebuild fast enough to re-cross threshold
within the same step after a full-`threshold_l2`-magnitude subtraction;
neither no amplification (B) nor the same average amplification spread
evenly (C) ever produces this. Confirmed by dedicated tracer-timing tests
(`test_spiked_later_current_step_agrees_with_self_spike_records` and the
cross-config sweep above) — this replaces Phase 13's mislabeled, single-
value `spiked` field entirely.

## Explicit corrections to Phase 13's report

1. **"Turning distance_weighting off made recruitment measurably worse"** —
   WRONG as a general claim (see finding 1); true only for the specific
   seed=1 draw Phase 13 happened to run. Corrected to: distance-on trades
   variance for a schedule-dependent effect that reverses direction between
   short and long schedules.
2. **"Config B reproduces the reported '3 active neurons' symptom almost
   exactly"** — this was real for seed=1 specifically, not a general
   property of config B; other seeds under B range from 1 to 6 active
   neurons. The *reported* symptom is real and reproducible under SOME
   seeds of B, but "config B causes this" overstates a single-seed
   observation as a config-level rule.
3. **"L2E5 forms/doesn't form a union of row 1 and col 1"** — L2E5 was
   Phase 13's arbitrarily-assigned example (per that phase's own prompt),
   not an identified tyrant; only 3/45 runs in this phase's grid have L2E5
   as tyrant. The underlying mechanism (collapse onto the always-active
   center pixel, atrophy of genuinely distinguishing pixels) is CONFIRMED
   general (45/45 runs) — the neuron-specific framing is corrected.
4. **The `spiked` field on loser-depression records** — mislabeled (read at
   the wrong moment; see "What was wrong with Phase 13" above). Replaced
   with three explicitly-timed fields.
5. Phase 13's exact-FE-saturation example (>1000x envelope-value asymmetry
   at 97% of cap) is **not contradicted or generalized further here** — it
   was already presented as a single-run illustration of a structural,
   code-level property (confirmed by direct reading of
   `exact_local_free_energy_update` vs. `bounded_signed_update`), not an
   empirical claim requiring seed-robustness in the first place.

## Full test suite

`pytest -q`: **265 passed, 5 failed** (254 pre-existing + this phase's 11
new `test_phase13b_tracer_timing.py` tests, all passing). The 5 failures are
the same pre-existing flow-rate failures documented since before Phase 6 —
unchanged. The 11 new tests verify the tracer instrumentation itself
against independently-reconstructed ground truth, not the engine.

## Files

- `phase13b_diagnostic.py` (new) — the corrected/strengthened measurement
  script (see docstring for the full design).
- `test_phase13b_tracer_timing.py` (new) — 11 tests validating the tracer's
  own timing/counting logic.
- `phase13b_diagnostic_summary.json` (new, committed) — the full 135-run
  grid, the 5-seed Phase-11-style comparison, and the topology-seed
  inertness check. Per-event full logs (tens of MB, one config/scenario/seed
  combination can run to tens of thousands of records) are disposable `/tmp`
  artifacts, not committed, same convention as Phase 13.

## Final commit chain / working-tree status

Continues from Phase 13 (`6655cfe`) on `july14-integration`. No engine file
touched. Not pushed, not merged, no PR. `july14` base untouched.
