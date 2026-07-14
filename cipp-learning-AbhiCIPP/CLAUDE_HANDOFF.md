# CLAUDE_HANDOFF.md

## Branch / HEAD

- Branch: `july14-integration` (created from `july14`)
- HEAD at creation: `6195ef8` (july14 was clean, up to date with
  `origin/july14`)
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

- Ran git diagnostics: root, remote, branch, status, branch list, recent log.
- Confirmed `july14` was clean and `july14-integration` did not yet exist.
- Created `july14-integration` from `july14` (no other branch changes).
- Confirmed current `backend/simulation.py` already defines `N_OUT=8` over 4
  `PATTERNS`, matching the required invariant (`N_PIX=9`, ring layout,
  hard-reset competitive depression, no learned `L2I->L2E` gate).
- Authored `CLAUDE.md` with the permanent rules for this repo.
- Authored this file, `CLAUDE_HANDOFF.md`.

## In progress

- Nothing yet — no porting work has started. This session only established
  the branch and the governing docs.

## Files changed

- `CLAUDE.md` (new)
- `CLAUDE_HANDOFF.md` (new)

No source files (`backend/`, `neuron_flexible.py`, `layers.py`, tests, etc.)
were modified in this session.

## Tests

- None run yet — no behavior was ported or changed in this session.
- Existing test surface for reference: `test_*.py` at repo root plus
  `tests/golden/`. Use focused subsets relevant to whatever is ported next
  (e.g. `test_l2_competition.py`, `test_hard_reset_inhibition.py` for
  competition/inhibition changes).

## Known problems

- Per `AGENT_HANDOFF.md` (pre-existing, on `feature/inhibitory-plasticity`),
  true one-to-one L2E ownership is still unsolved: sustained-presentation
  dominance under the current signed-spike regime is ≈0.55 with only ≈4/8
  distinct specialists and high seed variance. This is the problem the
  geometric-influence/temporal-winner brief is trying to address; it is not
  yet fixed on this branch.
- `four-pattern` branch carries diagnostic/tracer work (e.g. L2I extinction
  tracer) that has not been reviewed for what, if anything, should be ported.

## Next action

Read `July_14_Geometric_Influence_Temporal_Winner_Brief.txt` section by
section against the current `backend/simulation.py` / `neuron_flexible.py`
implementation, identify the first concrete behavior to port from
`four-pattern` (by hand, not merge), and define it as the first milestone of
this phase.
