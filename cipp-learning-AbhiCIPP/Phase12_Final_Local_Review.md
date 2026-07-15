# Phase 12 — Final Local Review (july14-integration)

**DO NOT PUBLISH.** This is a local-only review and handoff document. No code
was pushed, merged, or opened as a PR while producing it. No new neural
mechanism was implemented in this phase, and nothing was tuned around
Phase 11's validation results — the two mechanism-level findings below
(a backend/UI config gap, one remaining software tiebreak) were FOUND and,
in the config-gap case, fixed as a documentation/consistency correction, not
a neural-dynamics change.

## Scope

Continues directly from Phase 11 (`1a59ae8`). Covers Phases 6 through 11 as
a whole, since this is the final review of the entire corrected Phases 6-12
prompt sequence before the branch is handed off for human review.

## 1. Full test suite

`pytest -q` (full repo): **254 passed, 5 failed.**

The 5 failures are the same, pre-existing, unrelated set present at every
checkpoint since before Phase 6:
- `test_assembly_flow_credit.py::test_integration_four_pattern_regime_is_active_and_bounded`
- `test_flow_rate.py::test_flow_off_is_baseline`
- `test_flow_rate.py::test_flow_builds_charge_smoothly`
- `test_flow_rate.py::test_flow_can_cross_threshold_without_new_input`
- `test_flow_rate.py::test_flow_forces_single_chunk`

All 5 stem from the same root cause, documented since Phase 2/7's
checkpoints: `backend/simulation.py`'s `_build()` permanently pins
`excitatory_flow_rate`/`l2i_excitatory_flow_rate`/`inhibitory_flow_rate`/
`assembly_flow_credit` to `False` regardless of constructor kwargs (the
"SWAP + NEUTER" block, reversible by design), so the flow-rate feature these
tests exercise is deliberately inert in the current engine. Confirmed
unchanged in this phase — same 5 names, same failure messages, verified by
diffing this run's summary against Phase 7/8/9/10/11's recorded numbers in
this same file.

**254 = 220 (Phase 10 checkpoint) + 6 (Phase 11's `test_phase11_validation.py`)
+ 28 test collection change from this phase's own work: 0 new test files
were added in Phase 12** (this phase is review/consistency-fix only, per its
own scope). The `+6` from Phase 11's test file plus no Phase-12-specific
tests fully accounts for the 248→254 jump already recorded at the Phase 11
checkpoint; this run re-confirms it after Phase 12's `backend/api.py` fix.

## 2. Final end-to-end smoke checks

Beyond the unit/integration suite, this phase ran REAL, live-server-shaped
smoke checks that had not been possible in earlier checkpoints (Phase 7's
Known Problems flagged `starlette.testclient` as unavailable —
`httpx2` was installed into the session's throwaway venv this phase,
closing that gap):

- **REST, via `fastapi.testclient.TestClient(app)`:**
  - `GET /api/state` → 200; `dynamic.l2_inhibition`, `dynamic.adaptive_threshold`,
    and `dynamic.causal_story.l1i_first_source_set` all present and
    well-formed in the actual served JSON (not just in unit-level
    `dynamic_state()` calls).
  - `GET /api/config` → 200; every Phase 3/7/10 config key (see §3) is
    present in the served `spec`.
  - `POST /api/config` with `{adaptive_threshold: true, l2_inhibition_frac:
    0.7, symmetric_geometry: true}` → 200, `applied` echoes exactly those
    three keys; a follow-up `GET /api/state` shows
    `adaptive_threshold.enabled == True` and `l2_inhibition.magnitude ==
    5600.0` (`0.7 * threshold_l2(8000)`) — the live config round-trip
    actually changes engine behavior, not just accepted-and-ignored.
  - `POST /api/step` → 200.
  - `GET /api/pathway_influence` → 200.
- **WebSocket, via `TestClient.websocket_connect('/ws')`:** first message is
  `{"type": "topology", ...}`; sending `{"action": "step"}` yields
  `{"type": "dynamic", "data": {...}}` with `l2_inhibition` and
  `adaptive_threshold` both present in the streamed payload — the actual
  live-dashboard data path (not just the REST snapshot) was exercised
  end-to-end.

All of the above ran against a throwaway `TestClient` instance in an
isolated process; nothing was left running, and no state persisted outside
that check.

## 3. Configuration names, defaults, and backend/UI agreement

Audited `SimulationEngine.TUNABLE` (engine-side, source of truth for what
`apply_config` accepts) against `backend/api.py`'s `CONFIG_SPEC` (what the
dashboard's config panel can actually reach) in both directions:

**Found and fixed:** `symmetric_geometry`/`legacy_distance_compat` (Phase 3),
`l2_inhibition_delay`/`l2_inhibition_frac` (Phase 7), and
`adaptive_threshold`/`delta_threshold_frac`/`tau_threshold` (Phase 10) were
all `TUNABLE` on the engine but **absent from `CONFIG_SPEC`** — a real
backend/UI disagreement gap. The Phase 3 half of this gap predates Phases
6-12 entirely (introduced when `symmetric_geometry` was added, never
surfaced to the dashboard); the Phase 7/10 half was introduced by this
session's own work and had gone unnoticed until this review. Fixed by adding
all 7 keys to `CONFIG_SPEC` with matching `label`/`kind`/`min`/`max`/`step`/
`desc` entries, following the file's existing format exactly; left them
`advanced: true` (not added to `_MAIN_CONFIG_KEYS`), consistent with how
Phase 4's four `infl_*` pathways were treated (experimental/secondary
controls, not main-panel). Verified via the live HTTP round-trip in §2, not
just static inspection.

