# Phase 24 — Conditional Frequency Learning-Stop: GATED OFF

**Status: gate assessed, implementation NOT started. No new flag, no
learning-stop rule, no code change of any kind in this phase.**

## The gate

Phase 24 was explicitly scoped as: **"PROCEED ONLY IF Phase 23 establishes
a nontrivial frequency↔correct-prediction relationship. If gated off,
document why and stop that phase's implementation there — still commit a
report explaining the gate decision."**

## Why the gate fails

`Phase23_Frequency_Measurement_Report.md` established the opposite of what
would be needed to proceed:

1. **The known false-positive baseline (no prediction mechanism at all)
   sits closest to 0.5** (active-pixel mean frequency 0.528) — reconfirming
   Phase 17's already-documented false-positive risk.
2. **Genuine selective, PC-driven prediction (Phase 21's mechanism) sits
   FURTHER from 0.5** (0.834), not closer — a direct consequence of Phase
   21's own finding that selective inhibition delivers weaker overall
   suppression than the global baseline. A frequency-based stop rule keyed
   to "near 0.5" would trigger on the condition with NO real prediction and
   stay silent on the condition WITH real prediction — backwards from what
   the rule would need to do.
3. **Forcing an incorrect (wrong-pixel) prediction produces a frequency
   (0.854) statistically indistinguishable from correct prediction
   (0.834)** — frequency alone cannot discriminate correct from incorrect
   prediction sources at all, in either direction.

There is no nontrivial frequency↔correct-prediction relationship to build
a learning-stop rule on. Implementing one anyway would not be a neutral,
untested addition — it would very likely misfire in exactly the two ways
this phase's own instructions warn against: stopping learning during the
known false-positive (synchronized-suppression) regime, and/or failing to
stop (or incorrectly stopping) during genuine prediction, since the
underlying signal does not separate the two cases in the required
direction.

## Decision

**Do not implement any frequency-based learning-stop mechanism.** No new
flag is added. No engine or rule code changes in this phase. This is a
clean gate-off, not a deferred or partial implementation — revisiting it
would require a fundamentally different signal than raw firing frequency
(e.g. something that scales with `PCi`'s own decoder maturity or
per-synapse contribution, rather than a population-level rate, which is
closer to Phase 25's synapse-level scope — itself also gated, see
`Phase25_Synapse_Free_Energy_Gate_Report.md`).

## Commit

This report only. No production code, no tests beyond what Phase 23
already committed.
