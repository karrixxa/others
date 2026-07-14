# CLAUDE_HANDOFF.md

## Branch / HEAD

- Branch: `july14-integration` (created from `july14`)
- HEAD at creation: `6195ef8` (july14 was clean, up to date with
  `origin/july14`)
- Phase 0 checkpoint commit: `b02cd9e` (added `CLAUDE.md` +
  `CLAUDE_HANDOFF.md`)
- Phase 1 audit checkpoint commit: `225b8b1` (`Geometric_Influence_Temporal_Winner_Audit.md`)
- Phase 2 Milestone 1 checkpoint commit: `9163da2` (backend observability core)
- Phase 2 END checkpoint commit: `05c17a0` (frontend, phase complete)
- Phase 3 END checkpoint commit: `0e353cd` (seeded engine-owned geometry)
- This update corresponds to the **Phase 4 END** checkpoint (connection
  distance/influence as isolated experimental behavior) — commit hash filled
  in after this commit lands, see repo log.
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

**Phase 2 (complete) — Observability only:** added observability infrastructure
— shared pattern/probe metadata and dashboard preset, held-out probes with
presentation-scoped plasticity freeze, backend-driven Causal Story,
presentation IDs/boundaries, evidence-based receptive-field status,
actual-bounds Fit View, delivery/pre-post-integration diagnostics — with **no
neural equation and no preset value** changed.

**Phase 3 (complete) — Seeded engine-owned geometry only:** jittered/irregular
engine-owned positions (L1E jittered within its assigned cell, L1I paired near
its L1E, L2E placed irregularly with a minimum-separation constraint, L2I
fixed near center), seeded and fixed across reset/training/probes, changing
only on an explicit topology reseed, with the legacy symmetric ring/grid
preserved as a selectable ablation. A temporary legacy-distance-compatibility
shim kept `distance_weighting`'s delivered-charge numbers pinned to the legacy
reference geometry, so that phase changed **no neural dynamics**.

**Current phase (Phase 4, complete) — Connection distance/influence as
isolated experimental behavior, per explicit user instruction:** adds FOUR
NEW, fully independent experimental pathways — L2E→L2I, L2I→L2E, L2E→L1I,
L1I→L1E — each with its own default-OFF ablation flag and one shared,
configurable, safe-by-default power law (inverse-square, pure attenuation).
L1E→L2E's existing legacy pathway (Phase 2/3, `distance_weighting`/
`legacy_distance_compat`) is untouched. Every pathway exposes source, target,
distance, influence, raw weight, effective transmission, and whether
influence was actually applied, via a new `pathway_influence_report()`/
`GET /api/pathway_influence`. Influence is applied **exactly once** per
pathway — verified directly (delivery uses influence¹, learning always reads
the raw, unscaled weight) — and none of the four new flags is enabled by
default anywhere ("do not enable every pathway together"), so the
geometry-off and legacy-distance baselines from Phases 2/3 are completely
unaffected.

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

Phase 2 (observability infrastructure; see "Files changed" and commits
`9163da2`/`05c17a0` for full detail): shared pattern/probe metadata + dashboard
preset, held-out probes with presentation-scoped plasticity freeze, backend-
driven Causal Story/presentation tracking, evidence-based RF status,
delivery/pre-post-integration diagnostics, and the matching frontend
(probe controls, Causal Story tab, evidence-based status display, Fit View,
presentation-boundary markers, distance/influence display). No neural
equation or preset value changed.

Phase 3 (seeded engine-owned geometry; see commit `0e353cd`): jittered
L1E-in-cell / paired L1I / irregular-with-min-separation L2E / centered L2I
positions, seeded and fixed except on explicit topology reseed, legacy
ring/grid preserved as a selectable ablation, and a temporary
legacy-distance-compatibility shim that keeps that phase's dynamics
byte-identical to before it while clearly labeling the pinned numbers
wherever they're shown.

Phase 4 (connection distance/influence as isolated experimental behavior; see
"Files changed" below for full detail): rather than removing Phase 3's
legacy-distance-compat shim (the plan anticipated at the end of that phase),
the ACTUAL instruction for this phase was narrower and safer -- add FOUR NEW,
independently-ablated experimental pathways (L2E→L2I, L2I→L2E, L2E→L1I,
L1I→L1E) beside the untouched legacy L1E→L2E pathway, each default-off, each
fully audited (source/target/distance/influence/raw weight/effective
transmission/applied), using one shared safe-by-default power law. The
legacy-distance-compat shim and the L1E→L2E pathway it governs are completely
UNCHANGED by this phase.

