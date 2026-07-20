# Phase 35 mature-mechanism efficacy experiment

Measurement-only. Starting point: branch `phase35-dendrite-classes-codex1`,
commit `db30ceadbe18cf90e01f6d54dee0203f342b24a8` (the repaired checkpoint
verified in the previous review round). No production file was edited, no
learning rate/threshold/delay/inhibition/leak/geometry/equation/queue
behavior was changed, nothing was pushed.

## Verdict

**`MATURE_ACTIVE_SUPPRESSION_EFFECTIVE_BUT_OWNERSHIP_NEUTRAL`**

Once decoders are given enough natural physical exposure to actually
mature (the original 3,200-step grid never got there), enabling physical
PC-to-local-I delivery produces a real, reproducible, selective suppression
effect on expected/explained sensory activity, consistently across 6
independently-matured natural seeds, with no observed collateral damage to
novel activity anywhere it was structurally possible to measure. It shows
no visible effect on L2 ownership/collision dynamics, which remain exactly
as unstable under active suppression as under shadow.

## Checkout status

- Standalone scratch clone built from `phase35-conformance-repair-
  db30ceadbe18cf90e01f6d54dee0203f342b24a8.bundle`, entirely separate from
  Codex 1's or Codex 2's own directories and from the production repo.
  (One early misstep, caught and reversed before any real work: I first ran
  `git fetch`+`git worktree add` directly against the production repo's own
  `.git`, creating a local branch ref there. Deleted that branch and removed
  the worktree immediately -- verified afterward that `git branch`/`git
  status`/`git worktree list` in the production repo were back to exactly
  their prior state before proceeding with a proper standalone clone.)
- No commits were made in the scratch clone; it was used purely to import
  and run the already-committed `SimulationEngine`.
- Nothing pushed anywhere.
- No production source file was modified. The only "code" written for this
  experiment is a separate driver/library outside the repo
  (`scripts/lib.py`, `scripts/run_seed.py`), which imports and calls the
  committed engine through its existing public API and constructor
  parameters -- it does not patch, monkey-patch, or subclass any production
  class.

## Stage 1 -- natural maturation in shadow

Config (all via existing, documented `SimulationEngine` constructor
parameters -- no source line changed):

```
prediction_column_enabled=True          # Phase 35 decoder/coincidence learning ON
prediction_column_to_i_enabled=False    # physical PC-to-local-I suppression OFF
prediction_leak_diagnostic_disable=True # passive (PCi soma) decay OFF
loser_depression=False                  # loser depression OFF
l2e_budget=False                        # global (sum-renorm) normalization OFF (already the default)
```
`prediction_feedback_init`/`_max`/`_learning_rate`/`prediction_threshold`/
`prediction_lateral_weight` all left at their committed defaults (50, 1200,
0.15, 500, 150). No decoder weight was ever set by hand.

**Documented max horizon: 20,000 steps.** Chosen from calibration, not
guessed: a direct reproduction of the audit's own 3,200-step regime showed
natural ownership hadn't sharpened yet at that point; a longer 3-seed pilot
(checked every 5,000 steps to 60,000) found all three matured somewhere in
[5000, 10000]; a from-scratch numeric recurrence gave an independent
theoretical prediction of exactly 2,946 qualifying coincidence events to
cross the emergent maturity boundary. 20,000 steps is roughly 3x the
observed empirical requirement. Full detail in `calibration_log.txt`.

**A finding worth reporting on its own: natural single-responder emergence
is the minority outcome.** A 40-seed scan (held pattern "row 1", 6,000
steps each) found only 11/40 seeds produce a clean single natural L2
responder -- the other 29/40 show a *persistent, exact* tie (identical to
6 decimal places at every checkpoint) between two co-equal L2E neurons that
fire together on every qualifying step. This is the same L2-ownership
instability this project has documented extensively elsewhere, now visible
directly in decoder-maturation dynamics: even "clean" winners lead by a
narrow margin (~0.02% at 6,000 steps in the seed checked). The smoke seed
and the 5 additional seeds were drawn from the 11 clean-leader seeds
specifically so "the natural L2 first responder" is unambiguous, matching
the task's literal framing -- this is a deliberate seed-selection choice,
disclosed here rather than silently made.

**Results, all 6 seeds** (seeds 1, 3, 10, 14, 17, 22; leaders L2E5, L2E5,
L2E6, L2E4, L2E6, L2E2 respectively -- a different natural winner nearly
every time, confirming these are independent natural outcomes, not one
result copied six times):

- All 6 reached full 3-pixel maturity, between step 6,122 and 6,128.
- Per-pixel decoder-update event counts: 2946-2956 across all seeds --
  matching the independently-derived 2,946-event theoretical prediction to
  within 10 events in every case.
