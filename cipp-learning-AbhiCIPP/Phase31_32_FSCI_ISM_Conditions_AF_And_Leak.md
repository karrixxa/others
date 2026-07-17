# Phase 31/32 — FSCI/ISM Conditions A–F and Isolated Leak Experiment

**Status: measured. GATE ASSESSED (see the consolidated `FSCI_ISM_Final_Report.md`
for the overall verdict). Branch `l2-ownership-recovery`, on top of Phase 30.
Nothing pushed.**

## Conditions (explicit, per the FSCI/ISM plan)

| Cond | Encoder | Loser dep. | Decoder | PCi→Ii | PC leak |
|---|---|---|---|---|---|
| A | legacy signed-spike | ON | none | — | — |
| B | centered | OFF | none | — | — |
| C | centered | OFF | existing spike-gated | shadow (off) | ON |
| D | centered | OFF | new subthreshold | shadow (off) | ON |
| E | centered | OFF | new subthreshold | **active** | **OFF** |
| F | centered | OFF | new subthreshold | **active** | **ON** (preregistered default 0.3) |

"Shadow mode" = `prediction_column_to_i_enabled=False` (PCi learns/fires;
output never reaches Ii). E/F are the proposed full circuit; C/D are
ablations isolating decoder learning from suppression.

## Grid

30 weight seeds × 1 topology seed × 6 conditions × 2 pattern permutations
(`standard`, universal pixel 4; `shifted`, pixel 0↔4 swap) × continuous-
switching interleaved schedule (15 cycles, no boundary resets) = **360
runs, all reported.** `INTERLEAVED_CYCLES=15` (vs. Phase 27's 40) is a
documented tractability reduction applied identically to every condition/
pattern-set/seed — see the honest caveat on decoder maturation below.

## A real bug found and fixed mid-phase

`decoder_functional_check`'s first version used a naive `copy.deepcopy(engine)`
to build an independent zero-input probe. **`copy.deepcopy` does not
duplicate Python closures** — an instrumented engine's `.step` (and each
L2E's `.fire`, patched by Phase 27's `CausalTracer`) survives a deepcopy as
the SAME closure object, which still operates on the ORIGINAL engine, not
the copy (confirmed directly: `probe.step is engine.step` → `True`).
Stepping the "probe" was silently mutating the live engine. Fixed with
`_unpatched_deepcopy`, which strips the instance-level monkeypatch
overrides off the copy only (falling back to the class's true methods),
plus explicitly resetting every L1E/L2E/PCi membrane potential to resting
and draining both PC delivery queues before the zero-input phase begins
(residual carried-over charge was producing spurious "fired from feedback
alone" results even though the decoder weights were numerically almost
unchanged from init — the tell that caught the bug). Locked in by 6
regression tests in `test_phase31_fsci_ism_conditions_af.py`.

## Results (seed-averaged, n=30 each)

| pattern/cond | owners /4 | persist. collision | center/periph. ratio | carryover rate | decoder fired feedback-alone | never-fired |
|---|---|---|---|---|---|---|
| standard/A | 2.43 | 0.83 | 8.057 | — | — | 1.93 |
| standard/B | 2.93 | 0.87 | 1.610 | — | — | 3.90 |
| standard/C | 2.93 | 0.87 | 1.610 | 0.030 | 0.00 | 3.90 |
| standard/D | 2.93 | 0.87 | 1.610 | 0.029 | 0.00 | 3.90 |
| standard/E | 2.97 | 0.80 | 1.093 | **0.259** | 0.00 | 3.93 |
| standard/F | **3.13** | **0.77** | 0.948 | 0.029 | 0.00 | 3.83 |
| shifted/A | 1.17 | 1.00 | 10.893 | — | — | 1.90 |
| shifted/B | 1.83 | 1.00 | 1.747 | — | — | 4.00 |
| shifted/C | 1.83 | 1.00 | 1.747 | 0.035 | 0.00 | 4.00 |
| shifted/D | 1.83 | 1.00 | 1.747 | 0.033 | 0.00 | 4.00 |
| shifted/E | 2.30 | 0.93 | 1.397 | **0.274** | 0.00 | 3.97 |
| shifted/F | 2.23 | 0.93 | 1.141 | 0.030 | 0.00 | 3.67 |

## Phase 32 — isolated leak factorial (dedicated, separate from A–F)

A clean 2×2 (PCi→Ii shadow/active × PC leak off/on), 30 seeds each, using
the SAME already-existing `prediction_leak`/`prediction_leak_diagnostic_
disable` mechanism (no second, inconsistent leak equation introduced):

| Condition | leak value | mean carryover rate | mean total PC spikes (of ~1200 steps) | mean owners |
|---|---|---|---|---|
| shadow, leak OFF | 0.0 | **0.270** | 1194.4 | 2.93 |
| shadow, leak ON | 0.3 | 0.029 | 314.7 | 2.93 |
| active, leak OFF | 0.0 | **0.259** | 1333.5 | 2.97 |
| active, leak ON | 0.3 | 0.029 | 533.8 | 3.13 |

## Honest interpretation

**Leak is necessary but not sufficient.** Without it (leak OFF), PCi fires
on essentially every single step (1194–1334 out of ~1200) regardless of
shadow/active topology — a pathological runaway, exactly reproducing
Phase 19's own "no-leak diagnostic" failure mode in this new architecture.
With leak ON (the existing, preregistered default), the carryover/false-
prediction rate drops to **0.029–0.035 across every condition that has it
on (C, D, F, and both Phase 32 leak-on cells)** — this is statistically
indistinguishable from Phase 19's originally documented **2.92%**. **Leak
prevents catastrophic regression but does NOT improve carryover beyond the
already-documented baseline.** This is a direct, decisive answer to one of
the FSCI/ISM success-gate criteria (see the final report): the criterion
requiring carryover to "materially improve from the documented ~2.9%" is
**not met**.

**Ownership**: the centered encoder (A→B) produces the single largest
jump in both pattern sets (standard 2.43→2.93; shifted 1.17→1.83, a
near-complete collapse recovering to a mid-range value). Active
prediction (D→E→F) adds a further, real but modest improvement on top —
critically, **it never destroys ownership relative to B** in either
pattern set (standard: 2.93→2.97→3.13; shifted: 1.83→2.30→2.23) — this
success-gate criterion **is met**. No configuration reaches the required
"four stable owners across the seed set" bar in either pattern set,
though: standard tops out at 3.13/4 (F), shifted at 2.30/4 (E).

**Decoder maturation**: after the bug fix, **0% of runs show PCi firing
from feedback alone**, in every condition, both pattern sets — neither the
existing spike-gated decoder (C) nor the new subthreshold coincidence rule
(D) matures within this grid's 15-cycle (~1,200-step) window. This is an
honest negative, consistent with (and independently reconfirming) Phase
19/20's own finding that decoder weights plateau under realistic training
— **but this grid's reduced cycle count (vs. Phase 19/20's 10,000–50,000-
step runs) means this specific result should not be read as "the new rule
definitely does not help maturation at all," only "it does not mature
within this shorter, tractability-driven window."** A longer, dedicated
follow-up run at Phase 19/20's original scale is the natural next step to
resolve this ambiguity, not attempted here to keep the 360-run × 2-pattern-
set grid tractable in this session.

