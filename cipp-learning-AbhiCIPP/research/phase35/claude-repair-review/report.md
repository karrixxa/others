# Independent review: Codex 1's Phase 35 queue-defect repair

Reviewer: Claude (this session), read-only, in a fresh disposable checkout
independent of the one used in the previous review round. Nothing under
Codex 1's directories or the production repo was modified.

## Verdict

**`REPAIR_VERIFIED_NO_NEW_REGRESSIONS`**

The queue-carryover defect I flagged in the previous review is genuinely
fixed, not papered over: the offending reset code is deleted outright, real
passive provenance tracking replaces it, and the previously-bad test was
both removed and corrected rather than just bypassed. Gate A, the repaired
Gate B, and the two new regression tests all independently reproduce. A
direct byte-level hash comparison confirms default-off behavior is
unchanged all the way back to the true base commit. The four previously-
failing prediction-enabled tests still fail -- identically -- but that's
because they test assumptions the Phase 35 redesign deliberately broke, not
because of anything wrong with this repair or the underlying mechanism.

## 1. Bundle, checksum, lineage, diff

`sha256sum` matches the `.sha256` file and the task's stated value exactly:
`1b330b7402913a5ed92402fba41f1105d687ca1ed080985bef470903f8c3587e`.
`git bundle verify` reports OK, one ref, complete history. `db30cead`'s
single parent is exactly `4e712a4b...`, the commit reviewed last time -- no
merge, clean working tree. The diff touches exactly three files
(`CLAUDE_HANDOFF.md`, `backend/simulation.py`, and a newly-added, this-time-
committed `test_phase35_conformance_repair.py`), no cache/`.venv`/binary
content anywhere. `snn/dendrite.py` is untouched -- the repair is scoped
entirely to the presentation-boundary handling in `simulation.py`. Full
detail in `diff_review.md`.

## 2. Is the queue defect actually fixed?

Yes, on every specific sub-requirement, independently verified:

- **Queued events survive a switch**: `test_queue_carryover.py`'s
  `test_scheduled_pair_survives_pattern_switch_and_delivers_once` directly
  asserts `engine.l2e_to_pcol_queue[0]`/`s_to_pcol_queue[0]` are
  byte-unchanged immediately after `engine.set_pattern(...)` -- independently
  reproduced.
- **Deliver exactly once**: the same test confirms the carried-over pair
  fires on delivery and does not re-fire on the following (empty) step;
  `last_coincidence_step` stays put and `last_deliveries` goes empty.
- **Source/target/origin/scheduled/delivery time all survive**: the same
  test asserts each delivered record's `scheduled_step`, `arrival_step`,
  `delivered_step`, `source`, and `target` fields individually.
- **Only per-timestep compartment state clears**: `CoincidencePyramidalCell.
  update()` (unchanged, in the untouched `snn/dendrite.py`) still calls
  `clear_compartments()` every engine step via `pc.update()`
  (`backend/simulation.py` ~line 2887). The deleted block was the *only*
  place compartments were being force-cleared outside that normal per-step
  cadence -- and it's gone.
- **Stale arrivals are observable, not deleted**: the new
  `_prediction_column_origin_class` method classifies
  `current-correct`/`stale-same-pixel`/`stale-wrong-pixel`/`mixed` and
  exposes them through `dynamic_state()['prediction_column']
  ['last_deliveries']`/`['pending_deliveries']`. I confirmed by grep that
  this classifier's output is read *only* by the telemetry-assembly code --
  never by `resolve_coincidence`, `_apply_prediction_column_learning`, or
  any scheduling/delivery path. Telemetry is genuinely observation-only.

The fix mechanism: a new `pcol_delivery_metadata_queue` deque, the same
length as the physical delay queues, populated in lockstep at the scheduling
site and popped in lockstep at the delivery site -- passive metadata riding
alongside the physical events, never controlling them.

## 3. Was the bad test removed, or corrected?