## In progress

**Phase 4 (connection distance/influence, isolated experimental behavior) is
COMPLETE** — single-milestone phase, phase-end regressions run, this is the
phase-end checkpoint per `CLAUDE.md`. No further phase is currently queued;
awaiting user direction on what (if anything) comes next -- e.g. whether to
actually experiment with one pathway at a time, or revisit the
legacy_distance_compat shim removal originally anticipated after Phase 3.

## Files changed (Phase 4 — connection distance/influence, this checkpoint)

- `neuron_flexible.py`:
  - `Neuron.competitive_reset_influence` (new, default `1.0` = neutral): the
    ONLY place the L2I→L2E pathway's influence can enter, since that path has
    no learned weight/delivery step. `apply_competitive_reset()`'s depression
    `gain` is now `learning_rate * gate * p_loss * competitive_reset_influence`
    — the UNCONDITIONAL membrane reset itself is never touched by it.
  - `apply_inhibition()`: when the target neuron's `distance_weighting` is on
    (used here by the NEW L1I→L1E pathway), the DELIVERED discharge magnitude
    is scaled by `(distance_ref/max(distance,distance_min))^distance_power`
    (mirroring `effective_weights()` in `snn/rules/delivery.py`, but for this
    negative/inhibitory path, which delivers via `apply_inhibition` rather
    than `receive_input`). The per-discharge LEARNING call keeps using the
    RAW, unscaled gate magnitude — influence is applied exactly once, at
    delivery, never again in the learning update.
- `backend/simulation.py`:
  - New module-level Phase 4 section: `INFLUENCE_SAFE_MAX=4.0`,
    `_power_law_influence(d, ref, d_min, power)` (the shared, configurable
    power law — defaults `ref==d_min` make it pure attenuation, never
    amplifying), `_summarize_pathway(entries)` (min/median/max influence + a
    `safe` flag).
  - Seven new constructor params, all defaulting to neutral/off:
    `infl_power=2.0` (inverse-square), `infl_ref=1.0`, `infl_min=1.0`
    (ref==min by default), and `infl_l2e_l2i`/`infl_l2i_l2e`/`infl_l2e_l1i`/
    `infl_l1i_l1e` (all `False`).
  - `_apply_experimental_pathway_distances()`: computes real-geometry
    distances for the four new pathways from `self._geometry_xy` and sets
    `distance_weighting`/`distance_power`/`distance_ref`/`distance_min`/
    `.distance` on the target neuron(s) for each — reusing the SAME generic
    per-neuron delivery machinery the legacy L1E→L2E pathway already uses
    (`effective_weights()` in `snn/rules/delivery.py`), since L2I/L1I/L1E's
    distance fields were completely dormant before this phase (confirmed via
    `NeuronConfig.apply_to()`, which explicitly forces `distance_weighting`
    off for every non-L2E neuron — this method must run, and does run, AFTER
    that). L1I→L1E neutralizes L1E's abstract external-pixel channel
    (`distance[1] = infl_ref`, giving factor `1.0` exactly) so the sensory
    input is never accidentally attenuated. Called from both `_build()` and
    `reseed_topology()`.
  - `pathway_influence_report()` (new): the full per-connection audit across
    all FIVE pathways — source, target, distance, influence, raw weight,
    effective transmission, `applied` — reusing `_delivery_diagnostics()` for
    the untouched legacy L1E→L2E pathway.
  - `TUNABLE`/`apply_config()`: the seven new params are dashboard-configurable
    (bool-coerced flags, float-coerced power law).
- `backend/api.py`: new `GET /api/pathway_influence` endpoint (returns
  `pathway_influence_report()`); seven new `CONFIG_SPEC` entries (all
  `advanced=True`, so they render in the collapsed "Advanced" panel, not the
  main one — matching "isolated experimental", not a new default experience).