**Permutation (standard vs. shifted)**: the qualitative pattern —
centered encoder helps most, active prediction adds a modest further
gain, leak prevents runaway but doesn't improve the baseline carryover —
survives the pixel-index permutation. The absolute numbers are uniformly
worse for `shifted` (never exceeding 2.3/4 owners, persistent-collision
rate never below 0.93), showing the mechanism generalizes in *direction*
but the *magnitude* of ownership recovery is index-dependent, not fully
robust.

## Tests

`test_phase31_fsci_ism_conditions_af.py` — 6 tests, all passing: documents
the deepcopy-closure bug directly; confirms the fix produces a genuinely
independent probe that preserves weights/state; confirms
`decoder_functional_check` never mutates the original engine; confirms the
residual-charge reset actually prevents the spurious-firing false positive
(forces a PC's membrane far above threshold immediately before the check
and confirms the reset zeroes it before probing); confirms all six
conditions' kwargs are explicit and mutually distinguishable, and that A is
byte-identical to `DASHBOARD_PRESET`.

## Full test suite

**438 passed, 5 pre-existing failures** (confirmed at Phase 30's checkpoint,
unchanged by Phase 31/32 — these phases add only diagnostic scripts and
their own tests, no further engine changes).

## Files

- `phase31_fsci_ism_conditions_af.py` (new) — the A–F harness.
- `phase32_leak_isolated_experiment.py` (new) — the dedicated leak 2×2.
- `test_phase31_fsci_ism_conditions_af.py` (new) — 6 regression tests.
- `phase31_fsci_ism_conditions_af_results.json` (new, committed, ~2.6MB) —
  all 360 runs.
- `phase32_leak_isolated_experiment_results.json` (new, committed, ~1MB) —
  all 120 runs.

## Commit / branch status

Branch `l2-ownership-recovery`. Not pushed. `july14`, `july14-integration`,
and every backup branch untouched.
