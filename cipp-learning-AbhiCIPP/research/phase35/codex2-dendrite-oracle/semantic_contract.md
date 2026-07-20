# Phase 35 cell semantic contract

## Scope

This contract covers one coincidence pyramidal cell with a basal compartment, an
apical compartment, an ordinary soma, and an axonal output. It does not address
four-pattern ownership or integrated network suppression.

## Event identity

Every event has an immutable event ID plus branch, source, target, scheduled
timestep, delivered timestep, magnitude, origin-pattern metadata, and delivery
role. The event ID is unique within a simulation. Duplicate IDs are rejected.

`scheduled_timestep` is provenance only. Physical coincidence is determined by
`delivered_timestep`. A deferred event remains queued and, when presented to the
oracle as delivered, appears exactly once in the delivery ledger.

## Gate and state

At each timestep, active events are grouped by target. The gate opens for a
target iff that target has at least one active basal delivery and at least one
active apical delivery from the configured feedback source in that same
timestep. Events for another target, at another delivered timestep, from the
wrong feedback source, or in the shadow role do not open the gate.

Basal-only and apical-only deliveries cause zero coincidence charge, zero output
spikes, and zero decoder updates. Repeated deliveries on one branch and residual
learning traces cannot substitute for the missing branch. Compartment event
state is empty at the end of every timestep.

The oracle treats `active` and `shadow` as delivery roles. Both are observable in
the delivery ledger; only active events have causal effects. This is an explicit
interpretation because the supplied semantics name the case but do not otherwise
define shadow delivery.

## Soma, output, and learning

An opened gate contributes the configured coincidence charge. For each basal
source `j` paired at target `i`, only decoder association `d[j,i]` is updated.
The update is:

`d_after = min(d_max, d_before + eta * sum(magnitude of qualifying apical events))`

Maturity is tested against `d_before`. An output spike occurs only if the gate is
open, the pre-update association is mature, and coincidence charge meets the
soma threshold. Thus an update that crosses maturity cannot cause its current
event to spike; a subsequent coincidence may.

With apical feedback delivered to nine targets and basal events at only three,
only the three source-target associations selected by those basal events update.

## Pattern-switch provenance

Queued physical events survive a pattern switch. A coincidence is classified:

- `current-correct`: every paired event originates in the current pattern.
- `stale-same-pixel`: every event is stale and each retains the current pixel.
- `stale-wrong-pixel`: every event is stale and each names another pixel.
- `mixed`: current and stale events coexist, or stale members disagree between
  same-pixel and wrong-pixel status.

Classification records provenance; it does not suppress physical coincidence.

## Parameters

All numerical behavior is supplied through `Config`. `oracle_test` uses small
numbers for boundary tests. `legacy_candidate_only` records coincidence charge
500, soma threshold 500, `d_init` 50, maturity 350, `d_max` 1200, and eta 0.15
solely as a named candidate configuration. Those values are not universal and
are not asserted to match Phase 29.