- `test_influence_phase.py` (new) — 18 tests: all four new flags default off;
  `DASHBOARD_PRESET` doesn't enable any of them; the legacy L1E→L2E pathway
  and both Phase 2/3 baselines untouched; disabled-config byte-equivalence;
  each pathway's flag is independent of the others; close-vs-distant delivery
  for all four new pathways (L2E→L2I and L2E→L1I via `effective_weights()`
  directly, L1I→L1E via a direct `apply_inhibition()` call since its effect
  isn't reliably observable in L1E's spike outcome -- see Known problems,
  L2I→L2E via a direct `apply_competitive_reset()` comparison confirming the
  depression gain scales with distance while the reset itself stays exact);
  influence fixed across steps/training/probes and only changes on
  `reseed_topology()`; no-influence-squared checks (delivery uses
  `influence**1` exactly, not `influence**2`); learning uses the raw
  unscaled weight; no reported influence exceeds 1.0 under the default law;
  full `pathway_influence_report()` structure and `applied`-flag correctness.

### Phase 3 (prior checkpoint `0e353cd`)

- `backend/simulation.py`:
  - New geometry constants + helpers: `L1_JITTER_FRAC`, `L1I_PAIR_JITTER_FRAC`,
    `L2E_PLACEMENT_RADIUS`, `L2E_MIN_SEPARATION`,
    `L2E_PLACEMENT_MAX_TRIES/_RESTARTS`, `_legacy_l1_xy()` (the deterministic
    legacy grid, factored out and reused as both the `symmetric_geometry=True`
    source and the `legacy_distance_compat` reference), `_jittered_l1e_xy()`,
    `_paired_l1i_xy()`, `_irregular_l2e_xy()` (seeded rejection-sampling
    placement with a minimum-separation constraint).
  - Three new constructor params, all defaulting to the exact legacy behavior
    so every existing caller/test is unaffected: `topology_seed=1`,
    `symmetric_geometry=True`, `legacy_distance_compat=True`.
  - `_compute_geometry()`: returns legacy positions verbatim when
    `symmetric_geometry=True`, else draws jittered/irregular positions from
    `topology_seed` via a dedicated RNG stream (independent of the weight-init
    `seed`).
  - `_register_neurons()` now calls `_compute_geometry()` and caches the result
    on `self._geometry_xy`; positions are recomputed identically on every
    `_build()` (deterministic given `topology_seed`), which is exactly what
    keeps them FIXED across `reset()`/`apply_config()`/`reseed()` (weight)/
    probes — none of those change `topology_seed`.
  - `_apply_l2e_distances()`: when `legacy_distance_compat=True` (default), the
    per-L2E delivery distances come from the legacy reference geometry
    regardless of `symmetric_geometry`; when `False`, they come from the real
    `self._geometry_xy` positions (the Phase 4 path).
  - `reseed_topology()`: the ONLY thing that changes `topology_seed` (a new
    dedicated verb, deliberately NOT in `TUNABLE`/the generic config panel) —
    regenerates positions in place WITHOUT calling `_build()`, so every learned
    weight/confidence value and the current pattern/probe/auto-cycle state
    survive untouched.
  - `TUNABLE`/`apply_config()`: added `symmetric_geometry`/
    `legacy_distance_compat` as bool-coerced dashboard ablation toggles
    (rebuilds the network, like every other config toggle); `topology_seed`
    deliberately excluded.
  - `topology()`: new `geometry` descriptor (`symmetric`, `topology_seed`,
    `legacy_distance_compat`, `legacy_distance_compat_active`) so the UI can
    clearly label when distance/influence numbers are the temporary pinned
    placeholder rather than computed from the visible coordinates.
- `backend/api.py`: new `POST /api/reseed_topology` endpoint.
- `backend/presets.py`: `DASHBOARD_PRESET` now sets `symmetric_geometry=False`
  (the live dashboard shows the new jittered/irregular geometry) and
  `legacy_distance_compat=True` (dynamics stay pinned to the legacy baseline),
  with an explicit comment flagging Phase 4 as where this is expected to flip.
- `frontend/inspector.js`: a visible "legacy-distance compat active" notice
  card plus a `⚠`-marked, differently-colored delivery readout on every
  synapse row when `topology.geometry.legacy_distance_compat_active` is true —
  the pinned numbers are never shown as if computed from the displayed
  coordinates.
