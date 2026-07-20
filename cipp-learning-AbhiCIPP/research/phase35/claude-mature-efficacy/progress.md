# Progress

- [x] Built a standalone scratch clone from the repaired bundle
      (`db30cead...`), fully separate from Codex 1/Codex 2's directories
      and the production repo.
- [x] Caught and reversed an early misstep (a stray branch ref accidentally
      created in the production repo's own `.git` via `git fetch`) before
      any real work began; verified the production repo was back to its
      exact prior state.
- [x] Identified the exact existing config flags for each Stage 1
      requirement (decoder learning on, PC-to-I suppression off, passive
      soma decay off via the pre-existing `prediction_leak_diagnostic_
      disable` flag, loser depression off, global normalization off) --
      no production source changed, only constructor parameters chosen.
- [x] Calibrated a documented, evidence-based Stage 1 max horizon (20,000
      steps) via a short pilot, a 3-seed longer pilot, and an independent
      theoretical event-count derivation -- see `calibration_log.txt`.
- [x] Discovered and documented that natural single-L2-responder emergence
      is a minority outcome (11/40 seeds clean, 29/40 persistently,
      exactly tied) -- reported as a finding, and used to select seeds
      where "the natural L2 first responder" is unambiguous, as the task
      specifies.
- [x] Ran Stage 1 (natural maturation in shadow) for 6 seeds (smoke + 5),
      all reaching full 3-pixel maturity between steps 6122-6128, with
      full telemetry: responder history, decoder-update counts, per-pixel
      maturity times, inactive-pixel-unchanged confirmation, origin-class
      telemetry, first post-maturity PC spike.
- [x] Hit and solved a genuine independent finding: `CoincidencePyramidalCell`
      is not `copy.deepcopy`-safe (infinite recursion via its `__getattr__`
      delegation to `self.soma`) -- worked around entirely in the
      experiment harness (`clone_engine`/`_clone_pc` in `scripts/lib.py`),
      without touching `snn/dendrite.py`.
- [x] Solved a related structural issue: L1I's weight vector needed a
      correct shape (1-dim vs N_OUT-dim) once `prediction_column_to_i_
      enabled` differs between clones -- resolved by collapsing to the
      existing vector's own mean, documented as the one necessary
      non-attribute-flip adaptation.
- [x] Verified clone independence for all 6 seeds (step one clone, confirm
      the other's full state fingerprint is unchanged) -- ok=true in every
      case.
- [x] Ran all three Stage 2 tests (continued held presentation, one
      overlapping pattern switch, short interleaved four-pattern schedule)
      for both B (shadow) and C (active), for all 6 seeds -- 30-seed run
      never attempted, per instructions.
- [x] Confirmed decoder locality held (no inactive-pixel movement) through
      Stage 2's pattern-switch test in every seed before allowing the
      interleaved test to run.
- [x] Aggregated and analyzed results across seeds: found a consistent,
      reproducible 20% relative suppression effect (continued-held test),
      a smaller but real 3-4% effect (pattern-switch test), and a
      dramatic 60-100% PC/L1I event-count reduction (interleaved test),
      with zero measured novel-pixel over-suppression and no visible
      effect on L2 ownership/collision rates.
- [x] Wrote `report.md`, `results.json`, `calibration_log.txt`, this file,
      plus `per_seed/*.json`, `aggregate_rows.json`, and `scripts/*.py` to
      `/home/cxiong/codex-runs/claude-phase35-mature-efficacy/`.
- [x] Confirmed no processes from this experiment remain running.

Final status: complete. Verdict:
`MATURE_ACTIVE_SUPPRESSION_EFFECTIVE_BUT_OWNERSHIP_NEUTRAL`.

No production source was modified. Nothing pushed. Gate C, ownership
experiments, and 30-seed runs were explicitly out of scope and not
performed.
