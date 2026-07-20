# Phase 35 Architecture Status

## Frozen lineage

The current verified implementation is `db30ceadbe18cf90e01f6d54dee0203f342b24a8`, descended from Phase 29 base `4764f1758a7399439df2242dfa60819501fc2333` through implementation commit `4e712a4b7dea033b9191680a4b4e3577d93ca304` and the queue-carryover repair.

## Current architecture

- `DendriteCompartment` represents explicit `BASAL` and `APICAL` roles. A `CoincidencePyramidalCell` composes one basal compartment, one apical compartment, an ordinary soma/node, and axonal output.
- L1 sensory excitation targets the paired basal compartment. Every L2E source can reach all nine apical compartments through its local decoder connection `d[j,i]`.
- Coincidence is physical: basal and apical events must be delivered to the same target in the same engine timestep. Scheduling time, origin metadata, and learning traces cannot substitute for delivery-time coincidence.
- Neither branch alone deposits coincidence charge, fires the prediction cell, or updates a decoder. Compartment event state clears at each timestep boundary while already-scheduled queue events persist across presentation switches.
- Decoder learning is source/target local and basal-gated: `delta = eta * (1 - d_before/d_max)^2`, once per distinct delivered positive feedback source. The current event uses `d_before`; a boundary-crossing update can affect only a later valid coincidence.
- Maturity is an emergent charge condition, not a separate Boolean. At the committed defaults, basal contribution 150 plus decoder contribution 350 reaches soma threshold 500.
- The opt-in output route is `PC_i -> paired L1I_i -> paired sensory L1E_i`. The default-off engine remains equivalent to the Phase 29 baseline in the bounded hash and golden comparisons.

## Validated behavior

Gate A/B construction, explicit routing, single-branch controls, exact same-step coincidence, +/-1 rejection, clearing, no trace-driven firing, ordinary-neuron behavior, sparse learning, pre-learning maturity ordering, exactly-once queue carryover, four-class provenance telemetry, and default-off behavior have all been independently exercised. Corrected oracle v2 reports full agreement with repaired production over its bounded goldens and semantic enumeration.

Natural exposure confirms locality: inactive pixels remain byte-identical, stale switch arrivals are delivered rather than deleted, and long exposure can produce clean complete three-pixel decoders. Once mature, active prediction suppresses explained sensory activity. That suppression acts on later activity and remains ownership-neutral.

## Unresolved collision problem

The upstream L2 ownership failure predates useful prediction output. Shared L2I integrates several responder events before crossing threshold, so multiple L2E neurons physically spike and receive decoder credit during the accumulation window. Offline decomposition found no primary delivery-delay or post-inhibition-residual explanation for the fragmenting spikes.

Consequences observed across completed audits:

- decoder credit fragments across 4–6 L2 sources;
- 3,200-step exposure is insufficient for maturity;
- 25,600-step exposure produces selective decoders but not complete four-pattern coverage;
- persistent ownership collisions can reinforce a common-center decoder;
- 29/40 held-pattern seeds end in exact decoder/count ties, although only 4 are pure same-step crossings from onset;
- a one-step first-spike inhibitory path could precede all tied rivals in 19/29 seeds, while 10/29 already contain same-step rivals and require within-step symmetry breaking.

The historical paired/defer-once experiment is not a native path in this lineage and must not be treated as verified repaired-lineage production behavior.

## Experimental roadmap

1. Specify a biological first-spike recruitment pathway that closes the shared-L2I accumulation window without labels, owner locks, global argmax, or parameter forcing.
2. Add an explicit sub-step symmetry-breaking contract for genuine same-step crossings; first-spike delivery alone cannot retract a spike already emitted in the same outer timestep.
3. Evaluate the local residual/selective-switch timing contract as a separate mechanism. Preserve its two-event safeguard so a single missed familiar coincidence cannot force a switch.
4. Before integrated Gate C, require iso-seeded controls for random-stream equivalence, identical topology, queue carryover, exactly-once delivery, and default-off hashes.
5. Only after upstream ownership is measurably stable should prediction-to-local-I suppression be tested for four-pattern functional benefit. Do not tune eta, thresholds, delays, inhibition strength, or geometry to manufacture agreement.

## Current decision boundary

Phase 35 dendritic coincidence and local decoder semantics are validated at the repaired checkpoint. The load-bearing unresolved issue is upstream L2 physical competition: accumulation-window races and a minority of true same-step symmetries prevent robust ownership and complete decoder coverage. Prediction suppression should not be credited with solving that earlier failure.
