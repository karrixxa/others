# Phase 35 focused mismatch-reduction audit

## Verdict

`QUEUE_DEFECT_REAL_MATURITY_ORACLE_MISMATCH`

## Task A: pattern-switch queue loss

The smallest atomic loss is one event vector:

- source: `L2E0`
- target: `PC0.apical`
- scheduled timestep: 0
- intended delivery timestep: 1
- switch timestep: 1, before delivery
- queue: `SimulationEngine.l2e_to_pcol_queue`

The smallest lost physical coincidence adds the paired basal event `L1E0 ->
PC0.basal`, also scheduled at 0 for delivery at 1, in
`SimulationEngine.s_to_pcol_queue`.

`SimulationEngine._start_presentation` replaces both delayed deques with new
zero-filled deques. It also calls `clear_compartments()` on every prediction
cell. Thus both the global delayed queues and any current compartment deliveries
are cleared. The queued events are deleted from engine reachability; they are
not conditionally skipped and cannot be delivered later. Before the call the
two first queue vectors have index 0 equal to 1; afterward every entry is 0 and
both deque object identities have changed.

This is a genuine production defect against the accepted contract. It occurs in
real engine state before adapter projection. Ordinary compartment clearing is
separately correct: a cell containing one basal delivery becomes empty after
`CoincidencePyramidalCell.update()`. Repair should preserve physically queued
vectors across presentation switches while retaining normal end-of-timestep
compartment clearing.

Production locations in frozen commit `4e712a4`: queue replacement is
`backend/simulation.py` lines 2942-2948; ordinary cell clearing is
`snn/dendrite.py` lines 149-155. No production function was edited.

## Task B: maturity reduction

The minimal behavioral trace is one cell, one decoder, and two identical
coincidences. Parameters are `d=4`, eta 1, `d_max=11`, coincidence/maturity
threshold 5, soma threshold 7, positive basal signal with basal weight 0, and
positive apical signal 1.

On coincidence 0 production records:

- `d_before = 4.0` (`0x1.0000000000000p+2`)
- basal active, apical active, equal delivered timestep, delivered apical source,
  and positive apical signal: all true
- saturation base: `1 - 4/11 = 0.6363636363636364`
- saturation factor: `0.4049586776859504`
- independently calculated raw delta: `0.4049586776859504`
- stored delta: `0.4049586776859506`
- `d_after = 4.404958677685951` (`0x1.19ead7cd391fcp+2`)
- apical/combined dendritic charge: 4; soma potential remains 0
- current response: false

On coincidence 1, `d_before=4.404958677685951`, raw delta is
0.35945925655396566, stored delta is 0.3594592565539658, and
`d_after=4.764417934239916`. Combined dendritic charge remains below 5, soma
potential remains 0, and the next response is false.

The frozen adapter and direct production trace store exactly the same two
weights and responses. Production's independently evaluated equation matches
its stored deltas within floating-point subtraction precision.

The accepted oracle instead applies `eta * sum(apical magnitude)`, producing
delta 1, `4 -> 5`, no current-event spike, and a spike on the subsequent
coincidence. The divergence is therefore a different saturation/update
equation. It is not adapter input mapping, parameter mapping, meaningful numeric
rounding, missing persistence, mature-weight comparison, or somatic response
logic. Pre-update weight correctly controls the current event in production.

This maturity case is not presented to Codex 1 as a production repair target.
For regression purposes, it is a non-defect control documenting the frozen
production equation.

## Task C: repair-quality case

`minimal_counterexamples.json` contains the deterministic queue regression case.
With delay 1, enqueue feedback vector `[1,0,0,0,0,0,0,0]` and basal vector
`[1,0,0,0,0,0,0,0,0]`, switch presentation before delivery, then assert:

- both queued vectors remain present after the switch;
- each event is delivered exactly once at timestep 1;
- `PC0` records coincidence at timestep 1;
- ordinary end-of-timestep clearing still leaves both compartments empty.

Observed frozen behavior replaces both vectors with zeros, delivers neither,
and records no coincidence.

No Gate C, ownership experiment, parameter grid, or exhaustive enumeration was
run. No processes remain running.
