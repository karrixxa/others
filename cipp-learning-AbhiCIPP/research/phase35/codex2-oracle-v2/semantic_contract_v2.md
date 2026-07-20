# Phase 35 semantic contract v2

## Cell and event model

A coincidence pyramidal cell has basal and apical compartments, an ordinary
soma, and axonal output. Every physical event records ID, branch, source, target,
scheduled timestep, delivered timestep, magnitude, pattern provenance, and
active/shadow role. Coincidence uses delivered timestep only.

Active positive basal and configured apical deliveries to the same target in the
same timestep open the physical gate. Neither branch alone, an offset event, a
wrong target/source, a shadow event, or a residual trace can open it. Scheduled
events survive pattern switches and are delivered exactly once. Compartment
delivery state clears at the end of each timestep; clearing delivered state does
not clear future scheduled events.

## Charge and firing

For target `i`, basal charge is the sum of each positive basal magnitude times
the fixed basal weight. Apical charge is the sum of each positive apical event
magnitude times its pre-learning decoder weight `d[j,i]`. The ordinary soma
responds when their sum meets its threshold. Thus effective maturity emerges
from basal contribution, apical weights, event magnitudes, and soma threshold;
there is no separate Boolean maturity gate.

Firing is resolved entirely from `d_before_learning`. A learning update that
first moves effective charge across threshold cannot fire the current event. A
subsequent qualifying coincidence may fire.

## Local learning

Decoder identity is feedback source `j` and target pixel `i`: `d[j,i]`.
For each distinct configured feedback source physically delivered to an open
same-target gate:

`delta_d[j,i] = eta * local_eligibility * (1 - d[j,i] / d_max)^2`

`local_eligibility` is 1 exactly when all of these are true in the current
timestep: same-target basal is active; the configured feedback source `j` has a
positive active delivery to apical target `i`; and both deliveries share the
delivered timestep. Otherwise it is 0 and no update is stored.

Event magnitude is handled in two distinct ways. Positive magnitude participates
in physical charge linearly. For learning it is a binary local eligibility gate:
once positive, it does not multiply eta or the saturation factor. Multiple
events from the same source contribute separately to charge but cause at most
one update of `d[j,i]` in that timestep. Distinct delivered feedback sources each
update their own association once. Stored weights are clipped to `[0,d_max]`.

Learning does not require somatic firing; the local dendritic coincidence is the
learning gate. No other source or target weight may change. Accordingly, nine
apical targets with basal activity at three targets update only three target
associations and leave the other six byte-identical.

## Provenance

Pattern provenance is observational and never suppresses delivery. Arrived pairs
are classified current-correct, stale-same-pixel, stale-wrong-pixel, or mixed.

## Gating-structure resolution

The biological contract distinguishes physical coincidence from somatic output.
Same-step basal+apical delivery opens the dendritic gate; weighted charge then
determines whether the ordinary soma fires. The repaired production follows
this structure. It records a coincidence step before applying the charge
threshold and performs local learning for an open gate even when the soma does
not fire. No gating-contract disagreement was found in this scope.

Production ignores non-positive signals at compartment delivery. Oracle v2
therefore treats magnitude `<=0` as inactive, an explicit interpretation of an
event's physical activity rather than an additional maturity gate.

## Scope and parameters

All numeric constants are `Config` parameters. The legacy values 150, 50, 1200,
0.15, and 500 appear only as a named candidate configuration. This contract
does not cover Gate C, integrated suppression, ownership, or tuning.
