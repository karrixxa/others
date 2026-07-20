# Independent review: Codex 1's Phase 35 Gate A/B implementation

Reviewer: Claude (this session), read-only. Nothing under Codex 1's own
directories, the production repo, or Codex 1's live checkout was modified.
All work happened in a freshly cloned, disposable checkout built directly
from the supplied bundle.

## Verdict

**`MIXED`**

Bundle, checksum, and commit lineage all verify cleanly. The diff is
genuinely clean (exactly the four claimed files, no cache/binary noise).
Gate A (6/6) and Gate B (5/5) both independently reproduce exactly as
claimed, against real production code, not a parallel test-only model. But a
passing Gate B test locks in behavior that directly contradicts the
governing Phase 35 brief, the brief's "maturity" concept doesn't exist as an
independent gate in this implementation, and Codex 1's own baseline
classification is missing four genuine, reproducible regressions. None of
that regresses the default-off path. That combination of real, verified
strengths alongside real, verified defects is why this is `MIXED` rather
than a clean pass or a single-gate failure.

## 1. Bundle and checksum verification

`sha256sum` of the bundle matches both the `.sha256` file on disk and the
value given in the task, exactly:
`656b3a63522ddcb5f9960765769f90e167c660fb9ea5f7bbdbb4feaa6e727685`.
`git bundle verify` reports it as OK, containing exactly one ref
(`refs/heads/phase35-dendrite-classes-codex1` at `4e712a4b...`), with a
complete history.

## 2. Commit lineage and diff

`git log --pretty=%P -n1 4e712a4...` returns exactly one parent:
`4764f1758a7399439df2242dfa60819501fc2333` -- the stated base, no merge
commit. The full diff touches exactly `CLAUDE_HANDOFF.md`,
`backend/simulation.py`, `snn/__init__.py`, and a new `snn/dendrite.py` --
matching the claim exactly, with `git diff --numstat` confirming no binary
rows anywhere. Full analysis in `diff_review.md`.

One dead end worth flagging so it isn't rediscovered by someone else: early
in this review, the same base commit SHA appeared to resolve to two
different trees between the original repo and the disposable checkout --
briefly alarming, since that should be cryptographically impossible without
corruption or a deliberate collision. Fully resolved: it was a `git ls-tree`
cwd-restriction artifact (`/home/cxiong/others/cipp-learning-AbhiCIPP` is a
subdirectory of a repo rooted one level up, not a repo root itself), verified
away via `fsck --full` (clean in both repos) and independent SHA-1
recomputation from raw object bytes. No corruption, no tampering. Documented
in `diff_review.md` in case it saves someone else the same detour.

## 3. Cleanliness

No cache files, `.venv` artifacts, generated reports, or unrelated files
appear anywhere in the diff. Confirmed via `git diff --numstat`/`--stat`
matching the claimed file list exactly.

## 4. `CLAUDE_HANDOFF.md`

Appropriate documentation, consistent with this repo's existing per-phase
handoff convention (every prior phase appends a section here). Its specific
claim about the golden-equivalence result (five pre-existing numeric drifts,
unchanged) is independently confirmed correct. Its broader baseline
pass-count claim is not complete -- see section 5.

## 5. Baseline reproduction -- the most consequential finding

Running the full `test_*.py` suite plus `tests/golden/test_golden_equiv.py`
independently in the disposable checkout:

**Codex 1 claimed:** 35 passed, 3 environment-blocked, 1 pre-existing golden
failure (39 total).

**Independently reproduced:** 31 passed, 3 environment-blocked (same three:
`test_phase13b_tracer_timing.py`, `test_phase27_l2_ownership_causal_audit.py`,
`test_phase28a_local_common_input_feasibility.py` -- all `ModuleNotFoundError:
pytest`, an environment gap on this machine, not a code issue), 1
pre-existing golden failure (same 5/100 arrays, same drift values as the
independently-recorded Phase 29 base baseline from earlier in this
engagement), **and 4 new regressions Codex 1 did not report**:

- `test_phase20_frozen_reconstruction.py` -- `IndexError` at
  `e.pcol[4]._weights_array[j]`: the decoder array moved to
  `pcol[i].decoder_weights`, and this pre-existing caller wasn't updated.
