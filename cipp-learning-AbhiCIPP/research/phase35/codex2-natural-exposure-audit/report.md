# Phase 35 natural exposure and timing audit

## Verdict

`NATURAL_EXPOSURE_INSUFFICIENT`

Natural coincidence exposure produced thousands of correct local decoder
updates, but no decoder synapse matured and no prediction-column neuron fired in
any of five 3,200-step runs. The shadow mechanism therefore never became
physically available during the tested schedule.

## Isolation and configuration

- Checkout: `/home/cxiong/codex-runs/codex2-phase35-natural-exposure-checkout`
- Branch: `phase35-natural-exposure-codex2`
- Commit: `db30ceadbe18cf90e01f6d54dee0203f342b24a8`
- Initial and final production status: clean
- Claude checkout shared or accessed: no
- Production source edits: none
- Artifact commit: none; artifacts are outside the production repository

The schedule is the repository's established primary ownership schedule: 40
equal-interleaved rotations of `row 1`, `col 1`, `diag \`, `diag /`, with 20
steps per presentation, topology seed 1, and weight seeds 1–5. No live Claude
configuration artifact was present, so this was resolved from the established
Phase 27/diagnostic schedule constants rather than from Claude's checkout.

Shadow flags:

- `prediction_column_enabled=True`
- `prediction_column_to_i_enabled=False` (no physical PC-to-local-I delivery)
- `confidence_consolidation=False` (passive confidence decay path off)
- `loser_depression=False`
- `l2e_budget=False` (global weight normalization off)
- `homeostasis=False`
- prediction eta 0.15, decoder maximum 1200, initial decoder weight 50,
  lateral basal weight 150, soma threshold 500, feedback delay 1

No threshold, delay, geometry, inhibition, leak, rate, equation, or queue
setting was changed from the selected shadow configuration.

## Smoke and five-seed run

The two-cycle seed-1 smoke passed before the five full runs. It found no
default-off difference, inactive-pixel update, immediate crossing fire, lost
event, or duplicate event. The three plain-Python harness tests also passed.

| Seed | Classification | Persistent collision | First PC spike | Mature d / 72 | Mature columns | Max d | Active updates | Stale arrivals |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `NO_PERSISTENT_COLLISION` | none | none | 0 | 0 | 114.872193 | 4,851 | 1,143 |
| 2 | `NO_PERSISTENT_COLLISION` | none | none | 0 | 0 | 113.398149 | 4,878 | 1,059 |
| 3 | `MECHANISM_UNDEREXPOSED` | step 940 | none | 0 | 0 | 146.896616 | 4,137 | 1,041 |
| 4 | `NO_PERSISTENT_COLLISION` | none | none | 0 | 0 | 133.440157 | 4,473 | 903 |
| 5 | `NO_PERSISTENT_COLLISION` | none | none | 0 | 0 | 136.983583 | 4,560 | 1,215 |

Each run completed all 160 presentations and 3,200 steps before prediction
became available: fraction 1.0 and 160 presentations. No run has a first mature
sensory-plus-feedback coincidence, first physical PC spike, or counterfactual
local-I delivery. Seed 3's persistent collision therefore begins before
availability; the other four have no persistent collision by the established
running-modal metric.

The first physical L2E response for every pattern, earliest transient overlap,
persistent onset, all 72 update counters, maturity crossings, PC events, and
stale queue arrivals are recorded per seed in `results.json` and chronologically
in `timeline.csv`.

## Exposure, maturity, and locality

Across five runs there are 22,899 decoder updates, all on pixels active in the
origin pattern and zero on inactive pixels. Yet updates are distributed across
39–48 nonzero source-target associations per seed. The most-exposed individual
synapse receives 487–768 updates, leaving each seed's maximum decoder weight
between 113.398149 and 146.896616—far below the established effective
single-source maturity value 350.

Mature synapses: 0/72 in every seed. PC columns with a mature source: 0/9.
Per-pattern mature expected-pixel coverage: 0/3 for every pattern and seed.
Unwanted mature coverage in the other six pixels: zero.

The mean current-step coincidence rate is 0.154917 per PC cell-step (individual
seed range 0.138021–0.167083). Coincidence is therefore physically common, but
source-target-specific exposure is too diffuse for the slow bounded update to
mature naturally during 40 rotations.

No maturity crossing occurred, so the crossing-event ordering invariant was
not exercised naturally. It was not violated. No default-off or locality
invariant disagreement occurred.

## Ownership and feedforward compression indicators

The harness reused established measurements only: physical first responders,
running-modal transient/persistent collisions, L2E status, active-cell count,
first-responder share, and center/peripheral feedforward-weight ratio. It did
not introduce a new compression threshold.

Transient modal overlaps occur early in all seeds and self-correct in four. Seed
3 locks into a persistent collision at presentation index 47 / step 940, with
`L2E3` modal for `row 1` and `diag /`. Its end state has three active L2E cells
and three neurons that never become first responders, while prediction remains
unavailable. Full per-seed compression indicators are in `results.json`.

## Queue carryover

Repaired switch carryover is common, not merely semantic. There are 5,361 stale
arrivals among 99,762 recorded arrivals (5.374%). Every stale arrival records
source step, intended arrival step, origin/current pattern, target, and origin
class in the JSON/CSV timeline.

No due event was lost or delivered twice. Seeds with 12 undelivered tail events
have only events whose arrival step is at or beyond the run endpoint; they are
still pending, not lost. Queue locality and exactly-once invariants pass.

## Answers to the required questions

1. **Does natural decoder maturation occur at all?** No, not within any tested
   3,200-step/160-presentation run.
2. **Does it occur before ownership collisions lock in?** No. Seed 3 collides at
   step 940 with no mature synapse by step 3,200; the other seeds do not lock a
   persistent collision but also never make prediction available.
3. **Is there enough exposure for B-versus-C to test active suppression fairly?**
   No. Condition C would receive no PC-driven local-I event in these runs.
4. **If C fails, ineffective or too late?** Under this schedule, failure cannot
   establish ineffectiveness because the mechanism never becomes available. It
   is underexposed, not merely a late weak actuator.
5. **Do repaired carryover events matter naturally?** They are common: 5.374% of
   arrivals are stale across switches. They are not a rare semantic corner.

## Commands, runtime, and tests

Commands executed:

```text
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ...direct test functions... PY
PYTHONDONTWRITEBYTECODE=1 python3 run_natural_exposure_audit.py --smoke-only
PYTHONDONTWRITEBYTECODE=1 python3 run_natural_exposure_audit.py
```

Test results: 3/3 harness tests passed. Smoke runtime: 0.405 seconds. Final
five-seed command runtime: 46.707 seconds. An earlier valid five-seed execution
took 46.594 seconds; it was repeated solely to add per-event stale-arrival rows
to the required timeline, with the same classifications and invariant results.

No Gate C, ownership A/B/C duplication, parameter grid, manual maturation, or
production change was performed. No audit processes remain running.