**Confirmed, NOT fixed (correctly out of scope):** nine `TUNABLE` keys
remain unexposed in `CONFIG_SPEC` — `conf_cap_frac`, `eta_min`,
`hard_reset_clear_traces`, `inhibitory_delta_eta`, `inhibitory_margin_frac`,
`inhibitory_rule_mode`, `l2i_excitatory_flow_rate`, `l2i_hard_reset_losers`,
`seed`. All predate Phase 6 (most are explicitly noted elsewhere in this
file or in `backend/api.py`'s own comments as archived/inert/legacy —
`seed` is deliberately handled by its own load/save mechanism, not the
generic panel, mirroring `topology_seed`). None of these were touched by
Phases 6-11's work; closing them is unrelated scope and was left alone per
Phase 12's "do not implement new neural mechanisms" constraint (this is a
config-surface question, arguably fine to fix, but bundling nine
unrelated legacy-knob decisions into a "final review" commit risks
obscuring what Phases 6-12 actually changed — flagged as a candidate for a
future, explicitly-scoped cleanup pass instead).

Every key present in `CONFIG_SPEC` is confirmed `TUNABLE` on the engine
(zero orphaned UI controls that would silently no-op).

## 4. Probe restoration

Not re-implemented or newly tested in Phase 12 (already covered
extensively): `_set_plasticity_frozen`/`present_probe`/`_end_probe`'s
weight/confidence freeze (Phase 2), the representation-candidate reset at
probe start (Phase 6), the Phase 7 delayed-inhibition delivery continuing to
apply physically during a frozen probe while skipping only its structural
depression, and Phase 10's `threshold_adapt` snapshot/unconditional-restore
(both the natural-elapse and cancelled-by-manual-input exit paths) are all
covered by dedicated, currently-passing tests
(`test_observability_phase.py`, `test_representation_candidate.py`,
`test_l2i_causal_inhibition.py`, `test_l1i_causal_feedback.py`,
`test_adaptive_threshold.py`). Re-ran the full suite (§1) as this phase's
verification that all of them still hold together, rather than duplicating
their assertions here.

## 5. Deterministic seeds

Not re-implemented or newly tested in Phase 12: seed-based reproducibility
is covered by `test_adaptive_threshold.py::test_deterministic_replay`,
`test_phase11_validation.py::test_harness_is_deterministic`, and the
`sustained_dominance.py`/`ablation_harness.py`/`diagnostic_schedule.py`
scripts' own seed-driven design (same seed → same weight-init RNG stream →
same run, confirmed identical across every phase checkpoint that re-ran
them). `topology_seed` (geometry) and `seed` (weight init) remain
independent, as designed since Phase 3. No non-determinism was introduced
by Phases 6-12: every new engine attribute added (`_l2i_pending`,
`threshold_adapt`, `l1i_first_source_set`, etc.) is a pure function of prior
engine state and step count, never of wall-clock time or an unseeded RNG
call.