- All 3 active-pixel synapses of the natural leader matured in the *same*
  step every time (mechanically expected: the leader delivers identically
  to all 9 apical compartments whenever it wins, and a held pattern keeps
  all 3 active pixels' basal compartments active together).
- Inactive-pixel decoder weights: byte-unchanged in all 6 seeds, zero
  exceptions.
- Origin-class telemetry: 100% `current-correct` throughout Stage 1 in
  every seed (expected -- no pattern switch has happened yet).
- First physical PC spike after maturity: fired on the exact maturity-
  crossing step in the seed where I tracked it explicitly (seed 1, step
  6122) -- the crossing-event-doesn't-fire/next-one-does contract (verified
  independently in the previous review round) means the *first* fire
  should follow essentially immediately once mature, and it did.

## Independence verification

Hit a genuine, unrelated technical finding while implementing "make
independent deep copies": **`CoincidencePyramidalCell` is not safe to pass
through plain `copy.deepcopy`.** Its `__getattr__` (`snn/dendrite.py`
~line 157-158) delegates any unrecognized attribute to `self.soma`.
Python's default deepcopy/reduce protocol probes a partially-constructed,
attribute-less instance with `hasattr(y, '__setstate__')` before any
attribute is set; that probe falls into `__getattr__`, which tries
`self.soma` -- also unset on the partial instance -- which falls into
`__getattr__` again. Confirmed empirically: `RecursionError`, ~986 stack
frames, reproduced on the very first attempt. Worked around in
`scripts/lib.py`'s `clone_engine()`/`_clone_pc()` by cloning via `__dict__`
directly (`object.__new__` + per-field `copy.deepcopy`), which never
triggers attribute lookup on an incomplete instance -- no production file
was touched to make this work. `self.pcol` and `self.neurons` both hold
references to the *same* PC objects (`backend/simulation.py` line 1814:
`self.neurons[nid] = self.pcol[i]`), so the clone shares one `memo` dict
across both paths to guarantee both references resolve to the identical
clone, not divergent duplicates.

With that in place: for every one of the 6 seeds, cloned the checkpoint
twice, stepped one clone, and confirmed the other clone's full state
fingerprint (every weight, timestep, spike record, every PC's decoder and
basal weights) was byte-unchanged while the stepped clone's fingerprint
did change. **`ok=True` in all 6 seeds.**

## The one necessary adaptation: L1I weight-vector shape

`prediction_column_to_i_enabled` controls L1I's incoming-weight-vector
*shape* at build time (`l1i_n_feedback = 1 if enabled else N_OUT`,
`backend/simulation.py` ~line 1134). The Stage-1 checkpoint was built with
the flag off, so every L1I neuron's weight vector is 8-dimensional. B keeps
that (flag stays off). For C, flipping the flag on a clone without
addressing this would feed a 1-element delivery into an 8-dimensional
weight vector -- a real shape mismatch, not a semantic choice, and there is
no way to recover "the value the engine would have drawn at construction"
after the fact (that draw consumes a different number of RNG samples for a
differently-shaped array). Rather than inventing a new value, C's L1I
weight is collapsed to the mean of its own existing 8-dimensional vector,
applied identically and mechanically to all 9 L1I neurons in every seed.
Nothing else about L1I (its own learning rate, threshold, leak) is touched;
it keeps learning normally from that point on. This is the only place this
experiment did anything beyond a pure attribute flip, and it's a structural
necessity, not a tuning choice -- full detail and the actual before/after
numbers are in `results.json` and `scripts/lib.py`'s `make_bc()` docstring.

## Stage 2 -- B (shadow) vs C (active)

All three tests ran for all 6 seeds (smoke seed first, validated, then the
5 additional seeds -- 30 seeds was never run).

**Test 1, continued held-pattern presentation (1000 steps):** identical
across all 6 seeds regardless of which L2E naturally led --
`B` expected-pixel L1E firing rate 0.500 (1500/3000), `C` 0.400 (1200/3000):
a **20% relative reduction**. `B` delivers 0 L1I events (by construction);
`C` delivers exactly 1200, matching its PC spike count 1:1. Novel-pixel
firing was 0/6000 in both conditions -- a valid but weak negative control,
since "novel" pixels receive zero external drive at all under simple
single-pattern presentation, so there's nothing to over-suppress here by
construction (a real limitation of this specific test, noted honestly
rather than oversold as evidence of anything).

