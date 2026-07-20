# Pre-inhibition race timing-decomposition progress

- Reused the five completed source-fragmentation traces; production was not run.
- Verified all 120 race-involved fragmenting credits join to responder,
  contributor, threshold-crossing, scheduling, delivery, target-membrane, and
  rebound timestamps.
- Decomposed 104 genuine rival/secondary credits; retained 16 first-responder
  credits as `AMBIGUOUS_OR_MIXED` rather than inventing a rival interval.
- Primary intervals: accumulation 104, delivery delay 0, post-inhibition
  residual 0, ambiguous/mixed 16.
- Offline decomposition runtime: 0.99 seconds.
- Validation passed for all 120 event records.
- Source checkout remained clean. No production edit, rerun, commit, or push.

Verdict: `ACCUMULATION_WINDOW_DOMINATES`
