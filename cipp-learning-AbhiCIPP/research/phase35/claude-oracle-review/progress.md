# Progress

- [x] Confirmed read-only scope: did not modify anything under
      codex2-phase35-dendrite-oracle/, the production repo, or Codex 1's
      checkout. All output written only to this directory.
- [x] Read semantic_contract.md, reference_oracle.py, golden_cases.json,
      results.json, report.md in full.
- [x] Reproduced golden_cases.json and results.json independently from a
      scratch copy of reference_oracle.py (module import only, main() never
      invoked) -- byte-identical / matching counts, confirms artifacts are
      current and deterministic.
- [x] Probed live (against the scratch copy, not the original) whether
      Event.deferred affects simulate() output -- it does not.
- [x] Probed live whether two distinct basal events landing on the same
      target/timestep get deduplicated -- they do not; both pair with the
      apical event and both apply a decoder update to the same key.
- [x] Built a requirement-by-requirement coverage table against the 13
      checklist items, distinguishing independently-cross-checked coverage
      from self-referential (golden-file-only) coverage from vacuous/
      tautological checks from untested gaps.
- [x] Identified 5 concrete findings (F1-F5) with line numbers, severity,
      and recommendations.
- [x] Wrote report.md, coverage_review.json, progress.md to
      ~/codex-runs/claude-phase35-oracle-review/.

Final status: complete. Verdict: `ORACLE_VALID_WITH_COVERAGE_GAPS`.

No tests were added, no fixes were applied, per instructions -- gaps are
reported for Codex 2 or Codex 1 to address later.