**Test 2, switch to the one-overlapping second pattern ("col 1", 1000
steps):** a smaller but still real, directionally consistent effect: `B`
stays at 0.500; `C` drops to 0.485 (seeds 1/3/10/22) or 0.478 (seeds
14/17) -- 3-4% relative reduction, much weaker than test 1, because only
the shared pixel (4) has an already-mature decoder immediately after the
switch; the two newly-active pixels specific to "col 1" haven't had time to
mature. Decoder locality held in every seed (confirmed, not assumed --
this gates whether test 3 even runs). Stale-classification telemetry showed
100% `current-correct` in both conditions in every seed -- no
boundary-crossing stale coincidence happened to land inside this
particular 1000-step window. That's a fact about this test's timing, not a
sign anything is wrong with the queue-carryover classifier (its correctness
was independently verified on its own dedicated test in the previous review
round).

**Test 3, short equal-interleaved four-pattern schedule (2 rounds x 4
patterns x 100 steps, run because test 2 validated in all 6 seeds):** the
suppression effect is *dramatically* stronger here than in either
single-pattern test. Example (seed 1): `B` PC spikes per pattern per round
stayed near 50-150 throughout; `C` collapsed to 0-57, with "col 1" hitting
literally **zero** PC spikes in both rounds under active suppression versus
122-150 under shadow. This is consistent with a genuine negative-feedback
loop compounding over repeated switches (PC fires -> L1I suppresses its
paired L1E -> less L1E activity -> less PC basal drive -> fewer future
coincidences). One thing I'm flagging rather than fully resolving: L1E's
own raw firing *rate* for expected pixels barely moved (0.487 vs 0.500)
even as PC/L1I event counts collapsed by 60-100% -- the AND-gate nature of
coincidence detection (needing simultaneous mature basal *and* apical)
plausibly amplifies a small reduction in basal availability into a much
larger reduction in coincidence rate, but I have not decomposed this
rigorously enough to assert it as settled. Worth a focused follow-up if
this mechanism becomes load-bearing for anything downstream.

**Ownership-related metrics:** the multi-winner-L2E-step count (a proxy for
"ownership collisions") was 500 under B and 400 under C in every seed --
numerically identical to each condition's own PC-spike count, meaning
collision and prediction-relevant activity co-occur rather than being
independent. There is no sign that enabling suppression changes *which*
L2E's compete or how often they tie. The tie-rate finding from Stage 1 (29
of 40 scanned seeds persistently tied) is untouched by whether suppression
is delivered -- active suppression visibly changes sensory- and PC-layer
activity; it does not visibly touch L2-layer ownership dynamics in this
measurement.

## What this does and doesn't establish

Does establish: the coincidence/decoder mechanism, once actually given
enough natural exposure to mature, produces a real, selective,
reproducible local-suppression effect exactly where the brief said it
should (explained pixels), with no measured collateral damage where damage
was measurable. Does not establish: that this mechanism helps, hurts, or
touches the separate, still-open four-pattern L2-ownership-instability
problem -- consistent with the standing project guidance not to claim
prediction has solved ownership before a dedicated Gate D. This experiment
was explicitly not that gate, and none of its results should be read as
one.

## Artifacts

- `report.md` (this file), `results.json`, `calibration_log.txt` -- under
  `/home/cxiong/codex-runs/claude-phase35-mature-efficacy/`.
- `per_seed/seed_{1,3,10,14,17,22}.json` -- full raw output per seed
  (Stage 1 trajectory, independence check, L1I reshape log, all three
  Stage 2 tests' metrics for both B and C).
- `aggregate_rows.json` -- the flattened summary table used above.
- `scripts/` -- `lib.py`, `run_seed.py`, `aggregate.py`, `calibrate.py`,
  `calibrate_long.py`: the exact runnable code used to produce every number
  in this report, reproducible against the same bundle.

## Runtime and process status

Smoke seed: 22.9s wall. Each additional seed: ~13-15s. Total experiment
wall time (calibration + all 6 seeds + aggregation): approximately 3
minutes of actual simulation time across this session. No processes from
this experiment remain running -- every `python3` process this experiment
started (calibration scripts, `run_seed.py` x6, `aggregate.py`) completed
and exited before this report was written; confirmed via `ps -u cxiong`
immediately before finalizing.

Three unrelated processes were visible in that same check and are called
out here for transparency, none touched or interfered with:
`vlaunch`/`hermes chat` (already 24+ minutes old, not started by this
session), the usual VS Code IDE tooling, and a `python3 run_full_coverage.py`
process running from `/home/cxiong/codex-runs/codex2-phase35-full-decoder-
coverage` -- a directory this experiment never created or touched, started
independently at 10:50:52 (mid-way through this experiment's own run, by
coincidence). All Codex agents on this machine operate under the same
`cxiong` account, which is why it appears under a `ps -u cxiong` filter; its
working directory and independent start time confirm it belongs to Codex 2,
not to this experiment. Per instructions not to touch Codex 1 or Codex 2's
artifacts, it was left running and its directory was not inspected further.
