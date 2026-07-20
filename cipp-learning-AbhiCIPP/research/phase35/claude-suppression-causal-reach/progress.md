# Progress

- [x] Read `backend/simulation.py`'s complete `step()` function (lines
      ~2538-2923) before writing any tracing code, to establish the exact
      causal ordering rather than assume the task's proposed chain was
      literally same-step throughout.
- [x] Found and confirmed the real mechanism: `l1i_feedback_delay` is a
      one-step register (set at end of step t from that step's L1I fire,
      read at the start of step t+1's L1E processing) -- PC_i's suppression
      effect on L1E_i is inherently one step delayed, and L1E's resulting
      state feeds L2's feedforward drive in that same t+1 step.
- [x] Confirmed L1I's own accumulation requirement (weight below its own
      threshold after the mature-efficacy reshape; refractory=2, no leak)
      empirically produces a clean, near-exact 50/50 delivered/undelivered
      alternation on PC spike events.
- [x] Designed and built two explicitly separate analyses after recognizing
      a real confound: B's L1I is not silent (it receives the legacy global
      broadcast every step, more often than C's PC-driven path), so a naive
      B-vs-C comparison conflates "PC's specific effect" with "the whole
      regime differs." Analysis 1 (within-C matched comparison, using C's
      own natural delivered/undelivered split) isolates PC's causal
      contribution cleanly; Analysis 2 (B vs C) is kept for what it can
      legitimately answer and explicitly caveated.
- [x] Traced 6 clean-leader seeds (reused from the mature-efficacy
      experiment) -- identical results in every one: 100% sensory/L2
      blockade when delivered, 0% effect when not, zero ownership change.
- [x] Added a 7th seed (2) deliberately chosen for its persistent, exact
      two-way tie (identified in the mature-efficacy calibration log) to
      test whether suppression can redirect ownership under genuine
      competition, not just in the "walkover" clean-leader seeds. Result:
      both tied competitors blocked together, not selectively -- confirms
      the structural (not just "no competitor present") explanation.
- [x] Computed the requested aggregate fractions and traced them to an
      exact mechanistic cause (ff_vec driven to zero for all 3 active
      pixels together on delivered steps -- no partial/threshold-marginal
      case exists).
- [x] Surfaced and documented a needed correction to the prior mature-
      efficacy report: its "B_l1i_events=0" metric measured only selective
      delivery events, not total L1I activity -- B's L1I fires constantly
      via the legacy pathway. Does not change that experiment's verdict,
      but the specific number needed this caveat and now has it.
- [x] Selected and justified `SUPPRESSION_CHANGES_LATER_ACTIVITY_ONLY`
      against each of the other four specific-failure verdicts explicitly,
      with the reasoning for rejecting each.
- [x] Wrote `report.md`, `results.json`, this file, plus `per_seed/*.json`
      and `scripts/*.py` to
      `/home/cxiong/codex-runs/claude-phase35-suppression-causal-reach/`.
- [x] Confirmed no processes from this audit remain running.

Final status: complete. Verdict: `SUPPRESSION_CHANGES_LATER_ACTIVITY_ONLY`.

No production source was modified. Nothing pushed. Reused the existing
mature-efficacy checkout and construction code unchanged.