## 6. No software winner/tie-break shortcut remains — audit result

Grepped the full engine (`backend/simulation.py`) for `argmax`/`key=lambda`/
hidden-charge tiebreak patterns and checked every hit:

- `_resolve_l2_competition()` (the default, `event_driven=True` path — the
  one `DASHBOARD_PRESET` and every prior checkpoint's diagnostics actually
  exercise): confirmed clean. Every threshold-crosser fires; no argmax pick
  decides who physically fires (Phase 7).
- `_credit_source()`: confirmed clean, and actively IMPROVED this session
  (Phase 9) — ambiguity is now determined by the real per-step firer count
  (`self._last_eligible`), never an index/hidden-charge fallback.
- `_track_presentation()`'s `step_winner_idx = int(np.argmax(l2e))`: this
  IS an `argmax` call, but on a one-hot-or-multi-hot BINARY vector where
  every set bit is an ACTUAL physical firer this step — it picks which
  *already-fired* neuron's id to use as the raw `first_spiker` FACT when
  several fired simultaneously, never used to decide who fires or to award
  representation-candidate credit (that's `self.winner`, which stays `None`
  on a genuine tie regardless of this index). Documented as intentional
  since Phase 7's own handoff entry; reconfirmed here, not a shortcut.
- `_auto_cycle_tick()`'s `self._visit_spikes.argmax()`: decides which
  pattern auto-cycle's own curriculum bookkeeping logs as "trained" (a
  UI/logging convenience), never feeds back into `self.winner`, physical
  firing, or learning. Out of scope for the representation-candidate
  invariant.
- **`lasting_inhibition`'s branch (line ~2034,
  `winner = max(eligible, key=lambda j: l2.excitatory_neurons[j].potential)`):
  a genuine, remaining software tiebreak by hidden membrane charge.** This
  is the ONE other per-step L2 competition mechanism in the codebase besides
  `_resolve_l2_competition` — a pre-existing, `default=False`, opt-in
  ALTERNATE mechanism (a decaying shared inhibitory field) that Phase 7
  explicitly did not touch (documented in Phase 7's own "Files changed" as
  out of scope: `_resolve_l2_competition`, "the flagged 'legacy immediate-
  reset competition'", was the target — `lasting_inhibition` is a different,
  separately-named mechanism). It is NOT enabled by `DASHBOARD_PRESET` and
  was NOT exercised by any of Phase 11's 96 runs (none set
  `lasting_inhibition=True`). **Recorded here as an honest, unresolved
  finding, not fixed:** fixing it would mean redesigning a second,
  independent competition mechanism — squarely a "new neural mechanism"
  change, which this phase is explicitly barred from making. Flagged for a
  future phase if `lasting_inhibition` is ever meant to become a supported,
  non-experimental path.

**Conclusion: the default/dashboard competition path has zero remaining
software winner/tie-break shortcuts. Exactly one remains, confined to a
non-default, unexercised, pre-existing alternate mechanism, and is reported
rather than silently fixed.**

## 7. Phase 11 evidence vs. the stated success criteria

Full detail in `Phase11_Multiseed_Validation_Report.md`; summarized and
cross-checked here against the phase list's own success bar ("four distinct
stable pattern owners among the eight L2E neurons while spare neurons remain
recruitable... do not count one lucky seed as success"):

- **Not met, in any of the 16 (schedule × geometry × adaptive_threshold)
  conditions, across all 6 seed-topology combinations.** Best cell
  (short-interleaved, influence off, adaptive_threshold on): 4/6 — real and
  reproducible, but two seed-topology combinations still fell short, so per
  the instruction's own standard this is not a pass.
