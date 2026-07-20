# Diff review: commit 4e712a4b7dea033b9191680a4b4e3577d93ca304

Base: `4764f1758a7399439df2242dfa60819501fc2333` (verified as the single, direct
parent -- `git log --pretty=%P -n1 4e712a4...` returns exactly that hash, no
merge commit).

## Bundle/checksum verification

- `sha256sum` of `phase35-gate-a-b-4e712a4b7dea033b9191680a4b4e3577d93ca304.bundle`
  matches the `.sha256` file on disk and the value given in the task,
  byte-for-byte: `656b3a63522ddcb5f9960765769f90e167c660fb9ea5f7bbdbb4feaa6e727685`.
- `git bundle verify` reports OK, ref `refs/heads/phase35-dendrite-classes-codex1`
  at `4e712a4b7dea033b9191680a4b4e3577d93ca304`, complete history.
- Cloned fresh into a disposable checkout at
  `/tmp/.../scratchpad/phase35-gate-ab-independent-checkout` (never touching
  Codex 1's own `repo/`/`baseline-repo/` directories).

## A dead-end worth documenting: the "same SHA, different tree" scare

Early in this review, `git ls-tree 4764f17...` gave a flat ~100-entry listing
in the original production repo but a single-entry `cipp-learning-AbhiCIPP/`
wrapper in the disposable checkout -- for the *same* 40-hex commit SHA. This
briefly looked like a SHA-1 collision / bundle-tampering signal. Fully
resolved and NOT a real issue: `/home/cxiong/others/cipp-learning-AbhiCIPP` is
not itself a git top-level; the real `.git` lives at `/home/cxiong/others/.git`,
one level up, with the whole project tracked as a `cipp-learning-AbhiCIPP/`
subdirectory of that repo. `git ls-tree` without `--full-tree` silently
restricts to the caller's cwd-relative path when invoked from inside a
subdirectory, which is what produced the flat listing. Confirmed via
`rev-parse --show-toplevel`, `fsck --full` (clean on both repos), and an
independent SHA-1 recomputation from the raw 49-byte tree object content
(`tree 40000 cipp-learning-AbhiCIPP\0<20 raw bytes>`) -- identical in both
repos. No corruption, no collision. All path references below are relative to
the true project root (`.../cipp-learning-AbhiCIPP/` inside whichever
checkout).

## File-level change summary (`git diff --stat`)

```
CLAUDE_HANDOFF.md     |  20 ++++
backend/simulation.py | 139 +++++++++++------------
snn/__init__.py       |   6 +-
snn/dendrite.py       | 158 +++++++++++++++++++++++++++
4 files changed, 254 insertions(+), 69 deletions(-)
```

Matches the claimed changed-file list exactly. `git diff --numstat` confirms
no binary entries (every file reports real add/delete line counts). No
`__pycache__`, `.venv`, `.pyc`, generated JSON/report artifact, or any file
outside these four appears anywhere in the diff. Clean.

## `CLAUDE_HANDOFF.md`

A 20-line addition, appended at end-of-file, documenting the branch,
base commit, the new class names, the retained `PC_i -> L1I_i -> L1E_i`
route, the Gate A/B pass counts, and the claim that "the same five
pre-existing numeric drifts" persist in the default-off golden comparison.
This is legitimate handoff documentation consistent with the repo's existing
convention (every prior phase appends a section here) -- not unintended
production content. One factual note: elsewhere in this review (see
`report.md`) I found the *broader* baseline claim ("35 passed... 1
pre-existing golden failure") to be incomplete -- 4 additional, genuine
regressions exist in `prediction_column_enabled=True` paths that this
CLAUDE_HANDOFF.md entry does not mention. The golden-failure claim
specifically (five numeric drifts, unchanged) IS independently confirmed
correct; the summary just doesn't cover the whole picture.

## `snn/dendrite.py` (new file, 158 lines)

`DendriteRole` (str Enum: BASAL/APICAL), `DendriticDelivery` (frozen
dataclass event record), `DendriteCompartment` (role, `delivery_step`,
`deliveries` list, `.deliver()`, `.active`, `.charge`, `.clear()`),
`DendriticConnection` (source, target compartment, weight, plastic flag),
`CoincidencePyramidalCell` (two compartments + an ordinary `Neuron` soma).

Key mechanics (see `report.md` for the full semantic analysis):

- `DendriteCompartment.deliver()` raises `RuntimeError` if called with a step
  different from one already held -- a real, falsifiable guard against
  cross-timestep state leakage, not a documentation-only claim.
- `CoincidencePyramidalCell.resolve_coincidence(step)` (lines 124-141):
  requires `basal.active and apical.active` AND both compartments'
  `delivery_step == step` before doing anything. If that gate fails, returns
  `False` with zero soma mutation. If it passes, captures
  `last_d_before_learning = self.apical.charge` *before* any weight update,
  checks `basal.charge + last_d_before_learning >= coincidence_threshold`,
  and if so (and not refractory) deposits exactly one `soma.threshold` unit
  of potential -- not the graded sum -- then defers to `soma.check_threshold()`.
- `clear_compartments()` genuinely resets `delivery_step = None` and empties
  `deliveries` -- verified both by reading the code and by the independently
  reproduced Gate A test `test_offsets_rejected_and_clearing`, which asserts
  `pc.basal.delivery_step is None` after `.update()`.
- No trace/eligibility state of any kind exists in this file. Compartments
  hold only the current step's physical deliveries.
- There is **no separate "maturity" parameter or constant anywhere in this
  file or in `backend/simulation.py`'s prediction_* config**. See
  `report.md` finding F2 for the consequence.

## `backend/simulation.py` (139 changed lines across 5 hunks)

1. Import line: adds `CoincidencePyramidalCell` from `snn`.
2. `_build_prediction_column_population`: replaces the old single
   `Neuron(n_inputs=N_OUT+1, ...)` per PC with `soma = Neuron(n_inputs=1,...)`
   wrapped in a `CoincidencePyramidalCell`, basal source `L1E{i}`, apical
   sources `L2E0..L2E{N_OUT-1}`, `basal_weight=prediction_lateral_weight`
   (150.0 default), `apical_weights=[prediction_feedback_init]*N_OUT` (50.0
   default), `coincidence_threshold=prediction_threshold` (500.0 default).
   Config defaults (`prediction_feedback_init=50.0`, `prediction_feedback_max
   =1200.0`, `prediction_learning_rate=0.15`, `prediction_threshold=500.0`)
   match the brief's five legacy candidate constants for everything **except**
   the standalone "maturity: 350" constant, which has no counterpart anywhere.
3. `_apply_prediction_column_learning`: rewritten to gate on
   `pc.basal.active and pc.apical.active`, then for each apical connection
   whose source was actually delivered this step, apply
   `growth = eta * (1 - w/w_max)**2; w = clip(w + growth, 0, w_max)` -- the
   same saturating quadratic family used elsewhere in this codebase (see
   `test_neuron.py`'s charge-based rule), and a genuinely different equation
   from Codex 2's oracle's linear `w_before + eta*sum(magnitude)` rule (see
   `report.md` section 9).
4. `step()`: delivery loop now calls `pc.deliver_basal`/`pc.deliver_apical`
   for all cells first, then a second loop calls `resolve_coincidence(t)`
   (captures the pre-learning snapshot and the fire decision) **before**
   `_apply_prediction_column_learning(pc)` is invoked -- correct causal
   ordering, confirmed by the independently-reproduced Gate B test
   `test_d_before_learning_and_next_coincidence_fire`.
5. **`_start_presentation` (around line 2940, new code, all `+` lines):**
   unconditionally rebuilds `l2e_to_pcol_queue`/`s_to_pcol_queue` as
   zero-filled deques and calls `pc.clear_compartments()` for every PC at
   every pattern/probe switch. The added comment literally reads "Never let a
   queued basal/apical pair cross a pattern or probe boundary." This is a
   direct, explicit implementation of the exact behavior the Phase 35 brief
   prohibits ("Do not reset, discard, relabel, or pattern-filter already
   scheduled events at a pattern boundary... Do not hide queue carryover by
   resetting or dropping events at switches"). See `report.md` finding F1 --
   this is the single most significant defect in the diff, and it is locked
   in by a passing Gate B test (`test_pattern_switch_discards_queued_
   compartment_events`) whose name states the discarding behavior as the
   intended, asserted-correct outcome.
6. `topology()`/`dynamic_state()`: additive-only diagnostic fields
   (`prediction_column` dict with ids/roles/decoder_shape/route,
   per-PC `basal_sources`/`apical_sources`/`coincidence_step`/
   `d_before_learning`). Pure telemetry, no behavioral effect -- confirmed by
   reading; nothing here is read back into any decision path.
7. `_all_weights`/decoder introspection: switched from indexing
   `pcol[i]._weights_array` to `pcol[i].decoder_weights` /
   `.basal_connection.weight`. This is the root cause of the `test_phase20_
   frozen_reconstruction.py` regression (see `report.md`) -- other,
   un-updated call sites elsewhere in the test suite still assume the old
   `_weights_array` shape (`N_OUT+1`) and now hit an `IndexError` against the
   new soma's `[1.0]`-shaped array.

## `snn/__init__.py`

Adds the four new names to the module's exports. Mechanical, no behavior
change beyond making the names importable.

## Cleanliness (review task item 3)

No cache files, `.venv` files, generated report/JSON outputs, or files
unrelated to the stated Phase 35 scope appear anywhere in the diff. The four
changed files are exactly the four claimed. Confirmed via `git diff
--numstat` (no binary rows) and `git diff --stat` (matches claim exactly).