**Both.** `test_phase35_gate_b_repair.py` assembles its 6-test suite from 4
of the 5 original Gate B tests, explicitly *excluding*
`test_pattern_switch_discards_queued_compartment_events` (removed), and adds
2 new tests, one of which
(`test_scheduled_pair_survives_pattern_switch_and_delivers_once`) tests the
*exact same scenario* -- a pre-scheduled pair spanning a pattern switch --
but asserts the *opposite, correct* outcome (the pair survives and fires).
That's a correction, not a quiet deletion with nothing in its place.

## 4. Independent reproduction

All copied into my own disposable checkout and run there (not against
Codex 1's live checkout):

- **Gate A: 6/6**, identical test names.
- **Repaired Gate B: 6/6**, identical test names. One subtlety worth
  flagging for transparency: the driver script loads the 4 reused test
  *functions* from Codex 1's own artifact directory via an absolute path
  (`importlib.util.spec_from_file_location`), but those functions' own
  `from backend.simulation import ...` statements resolve against whatever
  `PYTHONPATH` is set when the process runs -- which I set to `.` inside my
  own disposable checkout. So the test *code* comes from Codex 1's
  directory, but the *production module it exercises* is genuinely mine.
- **New committed regression tests: 2/2** (`test_switch_preserves_
  scheduled_physical_pair_and_metadata`, `test_saturating_update_crosses_
  then_fires_on_following_coincidence`), run directly from the commit.
- **Default-off hash comparison**: built a `git worktree` of the pure base
  commit `4764f17`, ran an identical deterministic 120-step sequence
  (`SimulationEngine(seed=71)`, flag never touched, `set_pattern('row 1')`,
  120 steps) at both the base and the repaired commit, serialized
  `_all_weights()` and SHA-256'd it. **Byte-identical**:
  `55259e3475d3ab87f3256979420fe58f00ba70369966b5d55fec39b0f1122752` at both
  ends. Default-off behavior is unchanged across the entire Phase 35 change
  set, not just "the same known golden drift" as before -- this time a
  direct hash match.

## 5. The four previously-failing tests

Re-ran all four in isolation (300s timeout each) at `db30cead`. **All four
fail identically to how they failed at `4e712a4`** -- same error, same line.
This alone tells you the repair didn't touch whatever is causing them (it
didn't; `snn/dendrite.py` isn't even in this diff). The real question is
whether they're regressions or obsolete expectations. I investigated each
rather than taking the "obsolete" label on faith:

- **`test_phase20_frozen_reconstruction.py`** -- `IndexError` on
  `pcol[4]._weights_array[j]` for `j` up to `N_OUT-1`, but the array is now
  `[1.0]` (size 1). This is a data-structure assumption break: the decoder
  moved to `pcol[i].decoder_weights` as part of Phase 35's deliberate
  explicit-compartment redesign. **Obsolete API usage**, not a demonstrated
  behavioral regression -- it errors before reaching any actual assertion
  about reconstruction behavior.
