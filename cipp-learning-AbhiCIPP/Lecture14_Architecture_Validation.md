# Lecture 14 Architecture Validation — Final Consolidated Report (Phases 18–26)

**Branch: `july14-integration`. All work committed locally; nothing pushed.
Base branch `july14` untouched throughout.**

This report consolidates the full LPS Lecture 14 architectural
investigation, from the initial corrected-topology contract through every
gated/implemented phase. It states plainly what was built, what worked,
what didn't, and what remains default OFF.

## Architecture actually implemented

The final, transcript-faithful topology (`Phase18b_Lecture14_Local_
Coincidence_Architecture_Contract.md`): nine per-input-column S_i/PC_i/I_i
triplets.

- **`PC0`–`PC8`** (`prediction_column_enabled`, Phase 19): one prediction
  neuron per input column. Fixed local `S_i → PCi` lateral coincidence
  weight (never learned) plus a learned all-to-all `R_j → PCi` feedback
  matrix. Both afferents are **queued together and delivered together
  exactly one step later** — no same-step delivery of either pathway (a
  same-step lateral connection is not physically available in this
  engine's `step()` ordering without contaminating the sensory evidence
  that produced the `L2E` response). Decoder learning fires only on `PCi`'s
  own physical spike, and additionally requires the delivery's own `S_i`
  eligibility component to have been active — physical firing and decoder
  learning are deliberately decoupled, so mature feedback-only firing
  (input-free reconstruction) remains possible without being mistaken for
  evidence that a pixel was truly present.
- **`PCi → Ii`** (`prediction_column_to_i_enabled`, Phase 21): the first
  wiring where `PCi`'s own output affects any other neuron. Replaces
  `L1Ii`'s global N_OUT-wide `L2E` broadcast with a single input from its
  own paired `PCi`.
- **`pretrained_l1i_regulation`** (Phase 21): fixed vs. learned `L1I`
  regulation, a separate factorial variable from the topology flag above.

Every mechanism from Phases 19–21 remains **default OFF**. Every prior
prototype attempt is preserved unmerged on its own backup branch, never
deleted:

- `backup/phase19-candidate-a-wip` — the original eight-predictor-per-`L2E`
  attempt.
- `backup/phase19-eight-predictor-wip` — a second preservation of the same.
- `backup/phase19a-scaffold-config-ui-wip` — a concurrent session's
  "Phase 19A" scaffold continuation (config/UI only; the scaffold itself
  landed on `july14-integration` at `d91e7f7` as real shared history and is
  NOT superseded by rewriting — see below).
