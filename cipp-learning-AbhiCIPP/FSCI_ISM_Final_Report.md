# FSCI/ISM Investigation — Final Report

**Branch: `l2-ownership-recovery`. Starting SHA (Phase 27 checkpoint, this
investigation's baseline): `f09d8fe3f36cb76c67c081be5bf86c1c84cfe6bb`.
Ending SHA: `b0a10d7` (Phase 31/32) — see the Commits section for the exact
hash and every intermediate commit. Nothing pushed. `july14`,
`july14-integration`, and every backup branch untouched throughout.**

## Verdict: PARTIAL — do not promote the full circuit; the centered encoder alone is a defensible, isolated candidate

The FSCI/ISM investigation tested three coupled hypotheses in sequence,
each gated on the previous: (1) a centered/covariance sensory encoder to
stop unbounded universal-feature reinforcement; (2) an active,
non-cosmetic prediction/inhibition loop (`S_i/PC_i/I_i`) with a local
subthreshold decoder fixing the existing rule's cold-start plateau; (3) a
preregistered prediction-path membrane leak. **None of the explicit
success-gate criteria's hardest bars are met together** (four stable
first-responder owners; carryover materially below the documented ~2.9%;
realistic decoder maturation) — but two of the three component hypotheses
show real, honestly-earned, non-oversold partial support, and the
investigation correctly stopped rather than tuning parameters to force a
cleaner-looking pass.

## Gate-by-gate summary

### Gate 1 — centered/covariance encoder (Phase 29): PARTIAL PASS

