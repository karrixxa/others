# Phase 35 full decoder coverage and retention

## Verdict

`COLLISION_BLOCKS_COMPLETE_COVERAGE`

Normal local learning produces four distinct, clean pattern decoders in four of
five seeds by 51,200 steps, without manual assignments or forgetting. The one
persistent-collision seed does not recover full clean coverage even at 102,400:
its collided source merges multiple patterns into one mature union and destroys
an earlier clean decoder.

## Isolation and execution

- Checkout: `/home/cxiong/codex-runs/codex2-phase35-natural-exposure-checkout`
- Commit: `db30ceadbe18cf90e01f6d54dee0203f342b24a8`
- Shadow configuration: unchanged from the prior audits
- Production edits, commits, pushes: none
- Production status before and after: clean

The five seeds ran continuously to 51,200. Only seed 3 lacked four clean
patterns there, so only seed 3 continued in-place to 102,400. No seed was
restarted for its extension.

## Coverage checkpoints

| Seed | Clean at 25.6k | Patterns at 25.6k | Clean at 51.2k | Patterns at 51.2k | Extended | Final result |
|---:|---:|---|---:|---|:---:|---|
| 1 | 2 | row 1, diag / | 5 | all four | no | all four persistent; extra diag \ decoder |
| 2 | 2 | row 1, diag / | 5 | all four | no | all four persistent; extra diag \ decoder |
| 3 | 1 | col 1 | 2 | col 1, diag \ | yes | still only two at 102.4k |
| 4 | 3 | row 1, diag \, diag / | 4 | all four | no | all four persistent |
| 5 | 3 | col 1, diag \, diag / | 4 | all four | no | all four persistent |

Seeds 1, 2, 4, and 5 have four ownership-agreeing clean decoders on distinct L2
sources. Seeds 1 and 2 additionally mature a second clean diag \ decoder whose
source is not the final modal owner; the required owner-aligned set remains
present and distinct.

## First complete-decoder steps

| Seed | row 1 | col 1 | diag \ | diag / |
|---:|---:|---:|---:|---:|
| 1 | 24,484 | 40,426 | 46,362 | 25,432 |
| 2 | 24,249 | 27,631 | 47,961 | 24,541 |
| 3 | never | 25,068 | 34,060 | 34,228, then lost |
| 4 | 24,483 | 34,429 | 24,859 | 24,793 |
| 5 | 32,886 | 24,984 | 24,618 | 25,028 |

No clean decoder is lost in seeds 1, 2, 4, or 5. Seed 3 briefly obtains a clean
diag / decoder on collided `L2E3` at step 34,228. At step 36,565 it loses that
clean classification when further row-1 maturation changes the source to
`MULTI_PATTERN_UNION`. It never obtains a clean row-1 decoder.

## Collision mechanism in seed 3

The established persistent ownership collision starts at step 940. `L2E3` is
the modal owner for both row 1 and diag /. By 102,400 its mature pixels are:

`{0, 2, 3, 4, 5, 6, 8}`

This contains complete row 1 `{3,4,5}`, diag / `{2,4,6}`, and diag \
`{0,4,8}` sets within one source. Its weights are:

`[415.187, 69.104, 643.851, 623.164, 875.468, 623.164, 643.851, 69.104, 415.187]`

The collided source receives 63,696 decoder updates. Row 1 and diag / are not
uncovered because of inadequate charge by the final horizon—their pixels are
all mature. They are uncovered because the same collided source has matured
both patterns plus additional diag \ pixels, so it is no longer a clean
single-pattern decoder. This is collision-driven union/overgeneralization, not
simple late starvation.

Clean col 1 (`L2E6`) and diag \ (`L2E7`) decoders remain present in seed 3.
Extending another 51,200 steps does not create separate row/diag sources or
restore the lost clean diag / decoder.

## Retention and mature anatomy

At final checkpoints:

- seeds 1–2: 5 mature center and 10 mature peripheral synapses;
- seed 3: 3 mature center and 10 mature peripheral synapses;
- seeds 4–5: 4 mature center and 8 mature peripheral synapses.

For non-collision seeds, mature anatomy remains organized into exact
three-pixel line decoders. There are zero complete-decoder loss events across
those four seeds. Seed 3 has exactly one loss event and one large multi-pattern
union.

Ownership changes over the full observed histories are 7, 17, 12, 14, and 15
for seeds 1–5. Only seed 3 ends with a persistent cross-pattern ownership
collision.

## Active-mode availability

Counterfactual PC spike totals at 51,200 are:

- seed 1: 27,320
- seed 2: 30,054
- seed 3: 27,467
- seed 4: 36,488
- seed 5: 38,052

Seed 3 reaches 89,823 counterfactual PC spikes by 102,400. Thus its coverage
failure is not lack of prediction-column activity; ACTIVE mode would receive
many events, but two trained patterns lack distinct clean decoder sources.

## Primary answer

Normal local learning can produce four distinct, clean, persistent pattern
decoders without manual assignments: it does so in four of five seeds by
51,200. It does not do so reliably across all five seeds. A persistent ownership
collision can merge multiple patterns into one decoder source, erase an earlier
clean decoder, and block full clean coverage even at 102,400 steps.

## Runtime and tests

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 run_full_coverage.py
```

Exact runtime: 630.3777489231434 seconds. Harness tests: 2/2 passed.

No production file was changed, no commit was created, and nothing was pushed.
No audit processes remain running.
