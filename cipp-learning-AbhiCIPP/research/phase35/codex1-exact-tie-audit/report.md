# Phase 35 exact-tie physical-cause audit

## Verdict

`FAST_FIRST_SPIKE_PATH_CAN_RESOLVE_MOST_TIES`

The 29 final exact decoder-total ties are not one homogeneous physical event.
Nineteen seeds begin with one physical L2E responder and the first tied rival
does not cross until 2--8 engine steps later. With the established one-step
delivery convention, a hypothetical inhibition scheduled by that first spike
could physically arrive at the top of the next step before every tied rival in
those 19 seeds. Ten seeds already contain a same-step tied rival in their
earliest response set and therefore cannot be resolved by any ordinary
first-spike pathway whose effect arrives in a later engine timestep.

Thus a fast first-spike pathway can address most seeds (19/29), but it is not a
complete solution: the remaining 10/29 need sub-step physical symmetry breaking
or another mechanism that acts within the threshold-evaluation step.

## Reproduction and correction of the aggregate description

The identical 40-seed, 6,000-step held `row 1` scan reproduced Claude's top-line
split exactly: 11 clean leaders and 29 exact ties. Full-precision final decoder
totals show that the phrase "ties between two" was too narrow:

- nine seeds are 2-way ties;
- fourteen are 3-way ties;
- four are 4-way ties;
- two are 5-way ties.

These are equality of decoder totals and spike counts after a short transient,
not equality of feedforward weights. None of the 95 tied-neuron pairs ever had
identical feedforward vectors; their L-infinity differences at first co-activity
range from 46.08 to 150.73 (median 99.54). No final tie existed as a full
weight-and-membrane identity at initialization. All membranes do share the same
resting scalar initially, but their weights and subsequent trajectories do not.

## Per-seed physical classification

- `TRUE_SAME_STEP_CROSSING`: 4 seeds (6, 11, 18, 28). Every tied member's
  physical spikes are co-active from its first response onward.
- `MIXED_TIE`: 25 seeds. They have a brief non-identical onset—single response,
  partial same-step set, or alternating/sequential spikes—followed by nearly
  persistent co-activity and exactly equal final counts.
- `MODAL_COUNT_TIE_ONLY`: 0.
- `REPEATED_ALTERNATION`: 0 as a primary persistent mechanism.
- `LEARNED_TRAJECTORY_SYMMETRY`: 0. Learning never makes the tied feedforward
  vectors identical.

The earliest response set contains one neuron in 19 seeds, two neurons in nine,
and three neurons in one. For the 19 singleton-first seeds, first-to-rival delay
is 2 steps in 12 seeds, 4 in four, 6 in two, and 8 in one.

Although only four seeds are pure same-step crossings from onset, co-activity
rapidly dominates the mature trace: across the 95 tied pairs, 274,137 of 274,373
pairwise union spike steps are simultaneous (99.914%). First pairwise co-activity
appears at steps 32--96 (median 60). This explains Claude's observation of
persistent exact checkpoint ties while preserving the physically different
short onset histories.

## Threshold and inhibition cause

At every pair's first co-active threshold crossing, `results.json` records:

- engine step and complete physical response set;
- membrane at step start and at threshold evaluation;
- each threshold and overshoot;
- the complete feedforward-weight difference vector;
- shared-L2I contributors, crossing and scheduling step, threshold-causing
  source, and delivery step.

First-coactivity overshoot ranges from 5.16 to 998.71 charge units (median
296.16). For all 95 tied pairs, shared L2I eventually receives both same-step
events in its contributor window before it fires. The threshold-causing source
is consequently only the last contributor in a multi-source accumulator, not a
unique physical owner. Once a pair crosses in the same outer timestep, an
inhibition event caused by either spike can arrive no earlier than the next
timestep and cannot retract the companion spike already emitted.

## Method and validity

Claude's existing artifacts lacked per-step L2E membranes, physical spike sets,
and shared-L2I contributor/delivery joins, so the permitted scan was repeated
with passive observation against detached commit
`db30ceadbe18cf90e01f6d54dee0203f342b24a8`. Configuration was identical:
prediction-column learning on in shadow, PC-to-local-I off, prediction passive
leak disabled, loser depression off, and L2E budget/global normalization off.
No parameter or production object was modified by the observer.

The final instrumented scan took 344.88 seconds. An initial instrumentation pass
was repeated because it omitted individual first-spike timestamps and the later
L2I fire consuming an earlier contributor set; neither pass changed dynamics.

## Repository and process status

The standalone audit clone remains detached and clean at the required commit.
No production edits, commits, pushes, or parameter changes were made. No audit
processes remain running.
