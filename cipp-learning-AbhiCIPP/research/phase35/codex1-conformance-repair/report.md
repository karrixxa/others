# Phase 35 conformance repair report

Verdict: **QUEUE_FIXED_MATURITY_WAS_ADAPTER_ERROR**

## Provenance

- Frozen starting commit: `4e712a4b7dea033b9191680a4b4e3577d93ca304`
- Repair commit: `db30ceadbe18cf90e01f6d54dee0203f342b24a8`
- Branch: `phase35-dendrite-classes-codex1`
- No Claude checkout or artifact was modified.

## Issue 1: pattern-switch queue deletion

The pre-fix regression failed because `_start_presentation` replaced both
physical delay queues with zero vectors. The smallest semantic fix removes that
deletion. Per-timestep compartment clearing and ordinary soma membrane/reset
behavior are unchanged.

A passive metadata deque now advances in lockstep with the existing physical
queues. It records source, target, target compartment, scheduled step, expected
arrival step, actual delivered step, and origin pattern. At arrival, telemetry
classifies the target pair as `current-correct`, `stale-same-pixel`,
`stale-wrong-pixel`, or `mixed`. Classification occurs after the physical
vectors are popped and routed and cannot alter delivery. The regression verifies
that a stale same-pixel pair survives the switch, delivers once, fires once, and
is absent on the following timestep.

## Issue 2: maturity mismatch

Classification: **oracle expectation mismatch**.

The direct production trace uses the exact reported values: `d=4`, `eta=1`,
`d_max=11`, maturity/soma threshold `5`, basal weight `0`. Production's
established equation is:

`delta = eta * (1 - d/d_max)^2`

The first unrounded delta is `0.4049586776859504`, stored as
`0.4049586776859506`, so `d_after=4.404958677685951`. The oracle expected a
fixed delta of `1`, which is not the production equation. A second production
event reaches `4.764417934239916`; neither value is mature, so neither next
event can fire. The third update reaches `5.085760774726105`; that current event
still does not fire because it used `d_before=4.764417934239916`. The fourth
valid coincidence uses the persisted mature value and fires. This demonstrates
correct pre-learning ordering and state persistence without changing any
parameter or production learning code. The complete factor-by-factor trace is
in `maturity_trace.json`.

## Tests

- Gate A: 6/6 pass.
- Repaired Gate B: 6/6 pass. Four unchanged Gate B checks pass; the old test
  that required queue deletion was replaced by carryover and four-class
  telemetry checks.
- New source regressions: 2/2 pass.
- Queue carryover standalone: pass.
- Direct production maturity trace: pass.
- Default-off equivalence: identical 100-step hashes
  `b1f78f6d545cf131da9ae2bdeb7744cffed1db83908db59f4589b2b7b045e3b6`.
- Full available standalone suite: 32 pass, 3 environment-blocked because
  `pytest` is unavailable, and 5 failures. Four opt-in Phase 19-22 failures
  reproduce unchanged on frozen `4e712a4`; the fifth is the established Phase
  29 golden drift. No failure was introduced by this repair.

No Gate C, ownership experiment, tuning, or unrelated cleanup was performed.
Nothing was pushed.

## Changed files

- `backend/simulation.py`
- `test_phase35_conformance_repair.py`
- `CLAUDE_HANDOFF.md`

## Bundle

- `phase35-conformance-repair-db30ceadbe18cf90e01f6d54dee0203f342b24a8.bundle`
- SHA-256: `1b330b7402913a5ed92402fba41f1105d687ca1ed080985bef470903f8c3587e`