- `backup/phase19-corrected-prediction` — an intermediate corrected-
  topology attempt (per-column, no lateral connection, decoder gated on
  `L2Ej`'s spike) from earlier in this session, superseded by the final
  S_i/PC_i/I_i design.

**Note on `d91e7f7` ("Phase 19A: corrected prediction scaffold")**: this
commit was made by a concurrent session on the same checkout during this
investigation and is real, shared history — not rewritten, not reverted.
It implements a *different*, scaffold-only per-column topology
(`P0`–`P8`, decoder matrix, fixed `Pi → L1Ei` replay, no active learning
rule). This report's own `prediction_column_enabled` mechanism (`PC0`–`PC8`)
is a **separate, additively-coexisting, mutually-exclusive-at-build-time**
mechanism — enabling both raises rather than silently corrupting state
(see `SimulationEngine._build`'s explicit guard). `d91e7f7`'s own flag
(`prediction_excitatory_enabled`) is untouched and remains its own default-
off, unpromoted experiment.

## Phase-by-phase outcomes

| Phase | Outcome |
|---|---|
| 18 / 18b | Architecture contract corrected twice (eight-predictor → per-column-no-lateral → final S_i/PC_i/I_i with lime connection). Docs only. |
| 19 | **Mixed.** Genuine, real, pattern-selective coincidence learning within a single hold (precision 1.0, all 4 patterns). Corrected timing (queued S+R delivery) roughly doubled selectivity vs. the first attempt. **Continuous pattern-switching leaks a real ~2.9% false-prediction rate** from previous-pattern carryover — the promotion bar to `PCi→Ii` does **not** fully pass on this basis alone, but the mechanism was carried forward regardless per the phase's own scoping (Phase 21 tests the wiring itself, separately from this caveat). |
| 20 | **Honest negative for input-free reconstruction.** Realistic training (interleaved or single-hold, up to 50,000 steps) never matures decoder weights past a ~50–64 plateau reached by step 10,000 — far below the ~500 needed for feedback-alone firing. A **manually**-matured decoder reconstructs perfectly (precision/recall 1.0, no runaway, no false `L2E` activation), proving the architecture and cueing mechanism are sound; the gap is specifically that realistic training doesn't reach maturity. |
| 21 | **Positive.** Selective `PCi→Ii` input topology completely breaks all-nine `L1I` synchronization (0.42–0.48 → 0.00) and gives **exact** per-pixel selectivity (zero drive to inactive columns over a 3000-step hold). Honest trade-off: weaker overall suppression than global feedback, since `PCi` fires far less often than `L2E`. |
| 22 | **Confirms orthogonality.** `pretrained_l2i_recruitment` (Phase 17) and `prediction_column_to_i_enabled` (Phase 21) compose cleanly where independent, and Phase 21 does **not** fix Phase 17's tyranny (no mechanistic reason it should). **Positive, independent finding**: novel-pattern spare-capacity recruitment survives even severe upstream tyranny in 7/8 trials. |
| 23 | **Decisive negative for frequency-based gating.** The no-prediction baseline sits closest to 0.5 (0.528); genuine selective prediction sits further away (0.834); an incorrect (wrong-pixel) prediction produces frequency (0.854) indistinguishable from correct prediction (0.834). Frequency alone cannot detect correct prediction at all. |
| 24 | **Gated off** on Phase 23's result. No learning-stop rule implemented. |
| 25 | **Gated off.** Prediction signal is meaningful in direction (exact decoder selectivity) but not in growth dynamics (weights plateau because `PCi` stops firing — a bottleneck free-energy has no mechanism to address). No rule implemented. |
| 26 | **Final validation.** Full suite re-confirmed clean (379 passed, 5 pre-existing failures, no new failures). This report finalized and committed as the closing checkpoint of the investigation. |

## What must remain default OFF

Every flag introduced in this investigation stays OFF by default and is
NOT promoted: `prediction_column_enabled`, `prediction_column_to_i_enabled`,
`pretrained_l1i_regulation`, and (from Phase 17, unchanged)
`pretrained_l2i_recruitment`. `prediction_excitatory_enabled` (the
concurrent session's Phase 19A scaffold) likewise remains unpromoted.

## What remains conceptual / not implemented

- `PCi → Ii → Si` inhibitory suppression's downstream effect on learning
  (whether correct prediction gradually moves sensory pixels toward
  half-frequency) — Phase 21 wires the connection and measures L1I/L1E
  frequency effects directly, but does not test a multi-cycle learning
  trajectory under this suppression.
- Frequency-based learning-stop (Phase 24) — explicitly gated off.
- Synapse-level free-energy (Phase 25) — explicitly gated off.
- The Phase 19 carryover/false-prediction issue during continuous
  switching (~2.9%) remains an open, documented limitation — not silently
  patched by adopting boundary-clearing (explicitly disallowed as the
  primary mechanism).
- The upstream `L2` representation-ownership/tyranny problem (Phases 11,
  13b, 15, 16, 17, reconfirmed in Phase 22) remains unresolved and is
  orthogonal to everything built in Phases 18–25.
- Input-free reconstruction (Part 7's eventual capability) is
  architecturally proven possible (Phase 20's manual-maturity control) but
  not achieved under any realistic training regime tested.

## Commits (this investigation, `july14-integration`, base `3fef508`)

```
3e43cca  Phase 18b: corrected LPS Lecture 14 prediction architecture contract (docs only)
d91e7f7  Phase 19A: corrected prediction scaffold                          [concurrent session]
c0b590f  Phase 18b: correct Lecture 14 topology with local sensory-feedback coincidence
b9004ec  Phase 19: input-column prediction E shadow coincidence experiment
8be89a6  Phase 20: frozen reconstruction (measurement only, PC-grid level)
4d5d241  Phase 21: selective local predictive inhibition (PCi->Ii, 2x2 factorial)
0867533  Phase 22: full interaction of pretrained_l2i_recruitment x prediction_column_to_i_enabled (2x2)
019af0c  Phase 23: frequency measurement only (no gating)
439f4b3  Phase 24: GATED OFF -- no frequency-based learning-stop implemented
dcc37c3  Phase 25: GATED OFF -- no synapse-level free-energy rule implemented
```

Backup branches (all preserved, none merged, none pushed):
`backup/phase19-candidate-a-wip`, `backup/phase19-eight-predictor-wip`,
`backup/phase19a-scaffold-config-ui-wip`, `backup/phase19-corrected-prediction`.

## Test results

Full backend suite, final Phase 26 confirmation: **379 passed, 5 failed**
(925.57s). The 5 failures are the same pre-existing flow-rate/assembly-
flow-credit failures present since before this investigation began
(`test_assembly_flow_credit.py::test_integration_four_pattern_regime_is_active_and_bounded`,
`test_flow_rate.py::test_flow_off_is_baseline`,
`test_flow_rate.py::test_flow_builds_charge_smoothly`,
`test_flow_rate.py::test_flow_can_cross_threshold_without_new_input`,
`test_flow_rate.py::test_flow_forces_single_chunk`) — no new failures
introduced by any phase. The count rose from 375 (Phase 22) to 379 with
Phase 23's 4 new frequency-measurement tests (Phases 24/25 added no code
or tests, being gated off).

## Bugs found and fixed along the way

Two regression bugs, both the same underlying class (a generic per-neuron
sweep written before this investigation's new populations/flags existed,
applied uniformly without knowing about them):

1. `NeuronConfig.apply_to()`'s `is_l2e = not (is_l1e or is_l1i or is_l2i)`
   classification silently swept `PCi` (Phase 19) and selective-topology
   `L1Ii` (Phase 21) into the legacy L1E→L2E distance-weighting path,
   inflating delivered charge by orders of magnitude.
2. A generic `learning_rate = lr_frac * weight_cap` sweep in `_build()`
   silently overwrote `pretrained_l1i_regulation`'s own `learning_rate=0`
   pinning (Phase 21).

Both are fixed locally (not by touching the shared classification logic)
and guarded by dedicated regression tests.

## Overall verdict

The corrected Lecture 14 local-coincidence architecture is **partially
validated**: the core coincidence-detection and selective-inhibition
mechanisms work exactly as designed and are cleanly measurable (Phases 19,
21). Two real, structural limitations were found and honestly documented
rather than smoothed over: decoder weights do not mature under realistic
training (Phase 20), and continuous pattern-switching leaks a small but
real carryover rate (Phase 19). Two later phases were correctly gated off
by their own explicit criteria rather than implemented anyway (Phases 24,
25). Nothing here is promoted to any new default; the existing baseline
dynamics are provably unaffected (byte-identical flag-off tests throughout
Phases 19–22).