- `frontend/index.html` / `frontend/controls.js`: a "Reseed Topology" button
  (geometry-only; no confirmation dialog, since unlike Reseed/Reset it does
  not wipe learned state) so the feature — and Fit View reacting to new
  positions — is actually exercisable from the dashboard.
- `test_geometry_phase.py` (new) — 19 tests: legacy-ablation exact
  reproduction, seed reproduction (same/different topology_seed), fixity
  across reset/training/weight-reseed/probe/apply_config, `reseed_topology()`
  changes positions but preserves weights (and is a no-op under
  `symmetric_geometry=True`), spatial bounds (L1E cell confinement, L1I
  pairing, L2E placement radius, L2I center, z-coordinates unchanged),
  irregularity (>10 distinct pairwise L2E distances vs. the legacy ring's 6),
  minimum separation across 5 seeds, serialization (`geometry` descriptor +
  per-synapse delivery fields under the new geometry), the compat shim's
  distance-pinning in both directions, and the phase's central guarantee —
  `DASHBOARD_PRESET`'s new geometry produces a byte-identical winner sequence
  and final weights to what it would have produced before this phase.

### Phase 2 (prior checkpoints `9163da2`/`05c17a0`)

#### Milestone 2 — frontend

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

#### Milestone 1 — backend core (prior checkpoint `9163da2`)

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

### Phase 4 (this checkpoint)

- `test_influence_phase.py` (new, focused): **18/18 passed**.
- `pytest -q` (full suite): **168 passed, 5 failed** (150 prior + 18 new =
  168; same 5 pre-existing failures as every prior checkpoint, untouched).
- **Legacy/baseline equivalence:** `sustained_dominance.py`/
  `ablation_harness.py` (unmodified) still reproduce the Phase 1 numbers
  exactly; `test_disabled_equivalence_dashboard_preset_unaffected_by_new_params_existing`
  confirms `DASHBOARD_PRESET` (which does not set any of the four new flags)
  produces byte-identical winners/weights across a fresh 600-step run;
  `test_dashboard_preset_does_not_enable_any_new_pathway` asserts this
  directly against the preset dict, not just observed behavior.
- **Close vs. distant delivery, per pathway** (brief requirement, tested
  precisely, not just qualitatively):
  - L2E→L2I / L2E→L1I: `effective_weights()` at `d==ref==min` returns the RAW
    weight exactly (influence==1.0); at `d==5×ref` returns strictly less.
  - L1I→L1E: tested via a **direct** `apply_inhibition()` call (not the full
    engine loop) because L1E's pixel drive delivers exactly its own threshold
    with zero margin — ANY nonzero inhibition already fully suppresses firing
    regardless of magnitude, so the pathway's real, correctly-applied effect
    is not reliably observable in whether L1E ends up spiking (see Known
    problems). Direct test: close (`d==ref`) delivers the full discharge
    (potential → 0 exactly); distant (`d==2×ref`, power=2) delivers exactly
    25% (potential → 750.0 exactly) — confirming both the scaling AND that it
    is not squared (would be 6.25% / potential → 937.5 if it were).
  - L2I→L2E: `apply_competitive_reset()` compared directly at
    `competitive_reset_influence=1.0` vs. `0.25` — the depression magnitude
    scales down accordingly while `v_post` (the unconditional reset) is
    `resting_potential` in BOTH cases, confirming the reset invariant survives
    untouched.
- **No influence-squared bug**, verified two ways: (1) direct numeric
  comparison of `effective_weights()`'s output against `raw*influence**1`
  (matches) and `raw*influence**2` (does not match); (2) the L1I→L1E
  close/distant test above, where a squared factor would have produced a
  visibly different (937.5, not 750.0) result.
- **Learning uses the raw, unscaled weight**, not the distance-scaled
  delivered value — verified for the E→I feedforward rule directly (heavy
  distance attenuation on the delivery side does not gate whether/how much
  the raw weight learns).
- **Reset stability / fixed influence:** per-connection distances (hence
  influence) are identical before/after 60 steps of training plus a 10-step
  probe, and only change on an explicit `reseed_topology()` call — mirroring
  Phase 3's positional-fixity guarantee, now re-verified at the influence
  level for all three geometry-dependent new pathways.
- **Avoid extreme amplification:** with all four new pathways simultaneously
  enabled (deliberately stress-testing the "don't enable together" guidance
  rather than avoiding it), every reported `influence_max` is `<= 1.0` and
  every pathway's `safe` flag is `True`.
- **Full-stack smoke test (real server):** ran `uvicorn backend.api:app`,
  confirmed `GET /api/pathway_influence` returns all five pathways with
  correct entry counts (72/8/8/72/9) and sane values, and that the seven new
  `infl_*` config keys appear in `GET /api/config` under `advanced: true`
  (collapsed "Advanced" panel — not surfaced as a new default control).

### Phase 3 (prior checkpoint `0e353cd`)

- `test_geometry_phase.py` (new, focused): **19/19 passed** — legacy-ablation
  exact reproduction, seed reproduction, fixity across reset/training/
  weight-reseed/probe/apply_config, `reseed_topology()` semantics, spatial
  bounds, irregularity, minimum separation (5 seeds), serialization, and the
  compat shim in both directions.
- `pytest -q` (full suite): **150 passed, 5 failed** (131 prior + 19 new =
  150; same 5 pre-existing failures as every prior checkpoint, untouched).
- **Legacy equivalence — the central guarantee of this phase, verified at
  three levels:**
  1. `sustained_dominance.py` / `ablation_harness.py --seeds 1 2 --epochs 3`
     (unmodified; never pass the new geometry kwargs) reproduce the Phase 1
     numbers exactly, unchanged since Phase 2.
  2. Per-L2E `distance` arrays are `np.array_equal` between
     `symmetric_geometry=True` and `symmetric_geometry=False,
     legacy_distance_compat=True` — the geometry-derived input to the neural
     equations is provably identical regardless of displayed layout.
  3. `test_dashboard_preset_with_new_geometry_is_dynamically_identical_to_pre_phase3`
     runs `DASHBOARD_PRESET` (new geometry) against an otherwise-identical
     config forced back to `symmetric_geometry=True` (what it would have been
     before this phase) for 600 steps across all 4 training patterns: the
     **exact winner-sequence and final learned weights are identical**, not
     just aggregate statistics.
- Irregularity/separation verified numerically, not just by construction: a
  live-instance check found 27 of 28 possible pairwise L2E distances distinct
  (vs. the legacy ring's 6), with the enforced 1.3 minimum comfortably cleared
  (observed minimum 1.81 at `topology_seed=42`).
- **Full-stack smoke test (real server):** ran `uvicorn backend.api:app`,
  confirmed `topology.geometry` reports the new seeded state
  (`symmetric: false, legacy_distance_compat_active: true`) with genuinely
  irregular L2E positions (e.g. `L2E0 [1.663, 0.506, 4.0]`, nothing on a
  ring), and that `POST /api/reseed_topology` redraws positions live (new
  `topology_seed` returned, new coordinates on the next `/api/state` read)
  without disturbing the running network.
- Fit View's actual on-screen camera motion was not screenshotted (no browser
  in this environment, same limitation as Phase 2) — but its only input
  (`topology.neurons[i].pos`) was confirmed to carry real, varied, non-ring
  coordinates from the live server, and `renderer.fitView()` itself is
  unchanged code from Phase 2 (already reviewed).

### Phase 2 (prior checkpoints, unchanged by this phase)

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
  still unsolved and NEITHER Phase 2, 3, nor 4 fix it by default — the four
  new Phase 4 pathways are all off in `DASHBOARD_PRESET`, so the live
  dashboard's actual behavior is unchanged from Phase 3. See
  `Geometric_Influence_Temporal_Winner_Audit.md` for the full list of
  confirmed conflicts still awaiting a decision. Finding (2)'s
  perfect-ring-geometry concern is addressed for placement/rendering (Phase 3)
  and now has REAL, audited, opt-in influence pathways available for L2E→L2I/
  L2I→L2E/L2E→L1I/L1I→L1E (Phase 4) — but L1E→L2E itself (the pathway that
  concern was originally about) still runs under the `legacy_distance_compat`
  shim by default, so IT still hasn't been flipped over to the real new
  geometry. That flip was the original Phase 4 plan anticipated at the end of
  Phase 3; the ACTUAL Phase 4 instruction took a narrower, additive path
  instead (new isolated pathways, legacy pathway untouched) — flagged here so
  future work knows that flip is still on the table, separately, if wanted.
- **L1I→L1E's influence is real and correctly applied, but not reliably
  observable in whether L1E fires.** L1E's external-pixel drive delivers
  EXACTLY its own threshold with zero headroom (`e.weights=[-1,+1]*UNIT`,
  `thr_l1=1*UNIT` — "one pixel spike... fires the encoder in one hit," per
  the original module docstring). Any nonzero inhibitory discharge — scaled
  by distance-influence or not — already drops the post-inhibition potential
  below threshold, so L1E fails to fire either way. The pathway is verified
  correct at the mechanism level (`apply_inhibition`'s delivered magnitude
  provably scales with distance — see Tests), just not at the emergent
  spike/L2E level under the current L1 fixed-point design. If this pathway is
  meant to visibly change L1 spiking, L1E's threshold margin would need
  revisiting separately — out of scope for "isolated experimental behavior."
- `four-pattern` branch carries diagnostic/tracer work not yet reviewed for
  porting.
- The four new pathways currently share ONE power-law configuration
  (`infl_power`/`infl_ref`/`infl_min`), not independently tunable per pathway.
  A scope decision for simplicity/parameter-surface reasons — easy to split
  into per-pathway triples later if independent tuning turns out to matter.
- `pathway_influence_report()`/`GET /api/pathway_influence` is diagnostic-only
  (on-demand GET), not pushed with every `dynamic_state()` frame or surfaced
  in any frontend view yet — no UI change was made this phase (the
  instruction was backend/audit-focused; the existing generic config panel
  already exposes the four new toggles + power-law sliders under "Advanced"
  with no frontend code changes needed).
- Presentation boundaries are scoped to NAMED pattern/probe switches only
  (`set_pattern`/`present_probe`); raw pixel/random/noise edits do not start a
  new presentation record. Documented, not a bug — free-form manual input was
  never part of the brief's presentation protocol.
- Tie detection (`same_step_tie`) is validated against the default
  event-driven/chunked-charge path (what the live dashboard actually runs);
  the legacy `lasting_inhibition`/`event_driven=False` branches are wired
  (`_last_eligible` is set in both) but not separately tested here.
- No literal browser was opened for Phase 2 or Phase 3 (none available in
  this environment); Fit View / boundary-marker visuals were verified by code
  review plus confirmed-correct upstream data, not a screenshot. Flagged for a
  human or a browser-capable session to eyeball if desired.
- `topology_seed` is NOT persisted across a server restart (unlike the
  weight-init `seed`, which is deliberately persisted to `.claude/dashboard_seed.txt`
  — see `_load_seed`/`_save_seed`). A restart currently returns to
  `topology_seed=1`'s geometry. This was a deliberate scope decision (the
  instruction only required fixity across reset/training/probes, not across
  restarts) — flagged in case the user wants restart-persistence added later.
