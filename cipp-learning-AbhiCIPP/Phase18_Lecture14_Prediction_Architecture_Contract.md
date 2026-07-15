# Phase 18 — LPS Lecture 14 Prediction Architecture Contract

**No neural-dynamics change. No topology change. No runtime behavior added.**
This document specifies the smallest explicit architecture for testing
Lecture 14's prediction/reconstruction hypothesis, to be implemented
starting Phase 19. Every equation below that Lecture 14 itself does not
supply is explicitly marked **[EXPERIMENTAL CANDIDATE]** — Lecture 14 (see
`LPS_Lecture_14_Detailed_Summary.txt`/`_Expanded_Chronological_Notes.txt`)
describes the *shape* of the desired behavior (an excitatory prediction
population that reconstructs input, encoder/decoder duality, frequency-
linked free energy) but supplies no equation, no topology diagram with
indices, and no plasticity rule. Nothing here is a Lecture 14 equation;
everything numeric is this project's own candidate, adopted per the
independent LPS14 architecture review's Candidate A recommendation.

## Why this, and why now

Phase 17 tested ONE isolated piece of Lecture 14's proposal (pre-trained
shared L2I recruitment) and found a valid narrow negative result: it
improved WTA cleanliness but worsened tyranny and distinct ownership
(`Phase17_Lecture14_Mapping_and_Pretrained_L2I_Report.md`). That flag stays
default off and is not deleted. Lecture 14's actual claim is broader:
learning is supposed to *stop naturally* once a representation can predict
(reconstruct) its own input, via feedback that inhibits the already-learned
input. Testing that claim requires an actual reconstruction pathway, which
does not exist yet in this codebase at all. This phase specifies it; later
phases (19+) build and test it, each gated behind its own default-off flag,
each with its own promotion bar.

## Architecture

### Population: L2P0–L2P7

Eight new excitatory neurons, `L2P0`...`L2P7`, one per existing `L2E0`...
`L2E7`. Registered in `SimulationEngine._register_neurons()` following the
exact existing pattern (`self.neurons['L2Pk'] = ...`,
`self.meta['L2Pk'] = dict(id=..., label=f'pred {k}', layer='L2', type='E',
threshold=..., pos=...)`) — a `layer='L2'` new sub-population, distinct
`type='P'` recommended over reusing `type='E'` so the existing renderer/
raster per-population toggles (`layerKey`, Phase 14) can treat it as its
own group without being silently swept into L2E's existing E/I filters.
Position: offset outward from its paired L2Ek along the existing ring/
irregular-geometry radius (e.g. `L2E_k`'s `(x,y)` scaled by a fixed radius
multiplier, z raised by a fixed offset) so it renders as a visually
distinct but spatially-paired dot — **[EXPERIMENTAL CANDIDATE: exact offset
values]**, purely cosmetic, no effect on any physical delivery (this
codebase's distance-weighting pathways are all explicitly gated per-
pathway by their own flags, and none will be pointed at L2P positions
unless a later phase explicitly adds that).

### Connections

**1. L2Ek → L2Pk (fixed, physical, one-to-one recruitment).** Exactly one
excitatory synapse per pairing, analogous to the existing L2E→L2I
recruitment synapse but PAIRED rather than all-to-one. Direction:
`source=L2Ek, target=L2Pk`. This is the "L2E must physically excite L2P"
requirement — implemented as a real `receive_input`/`fire()` event on
L2Ek's own spike, delivered to L2Pk exactly like the existing L2E→L2I
delivery (`CorticalColumn.set_lateral_excitation_weights`-style, but a
1-to-1 diagonal matrix instead of an n-to-1 fan-in). Fixed value candidate:
the resolved `L2Pk` threshold itself (same reasoning as Phase 17's
`pretrained_l2i_recruitment`: one physical L2Ek spike alone is sufficient
to cross L2Pk's own threshold) — **[EXPERIMENTAL CANDIDATE: exact fixed
value]**, but the *direction* (fixed, not learned) is a deliberate, explicit
design choice per the independent review: this pairing's job is encoding
identity-preservation (which L2E paired with which L2P), not competition,
so there is nothing to learn here and no reason to risk drift.