The other session's own centered-encoder runs
(`/tmp/l2-commonness-budget-review/audit.py`) were permanently inaccessible
(isolated sandbox, confirmed gone even after completion) — implemented and
ran the exact specified rule from scratch instead, with preregistered
`alpha=1/80` (from Phase 28A's own independent, already-completed grid) and
`eta` = each neuron's existing `learning_rate` (no new free parameter).
30 seeds × 2 conditions (legacy/centered) × 2 schedules = 120 runs.

- Center/peripheral weight ratio: **78% reduction** on the interleaved
  schedule (7.68 → 1.66) — the exact targeted pathology, decisively fixed.
- Mean distinct owners and same-step ambiguity improve on BOTH schedules.
- Persistent-collision rate is slightly WORSE on interleaved (66.7% →
  73.3%) even as it improves on long-hold (43.3% → 26.7%) — mass shifts
  from severe collapse toward a 3-owner middle, not toward zero collisions.

**Decision: proceed** (the plan's own structure never expected the encoder
alone to solve ownership — it is one ingredient combined with prediction/
inhibition in conditions B–F).

### Gate 2 — engine flags promoted (Phase 30): PASS (implementation gate, not an empirical one)

Both `centered_encoder_enabled` and `prediction_subthreshold_decoder_enabled`
implemented as real, default-OFF `SimulationEngine` flags, byte-identical
when off (verified directly). 16 new tests (locality, coincidence
dependence, saturation, absence of unintended learning, mutual
exclusivity with the existing decoder rule). Full suite: 438 passed, 5
pre-existing failures, no new failures.

### Gate 3 — conditions A–F, full grid (Phase 31): the hardest bars are not met

30 seeds × 2 pattern permutations × 6 conditions × continuous-switching
interleaved schedule (15 cycles), 360 runs, all reported (see
`Phase31_32_FSCI_ISM_Conditions_AF_And_Leak.md` for the full table).

- **Ownership**: standard pattern set climbs A→F: 2.43 → 2.93 → 2.93 →
  2.93 → 2.97 → **3.13**/4. Shifted (permuted universal pixel): 1.17 →
  1.83 → 1.83 → 1.83 → **2.30** → 2.23/4. Active prediction (E/F) never
  destroys ownership relative to the encoder-only condition B, in EITHER
  pattern set — this specific success-gate criterion **passes cleanly**.
  But **no condition reaches four stable owners** in either pattern set —
  the single hardest success-gate bar **fails**.
- **Decoder maturation**: **0% of runs** show any PCi firing from feedback
  alone, in every condition, both pattern sets (after fixing a real
  methodology bug — see below). Realistic decoder learning does **not**
  mature within this grid's window — an honest negative, though the
  reduced cycle count (15 vs. Phase 19/20's 10,000–50,000-step runs) means
  genuine long-timescale maturation remains untested, not disproven.
- **Continuous-switch carryover**: shadow-mode conditions (C, D) land at
  2.9–3.5%, closely reproducing Phase 19's original 2.92% (a strong
  cross-phase consistency check). Active mode WITHOUT leak (E) explodes to
  25.9–27.4% — PCi fires on almost every step, a pathological runaway.
  Active mode WITH leak (F) returns to 2.9–3.0% — **statistically
  unchanged from the original ~2.9% baseline, not materially improved.**
  This success-gate criterion **fails**.
- **Permutation robustness**: the qualitative direction of every finding
  above survives the pixel-index permutation (universal pixel moved from 4
  to 0), but the magnitude is uniformly weaker for the shifted set (never
  exceeds 2.3/4 owners; persistent-collision rate never drops below 93%).
  Qualitative generalization: yes. Full magnitude robustness: no.

### Gate 4 — isolated leak factorial (Phase 32): decisive, standalone confirmation

A dedicated 2×2 (shadow/active PCi→Ii × leak off/on), 30 seeds each, 120
runs, kept fully separate from the A–F grid. Confirms independently: leak
OFF → ~100% PC spike rate and ~26–27% carryover in BOTH topologies; leak ON
→ carryover 2.9% in both, matching Phase 19 almost exactly. **Leak is
necessary to prevent catastrophic regression once PCi→Ii is activated, but
is not sufficient to improve carryover beyond the pre-existing baseline.**

## A real methodology bug found and fixed

`decoder_functional_check`'s original implementation used
`copy.deepcopy(engine)` to build an independent zero-input reconstruction
probe. **Python's `copy.deepcopy` does not duplicate closures** — an
already-instrumented (Phase 27 `CausalTracer`-patched) engine's `.step`
(and each L2E's `.fire`) survive a deepcopy as the SAME closure object,
which still operates on the ORIGINAL engine. The naive probe was silently
stepping the live, real engine instead of an isolated copy — confirmed
directly (`probe.step is engine.step` → `True`). This produced a spurious
"PCi reconstructed from feedback alone" result even though the decoder
weights were, numerically, barely different from their initialization
value — the tell that caught the bug. Fixed with `_unpatched_deepcopy`
(strips the instance-level monkeypatch overrides post-copy) plus an
explicit membrane-potential and delivery-queue reset before the zero-input
phase begins (eliminating leftover live-run charge as a confound). Locked
in with 6 dedicated regression tests. This is the single most important
correctness finding of this investigation's tooling — without it, the
grid would have reported a false positive for decoder maturation in
exactly the two conditions (E, F) most central to the whole plan's
narrative.

## What is NOT tested / genuine open gaps

- **Long-timescale decoder maturation** (Phase 19/20's original
  10,000–50,000-step scale) — this grid used 15 cycles (~1,200 steps) for
  tractability across a 360-run × 2-permutation grid; whether the
  subthreshold rule outperforms the existing spike-gated rule at a longer
  timescale is a genuinely open, falsifiable, and directly testable
  follow-up.
- **"Familiar inputs produce lower residual activity than novel inputs"**
  and **"a novel pattern retains prediction error and can recruit spare
  capacity"** — not directly measured in this checkpoint's grid (no novel-
  pattern probe was built into the A–F harness); Phase 16/22 already
  established spare-capacity recruitment generally, but not re-verified in
  this specific configuration.
- **A dedicated "suppression precision" metric** (does prediction
  selectively suppress explained columns without suppressing wrong/inactive
  ones) is only indirectly inferable from the carryover precision numbers
  (~96–97% even at F), not a standalone measurement.

## Recommendation

**Do not promote conditions E/F (the full active circuit) as a new
default.** The hardest, most load-bearing success-gate criteria (four
stable owners; material carryover improvement; realistic decoder
maturation) are not met, and per the explicit instruction not to tune
parameters or add mechanisms merely to force success, no further parameter
search was performed to manufacture a cleaner pass. **The centered encoder
(condition B) is the one component with unambiguous, large, mechanism-
confirming support** (the 78–90% center/peripheral ratio reduction is
real and reproducible across two independent grids — Phase 29 and Phase
31) and remains a defensible candidate for a narrower, future promotion
decision on its own, separate from the full prediction/inhibition circuit.
The next smallest falsifiable step, if this investigation continues, is
the long-timescale decoder-maturation follow-up identified above — not a
parameter retune of `alpha`/`eta_sub`/the leak time constant on the
existing short-window grid.

## Commits (this investigation, `l2-ownership-recovery`, base `7dc6f4f`)

```
f09d8fe  Phase 27: L2 ownership causal audit (measurement only)               [pre-existing baseline]
4c3edbe  Phase 28A: local common-input feasibility -- NEGATIVE result, no Phase 28B
4764f17  Phase 29: FSCI/ISM centered/covariance encoder ownership gate -- partial pass
32e063c  Phase 30: promote centered encoder + subthreshold decoder to real engine flags
b0a10d7  Phase 31/32: FSCI/ISM conditions A-F full grid + isolated leak experiment
```

## Test results

Full suite (final, at this report's checkpoint): re-confirmed clean, same
5 pre-existing failures throughout Phases 29–32 (`test_assembly_flow_
credit.py::test_integration_four_pattern_regime_is_active_and_bounded`,
`test_flow_rate.py::test_flow_off_is_baseline`, `test_flow_rate.py::
test_flow_builds_charge_smoothly`, `test_flow_rate.py::test_flow_can_
cross_threshold_without_new_input`, `test_flow_rate.py::test_flow_forces_
single_chunk`) — present since before Phase 6, unrelated to this
investigation, unchanged. See `FSCI_ISM_Final_Report.json` for the exact
final pass/fail count and per-phase test-file breakdown.

## Machine-readable data

`FSCI_ISM_Final_Report.json` — starting/ending SHAs, every condition's
full kwargs, all 480 per-seed outcomes (360 A–F + 120 leak), the
methodology-bug fix, test results, and this same verdict in structured
form. Full per-seed raw data: `phase31_fsci_ism_conditions_af_results.json`,
`phase32_leak_isolated_experiment_results.json`,
`phase29_centered_encoder_ownership_gate_results.json`.
