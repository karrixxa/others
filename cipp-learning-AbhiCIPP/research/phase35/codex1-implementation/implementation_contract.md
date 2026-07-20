# Phase 35 implementation contract

## Scope and invariant

The implementation is opt-in through the existing `prediction_column_enabled`
path. When it is false, no dendritic cell is constructed, no new queue or random
draw participates in execution, and ordinary neurons follow the Phase 29 path.

## Objects and routing

- `DendriteRole` defines `BASAL` and `APICAL`.
- `DendriteCompartment` accepts physical deliveries for exactly one engine
  timestep and never owns a learning/eligibility trace.
- `DendriticConnection` names one source, one explicit compartment target, one
  weight, and whether that connection is plastic.
- `CoincidencePyramidalCell` composes one basal compartment, one apical
  compartment, and one ordinary `Neuron` soma. `fire()` is its axonal output.
- `L1E_i -> PC_i.basal` is fixed and paired.
- `L2E_j -> PC_i.apical` uses decoder weight `d[j,i]` and fans out across all
  nine prediction cells.
- Opt-in output remains `PC_i -> L1I_i -> L1E_i`, using the existing paired
  inhibitory register for physical delivery to the sensory neuron.

## Execution order

1. At timestep start, pop the apical and basal physical-delivery vectors that
   were scheduled together from the same prior engine timestep.
2. Route each positive event through its explicit compartment connection.
3. Resolve coincidence only if both compartments received physical delivery at
   the current engine timestep.
4. Compute the soma firing decision from the delivered weights before learning.
   Neither branch alone deposits any soma charge.
5. If both branches were physically delivered and plasticity is enabled, update
   only the delivered apical decoder connections. Basal is fixed.
6. Fire the ordinary soma if the pre-learning coincidence decision qualified.
7. Route its axonal event only to paired `L1I_i` when selective output is enabled.
8. At timestep end, advance the ordinary soma and clear both compartments.
9. At a presentation/pattern/probe switch, replace both delayed queues with
   zeros and clear compartments so an event cannot cross the boundary.

## Learning rule

For each physically delivered apical connection only:

`d_after = clip(d_before + eta * (1 - d_before / d_max)^2, 0, d_max)`

The update requires current-step basal delivery. It uses no label, loss,
ownership, rival, argmax, normalization, or learning trace. A weight that crosses
the firing boundary during this update can affect only a later coincidence.

## Checkpoint exclusions

No Gate C, ownership experiment, parameter grid, labels, global loss, owner
locks, balanced initialization, nonlocal normalization, Phase 33 mechanism, or
reconstructed Phase 34 behavior is included.
