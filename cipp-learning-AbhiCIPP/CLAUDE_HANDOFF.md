# CLAUDE_HANDOFF.md

## Branch / HEAD

- Branch: `july14-integration` (created from `july14`)
- HEAD at creation: `6195ef8` (july14 was clean, up to date with
  `origin/july14`)
- Phase 0 checkpoint commit: `b02cd9e` (added `CLAUDE.md` +
  `CLAUDE_HANDOFF.md`)
- Phase 1 audit checkpoint commit: `225b8b1` (`Geometric_Influence_Temporal_Winner_Audit.md`)
- Phase 2 Milestone 1 checkpoint commit: `9163da2` (backend observability core)
- This update corresponds to the **Phase 2 END** checkpoint (Milestone 2,
  frontend, complete) — commit hash filled in after this commit lands, see
  repo log.
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

**Phase 2 (Observability) is COMPLETE** — both milestones done, phase-end
regressions run, this is the phase-end checkpoint per `CLAUDE.md`. Next phase
(seeded engine-owned geometry) is queued, per explicit user instruction
received while this phase was wrapping up; not started yet.

## Files changed (Milestone 2 — frontend, this checkpoint)

- `frontend/index.html` — "Presentation" top-bar stat pill; "Held-out Probes"
  sidebar section (`#probe-buttons`, `#probe-status`); `#fit-view` button in
  the viewport; new "Causal Story" bottom-panel tab (`#causal-current` /
  `#causal-history`). Explicitly did **not** add an "Input Weights" tab.
- `frontend/style.css` — styling for the above (`.probe-btn`, `.probe-status`,
  `#fit-view`, `.causal-*`).
- `frontend/controls.js` — `buildProbeButtons()` (mirrors
  `buildPatternButtons()`, posts to `/api/probe`); `_updateProbeStatus()`
  reflecting `dyn.probe`/`dyn.causal_story` (frozen state, steps elapsed).
- `frontend/app.js` — top-bar "Presentation" readout from `dyn.causal_story`;
  wires the new `CausalStory` module; wires `#fit-view` to `renderer.fitView()`.
- `frontend/receptive.js` — **removed** the client-side top-3-weight-ratio
  "dead" guess (the audit-flagged divergence risk); now reads
  `state.rf_status.status` (`unrecruited`/`active`/`quiet`) straight from the
  backend.
- `frontend/raster.js` / `frontend/charge.js` — presentation-boundary vertical
  markers (solid = training pattern, dashed = probe), driven purely by
  watching `dyn.causal_story.presentation_id` change (backend-computed value;
  the frontend does no detection/inference of its own, only bookkeeping of
  already-known state). Both remain continuous rolling-history, real-spike-only
  views (`raster.js`) and threshold-normalized-charge views (`charge.js`,
  `activation` = V/θ) — these were already correct per the Phase 1 audit and
  are unchanged in that respect.
- `frontend/renderer.js` — `fitView()`: computes the actual bounding box from
  `this.pos` (built only from `topology.neurons[i].pos`, i.e. real engine
  coordinates — verified non-degenerate: x∈[-3.2,3.2], y∈[-3.2,3.2],
  z∈[-2.0,6.0] across all 27 neurons on the live server), then repositions the
  camera/target with 20% padding along the SAME default viewing direction. The
  default camera pose and the rest of the 3D view are untouched.
- `frontend/inspector.js` — synapse rows now show `distance`/`influence`/
  `effective` (from `backend/_delivery_diagnostics`) when present.
- `frontend/causal.js` (new) — pure renderer of `dyn.causal_story`; computes
  nothing itself (no first-spike/tie/source detection client-side).

All new/changed JS files pass `node --input-type=module --check` (syntax-only;
no bundler in this project). No file in `frontend/` steps or mutates engine
state — every action is still an HTTP POST, exactly as before.

## Files changed (Milestone 1 — backend core, prior checkpoint `9163da2`)

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
- **Full-stack smoke test (real server, not just unit tests):** ran
  `uvicorn backend.api:app` in the background and drove it with an actual
  websocket client (the runner only steps while a client is connected —
  confirmed by reading `backend/websocket.py`, pre-existing behavior, not a
  regression). Verified over the wire:
  - `topology`/`dynamic` messages contain `probes`, `pattern_roles`,
    per-synapse `distance`/`influence`/`effective`, `causal_story`, `probe`,
    `rf_status`.
  - `POST /api/probe {"name": "col 0", "steps": 20}` → `causal_story.role`
    flips to `probe` and `plasticity_frozen`/`probe.active` read `True` for
    exactly the requested 20 frames, then both flip back to `False` and the
    engine auto-restores the prior training pattern — `presentation_log`
    history shows both presentations in order.
  - Topology neuron positions are real, non-degenerate 3D coordinates (see
    Fit View note above), confirming `renderer.fitView()` has genuine engine
    geometry to compute a bounding box from.
- Raster/charge boundary-marker *rendering* and Fit View's on-screen camera
  motion were verified by code review + confirmed correct upstream data (the
  `causal_story.presentation_id` transitions and real topology bounds above),
  not by literally opening a browser (none available in this environment). If
  the user wants a visual check, the dashboard now runs correctly
  end-to-end (`uvicorn backend.api:app`, verified above) and can be opened at
  `http://127.0.0.1:8000`.

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
- No literal browser was opened for this phase (none available in this
  environment); Fit View / boundary-marker visuals were verified by code
  review plus confirmed-correct upstream data, not a screenshot. Flagged for a
  human or a browser-capable session to eyeball if desired.

## Next action

Phase 2 is closed. Next phase, per explicit user instruction: **seeded
engine-owned geometry** (still observability/topology infrastructure, not a
dynamics change) —
- Keep `N_OUT=8`.
- Jitter L1E within assigned 3×3 cells; place each L1I near its paired L1E.
- Place all 8 L2E irregularly with a minimum-separation constraint; keep the
  single L2I near the center.
- Coordinates fixed across reset/training/probes, changing only on an
  explicit topology reseed (distinct from the existing weight-only
  `reseed()` — needs a decision on whether to extend it or add a new verb).
- Renderer must consume engine coordinates (already true per the Phase 1
  audit and this phase's `fitView()` work — no renderer-side position logic
  exists to remove).
- Preserve the current symmetric ring/grid layout as a selectable legacy
  ablation (do not delete it).
- Do NOT enable neural distance effects beyond the current baseline if doing
  so would change it — `distance_weighting=True` is already live in
  `backend/api.py` (Phase 1 audit finding #4); changing the geometry WILL
  change what that live feature computes, since it already reads L2_HOMES/
  pixel positions. This needs an explicit decision (flagged, not resolved):
  either (a) keep `distance_weighting` on and accept baseline behavior changes
  as the intended point of jittered geometry, or (b) temporarily pin geometry
  distances at their CURRENT ring/grid values for the influence calculation
  while the jittered layout is only used for placement/rendering/minimum-
  separation, so the "no baseline change yet" instruction is honored exactly.
  Surface this choice to the user before implementing rather than picking
  silently.
