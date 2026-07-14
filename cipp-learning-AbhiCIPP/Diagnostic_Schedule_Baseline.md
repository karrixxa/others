# Diagnostic Schedule — Baseline (Phase 5)

Read-only baseline captured with `diagnostic_schedule.py` on `july14-integration`,
against `backend.presets.DASHBOARD_PRESET` (the live dashboard's exact config).
No engine/competition code was changed to produce this — see that file's module
docstring for the full non-mutating-evaluation methodology (a disposable engine
per seed for the live interleaved pass, plus a further deep-copied,
plasticity-frozen copy for the consistency re-test).

Command: `PYTHONPATH=. python diagnostic_schedule.py --seeds 1 2 3 4 5`
(defaults: `cycles=15`, `presentation_steps=20`, `consistency_reps=5`, cycle
order `row 1 -> col 1 -> diag \ -> diag / -> repeat`, equal interleaved
exposure, no pattern trained to saturation).

## Per-seed results

| seed | row 1 owner (consistency) | col 1 owner (consistency) | diag \ owner (consistency) | diag / owner (consistency) | distinct owners | collisions |
|---|---|---|---|---|---|---|
| 1 | L2E3 (0.47) | L2E4 (0.47) | L2E3 (0.67) | L2E4 (0.53) | 2/4 | L2E4:{col 1, diag /}, L2E3:{row 1, diag \\} |
| 2 | L2E0 (0.80) | L2E3 (0.93) | L2E3 (0.67) | L2E3 (0.60) | 2/4 | L2E3:{col 1, diag \\, diag /} |
| 3 | L2E5 (0.87) | L2E3 (0.93) | L2E3 (0.60) | L2E5 (0.80) | 2/4 | L2E3:{col 1, diag \\}, L2E5:{row 1, diag /} |
| 4 | L2E4 (0.67) | L2E1 (0.80) | L2E1 (0.53) | L2E1 (0.93) | 2/4 | L2E1:{col 1, diag \\, diag /} |
| 5 | L2E3 (0.87) | L2E5 (0.93) | L2E7 (0.93) | L2E5 (0.67) | 3/4 | L2E5:{col 1, diag /} |

**Mean over 5 seeds:** distinct owners = **2.20/4**; per-pattern consistency —
row 1 = 0.734, col 1 = 0.813, diag \\ = 0.680, diag / = 0.707.

## Silent / recruitable cells (per seed)

| seed | silent (never a first responder) | recruitable (fired first sometimes, never a modal owner) |
|---|---|---|
| 1 | L2E0, L2E1, L2E2, L2E6, L2E7 | L2E5 |
| 2 | L2E1, L2E2, L2E4, L2E5, L2E6 | L2E7 |
| 3 | L2E0, L2E1, L2E2, L2E4, L2E6 | L2E7 |
| 4 | L2E0, L2E2, L2E5, L2E6, L2E7 | L2E3 |
| 5 | L2E0, L2E1, L2E2, L2E6 | L2E4 |

Consistently 5 silent + 1 recruitable = 6 of the 8 L2E cells not acting as a
modal owner in this short (15-cycle) run — the architecture provides 4 spare
cells beyond the 4 needed; the sweep shows only 2-3 are actually recruited as
distinct owners within this window.

## Forgetting

Present in most seeds for at least one pattern (modal owner differs between
the first half and second half of that pattern's presentations within the
same run) — seed 1: row 1 changed; seed 3: diag \\ changed; seed 4: row 1
changed; seeds 2 and 5: no pattern changed owner within the run. Consistent
with `AGENT_HANDOFF.md`'s documented round-robin/no-stable-tiling state — this
diagnostic did not fix or investigate it further (observation only).

## L2I activity

Mean L2I spikes per presentation (20-step window): 4.12 - 4.63 across seeds
(total 245-278 over 60 presentations/seed). Global inhibition engages on the
large majority of presentations, consistent with the engine's per-step
event-driven competition resolving on nearly every volley.

## L1I selectivity

**All-nine-synchrony rate: 1.0 in every seed, with zero exceptions.** Every
single L1I-firing step in this entire baseline sweep (5 seeds x 60
presentations x up to 20 steps) fired all 9 positions together, never a
spatially-selective subset. This is an empirical, quantitative confirmation of
the Phase 1 audit's finding #3 (all 9 L1I units share one literal weight
vector and receive an identical scalar signal, so their synchrony is
structural, not a serializer artifact) — measured directly via the interleaved
schedule rather than inferred from code reading alone.

## Frozen-replay consistency re-test

Zero weight drift confirmed in all 5 seeds (`frozen_replay_zero_weight_drift =
True` every time) — the plasticity-frozen copy mechanism (reusing Phase 2's
`_set_plasticity_frozen`) held perfectly. Once frozen, first-responder
consistency per pattern is high but not always 1.0 (seed 2 row 1: 0.6; seed 4
row 1: 0.8, diag \\: 0.6; seed 5 diag /: 0.6) — meaning even with weights
completely fixed, the SAME pattern does not always evoke the SAME first
responder on repeated brief presentations. This isolates a genuine physical/
temporal source of variability (residual charge/timing at presentation
boundaries) from weight drift, and is a more precise measurement of
first-responder reliability than anything available before this phase.

## Scope note

This baseline reflects `DASHBOARD_PRESET` exactly as Phase 4 left it — no
competition, learning-rule, or preset value was changed to produce it (see
`CLAUDE.md` and the Phase 5 entry in `CLAUDE_HANDOFF.md`). Re-run the same
command after any future competition change to compare against this baseline.
