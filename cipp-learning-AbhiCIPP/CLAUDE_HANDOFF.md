# CLAUDE_HANDOFF.md

## Branch / HEAD

- Branch: `july14-integration` (created from `july14`)
- HEAD at creation: `6195ef8` (july14 was clean, up to date with
  `origin/july14`)
- Phase 0 checkpoint commit: `b02cd9e` (added `CLAUDE.md` +
  `CLAUDE_HANDOFF.md`)
- Phase 1 audit checkpoint commit: `225b8b1` (`Geometric_Influence_Temporal_Winner_Audit.md`)
- This update corresponds to the Phase 2 (observability), Milestone 1
  checkpoint (backend core) — commit hash filled in after this commit lands,
  see repo log.
- Base branch `july14` is untouched and remains the protected base.
- `four-pattern` branch exists (checked out in a separate worktree at
  `/home/charisxiong/Documents/others`) and is explicitly NOT merged here —
  see `CLAUDE.md`.

## Goal

Port relevant behavior from `four-pattern` into `july14-integration` by hand
(no merge), guided by
`July_14_Geometric_Influence_Temporal_Winner_Brief.txt`, while preserving the
architecture invariants in `CLAUDE.md`: four center-crossing patterns,
`N_OUT=8` (four active + four spare/recruitable L2E cells), no
pattern-to-neuron assignment/argmax/owner-lock/oracle/global
`normalizeW`/fake spikes/UI-side simulation.

**Current phase (Phase 2 — Observability only, per explicit user instruction):**
add observability infrastructure — shared pattern/probe metadata and dashboard
preset, held-out probes with presentation-scoped plasticity freeze, backend-
driven Causal Story, presentation IDs/boundaries, evidence-based receptive-field
status, actual-bounds Fit View, delivery/pre-post-integration diagnostics — while
changing **no neural equation and no preset value**. This phase is scoped
strictly to observability; the audit's confirmed conflicts (latest-spike winner
label, perfect-ring geometry, non-selective L1I, etc.) are NOT being fixed here.

## Completed (this session)

Phase 0 (branch/docs setup):
- Ran git diagnostics: root, remote, branch, status, branch list, recent log.
- Confirmed `july14` was clean and `july14-integration` did not yet exist.
- Created `july14-integration` from `july14` (no other branch changes).
- Authored `CLAUDE.md` with the permanent rules for this repo.
- Authored this file, `CLAUDE_HANDOFF.md`. Committed as `b02cd9e`.

Phase 1 (required audit, brief §14 + §20 — read-only, no mechanisms changed):
- Full read of `July_14_Geometric_Influence_Temporal_Winner_Brief.txt`.
- Audited `backend/simulation.py`, `neuron_flexible.py`, `layers.py`,
  `snn/rules/*.py`, `backend/api.py`, `backend/serializer.py`,
  `backend/websocket.py`, and all of `frontend/*.js` against every item in
  brief §14 and §20.
- Wrote up findings in `Geometric_Influence_Temporal_Winner_Audit.md` —
  read that file for full detail with file:line citations. Six headline
  findings, most importantly: (1) the dashboard's exposed "winner" is
  latest-spike-wins, not first-spike-wins, contradicting the brief's core
  thesis; (2) L2E geometry is a perfect ring (only a 2-way, not 8-way,
  geometric signature); (3) all 9 L1I units share one literal weight vector
  and threshold, so their synchrony is structural, not a serializer bug; (4)
  `distance_weighting=True` is live in `backend/api.py`, not an inert
  default, but starved of symmetry-breaking effect by finding (2); (5) no
  literal influence-squaring bug for the winner's own learning, but a
  two-stage reuse of one distance-derived quantity in the loser depression
  path; (6) no fake raster spikes, no UI-side simulation, no coordinate
  ownership conflict — the frontend audited clean apart from one client-side
  "dead neuron" label that could diverge from the backend's own notion.
- Ran the unmodified baseline test suite and two unmodified diagnostics (see
  Tests below) to anchor these findings against actual current behavior.

## In progress

Phase 2 (Observability), Milestone 1 of 2 — **backend core, DONE**; Milestone 2
(frontend) is next, in the same session, no stop in between per `CLAUDE.md`.

## Files changed (this checkpoint)