- `L2E_PLACEMENT_RADIUS=3.6` / `L2E_MIN_SEPARATION=1.3` were chosen to keep
  the new layout roughly the same visual scale as the legacy ring (radius 3.2)
  while giving the rejection sampler comfortable room (observed min separation
  well above the floor across the seeds tested) — not derived from any brief
  requirement beyond "bounded" and "minimum separation enforced". Revisit if a
  tighter/looser packing is wanted.

## Next action

Phase 4 is closed. No further phase is currently instructed. Candidates for a
future phase, none started, all needing their own explicit go-ahead:
- Actually experiment with the four new pathways one at a time (per "do not
  enable every pathway together") and observe effects on ownership/dominance
  metrics — the infrastructure is ready (`pathway_influence_report()`,
  per-pathway toggles) but no experiment has been run yet.
- Revisit whether to flip `legacy_distance_compat=False` for the ORIGINAL
  L1E→L2E pathway (the plan anticipated at the end of Phase 3) — this is the
  one change in this whole area still expected to alter baseline dynamics
  when it happens, so it should stay a deliberate, separately-approved step.
- Whether `topology_seed` should persist across a server restart like the
  weight-init `seed` does (currently does not — see Known problems from
  Phase 3, still applicable).
- Whether the four new pathways should get independent per-pathway power-law
  configs instead of the current shared one.
