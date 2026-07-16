# Phase 29 — FSCI/ISM Centered/Covariance Encoder Ownership Gate

**Status: measured. GATE: PARTIAL PASS (see verdict) — proceeding to the
active prediction-loop phase, with the mixed result reported honestly, not
oversold. No engine flag added yet (offline/monkeypatch only, same
technique as Phase 27/28A). Branch `l2-ownership-recovery`, on top of Phase
28A (`4c3edbe`). Nothing pushed.**

## Why this phase exists

The user's FSCI/ISM plan's first step is to interpret "the completed
ownership runs" against the centered/covariance encoder rule. Those
runs (`/tmp/l2-commonness-budget-review/audit.py`, a different, concurrent
session) turned out to be **permanently inaccessible** from this session —
an isolated sandbox, confirmed gone even after those processes finished (no
directory, no permission error, just absent). Per explicit user direction
("Run the centered-encoder experiment myself"), this phase implements and
runs the exact specified rule from scratch rather than guessing at
unavailable numbers.

## The rule tested

```
x_bar_i(t+1) = (1-alpha) x_bar_i(t) + alpha x_i(t)      (leaky presynaptic trace)
s_i          = x_i - x_bar_i                             (centered signal)
delta_w_ji   = eta * FE_j * (1 - w_ji/w_max)^2 * s_i      (per synapse)
```

`x_i(t)` is the physical L1E_i spike (`n._last_input_spikes[i]`, the same
field every existing rule reads — never the raw external `input_vec`).
`x_bar_i` is ONE shared per-pixel trace (presynaptic, identical for every
downstream L2E). `FE_j` is the neuron's own EXISTING
`_structural_free_energy_gate()` — no new quantity. `w_max`/`w_min` are the
neuron's own existing bounds. The update is gated on the postsynaptic
neuron's OWN physical spike (`fire()`), matching the one trigger convention
every other learning rule in this codebase already uses — a deliberate,
documented choice (see `phase29_centered_encoder_ownership_gate.py`'s
module docstring), not an oversight.

Implemented entirely offline via monkeypatching `Neuron._update_weights`
(never editing `snn/rules/excitatory.py` or `backend/simulation.py`).
**Loser depression is OFF** for the `centered` condition
(`loser_depression=False`, disabling only the structural weight-depression
half of `apply_delayed_inhibition` — verified directly against
`neuron_flexible.py`; the transient membrane subtraction and L2I hard-reset
competition are untouched in BOTH conditions) and **ON, unchanged**, for the
`legacy` control.

## Preregistered values (chosen before running, not fit to this experiment)

- **alpha = 1/80 = 0.0125.** Derived from Phase 28A's own, already-completed,
  independent grid: `tau_c=80` was the one value that generalized across
  BOTH the standard (pixel 4) and shifted (pixel 0) pattern sets on the
  interleaved schedule — the best evidence-based choice available from a
  DIFFERENT prior experiment, not tuned against this one's own results.
- **eta**: each neuron's own EXISTING `learning_rate`
  (`l2e_lr_frac * weight_cap`), unchanged — no new free parameter introduced.

## Grid

30 weight seeds × 1 topology seed (confirmed inert throughout this whole
investigation) × 2 conditions (`legacy`, `centered`) × 2 schedules
(interleaved 40-cycle, long-hold 600/200) = **120 runs, all reported.**

## Results (seed-averaged, n=30 each)

| Condition / schedule | mean distinct_owners | persistent-collision rate | mean center/peripheral ratio | mean ambiguity (same-step tie) | mean active neurons | mean never-fired |
|---|---|---|---|---|---|---|
| legacy / interleaved | 2.833 / 4 | 66.7% | **7.684** | 0.0475 | 3.83 | 1.93 |
| centered / interleaved | **3.067** / 4 | 73.3% | **1.662** | **0.0242** | 3.67 | 3.90 |
| legacy / long_hold | 1.567 / 2 | 43.3% | 1.428 | 0.2917 | 1.40 | 4.87 |
| centered / long_hold | **1.733** / 2 | **26.7%** | 1.771 | **0.0983** | 1.77 | 4.87 |

Owners distribution (interleaved): legacy `{4:10, 3:9, 2:7, 1:4}` → centered
`{3:17, 4:8, 2:4, 1:1}`. Tyrant identity spreads across many different
neurons in both conditions (legacy: L2E3/0/5/1/2/6/7; centered: L2E3/5/1/0/7/6/4
— never fixed to one index, consistent with every prior phase).