- `backend/presets.py` (new) — `DASHBOARD_PRESET`, the exact kwargs
  `backend/api.py` used to construct inline, now named/importable (no values
  changed; addresses the audit's "preset parity" gap for future diagnostics).
- `backend/api.py` — engine construction now `SimulationEngine(seed=_load_seed(),
  **DASHBOARD_PRESET)`; added `ProbeBody` + `POST /api/probe`.
- `backend/simulation.py`:
  - `PROBES` (row 0/row 2/col 0/col 2, held-out) + `PATTERN_ROLE` shared
    metadata. `PATTERNS` and `_cycle_order` (auto-cycle) are untouched, so
    auto-cycle remains training-patterns-only by construction.
  - Presentation tracking: `presentation_id`/`_start_presentation`/
    `_track_presentation`/`presentation_log`, capturing brief §9's fields
    (first physical L2E responder, first-spike step, same-step tie, first
    L1I/L2I source+step) from already-decided physical events only.
  - `present_probe`/`_end_probe`/`_cancel_probe_if_active`: presentation-scoped
    plasticity freeze via `Neuron.plasticity_frozen`, auto-restores the prior
    pattern/input after `steps` (default: `visit_steps`), never touches
    auto-cycle's paused `_visit_step`/`_visit_spikes`/`_pattern_streak`.
  - Evidence bookkeeping: `_neuron_total_spikes`, `_neuron_last_fired_t`,
    `_neuron_first_responder_counts`, `_pattern_first_responder_log`, and
    `_l2e_status(j)` — replaces the audit-flagged client-side weight-sum
    "dead" guess with an observed-behavior status (`unrecruited`/`active`/`quiet`).
  - `_delivery_diagnostics()` — per-feedforward-synapse distance/influence/
    effective-transmission, always computed (not gated on `distance_weighting`),
    closing the audit's "distance/influence absent end-to-end" gap.
  - `topology()`/`dynamic_state()` extended: `probes`, `probe_vectors`,
    `pattern_roles`, per-synapse `distance`/`influence`/`effective`,
    `causal_story`, `probe`, `rf_status` per L2E, `l2_drive`, `l2_charge`
    (previously computed internally but never serialized), `inh_events`.
- `neuron_flexible.py` — added `Neuron.plasticity_frozen` (default `False`,
  every existing caller unaffected) and guarded it in the only three
  weight-mutating call sites (`_update_weights`, `apply_competitive_reset`'s
  depression, `apply_inhibition`'s gate-plasticity/loser-depression) plus
  `_homeostatic_scaling`; all PHYSICAL effects (membrane integration,
  threshold crossing, firing, the unconditional reset/discharge) are
  untouched by the flag.
- `test_observability_phase.py` (new) — 14 tests: pattern/probe metadata,
  auto-cycle training-only, probe immutability (weights AND confidence
  byte-identical across a probe presentation, with real spikes still
  occurring), probe auto-restore/unfreeze, probe-vs-auto-cycle bookkeeping
  safety, manual-input cancels a probe, presentation ID increments +
  history, first-responder evidence accumulation, serialization contents,
  evidence-based status semantics, legacy-equivalence checks.

No neural equation and no preset VALUE was changed. `CLAUDE_HANDOFF.md`
(this file) is also part of this checkpoint's commit.

## Tests

- `test_observability_phase.py` (new, focused): **14/14 passed**.
- `pytest -q` (full suite): **131 passed, 5 failed** (117 pre-existing + 14
  new = 131; same 5 pre-existing `test_flow_rate.py`/
  `test_assembly_flow_credit.py` failures as the Phase 1 baseline, unrelated
  to this work, not touched).
- **Legacy equivalence, verified two ways:**
  1. `sustained_dominance.py` and `ablation_harness.py --seeds 1 2 --epochs 3`
     (both unmodified) reproduce the Phase 1 audit's recorded numbers
     exactly: `distinct=2.00/4, sustained_dominance=0.497, dead=5.00` and
     `dom=0.39±0.015, distinct=2/4, collisions=2, dead=5, rf_cos
     0.915->0.904` respectively.
  2. `test_plasticity_frozen_defaults_false_and_learning_is_unaffected` in the
     new test file asserts weights actually change over 80 steps under the
     (untouched) default `plasticity_frozen=False` path.
- Probe immutability verified directly: `test_probe_presentation_never_mutates_a_weight_or_confidence`
  hashes every synapse weight and every confidence value before/after a
  25-step probe and asserts equality, while also asserting `spikes > 0`
  during the probe (physical dynamics stay live).
- Fit View and raster-boundary accuracy are frontend (Milestone 2, not yet
  built as of this checkpoint) — to be tested with the frontend work.

## Known problems

- Per `AGENT_HANDOFF.md`/the Phase 1 audit, true one-to-one L2E ownership is
  still unsolved and this phase does not touch it (observability only, by
  explicit instruction). See `Geometric_Influence_Temporal_Winner_Audit.md`
  for the full list of confirmed conflicts still awaiting a decision.
- `four-pattern` branch carries diagnostic/tracer work not yet reviewed for
  porting.
- Presentation boundaries are scoped to NAMED pattern/probe switches only
  (`set_pattern`/`present_probe`); raw pixel/random/noise edits do not start a
  new presentation record. Documented, not a bug — free-form manual input was
  never part of the brief's presentation protocol.
- Tie detection (`same_step_tie`) is validated against the default
  event-driven/chunked-charge path (what the live dashboard actually runs);
  the legacy `lasting_inhibition`/`event_driven=False` branches are wired
  (`_last_eligible` is set in both) but not separately tested here.

## Next action

Milestone 2 (frontend, same session): probe buttons + plasticity-frozen
indicator in `controls.js`/`index.html`; evidence-based status in
`receptive.js` (replace the client-side weight-sum "dead" guess);
presentation-boundary markers in `raster.js`/`charge.js`; actual-bounds Fit
View in `renderer.js`; a new backend-driven "Causal Story" tab (no "Input
Weights" tab); distance/influence display in `inspector.js`. Then: run/smoke
test the dashboard, final regression pass, update this handoff again, commit,
report, stop (per `CLAUDE.md`'s phase-end protocol).