- `test_phase21_selective_inhibition.py` -- an active pixel's L1I never
  fires at all ("over-suppression").
- `test_phase22_full_interaction.py` -- "PC should still fire for its own
  active pixels when combined" now fails.
- `test_prediction_column_phase19.py` -- expects a graded pre-threshold
  potential rise from a delayed delivery; the new gate is all-or-nothing
  (deposits exactly one `soma.threshold` unit only on a qualifying
  coincidence), so this assumption no longer holds.

Each of these was re-run in isolation with a 300-second timeout specifically
to rule out the kind of batch-run flakiness I saw earlier in this engagement
(where `test_prediction_column_phase19.py` looked like a failure in a
crowded batch but passed cleanly alone at the Phase 29 base) -- all four
reproduce deterministically every time, and all four are confirmed to have
passed at the `4764f17` base. All four exercise `prediction_column_enabled=
True` paths specifically; none reproduce with the flag off, so this is not a
default-off regression, but it is a real gap between what was reported and
what independently reproduces.

## 6. Gate A / Gate B independent reproduction

Copied `test_phase35_gate_a.py` and `test_phase35_gate_b.py` (from Codex 1's
artifact directory, since neither is part of the committed diff) into my own
disposable checkout and ran them there -- against my own clone, not Codex
1's live checkout. Both reproduce exactly as claimed: **Gate A 6/6, Gate B
5/5**, identical test names.

Both files import the real production modules directly
(`from backend.simulation import SimulationEngine`,
`from snn.dendrite import CoincidencePyramidalCell, ...`) and drive them
through their real public API (`.step()`, `.set_pattern()`,
`.deliver_basal()`, `.resolve_coincidence()`). No parallel test-only
reimplementation of the coincidence/decoder logic exists anywhere -- these
tests genuinely exercise the production implementation.

One of the five passing Gate B tests is itself a finding, not just a pass:
**`test_pattern_switch_discards_queued_compartment_events`** -- its own name
and assertion (`assert not any(e.spiked[f'PC{i}'] ...)` after a pattern
switch that had a coincidence already queued) lock in exactly the behavior
the brief prohibits. A green checkmark here is evidence of the defect, not
evidence against it.

## 7. Implementation review against the 15-item checklist

Full table with exact file/function locations in `results.json`
(`semantic_property_review`). Summary:

