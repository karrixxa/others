# Phase 35 source-fragmentation audit progress

- Created a separate detached clean checkout at
  `db30ceadbe18cf90e01f6d54dee0203f342b24a8`.
- Verified shadow-only prediction-column topology: decoder enabled,
  `prediction_column_to_i_enabled=False`, and no synapse with a PC source.
- Verified passive signed depression, loser depression, positive-weight budget,
  homeostasis, and confidence/global consolidation controls are off.
- Smoke seed 0 passed over 80 steps and reproduced 3-source peripheral and
  6-source center fragmentation.
- Completed seeds 1–5, 12,800 steps and 640 equal-interleaved presentations
  each. Total measured runtime: 134.90 seconds.
- Recorded 3,200 presentation traces and 93,318 decoder-update traces.
- Validated every fragmenting new-source event has an allowed causal
  classification; integrity check passed.
- Re-ran the repaired Phase 35 conformance regression: 2/2 pass.
- Repository remained clean. No production edit, commit, push, paired-path
  reconstruction, label, lock, or manual maturity operation occurred.

Verdict: `FRAGMENTATION_FROM_PRE_INHIBITION_RACE`
