# Phase 30 — Engine Flags: Centered Encoder + Subthreshold Decoder

**Status: implemented as real, default-OFF `backend/simulation.py` flags
(promoted from Phase 29's offline monkeypatch). Both flag-off exactly
byte-identical to the pre-existing baseline. Branch `l2-ownership-recovery`,
on top of Phase 29 (`4764f17`). Nothing pushed.**

## What was added

Two new, independent, default-OFF constructor flags, both fully wired
through `self.params`/the `TUNABLE` tuple/`apply_config`'s bool coercion,
matching every existing flag's convention:

### `centered_encoder_enabled` (+ `centered_encoder_alpha`)

Promotes Phase 29's offline-monkeypatch centered/covariance encoder
rule into a real `ExcitatoryRule` (`snn/rules/excitatory.py`'s
`CenteredEncoderRule`), dispatched by `select_excitatory_rule` with the
HIGHEST precedence (checked before `signed_spike_learning`/
`assembly_flow_credit`). A single shared, engine-level per-pixel trace
(`self._centered_x_bar`, `N_PIX` floats) is injected onto every L2E neuron
as a REFERENCE (`n._centered_x_bar`) at `_build()` time — every L2E reads
the SAME presynaptic trace, never a private copy. `step()` advances the
trace once per step, AFTER every L2E's own `fire()` for that step has
already read the pre-update value (same causal-ordering convention proven
in Phase 29's own harness — a spike this step reflects only spikes
strictly before it).

### `prediction_subthreshold_decoder_enabled` (+ learning rate, z/u time constants)

The local subthreshold coincidence decoder from
`Phase18b_Lecture14_Local_Coincidence_Architecture_Contract.md`. Two
short, exponentially-decaying traces:

- `_pcol_z_R` (shared, `N_OUT` floats) — presynaptic trace of REAL L2Ej
  spikes, built from `dec_vec_pcol` (the SAME already-delayed real event
  vector the existing spike-gated rule reads — no new timing violation).
- `_pcol_u_S` (per-PCi, `N_PIX` floats) — local sensory eligibility trace of
  each PCi's own delivered lateral `S_i` component (`lat_vec_pcol`).

Update `delta_d_ji = eta_sub * z_j^R * u_i^S * (1 - d_ji/d_max)^2`, applied
to EVERY PCi EVERY step, regardless of whether PCi itself physically
spikes — the explicit fix for the existing rule's cold-start plateau.
`u_i^S <= 0` skips the whole update (no paired sensory eligibility, no
update); only `j` indices with `z_j^R > 0` move (no R_j spike, no update;
absent columns unchanged). Mutually exclusive with the existing spike-gated
`_apply_prediction_column_learning` (this flag REPLACES it, never both).
Actual `PCi -> Ii` inhibition is completely untouched — it still requires
PCi's own physical spike; this flag changes ONLY the decoder's learning
trigger.

Both flags default OFF; every new code path is behind an `if
self.<flag>_enabled:` guard, so flag-off behavior is exactly byte-identical
to the pre-Phase-30 baseline (verified directly, not assumed —
`test_centered_encoder_off_is_byte_identical_to_baseline`,
`test_subthreshold_decoder_off_is_byte_identical_to_baseline`).

## Tests

`test_phase30_subthreshold_decoder_and_centered_encoder.py` — 16 tests, all
passing: both flags off byte-identical; centered encoder trace genuinely
shared across all L2E neurons; centered encoder disables no OTHER
mechanism (loser depression/L2I hard-reset stay independently settable);
`CenteredEncoderRule.on_fire` is local (no cross-neuron/global state);
subthreshold decoder inert without `prediction_column_enabled`; no-R_j-
spike-means-no-update (a never-fired L2E's decoder index provably never
moves); no-sensory-eligibility-means-no-update; coincidence dependence
(neither trace alone is sufficient, both together produce genuine
potentiation); absent columns remain unchanged in a mixed-eligibility
event; saturates at `prediction_feedback_max`; never touches the fixed
lateral index; potentiation does not require a PCi somatic spike (direct
test); frozen plasticity blocks the new rule too; the new and old decoder
rules are mutually exclusive (a `pc.fire()` call alone never applies
either rule directly — decoder learning is only ever invoked from `step()`).

## Full test suite

`pytest -q`: **438 passed, 5 pre-existing failures** (751.35s / 0:12:31).
Exactly matches the expected count: 391 (Phase 27) + 18 (Phase 28A) + 13
(Phase 29) + 16 (this phase's new test file) = 438. No new failures.

## Files

- `backend/simulation.py` (modified) — new constructor params, `_build()`
  wiring, `step()`'s PC-block and end-of-step trace updates,
  `_apply_subthreshold_decoder_learning`, TUNABLE/apply_config entries.
- `neuron_flexible.py` (modified) — `centered_encoder_enabled`/
  `_centered_x_bar` default attributes.
- `snn/rules/excitatory.py` (modified) — `CenteredEncoderRule`,
  `select_excitatory_rule`'s new dispatch branch.
- `test_phase30_subthreshold_decoder_and_centered_encoder.py` (new).

## Commit / branch status

Branch `l2-ownership-recovery`, on top of `4764f17`. Not pushed.