**2. L2Pk → L1Ei (nine independent, LEARNED decoder synapses per L2Pk).**
This is the actual prediction/reconstruction pathway and the only LEARNED
connection in this contract. Every `L2Pk` gets nine independent afferent-
reversed (efferent) weights, one per L1 pixel — architecturally the
*mirror* of L2Ek's own nine feedforward encoder weights
(`ff{i}->{k}`, `L1Ei -> L2Ek`), but **a completely separate weight array,
never aliased, never copied, never tied**. Naming convention:
`decoder{k}->{i}` for the synapse from `L2Pk` to `L1Ei`, distinct from the
existing `ff{i}->{k}` encoder id. Direction: `source=L2Pk, target=L1Ei`.
**Prediction feedback cannot arrive earlier than t+1** (per the independent
review's explicit constraint) — implemented via the same one-step delayed-
register pattern already used for `l1i_feedback_delay`, so a `L2Pk` spike
at step `t` can only affect `L1Ei`'s membrane starting at step `t+1`,
never the same step. **No direct `L2P → L1I` pathway in this first
reconstruction milestone** (Phase 20) — that is Phase 21's job, and is
architecturally a completely separate synapse set (`L2Pk -> L1Ii`), not a
reuse or repurposing of the `L2Pk -> L1Ei` decoder weights.

L1E's own afferent array currently has exactly 2 slots (`[from_paired_L1I,
external_pixel]`, `layers.py::InputLayer.__init__`, hardcoded
`Neuron(n_inputs=2, ...)`). Reconstruction requires a THIRD slot,
`[from_paired_L1I, external_pixel, from_L2P_decoder]`. This phase does not
touch that constructor — Phase 19/20 will add the third slot conditionally
(only when `prediction_feedback_enabled` is True), so `InputLayer` continues
building exactly 2-slot L1E neurons whenever prediction is off, preserving
byte-identical behavior for every existing caller.

### Thresholds

`L2Pk`'s own threshold: **[EXPERIMENTAL CANDIDATE]** — proposed equal to
`L2Ek`'s own threshold (`threshold_l2`), the simplest choice with no new
free parameter, consistent with "keep the L2I neuron, membrane, threshold
check, and physical spike" conservatism established in Phase 17. `L2Pk`
must physically integrate (`receive_input`) and cross `check_threshold()`
on its own, exactly like every other neuron in this codebase — never a
software pass-through of L2Ek's own spike flag.

### Delays

- `L2Ek → L2Pk`: **instantaneous, same-step** (matches the existing
  L2E→L2I recruitment delivery, which is also instantaneous — only the
  *inhibitory return trip* L2I→L2E is causally delayed in this codebase,
  not the excitatory recruitment step itself).
- `L2Pk → L1Ei` (decoder delivery): **exactly one step delayed** (t+1),
  per the independent review's explicit constraint, implemented via a
  dedicated one-step register, the same pattern as `l1i_feedback_delay`.

### Plasticity event (decoder learning)

**On `L2Pk`'s own physical spike only** (never on `L2Ek`'s spike, never on
any other neuron's spike, never triggered by a step counter or timer):
update all nine of `L2Pk`'s own decoder weights from LOCAL current L1E
activity only. Candidate (per the independent review, explicitly marked
experimental, not a Lecture 14 equation):

```
delta_d_ji = eta_pred * s_Pj * (x_i - d_ji)     [EXPERIMENTAL CANDIDATE]
```

where `d_ji` is `L2Pj`'s decoder weight to pixel `i`, `s_Pj` is `L2Pj`'s
own binary spike indicator (this update only runs when `s_Pj=1`, so the
term is redundant given the "on its own spike only" gate — kept in the
formula for clarity that this is a per-synapse local rule, not a
population-wide one), and `x_i` is `L1Ei`'s own current activation
(binary spike state, matching this codebase's existing signed-spike
convention rather than introducing a new continuous "activity" variable).
Units/bounds: `d_ji` clamped to `[0, w_cap_pred]` for some fixed
**[EXPERIMENTAL CANDIDATE]** cap (proposed: same scale as the encoder's own
`weight_cap` so a saturated decoder can deliver comparable charge to a
saturated encoder synapse); `eta_pred` is a new, separately-named rate
(never aliased to `learning_rate`/`l2e_lr_frac`), default value
**[EXPERIMENTAL CANDIDATE]**. This is a plain delta rule (pulls `d_ji`
toward the target `x_i` at rate `eta_pred`, per-synapse, per-event) —
deliberately the SIMPLEST possible local, bounded candidate, per the
review's explicit instruction not to add voltage metaplasticity,
covariance normalization, center-frequency penalties, homeostasis, or
competing decoder rules before determining whether this simple rule
succeeds or fails.

No pattern name, winner record, owner table, neuron index preference, or
cross-neuron comparison is read anywhere in this rule — it reads exactly
two already-decided physical facts (`L2Pj` fired; `L1Ei`'s current
activation) and one own-synapse value (`d_ji`), the same locality
discipline audited directly in Phase 15's and Phase 17's own tests.

### Observability

New `dynamic_state()` block, e.g. `prediction` (name **[EXPERIMENTAL
CANDIDATE — naming only]**): per-`L2Pk` spike flag, potential/activation,
and the full 9-value decoder vector, plus a `changed_decoders` sparse-delta
list mirroring the existing `changed_synapses` convention exactly. New
`topology()` synapses for `L2Ek->L2Pk` (kind e.g. `prediction_recruitment`,
fixed/unweighted like `reset_inhibition`) and `L2Pk->L1Ei` (kind e.g.
`decoder`, weighted, following the existing per-connection distance/
influence/effective-transmission reporting convention if distance ever
applies to it — not planned for the first milestone). Frontend: reuse
Phase 14's View Controls pattern (an independent P-population visibility
toggle, an independent decoder-edge-kind toggle) — no new frontend
mechanism invented ad hoc.

### Reconstruction test (Phase 20 preview, specified here for the contract)

Freeze all plasticity, remove external input, cue exactly one `L2Ek` or its
paired `L2Pk` through an explicit experimental control (never by writing
`input_vec` pixels directly, never by rendering the stored decoder weights
as if they were spikes — the physical chain cue → `L2Pk` fire → decoder
delivery → `L1Ei` integration → `L1Ei`'s own `check_threshold()`/`fire()`
must run for real). Measure precision/recall of which `L1Ei` actually fire
against the pattern's true active pixels, separating center pixel 4
(legitimately part of all four patterns — strong center reconstruction is
NOT itself a failure) from the peripheral, pattern-distinguishing pixels
(where failure would actually show up as center-only collapse). Full
control list specified in Phase 20's own report (no cue / correct cue /
wrong-`L2P` cue / random decoder / shuffled decoder / center-only decoder /
rate-matched time-shuffled prediction).

### Loop / runaway risks

1. **Recurrent excitation loop**: `L2Pk` fires → `L1Ei` fires → (if
   feedforward pathway is still live) `L1Ei` re-excites `L2Ek` → `L2Ek`
   re-excites `L2Pk` → repeat. Mitigated by: decoder delivery is delayed
   one step (never same-step), `L1Ei`'s own refractory period still applies
   normally, and Phase 20's reconstruction protocol explicitly **removes
   external input** and measures for exactly this (persistence after cue
   removal, runaway recurrence, false L2E activation are named required
   metrics).
2. **Cross-talk between decoders**: since all nine `L1Ei` are shared
   targets across all eight `L2Pk`, an L1Ei could in principle receive
   simultaneous predicted excitation from more than one `L2Pk` (e.g. the
   shared center pixel, legitimately targeted by every pattern's decoder).
   This is expected and explicitly not treated as failure for the center
   pixel; the peripheral-pixel controls test whether it becomes a problem
   there too.
3. **Decoder monopolization by a single tyrant** (per the independent
   review's correction #7): if upstream L2E competition has already
   collapsed to one dominant owner (a known, documented risk — Phases 11,
   13b, 15, 16, 17), that one neuron's `L2P` partner will be the only one
   ever getting real training data, producing a mixed/blurred decoder that
   looks like decoder-rule failure but is actually a symptom of upstream
   representation collapse. Phase 19+ reports must separate "representation
   ownership," "decoder quality conditional on owner," "mixed-pattern
   reconstruction," and "center-only failure" as distinct findings, never
   conflated.
4. **First-input-only claim**: nothing in this contract, nor in Phases
   19-20, tests *next-input* temporal prediction — only *current-pattern*
   reconstruction (cue this pattern, reconstruct this pattern). A genuine
   temporal-sequence experiment is out of scope until explicitly run later
   (Lecture 14's own "time may be required" hypothesis stays classified
   ABSENT/deferred per Phase 17's mapping).

### Why one shared global prediction neuron cannot distinguish four representations

The existing `L2I` is exactly this failure mode already, by construction:
one neuron, one scalar threshold, one incoming weight per `L2E` source. It
can represent *that some L2E fired* (a 1-bit "competition happened"
signal) but cannot represent *which* pattern's pixels should be predicted,
because a single neuron's only observable output is a spike or not — there
is no way to recover nine independent per-pixel decoder values from one
scalar. A single shared prediction neuron summing all eight `L2E→P` inputs
into one pooled decoder would produce exactly one blended, pattern-agnostic
reconstruction (effectively the union — or, worse, whichever pattern fires
`L2E` most often — of all four patterns' pixels), never four
distinguishable reconstructions. The one-to-one `L2Ek↔L2Pk` pairing is
therefore not a stylistic choice; it is the minimum structure that lets
each stored representation keep an independently addressable decoder.

## What this phase does NOT do

- No code in `backend/simulation.py`, `neuron_flexible.py`, `layers.py`, or
  `cortical_column_flexible.py` is modified.
- No new flag, no new neuron, no new synapse exists yet after this commit.
- No equation above is adopted as final — every one is marked
  **[EXPERIMENTAL CANDIDATE]** and subject to revision once Phase 19's
  actual measurements come in.

## Baseline verification

Full backend suite re-run after this documentation-only commit, to confirm
this phase truly added zero runtime behavior: **299 passed, 5 failed**
(identical pre-existing flow-rate failures, unchanged from Phase 17).
