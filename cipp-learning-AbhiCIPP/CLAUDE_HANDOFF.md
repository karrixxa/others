# CLAUDE_HANDOFF.md

## Branch / HEAD

- Branch: `july14-integration` (created from `july14`)
- HEAD at creation: `6195ef8` (july14 was clean, up to date with
  `origin/july14`)
- Phase 0 checkpoint commit: `b02cd9e` (added `CLAUDE.md` +
  `CLAUDE_HANDOFF.md`)
- This update corresponds to the Phase 1 audit checkpoint (commit hash filled
  in after this commit lands — see repo log).
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

- No porting/implementation work has started. Per brief §15's proposed
  sequence, Phase 1 (preserve baseline / audit) is what this session
  completed; Phase 2 (centralize config + learning-rule functions) is next,
  pending user direction on which conflict to resolve first.

## Files changed

- `CLAUDE.md` (Phase 0, already committed in `b02cd9e`)
- `CLAUDE_HANDOFF.md` (this update)
- `Geometric_Influence_Temporal_Winner_Audit.md` (new — full Phase 1 audit)

No source files (`backend/`, `neuron_flexible.py`, `layers.py`, `snn/`,
`frontend/`, tests, etc.) were modified. No mechanisms were touched.

## Tests

- `pytest -q` (unmodified): **117 passed, 5 failed**. All 5 failures are
  pre-existing and confirmed unrelated to this session (no code touched):
  `test_assembly_flow_credit.py::test_integration_four_pattern_regime_is_active_and_bounded`
  and 4 in `test_flow_rate.py` — all exercise `excitatory_flow_rate`, which
  `backend/api.py` now pins off unconditionally in `_build`, so these tests'
  premise (flow-on changes behavior) appears stale versus current engine
  behavior. Flagged for whoever picks up flow-rate/chunked-charge work next;
  not fixed here.
- `sustained_dominance.py` (unmodified): baseline mean over 4 seeds
  `distinct=2.00/4, sustained_dominance=0.497, dead=5.00` — matches
  `AGENT_HANDOFF.md`'s documented current state.
- `ablation_harness.py --seeds 1 2 --epochs 3` (unmodified, small run):
  `dom=0.39±0.015, distinct=2/4, collisions=2, dead=5`.
- No diagnostic output files were committed (throwaway venv + run outputs
  live outside the repo; numbers transcribed into the audit doc instead).

## Known problems

- Per `AGENT_HANDOFF.md`, true one-to-one L2E ownership is still unsolved
  (sustained dominance ≈0.5, ~2/4 distinct specialists this session,
  matching the historical range). The audit's headline findings (latest-spike
  winner label, perfect-ring geometry, non-selective L1I) are strong
  candidates for *why* — see `Geometric_Influence_Temporal_Winner_Audit.md`'s
  classification summary for the full list of conflicts that need a decision
  before implementation starts.
- `four-pattern` branch carries diagnostic/tracer work (e.g. L2I extinction
  tracer) that has not been reviewed for what, if anything, should be ported.
- Dashboard (`backend/api.py`) and CLI diagnostics (`ablation_harness.py`,
  `stage_learning_harness.py`) run materially different behavioral presets
  (distance-weighting, structural-free-energy, loser-depression, hard-reset
  flags all differ) — diagnostic results are not apples-to-apples with live
  dashboard behavior until this is reconciled (brief §13).

## Next action

Per brief §15 Phase 2 ("centralize configuration and learning rules"): decide,
with the user, which of the audit's confirmed conflicts to resolve first —
the leading candidate is the latest-spike-vs-first-spike winner definition,
since it likely undermines every ownership/dominance metric currently in use
and blocks meaningfully measuring any geometry/influence change. Do not start
implementation until that decision is made; this audit's job was to separate
confirmed behavior from hypothesis, not to fix anything.