- Re-verified via `test_phase11_validation.py::test_success_criterion_evaluation_matches_recorded_data`
  (re-derives the 4/6 figure directly from the raw JSON, independent of the
  markdown report's prose) — still 4/6 on this final re-run.
- This is consistent with, and a direct continuation of, the Phase 1 audit's
  original finding: one-to-one L2E ownership was already known to be
  unsolved before Phase 6, and remains unsolved after Phases 6-10's causal-
  dynamics work. No phase in this sequence claimed to solve it outright;
  each replaced one specific mechanism with a more physically-grounded
  version (first-spike semantics, causal L2I competition, exact local
  free-energy learning, causal L1I feedback, adaptive threshold) and Phase
  11 measured where that collective work landed. It landed closer in some
  configurations (short-interleaved + adaptive threshold) than others
  (long-saturation; influence-on in short-interleaved), but not at the
  stated bar anywhere.

## 8. Unresolved failures — documented honestly

1. **Central ownership-consolidation problem remains open** (§7) — the
   single largest unresolved item across this entire 12-phase sequence.
2. **One software tiebreak remains**, confined to the non-default
   `lasting_inhibition` mechanism (§6).
3. **Nine legacy `TUNABLE` keys remain unexposed** in the dashboard config
   panel (§3) — pre-existing, out of this session's scope, not touched.
4. **`adaptive_threshold`'s effect is genuinely mixed**, not a clean win
   (Phase 11 §Conclusions) — it helps most conditions, is flat in one, and
   actively hurts one (short-interleaved, symmetric geometry + influence
   on).
5. **Distance-weighting "influence" has a schedule-dependent effect**
   (helps long-saturation, hurts short-interleaved) that Phase 11 measured
   but did not investigate the cause of.
6. **The 5 pre-existing flow-rate test failures remain unaddressed** (§1) —
   correctly out of scope for every phase in this sequence (they test a
   feature the engine permanently neuters by design), but flagged again
   here for completeness, since Phase 12 is the final checkpoint before
   handoff.

None of these were resolved by tuning parameters or adding new mechanisms in
Phase 12, per its explicit constraint.

## Final commit chain (this session, Phases 7-12)

```
1a59ae8  Phase 11: controlled multi-seed validation (measurement only)
d333945  Phase 10: adaptive-threshold ablation (separate from homeostasis, L2E only)
3dd6f4c  Phase 9: causal L1I predictive feedback (source/arrival/threshold/delivery)
c0ac363  Phase 8: exact local free-energy learning (delta_w = LR*FE*(1-w/w_max)^2*signal)
d946ff0  Phase 7: physical L2I competition (causal, delayed L2E->L2I->L2E events)
```

Plus this Phase 12 review (commit hash filled in after landing — see repo
log / `CLAUDE_HANDOFF.md`'s Branch/HEAD section). Phase 6 (`aa271fc`) and
earlier were completed in a prior session, per `CLAUDE_HANDOFF.md`.

## Working-tree / branch status at handoff

- Branch: `july14-integration`, based on `july14` (untouched, still the
  protected base).
- Working tree: clean except for generated `__pycache__` directories
  (never committed, correctly `.gitignore`-equivalent by convention — see
  every prior phase's commit hygiene).
- **Not pushed.** No remote branch created or updated. No PR opened. No
  merge performed. `four-pattern` remains unmerged (ported by hand only, per
  `CLAUDE.md`).
- Ready for human review at `d946ff0`..`<this commit>` on
  `july14-integration`. The "LATER PUSH PROMPT" in the corrected prompt file
  explicitly gates any push behind separate, explicit human confirmation
  after this review — not executed, not implied, not requested here.

## Conclusions

Phases 7-12 are complete, individually validated, and internally consistent
with each other and with Phases 0-6 from the prior session. The engine's
default/dashboard competition, learning, and feedback paths are free of
software tie-break shortcuts; the one remaining exception is isolated to a
non-default alternate mechanism and is documented rather than silently
patched. Backend/UI configuration surface is now consistent for every
mechanism this session touched. The central scientific question this whole
sequence was built around — can the architecture achieve stable one-to-one
L2E ownership — remains open, measured across 96 controlled runs rather than
asserted, with the honest result that no tested configuration reaches it
reliably. This branch is ready for human review; no further phase work was
started beyond this report.
