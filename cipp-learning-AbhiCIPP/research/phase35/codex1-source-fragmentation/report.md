# L2 source-fragmentation causal audit

Verdict: **FRAGMENTATION_FROM_PRE_INHIBITION_RACE**

## Scope and configuration

- Exact commit: `db30ceadbe18cf90e01f6d54dee0203f342b24a8`
- Five full seeds: 1–5
- Steps per seed: 12,800
- Schedule: 640 presentations per seed, 20 steps each, ordered
  `row 1 -> col 1 -> diag \ -> diag /`, repeated equally.
- Phase 35 prediction column enabled in shadow mode only.
- `PC_i -> L1I_i` physically disabled; no PC-source synapse exists.
- Loser depression, signed/passive depression, positive-weight budget/global
  normalization, homeostasis, and confidence consolidation disabled.
- Existing quadratic bounded decoder potentiation unchanged.

No production method was replaced or monkeypatched. No paired/defer-once path
was introduced.

## Main result

The five runs produced 165 events where a pixel acquired a second or later
decoder-credit source. Causal factors can overlap:

- same-presentation pre-inhibition race: 120/165 (72.7%);
- later owner switching: 54/165 (32.7%);
- cross-pattern common-pixel reuse: 23/165 (13.9%);
- stale queue carryover: 0/165.

Because pre-inhibition race participates in a clear majority of fragmenting
new-source events and exceeds owner-switching participation by more than 2:1,
the primary cause is the L2 race before shared inhibition arrives. Ownership
switching is a substantial secondary amplifier, not the dominant initiating
cause. Of the 165 events, 88 have overlapping factors and are classified
`MIXED`; the component-factor counts above preserve that causal overlap.

## Physical timing evidence

Across 3,200 presentations:

- all 3,200 produced an L2 response;
- 713 presentations had multiple distinct L2 responders before the first
  inhibitory arrival;
- 1,920 presentations accumulated more than one contributor before an L2I
  threshold crossing;
- 3,199 presentations had at least one post-inhibition responder/rebound;
- 22,326 inhibitory events were scheduled and 22,323 arrived within the finite
  measurement window (the final three remained pending at the endpoint);
- all 178,584 due target deliveries were applied; none was skipped.

Thus fragmentation is not explained by wrong targets or missing delivery. The
shared L2I commonly needs evidence from multiple L2 sources, so multiple sources
physically spike and become eligible for decoder credit before its one-step
delivery. Strong post-delivery rebound then provides repeated later
opportunities and contributes to subsequent owner changes.

## Fragmentation and onset

Final credited-source counts were 4–6 for every pixel in every seed. The
universal center finished with `[6, 6, 5, 6, 5]` sources.

Center fragmentation occurred extremely early:

- it reached two and three sources during presentation 0 in every seed;
- it reached four sources by presentation 1 in every seed;
- seeds 1, 2, and 4 reached six sources by steps 49, 34, and 56;
- seeds 3 and 5 reached five sources by steps 70 and 32.

Causal-winner collision onset was presentation 3 in all seeds. First-responder
collision onset was presentation `[3, 6, 3, 3, 3]`; compression onset was
`[21, 6, 5, 11, 5]`. Only seed 3 had a collision that remained persistent from
presentation 3 through the endpoint under the strict suffix definition.

## Common pixel and stale delivery

The center's cross-pattern reuse adds 23 common-pixel causal factors, explaining
why its source count is generally the largest. It is secondary because
peripheral pixels—which occur in only one trained pattern—also finish with 4–6
sources, and pre-inhibition race is already present during the first pattern.

The repaired queue behavior produced 4,857 stale-classified decoder updates in
total, but all were repeats of already-credited source/pixel associations. No
pixel acquired a new fragmenting source from stale carryover.

## Decoder credit mass

Every update's source, target pixel, pre/post decoder value, unrounded stored
delta, physical scheduled/delivered step, origin pattern, presentation, and
causal factors are preserved in the seed traces. Aggregate update mass by L2
source was:

- L2E0 535.85; L2E1 814.92; L2E2 513.15; L2E3 3240.04;
- L2E4 1449.70; L2E5 1878.45; L2E6 1121.87; L2E7 1647.34.

Per-pixel/per-source mass and first attainment of 2–6 credited sources are in
each trace's `update_mass_per_pixel_source` and
`credited_source_threshold_onsets` fields.

## Tests and integrity

- Smoke seed: pass.
- Audit integrity validation: pass; 5 traces, 3,200 presentations, 93,318
  decoder updates, 165 fragmenting new-source events.
- Existing Phase 35 conformance repair tests: 2/2 pass.
- Checkout status: clean detached HEAD.
- Production edits/commits/pushes: none.
- Measurement runtime: 134.90 seconds; validation and smoke under two seconds.
