# Pre-inhibition race timing-decomposition audit

Verdict: **ACCUMULATION_WINDOW_DOMINATES**

## Evidence set

This audit reused the five existing 12,800-step traces from
`codex1-phase35-source-fragmentation`. Production was not rerun because every
required passive timestamp and membrane record was present.

The source audit contained 120 fragmenting new-source credits with a
same-presentation race factor:

- 104 credits were genuine secondary/rival L2 sources;
- 16 credited the presentation's first responder while another source also
  raced, so they are conservatively `AMBIGUOUS_OR_MIXED`.

## Primary causal interval

Every one of the 104 genuine secondary spikes occurred before—or in the same
engine step immediately before—the shared L2I threshold evaluation:

- `ACCUMULATION_WINDOW`: 104
- `DELIVERY_DELAY`: 0
- `POST_INHIBITION_RESIDUAL`: 0
- `AMBIGUOUS_OR_MIXED`: 16 (the first-responder credits above)

Within a timestep, L2E firing precedes L2I receive/threshold evaluation. A rival
that supplies the threshold-crossing contribution is therefore classified in
the accumulation window even though its spike and the crossing share a step.

The mechanism is clear: the first responder alone does not generally cross the
shared inhibitory threshold. Additional L2 sources spike and contribute while
the shared I unit accumulates evidence. By the time inhibition is scheduled,
their decoder events have already been physically emitted.

## Timing distributions

First responder to rival margin:

- minimum 1 step; median 2; p90 4; maximum 6;
- histogram: `{1:35, 2:29, 3:27, 4:10, 6:3}`.

First responder to L2I threshold crossing:

- minimum 1; median 3; p90 4; maximum 6;
- histogram: `{1:10, 2:37, 3:30, 4:20, 6:7}`.

Threshold crossing to inhibitory delivery was exactly one step for all 104
secondary events. It caused none of these credits: every credited rival had
already fired before crossing.

Sixty-one of the 104 secondary sources fired again after delivery. Their first
rebound occurred 5–12 steps later (median 8, p90 10). However, every target's
recorded post-inhibition membrane was exactly zero. These are fresh
reaccumulation rebounds, not retained post-inhibition residual charge.

## Offline counterfactual estimates

These are interval-removal counts over observed events, not altered simulations:

- observed genuine secondary spikes: 104;
- if delivery delay were zero: 104 remain, because all occurred before the
  threshold crossing that schedules delivery;
- if shared L2I crossed on the first L2 spike: 0 remain under the timing-only
  estimate, because the minimum rival margin is one step and the existing
  one-step delivery would arrive before the earliest rival;
- if post-inhibition residual charge were removed: 104 remain, because recorded
  residual was already zero and no primary event belonged to that interval.

The first-spike-crossing estimate does not prescribe a threshold or strength;
it identifies the causal boundary. A future biological mechanism must shorten
or localize inhibitory recruitment so the first responder can recruit effective
competition before other L2 cells emit spikes. Merely eliminating the transport
delay or increasing drain cannot undo spikes already emitted during shared-I
accumulation.

## Trace fields

`event_decomposition.json` preserves for every event:

- first and rival spike steps;
- contributor arrival steps and contributor identities;
- L2I crossing source and step;
- scheduling and delivery steps;
- before/after rival membrane and residual;
- causal ordering booleans;
- later rebound step/delay;
- primary interval classification.

## Integrity

- Decomposition runtime: 0.99 seconds.
- Validation: pass, all 120 records complete and exactly one allowed interval.
- Production tests/reruns: none required.
- Source checkout: clean detached at
  `db30ceadbe18cf90e01f6d54dee0203f342b24a8`.
- Production edits, commits, and pushes: none.
