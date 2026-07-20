# Phase 35 decoder assembly and selectivity analysis

## Verdict

`CLEAN_PATTERN_DECODERS_EMERGE`

The five frozen 25,600-step outcomes contain 11 complete, clean three-pixel
pattern decoders. Every complete decoder agrees with its L2 source's observed
modal ownership. There are no partial-single-pattern, scattered-fragment, or
multi-pattern-union mature decoders.

This was a passive analysis of
`codex2-phase35-long-horizon-maturity/results.json`. Production was not rerun or
edited.

## Classification rule

Maturity uses the established effective threshold 350. Decoder classes are
defined only from mature-pixel sets:

- `COMPLETE_SINGLE_PATTERN`: exactly one trained three-pixel set.
- `PARTIAL_SINGLE_PATTERN`: a strict nonempty subset of exactly one pattern.
- `CENTER_ONLY`: only shared pixel 4.
- `MULTI_PATTERN_UNION`: contains at least two complete pattern sets.
- `SCATTERED_FRAGMENT`: spans patterns without a clean category above.
- `IMMATURE`: no mature decoder synapse.

Across all 40 L2 sources: 11 complete, 1 center-only, and 28 immature.

## Per-seed assembly

| Seed | Mature synapses | Complete decoders | Complete patterns | Center / peripheral mature | Collided-owner mature | Usable pattern prediction |
|---:|---:|---:|---|---:|---:|:---:|
| 1 | 6 | 2 | row 1, diag / | 2 / 4 | 0 | yes |
| 2 | 6 | 2 | row 1, diag / | 2 / 4 | 0 | yes |
| 3 | 4 | 1 | col 1 | 2 / 2 | 1 | yes |
| 4 | 9 | 3 | row 1, diag \, diag / | 3 / 6 | 0 | yes |
| 5 | 9 | 3 | col 1, diag \, diag / | 3 / 6 | 0 | yes |

Complete decoders always use distinct L2 sources within a seed. Four to nine
mature synapses therefore do provide usable pattern-level prediction: every
seed has at least one complete decoder. They do not provide all four patterns;
coverage ranges from one to three distinct complete patterns per seed.

## Decoder identities and ownership

- Seed 1: `L2E4 -> {3,4,5}` is row 1; `L2E2 -> {2,4,6}` is diag /.
- Seed 2: `L2E0 -> {3,4,5}` is row 1; `L2E5 -> {2,4,6}` is diag /.
- Seed 3: `L2E6 -> {1,4,7}` is col 1. Collided `L2E3`, modal for row 1
  and diag /, matures only shared center pixel 4.
- Seed 4: `L2E4` is row 1, `L2E3` is diag \, and `L2E1` is diag /.
- Seed 5: `L2E3` is col 1, `L2E7` is diag \, and `L2E5` is diag /.

All 11 complete decoders have ownership status `AGREES`. Seed 3's center-only
decoder is explicitly nonselective rather than assigned to either collided
pattern. The remaining sources are immature even when some subthreshold weights
show pattern-shaped structure.

`results.json` reports every source's nine full-precision weights, mature
pixels, the trained patterns containing each mature pixel, complete/partial
sets, classification, ownership agreement, and nine update counts.

## Collision and union behavior

Only seed 3 has a persistent collision. Its collided source `L2E3` receives
16,176 updates—50.12% of all decoder updates in that seed—but its mature decoder
is center-only. It does not form the union `{2,3,4,5,6}` of row 1 and diag /;
all four peripheral weights remain below 350. Of seed 3's four mature synapses,
one belongs to the collided owner and three belong to the non-collided, clean
col-1 owner.

Thus collision concentrates learning strongly without producing a mature
multi-pattern-union decoder at this horizon. No seed contains any
`MULTI_PATTERN_UNION` or `SCATTERED_FRAGMENT` classification.

## Update concentration

Per-source update HHI is 0.183, 0.191, 0.377, 0.264, and 0.263 for seeds 1–5.
The largest source shares are respectively 24.15%, 23.90%, 50.12%, 33.83%, and
33.98%. Seed 3 is the clearest collision-driven concentration; other seeds
concentrate enough exposure on stable owners to mature complete three-pixel
assemblies.

Aggregate mature anatomy is 12 center synapses and 22 peripheral synapses.
The two-to-one peripheral/center ratio within each complete decoder is exact,
as required by the line-pattern geometry. The lone excess center is seed 3's
collided center-only decoder.

## Interpretation

Long-horizon maturity is selective, not merely scalar growth. Once sufficient
exposure accrues, decoder rows assemble the same three active pixels associated
with their physical modal L2 response. The limitation at 25,600 steps is pattern
coverage—only one to three of four patterns per seed—not malformed mature
decoders.

No simulation, production edit, commit, or push was performed. No processes
remain running.