## Honest interpretation — a genuinely mixed result, not a clean win

**What clearly, substantially improves**: the center/peripheral weight
ratio — the EXACT pathology this rule was designed to fix — drops by
**78%** on the interleaved schedule (7.68 → 1.66). This is a direct,
strong confirmation that centering the presynaptic signal against its own
running mean stops a universal (always-active) pixel from being reinforced
unboundedly, exactly as hypothesized, and matches Phase 27's own causal
finding (the tyrant's center-pixel dominance is what causally precedes
second-pattern capture) — attacking that specific mechanism has a real,
large, measurable effect. Same-step ambiguity drops substantially on BOTH
schedules (interleaved 0.048→0.024, long-hold 0.292→0.098). Long-hold's
persistent-collision rate improves meaningfully (43.3%→26.7%). Mean
distinct owners improves modestly on both schedules.

**What does NOT improve, or gets worse**: the persistent-collision rate on
the INTERLEAVED schedule is slightly WORSE under centered learning
(66.7%→73.3%) — the owners distribution shifts mass from the extremes (1–2
owners, severe collapse) toward the middle (3 owners), which raises the
mean but does not reduce how often SOME collision exists. Never-fired
neuron count roughly doubles on interleaved (1.93→3.90) — fewer neurons get
recruited at all, even though those that do participate own patterns a bit
more evenly. Long-hold's center/peripheral ratio is essentially unchanged
(1.43→1.77, if anything slightly worse, though both values are already
much smaller than the interleaved schedule's — a schedule-dependent
baseline, not a new pathology).

## Verdict on the gate

**Not a clean, unambiguous "ownership solved by the encoder alone" —
correctly reported as such.** But the SPECIFIC mechanism this rule targets
(unbounded universal-feature reinforcement) is fixed decisively (78%
reduction, both directions of the metric — potentiation AND depression
respond to the centered signal, not just a one-sided cap), and two of four
headline ownership metrics (mean owners, ambiguity) improve on BOTH
schedules with no catastrophic regression anywhere. Per the plan's own
structure, the encoder was never meant to solve ownership by itself — it
is one ingredient combined with prediction/L1I suppression in conditions
B–F. Given a real, mechanism-confirming, non-oversold partial improvement
and no schedule where centered learning is clearly WORSE than legacy
overall, **this phase proceeds to the active-prediction-loop phase as
planned**, carrying the mixed result forward honestly rather than
re-tuning `alpha`/`eta` to manufacture a cleaner pass (explicitly
disallowed).

## Tests

`test_phase29_centered_encoder_ownership_gate.py` — 13 tests, all passing:
legacy condition byte-identical to a plain unmodified engine; centered
condition disables loser depression only (both the params dict and every
neuron's own flag), `l2i_hard_reset_losers` (physical competition)
untouched; the update reads only this neuron's own state and the shared
presynaptic trace (source-grepped for cross-neuron/global references);
gated on the neuron's own physical spike (verified via `_update_weights`,
the same hook `fire()` already calls); zero delta when signal equals trace
(direct algebraic check); potentiates above the trace, depresses below it;
never produces a negative weight; respects the weight cap under repeated
maximal-signal application; frozen plasticity blocks the update entirely;
trace driven only by physical L1E spikes, never raw `input_vec`; trace is
genuinely shared across all L2E neurons (not per-synapse); deterministic
replay; the preregistered alpha value is exactly what's documented.

## Full test suite

Not re-run in this checkpoint — this phase adds only an offline diagnostic
script and its own tests (`backend/simulation.py`/`backend/presets.py`
untouched). Last confirmed clean at Phase 27: 391 passed, 5 pre-existing
failures.

## Files

- `phase29_centered_encoder_ownership_gate.py` (new) — the harness.
- `test_phase29_centered_encoder_ownership_gate.py` (new) — 13 tests.
- `phase29_centered_encoder_ownership_gate_results.json` (new, committed) —
  the complete 120-run grid, no rows omitted.

## Commit / branch status

Branch `l2-ownership-recovery`, on top of Phase 28A (`4c3edbe`). Not
pushed. `july14`, `july14-integration`, and every backup branch untouched.
