# Phase 35 long-horizon maturity kinetics audit

## Verdict

`MIXED_MATURITY_FAILURE`

All five shadow seeds mature naturally by 25,600 steps, so maturity is neither
prevented nor plateaued. Timing relative to ownership is mixed: seed 3 locks a
persistent collision at step 940 and first matures at step 13,745; the other
four seeds have no persistent collision and first mature between steps 17,132
and 24,332. The original 3,200-step insufficiency is primarily short elapsed
time amplified by strong source fragmentation, with collision-related source
capture in the one collision-bearing seed.

## Isolation and fixed configuration

- Checkout: `/home/cxiong/codex-runs/codex2-phase35-natural-exposure-checkout`
- Local audit branch: `phase35-natural-exposure-codex2`
- Repaired production commit: `db30ceadbe18cf90e01f6d54dee0203f342b24a8`
- Production status before and after: clean
- Production edits: none
- Pushes or artifact commits: none

The configuration is unchanged from the prior shadow audit: prediction-column
learning on; PC-to-local-I delivery off; confidence/passive decay off; loser
depression off; L2E budget/global normalization off; homeostasis off; bounded
saturating decoder potentiation on. The schedule remains the four-pattern
equal-interleaved sequence with 20 steps per presentation, topology seed 1,
and weight seeds 1–5.

Decoder constants were read, not changed: initial weight 50, maximum 1200, eta
0.15, fixed basal contribution 150, and soma threshold 500. Effective
single-source maturity is therefore 350. The exact saturating recurrence needs
2,946 qualifying updates to move from 50 across 350.

## Checkpoint kinetics

| Seed | Mature at 3.2k | 6.4k | 12.8k | 25.6k | First maturity | Persistent collision | Max d at 25.6k | PC spikes at 25.6k |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 6 | 24,332 | none | 361.436 | 571 |
| 2 | 0 | 0 | 0 | 6 | 24,169 | none | 362.972 | 927 |
| 3 | 0 | 0 | 0 | 4 | 13,745 | 940 | 501.327 | 2,739 |
| 4 | 0 | 0 | 0 | 9 | 17,323 | none | 440.581 | 2,329 |
| 5 | 0 | 0 | 0 | 9 | 17,132 | none | 442.319 | 2,203 |

No synapse is mature at 12,800. Every seed has mature synapses at 25,600, so
the conditional 51,200-step extension was not run.

The weight trajectories are monotonic and still moving:

- seed 1 maximum: 114.87 → 138.98 → 225.18 → 361.44
- seed 2: 113.40 → 143.77 → 227.26 → 362.97
- seed 3: 146.90 → 218.40 → 335.14 → 501.33
- seed 4: 133.44 → 191.70 → 291.00 → 440.58
- seed 5: 136.98 → 194.76 → 293.49 → 442.32

All 72 weights, quantiles, means, update counts, and per-synapse observed-rate
projections are recorded at every checkpoint in `results.json`. Final medians
remain near initialization (50.14–50.62), showing a small mature tail rather
than population-wide maturation.

No crossing event fires immediately: all recorded
`crossing_step_pc_spike` values are false. PC activity begins only from later
qualifying events using pre-learning weights.

## Why 3,200 steps were insufficient

### Elapsed time

The earliest observed stationary-rate projection at 25,600 accurately brackets
the actual first crossing:

- seed 1 projected 24,328; observed 24,332
- seed 2 projected 24,165; observed 24,169
- seed 3 projected 13,987; observed 13,745
- seed 4 projected 17,568; observed 17,323
- seed 5 projected 17,450; observed 17,132

Thus 3,200 steps was between 13% and 23% of the eventual first-maturity time.

### Source fragmentation

Every pixel credits 4–6 distinct L2 sources. For the common center pixel PC4,
the aggregate-over-best-source fragmentation factors are:

- seed 1: 4.14
- seed 2: 4.18
- seed 3: 2.00
- seed 4: 2.96
- seed 5: 2.94

If each pixel's observed aggregate qualifying events had belonged to one stable
source, the center-pixel maturity projection would be 5,774–7,010 steps.
Observed fastest-source projections are 13,987–24,328 steps, a fragmentation
delay of roughly 6,977–18,453 steps. This is a counterfactual calculation only;
no dynamics or source assignment was changed.

Peripheral pixels are often less fragmented (factor approximately 1.01–2.08),
but each line pattern requires three useful associations. Center maturation
usually arrives first, while peripheral maturity accumulates later.

### Ownership instability and collision

Across seeds, 10.6%–27.7% of pattern-origin decoder updates go to sources other
than the final modal responder. Individual unstable pattern/source cases retain
only 48%–68% of their credit on the final modal source. This is observational
source fragmentation, not label-gated learning.

Seed 3 is the clearest collision case. `L2E3` becomes the persistent modal owner
for both `row 1` and `diag /` at step 940 and first matures `d[3,4]` at step
13,745. It then receives two patterns' common-center exposure, explaining its
earlier and larger decoder maximum. Maturity in this seed occurs after the
ownership collision and reinforces the collided source rather than preceding
the lock-in.

The other four seeds have no persistent collision by the established running-
modal metric. Their first maturity is therefore classified as before/no
collision rather than after collision.

### Plateau assessment

Weights do not plateau below maturity. All five maximum trajectories cross 350,
and bounded saturation continues increasing them afterward. The failure mode at
3,200 is not a subthreshold fixed point.

Overall diagnosis: insufficient elapsed time plus source fragmentation, with a
collision-driven source-capture component in seed 3. This mixture motivates the
required `MIXED_MATURITY_FAILURE` verdict.

## Locality, queue, ownership, and compression

At 25,600 steps cumulative active-pixel update counts are 32,277–39,183 per
seed. Inactive-pixel updates are zero at every checkpoint. No owner labels enter
dynamics; labels are used only afterward to attribute origin-pattern credit.

Queue arrivals total 142,227–157,356 per seed. Stale rates range from 0.586% to
9.498%, depending on whether sources fire at switch boundaries. No due queued
event is lost or duplicated at any checkpoint.

Ownership changes total 7–17 per seed. The report uses only established project
indicators: physical first-responder shares, running-modal collisions, L2E
status/active count, never-first-responder cells, and center/peripheral
feedforward-weight ratios. Full checkpoint values are in `results.json`; no new
compression threshold was introduced.

## Runtime, commands, and process status

Harness tests: 3/3 passed.

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 run_long_horizon_maturity.py
```

Exact measured five-seed runtime: 263.3971283598803 seconds. The optional
`--extend-51200` command was not run because maturity was present by 25,600.

No production source was edited, no commit was created, and nothing was pushed.
No audit processes remain running.
