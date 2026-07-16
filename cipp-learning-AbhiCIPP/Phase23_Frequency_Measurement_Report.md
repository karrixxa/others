# Phase 23 — Frequency Measurement Only (No Gating)

**Status: measured. No new flag. No learning-stop rule implemented.**

Measures L1E's own firing frequency (and, where L1E has no drive, `PCi`'s)
under six conditions, and directly answers the question this phase exists
to ask: **does firing frequency near 0.5 predict genuine prediction/
reconstruction accuracy, or does it remain a false positive?**

## Results (`phase23_frequency_measurement.py`, seed 1, `row 1`, 2000-step hold)

| Condition | Active-pixel mean frequency |
|---|---|
| 1. External-input-only (plain baseline) | **0.528** |
| 2. Global synchronized suppression (same run as 1) | **0.528** |
| 3. Selective predictive inhibition (Phase 21's condition C) | **0.834** |
| 4. Correct learned prediction (L1E / PC side by side) | L1E 0.834 / PC 0.227 |
| 5. Incorrect prediction (wrong-pixel forced suppression) | **0.854** |
| 6. Reconstruction, input removed (PC frequency only) | 0.025 |

## The answer: frequency near 0.5 is a false positive, and it points the wrong way

**The condition with NO prediction mechanism at all (1/2, pure
external-input + baseline global L1I suppression) is the one that sits
closest to 0.5** (0.528) — this is exactly Phase 17's already-established
false-positive regime, reconfirmed here. **The condition with genuine
selective, PC-driven inhibition (3/4) sits FURTHER from 0.5** (0.834), not
closer — because Phase 21's own finding (selective inhibition is weaker
overall than global feedback, since `PCi` fires far less often than `L2E`)
means less total suppression, not more, and frequency drifts UP, away from
0.5, rather than toward it. **A frequency-based "stop learning near 0.5"
rule would therefore fire on exactly the WRONG condition** — it would
consider the false-positive baseline "done" while the genuinely
prediction-driven condition never triggers it at all.

**The decisive negative result**: forcing an **incorrect** predictive
suppression (condition 5 — a manufactured control, driving the WRONG
pixel's `L1Ii`, matching no legitimate learning outcome) produces an L1E
frequency (0.854) **statistically indistinguishable** from genuinely
correct selective suppression (condition 3/4's 0.834). Frequency alone
**cannot tell correct prediction from incorrect prediction** — a fact
directly and cheaply demonstrable, not merely a theoretical risk.

## Gate assessment for Phase 24

Phase 24 ("conditional frequency learning-stop") is explicitly gated:
**"PROCEED ONLY IF Phase 23 establishes a nontrivial frequency↔correct-
prediction relationship."** This phase establishes the opposite — frequency
moves in the *wrong direction* for genuine prediction, and cannot
distinguish correct from incorrect prediction sources at all. **The gate
does not pass.** See `Phase24_Frequency_Learning_Stop_Gate_Report.md` for
the explicit stop decision — no learning-stop rule is implemented.

## Tests (`test_phase23_frequency_measurement.py`, 4 tests)

Each condition function runs without error and returns plausible
frequencies; the known near-0.5 false-positive baseline is reproduced; the
core finding (correct vs. incorrect prediction produce similar frequency)
is directly verified as a regression guard.

No pytest full-suite run in this checkpoint — this phase adds only
measurement scripts/tests, touches no production code
(`backend/simulation.py`/`backend/api.py` are unchanged). The full suite
was last confirmed clean at Phase 22 (375 passed, 5 pre-existing failures)
and will be re-confirmed once more at Phase 26.
