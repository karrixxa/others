# Phase 39: why decoder maturation is slow, and the one timescale change

## Calculation (existing equations only)

Decoder growth per qualifying event (`_apply_prediction_column_learning`):

    d_{n+1} = d_n + eta * (1 - d_n / d_max)^2

Default init `d_0=50`, `d_max=1200`, crossing point at
`threshold - lateral = 500 - 150 = 350`.

At `eta=0.15` (prior default): closed-form iteration of the recurrence above
reaches `d=350` after **2946 events** -- this exact figure is already
documented in the Phase 35 ledger (`claude-repair-review`).

## Observed event rate (Phase 38.2 natural smoke, genuine-default config)

800 steps produced 33 qualifying basal+apical co-delivery events (decoder
went 50 -> ~64.7 under `eta=0.5`): **0.0413 events/step** (~1 qualifying
coincidence every 24 steps). This rate is a property of how often L2E wins
AND L1E is active on the *same originating step* -- unrelated to `eta`.

## Why maturation takes so long

2946 events / 0.0413 events-per-step ≈ **71,000 steps** to mature at the
prior default `eta=0.15`. The bottleneck is the qualifying-event rate
(structural), compounded by the saturating envelope `(1-d/d_max)^2`
shrinking the per-event increment as `d` grows -- not a bug, just two
naturally slow factors multiplying together.

## The one change

`prediction_learning_rate` default: `0.15 -> 1.5` (10x). At `eta=1.5`, the
same crossing (`d=350`) takes **295 events** (~7,100 steps at the measured
rate) -- still hundreds of genuine, physically-delivered coincidences, never
a one-shot jump, preserving bounded local learning and real learned
maturation. No threshold, init, or max value touched.
