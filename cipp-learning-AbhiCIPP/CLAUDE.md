# CLAUDE.md — Permanent Rules for this Repo

These rules are permanent and apply to all work in this checkout. They persist
across sessions and survive context resets. Do not remove or weaken them
without explicit user approval.

## Required reading

- Read `July_14_Geometric_Influence_Temporal_Winner_Brief.txt` by relevant
  section before working on any topic it covers (geometry, competition,
  self-organization, L2I/L1I dynamics). Do not rely on memory of it — re-read
  the section that applies to the current task.

## Design priorities

- Biological plausibility and local physical dynamics take priority over
  computational convenience or clean classification metrics. When a design
  choice conflicts with this, prefer the biologically grounded option.

## Architecture invariants

- Four center-crossing patterns (row 1, col 1, diag \, diag /). Keep
  `N_OUT=8` for the L2E pool: four cells actively specialize, four remain
  spare/recruitable overcapacity. Do not shrink the pool to exactly four or
  otherwise couple `N_OUT` to `len(PATTERNS)`.
- No pattern-to-neuron assignments. No argmax representative. No owner lock.
  No oracle. No global `normalizeW`. No fake raster spikes. No UI-side
  simulation. If a change would introduce any of these, stop and flag it
  instead of implementing it.

## Branch discipline

- Work only on `july14-integration`. `july14` remains the protected base —
  never commit or push directly to it.
- Do not merge `four-pattern` into `july14-integration`. Port behavior only:
  re-implement the relevant logic by hand, reviewed against the priorities
  above, rather than merging or cherry-picking wholesale.
- Local commits are authorized at any time. Pushing to any remote requires
  explicit user approval — never push without asking first.
- Never run `git reset`, `git clean`, `git stash`, `git restore`, `git
  checkout -- <path>`, `git push --force`, or any other discard/rewrite
  operation without explicit user approval.

## Workflow

- Divide each phase of work into coherent milestones.
- After every milestone: run the focused tests for what changed, update
  `CLAUDE_HANDOFF.md`, make a local checkpoint commit, then continue the same
  phase. Do not stop between milestones unless blocked.
- If context may expire before a milestone is done: stop starting new work,
  test what already exists, update `CLAUDE_HANDOFF.md`, and commit with
  message `WIP: preserve unfinished <task>`.
- Never commit caches, virtual environments, or generated diagnostic outputs
  (e.g. `__pycache__/`, `.venv/`, ad-hoc report artifacts). Check `git status`
  before committing and exclude anything generated.
- At the end of each phase: run the regression tests, update
  `CLAUDE_HANDOFF.md`, commit, report to the user, and stop for review.