**Genuinely satisfied, independently verified:** explicit basal/apical
separation; compartments as explicit connection targets; same-delivered-step
coincidence gate; basal-alone and apical-alone producing zero effect
(including the crossing-event-doesn't-fire-next-one-does causal order);
absence of any trace/eligibility state that could fake a coincidence;
per-engine-step compartment clearing; ordinary `Neuron` untouched;
source/target-local decoder updates with byte-identical inactive weights;
exactly the three basal-active targets learning in the nine-target case.

**Partially satisfied / needs attention:**

- **`d_before_learning` maturity ordering** -- causal order (fire decision
  uses the pre-update value) is correct, but there is no independent
  "maturity" constant. `snn/dendrite.py:79` (`CoincidencePyramidalCell.
  __init__`) has only `coincidence_threshold`; the brief's 350-vs-500
  two-gate design is collapsed into one combined check
  (`basal.charge + apical.charge >= coincidence_threshold`,
  `backend/simulation.py`'s call into `resolve_coincidence`). With
  `prediction_lateral_weight` fixed at 150 and `prediction_threshold` at
  500, this happens to reduce to "apical weight >= 350" for a single basal
  signal of 1.0 -- reproducing the brief's own 349.9/350.0 example exactly
  (Gate B's `test_d_before_learning_and_next_coincidence_fire`) -- but that
  equivalence is an emergent consequence of `150 + 350 = 500` at these
  specific defaults, not a structurally independent, separately-tunable
  gate. Changing `prediction_lateral_weight` alone would silently move the
  effective maturity boundary.
- **No duplicate event delivery** -- confirmed for the tested case (an empty
  follow-up step doesn't re-fire), but every apical connection for one PC
  shares a single `DendriteCompartment`, and `.charge` sums across
  simultaneously-delivered sources. Two individually-immature decoders
  co-occurring in one step (a real reachable state, since the engine's own
  L2 competition allows multiple L2E winners in one step) could sum past
  threshold together. Gate A/B never construct this scenario in either
  direction, so it's an open question, not a confirmed defect.
- **Default-off equivalence** -- genuinely true (independently confirmed via
  the unchanged golden failure set), but not actually established by the
  test named for it (`test_default_off_equivalence` compares two engines
  that are already both `prediction_column_enabled=False`, since neither
  `DASHBOARD_PRESET` nor the class default turns it on -- closer to a
  determinism check than an old-vs-new comparison).

**Genuinely absent, as required:** no labels, owner locks, global loss,
argmax ownership, balanced initialization, or nonlocal normalization appear
anywhere in the diff.

**The one clear architectural defect:** queue carryover across a
pattern/probe switch is actively discarded (`backend/simulation.py`,
`_start_presentation`, ~line 2940) -- see section 6 and `diff_review.md`
for the exact code and the brief passage it contradicts.

## 8. Comparison with Codex 2's oracle

Read-only; `/home/cxiong/codex-runs/codex2-phase35-dendrite-oracle/` was not
touched. Three concrete, structural mismatches between what the oracle
validates and what the production code actually does (full detail in
`results.json.comparison_with_codex2_oracle`):

1. **Decoder update equation.** Oracle: linear,
   `d_after = min(d_max, d_before + eta*sum(magnitude))`. Production:
   saturating quadratic, `growth = eta*(1-w/w_max)**2`, matching this
   repo's existing charge-based rule family. These are different equations
   -- the oracle's numeric trajectory is not ground truth for the
   production decoder's actual values over time.
2. **Decoder key convention.** The standalone oracle review flagged (as
   finding F1 there) that the oracle keys `d[j,i]` by the *basal* event's
   source, per its own contract text, and that no test in the oracle could
   distinguish this from keying by the apical/feedback source, since only
   one feedback source is ever configured per run. Comparing against the
   real implementation resolves the ambiguity: production naturally keys by
   the apical/feedback source (`pc.apical_connections[j].source ==
   f'L2E{j}'`), matching the brief's own mapping. The oracle's convention
   does not match production.
3. **Coincidence/maturity structure.** The oracle implements the brief's
   literal two-gate design (a fixed `coincidence_charge` constant plus a
   separate `maturity` threshold tested against `d_before`) -- structurally
   closer to the brief's spec than the production implementation's single
   collapsed threshold (finding F2, section 7). Both happen to reproduce the
   same 349.9/350.0 numeric example under their own respective default
   parameterizations, but for different structural reasons.

Net: the production implementation should not be assumed validated by
Codex 2's oracle as it currently stands. The two disagree on the update
equation, the key convention, and the gating structure. The oracle also has
two vacuous checks (documented in its own standalone review) that production
happens to genuinely satisfy anyway (real compartment clearing, a real
same-timestep-conflict guard on delivery) -- so production isn't worse than
the oracle here, just different, and the mismatches need reconciling before
either artifact can certify the other.

## 9. Processes remaining

None from this review. `ps -u cxiong` shows no python or git process tied to
any checkout used here still running. (Unrelated, pre-existing IDE tooling --
a VS Code Python-environment helper and the Pylance language server -- were
observed in the process list; these belong to the user's editor session, not
this review, and were not started or touched by this work.)

## Artifacts

- `progress.md`, this `report.md`, `results.json`, `diff_review.md`,
  `test_log.txt` -- all under
  `/home/cxiong/codex-runs/claude-phase35-gate-a-b-review/`.
- Disposable checkout (not cleaned up, left for inspection):
  `/tmp/claude-275450548/-home-cxiong-others-cipp-learning-AbhiCIPP/55d19a97-a1ec-436c-ada9-dbb060f69996/scratchpad/phase35-gate-ab-independent-checkout/`
  (a `/tmp` scratch path scoped to this session).

No fixes were applied. No Gate C, ownership, or parameter-tuning work was
performed, per instructions.