- **`test_phase21_selective_inhibition.py`** and
  **`test_phase22_full_interaction.py`** -- both fail because, after up to
  1500 engine steps, PC never fires at all under the test's *default,
  unaccelerated* `prediction_learning_rate=0.15`/`prediction_feedback_init=
  50.0` config. I independently recomputed how many qualifying coincidence
  *events* (not engine steps) it takes a decoder starting at 50 to reach the
  emergent maturity boundary (350) under `eta=0.15`: **exactly 2946** (a
  from-scratch recurrence simulation, not taken from any document -- and it
  happens to match the brief's own "~2946" prediction exactly). A
  1500-engine-step budget cannot possibly supply 2946 qualifying coincidence
  events even in the best case. Under the old Phase 19 additive/graded
  model, PC could contribute partial charge much sooner; Phase 35's
  all-or-nothing gate deliberately requires genuine decoder maturation
  first. Gate B's own tests correctly sidestep this by using accelerated
  configs (`prediction_learning_rate=100.0` or `prediction_feedback_init=
  400.0`); these two pre-existing tests were never updated to do the same.
  **Obsolete expectation**, not a regression in the mechanism itself.
- **`test_prediction_column_phase19.py`** -- expects a graded, sub-threshold
  potential rise from a "delayed delivery arriving this step." Phase 35's
  `resolve_coincidence` is deliberately all-or-nothing (deposits either zero
  charge or exactly one `soma.threshold` unit, never a partial amount) --
  this is the literal, explicitly-required brief behavior, not an accident.
  **Obsolete expectation** -- the test encodes the pre-Phase-35 model the
  brief explicitly asked to replace.

None of the four is a real Phase 35 regression, an environment problem, or
unrelated pre-existing behavior -- all four are pre-existing tests whose
assumptions no longer hold against a deliberately redesigned architecture.
They would still need real work to restore as meaningful regression
coverage (porting the API usage and/or accelerating their learning-rate
configs and/or extending their step budgets), but their current failure is
expected, not alarming. Codex 1's `CLAUDE_HANDOFF.md` entry for this repair
correctly and completely discloses all four this time, attributed to
`4e712a4`, with "No repair regression was observed" -- matching what I
independently found, and a real improvement in reporting completeness over
the previous round's incomplete claim.

## 6. Maturity semantics

Two independent checks, not just re-reading the code:

- **No hardcoding**: grepped `snn/dendrite.py` for the literal values 150,
  350, 500, 1200, 0.15 -- zero matches. `coincidence_threshold` and both
  branch weights are plain constructor arguments throughout.
- **Genericity**: constructed a `CoincidencePyramidalCell` by hand with
  parameters unrelated to any Phase 35 default (basal weight 30, soma
  threshold 200, apical init 60, eta 5, `w_max` 500). Predicted emergent
  boundary: `200 - 30 = 170`. Observed: first fire occurred with the decoder
  at 170.90, immediately after crossing 170. The mechanism generalizes
  correctly to arbitrary consistent parameters -- it is not secretly tied to
  150/350/500/1200/0.15.

On whether a separate maturity Boolean is actually required: I don't think
so, and I don't think its absence is a defect. `CLAUDE.md`'s own stated
priority is that biological plausibility and local physical dynamics take
priority over clean classification metrics. A biological synapse doesn't
carry an independent "am I mature" register separate from its own weight --
whether its contribution, combined with everything else converging on the
soma, crosses the soma's own threshold *is* the physically meaningful test.
Codex 1's single combined-threshold design is arguably a *more* biologically
faithful reading of "maturity" than an independently-configured constant
compared in isolation from actual charge summation would be (the latter is
closer to a software gate bolted onto the dynamics than a property of the
dynamics themselves). The real, worth-documenting consequence is that
`prediction_lateral_weight` and `prediction_threshold` are now *coupled* --
changing one moves the effective maturity boundary -- which is a real,
predictable coupling worth remembering for future config changes, but that's
coupling, not fragility or hardcoding. **`EMERGENT_MATURITY_VALID`.**

## 7. Cleanliness

No cache files, `.venv` artifacts, generated reports, or unrelated changes
anywhere in the diff. Exactly the three claimed files, confirmed via
`git diff --numstat`.

## 8. Scope discipline

No production code, Codex 1's checkout, or Codex 2's oracle was modified. No
Gate C, ownership evaluation, or parameter tuning was performed.

## Processes remaining

None from this review. Same unrelated, pre-existing IDE tooling (VS Code's
Python-environment helper, the Pylance language server) observed in the
process list as in the previous round -- not started or touched by this
work.

## Artifacts

`progress.md`, this `report.md`, `results.json`, `diff_review.md`,
`test_log.txt` -- all under
`/home/cxiong/codex-runs/claude-phase35-repair-review/`. Disposable checkout
(left for inspection, a `/tmp` scratch path scoped to this session):
`/tmp/claude-275450548/-home-cxiong-others-cipp-learning-AbhiCIPP/55d19a97-a1ec-436c-ada9-dbb060f69996/scratchpad/phase35-repair-independent-checkout/`.
