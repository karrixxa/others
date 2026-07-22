# Tenant Compliance Without a Forced Winner — Research Baseline

## Scope and status

- **Status:** approved research baseline for a later plan of action.
- **Scope:** current hybrid cortical-column and relevant production winner-control behavior.
- **Authority:** [`Documents/tenants.txt`](../tenants.txt), normalized below only for spelling and testability.
- **Implementation status:** **no implementation is specified or authorized by this document.** Options and recommendations are research inputs, not a committed design.
- **Relationship to prior audit:** this document tightens [`hybrid_cortical_column_tenant_outline.md`](hybrid_cortical_column_tenant_outline.md) around strict causal semantics. In particular, it distinguishes a permissive production-profile audit from a strict “no fabricated event” audit.
- **Living lever catalog:** [`forced_learning_inventory.md`](forced_learning_inventory.md) (Stage 9 dispositions: keep-as-labeled-control / replace-with-biology / retire / audit-only).

## Normalized T1–T9 authority

The source uses “casual”; the firing-versus-not-firing context makes **causal** the defensible normalization.

| ID | Normalized authority |
|---|---|
| T1 | Firing is causal; not firing is non-causal (`ONE` versus `Z`). |
| T2 | Neurons that fire together wire together. |
| T3 | Each neuron controls its own local learning and owns no more than one pattern. |
| T4 | Excitatory and inhibitory cells, weights, and connections are explicit. |
| T5 | A neuron that fires observes a refractory period. |
| T6 | Each symbol binds one-to-one to a learned neural representation. |
| T7 | Learning remains continuous and online. |
| T8 | Learned neural state supports prediction. |
| T9 | Learning occurs in the neuron, using only information delivered through its connections; no global learning authority decides or mutates it. |

## Exact forced-winner causal chain

The hybrid leak is a chain, not a single WTA defect:

1. **`line_id` overrides the supplied sensory pattern.**  
   `backend/cognative_paradigm/cortical_column/cortical_column.py:HybridCorticalColumn.process_pattern` deletes `pattern` and calls `Layer4Adapter.line_indices(line_id)`.
2. **Catalog identity becomes fixed input indices.**  
   `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter.line_indices` reads `backend/cognative_paradigm/lines.py:LINE_INDICES`.
3. **Relay silence falls back to modulated input.**  
   `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter.process` sets `modulated_cell_indices=fired_indices or modulated_indices`. Thus an empty excitatory relay spike set can still become downstream activation.
4. **Activation is compared with preassigned assembly templates.**  
   `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork.__post_init__` creates one `ContextAssembly` per `LINE_IDS`; `backend/cognative_paradigm/cortical_column/context_assembly.py:ContextAssembly.template_indices` reads the matching fixed `LINE_INDICES`.
5. **A maximum membrane candidate is always selected.**  
   `ContextAssemblyNetwork._compete` calls `max(...)` over all assemblies and gives the observed `line_id` a deterministic tie preference.
6. **Winner identity is returned below threshold.**  
   In `ContextAssemblyNetwork._compete`, threshold controls only whether `Neuron.fire(timestep)` is called. The selected `winner_id` is returned regardless. The same method also multiplies every loser membrane by `0.5` without an inhibitory spike or weighted inhibitory connection.
7. **The noncausal candidate is learned and activated.**  
   `ContextAssemblyNetwork.integrate` unconditionally calls `ContextTransitionMap.observe`, then writes the returned candidate to `ColumnState.active_assembly_ids` and a nonzero compact context code.
8. **L5 records symbolic transitions regardless of L2/3 firing.**  
   `HybridCorticalColumn.process_pattern` calls `NextLinePredictor.record_step`; `backend/cognative_paradigm/domain/sequence_transition_memory.py:SequenceTransitionMemory.observe` increments a shared `(from_line_id, to_line_id)` count.
9. **L5 predicts by maximum count with insertion-order tie behavior.**  
   `SequenceTransitionMemory.best_successor` uses `max(successors, key=count)`. Equal counts retain the first inserted successor. `NextLinePredictor._unknown_prediction` also returns a catalog placeholder at confidence zero.
10. **L6 maps symbolic prediction to fixed gain.**  
    `backend/cognative_paradigm/cortical_column/feedback_gain_controller.py:FeedbackGainController._gain_for_prediction` assigns `2.0` to predicted catalog cells and `0.5` elsewhere.
11. **The next L4 tick consumes that gain.**  
    `HybridCorticalColumn.process_pattern` passes `ColumnState.pending_gain` into `Layer4Adapter.process` before any current-tick causal representation is established.

Compactly:

`line_id → fixed indices → fired_indices-or-modulated fallback → preassigned assembly template → max Vm + line tie-break → winner returned below threshold → unconditional transition map + active state → L5 symbolic transition count → max successor/insertion tie → L6 2.0/0.5 → next L4`

This chain turns `Z` into representation, learning, prediction, and feedback.

## “No forced win” invariants

1. **Authentic register authority:** an active representation requires an authentic register `ONE` and matching spike event from its neuron or population during that tick.
2. **Abstention:** no threshold crossing yields `winner=None`, no active assembly, and context code `0`; absence is not settled by catalog order, label, or maximum subthreshold voltage.
3. **Causal learning:** no transition, plasticity, eligibility, consolidation, binding, or predictor-memory delta occurs without the pre/post events required by that rule.
4. **Actual-pattern authority:** sensory representations derive from the supplied `Pattern` and authentic relay spikes. `line_id` is evaluation metadata, not neural input authority.
5. **No fallback or fabrication:** sensory input, modulated drive, and relay output remain distinct. Empty relay output cannot fall back to input indices.
6. **No downstream effect after abstention:** abstention produces no binding, prediction update, confidence, or non-unity gain.
7. **Inhibition cannot grant a winner:** inhibition may suppress activity through explicit local connections; it cannot assign identity, elevate another neuron, or convert `Z` to `ONE`.
8. **Refractory truth:** a refractory neuron cannot be reported as fired. Event log, register, and return value must agree.
9. **Local learned state:** mutable learned quantities belong to the receiving neuron or synapse; network objects may route events and expose read-only diagnostics.
10. **Auditable provenance:** every learned delta identifies the presynaptic event, postsynaptic event, receiving synapse/neuron, timing, and any connected modulatory event.

## Tenant remediation matrix

The recommended directions below are staged research guidance. They do not lock class design, migration order, or parameter values.

| Tenant | Current mechanism | Violation | Target invariant | Options | Recommended direction | Acceptance tests |
|---|---|---|---|---|---|---|
| T1 | L4 relay-silence fallback; below-threshold L2/3 maximum returned; symbolic L5/L6 proceed | `Z` acquires causal effects | Authentic register authority; abstention; no downstream effect after abstention | Nullable winner; authentic spike set; explicit abstention result; plural causal spikers | Propagate authentic spike-set/abstention semantics through all layers | Empty relay output and subthreshold L2/3 produce no active representation, learned delta, prediction update, or gain; false-winner rate exactly `0` |
| T2 | Shared symbolic transition counts stand in for synaptic co-firing | Counts can change without causal pre/post spikes | Causal learning with local timing evidence | Bounded Hebbian coincidence; pair STDP; triplet STDP; local eligibility trace | Begin with bounded receiving-synapse updates and compare timing rules experimentally | No post-spike means no potentiation; only the participating synapse changes within the defined timing window |
| T3 | Four assemblies start prebound to catalog labels; shared maps own learning | Neurons do not establish local ownership and identity is predetermined | One-pattern local ownership; actual-pattern authority | Individual owner neuron; population with one local binder; revisable binding after mismatch | Start neurons unbound and bind only after repeated causal local evidence | Neuron/catalog permutation does not predetermine labels; no neuron owns two patterns; no binding occurs without spikes |
| T4 | Hybrid L4 has E/I motifs; L2/3 uses loser `Vm × 0.5`; L5/L6 lack explicit E/I topology | Scalar/network suppression bypasses inhibitory cells and weighted connections | Inhibition is explicit, local, graded, and cannot grant a winner | Soft lateral inhibition; central interneuron; local divisive E/I pool; dendrite-targeting inhibition | Evaluate graded spiking inhibition before hard exclusivity | Every suppression delta traces to inhibitory spike/conductance; inhibition may suppress all candidates and never creates an E spike |
| T5 | L2/3 stores refractory state but integrates directly and calls `fire()` outside the common refractory-gated path | A refractory candidate can remain eligible and event truth may diverge | Refractory truth | Common `LifDynamics.try_spike`; clamp/reset during refractory; receive subthreshold input but gate spikes | Reuse the authentic LIF spike path after doctrine resolves whether refractory integration is permitted | Repeated suprathreshold input during refractory yields no second event; register/event/return mismatches exactly `0` |
| T6 | `asm_h1`, `asm_v1`, `asm_d0`, `asm_d1` are static symbol aliases | No emergent one-to-one binding | One learned symbol ↔ one learned representation owner | Local neuron memory plus read-only index; designated binder in an assembly; delayed consolidation | Separate labels from patterns and bind only after causal evidence | Label/pattern permutations still produce a unique learned bijection; duplicate owners and unowned accepted symbols are `0` |
| T7 | Online maps update every eligible call, including noncausal observations; no bounded stability rule | Continuous learning includes invalid evidence and may grow without bound | Continuous, causal, bounded local learning | Weight bounds; homeostasis; decay; metaplasticity; confidence-gated consolidation | Preserve online operation only after causal gates; benchmark retention and adaptation | Abstained ticks change nothing; long streams remain finite; adaptation does not catastrophically erase stable representations |
| T8 | Shared frequency table predicts symbols; equal counts resolve by insertion order | Prediction is global, symbolic, and cannot honestly represent ambiguity | Prediction from causal local state with uncertainty/abstention | Local recurrent transition synapses; population vote; latency/rate confidence; symbolic oracle baseline | Replace or shadow the table with receiving-neuron recurrent synapses; keep table only as a benchmark oracle | No causal predecessor spike means no prediction; equal evidence yields unknown or plural prediction, never catalog-order selection |
| T9 | Shared transition/predictor dictionaries, network WTA, deterministic gain, and production-level registries/gates | Global state decides learning, ownership, or eligibility | Local learned state and auditable connected provenance | Per-neuron incoming synapses; synapse-local eligibility; local dendritic gain; read-only aggregate diagnostics | Move all mutation authority behind neurons/synapses and prohibit global ownership state from deciding a learned delta | Mutation audit maps every delta to a receiver and connected events; deltas based on global state exactly `0` |

## Production force-fire and wipe audit

### What production gets right

Production excitatory competition is stronger than the hybrid path under causal criteria:

- `backend/cognative_paradigm/simulation/wta_coordinator.py:WtaCoordinator` can return no excitatory winner when no candidate spikes.
- Excitatory candidates use `LifDynamics.try_spike`.
- `backend/cognative_paradigm/simulation/nucleus_network.py:NucleusNetwork._apply_authentic_spiker_learning` learns from authentic population spike IDs rather than using diagnostic winner identity as the sole gate.
- Maximum/tie logic identifies a primary among authentic spikers; it does not create an E spike from complete silence.

### Strict-profile exceptions

1. **Forced central inhibitor reports firing while refractory.**  
   `backend/cognative_paradigm/simulation/pretrained_inhibitor_exclusivity.py:PretrainedInhibitorExclusivityPolicy.force_central_fire` returns `(threshold-or-membrane, True)` if the central neuron is refractory and otherwise returns `fired or True`. This can assert an inhibitory event without an authentic register transition.
2. **Loser membrane wipe bypasses weighted synaptic inhibition.**  
   `PretrainedInhibitorExclusivityPolicy.wipe_loser_membranes` directly sets every nonwinner E membrane to `0.0`.
3. **Descending force mode injects threshold and may wipe primary E.**  
   `backend/cognative_paradigm/simulation/descending_inhibition.py:DescendingInhibition._force_pair_inhibition` raises paired I to threshold after an authentic E′ spike and can directly zero the paired primary E membrane. `DescendingInhibition._graded_pair_inhibition` is the available natural-threshold alternative.
4. **Global ownership and eligibility remain migration hazards.**  
   `BoundMatchRecallPolicy`, `PatternMemorySnapshot.owner_for_pattern`, `SymbolRegistry`, and `FeatureCodeOwnership` can provide network-level ownership or eligibility authority. They do not necessarily fabricate spikes, but they require T9 scrutiny.

### Revised production verdicts

The prior audit’s “production T1–T8 PASS, T9 PARTIAL” remains defensible only for a **permissive operational profile** that treats forced inhibitory cascades and direct wipes as accepted abstractions after an authentic E spike.

Under strict no-fabricated-event semantics:

- **T1: PARTIAL.** Excitatory winners require authentic E spikes, but inhibitory firing can be reported without an authentic event.
- **T2: PASS with profile evidence.** Production has spike-linked, neuron-associated conductance plasticity; benchmark provenance remains required.
- **T3: PASS with T9 qualification.** Neuron-associated memory is strong, while global eligibility/ownership orchestration remains interpretive.
- **T4: profile-dependent — PASS for explicit graded E/I; PARTIAL where direct force/wipe substitutes for synaptic dynamics.**
- **T5: PARTIAL.** The central force-fire policy treats refractory as fired.
- **T6: PASS with T9 qualification.** Learned binding exists, but registry authority must remain an index rather than a global learning decider.
- **T7: PASS with causal-audit condition.**
- **T8: PASS with profile evidence.**
- **T9: PARTIAL.** Neuron-owned conductances and eligibility coexist with cross-neuron snapshots, winner/gating decisions, and simulator-level registries.

Production force modes do **not** manufacture an excitatory winner from complete silence: their hard-exclusivity trigger is an authentic E or E′ spike. They still violate the stricter invariants for fabricated inhibitory events, refractory truth, and synaptic-only suppression. They should remain legacy/control profiles, not defaults imported into a strict biological-compliance path.

## Benchmark protocol

### Conditions

Run paired seeds across neuron permutations and label permutations:

1. clean learned sequences;
2. reversed, shuffled, repeated-symbol, and branching sequences;
3. partial and superposed patterns;
4. mismatched `line_id` versus actual `Pattern`;
5. novel noncatalog patterns;
6. relay-silent low-drive input;
7. threshold-near noise and exact membrane ties;
8. long continuous streams and changed sequences;
9. pulses repeated inside the refractory interval;
10. delayed/distractor context.

Compare at minimum: current hybrid, causal-gated hybrid, actual-pattern/emergent binding, local recurrent Hebbian, local STDP/eligibility, graded E/I, optional dendritic/gain profile, production force profile, and production graded profile.

### Required metrics and gates

- **False-winner rate:** reported active representation without an authentic register `ONE` divided by reported representations. **Required: exactly `0`.**
- **Learning without causal provenance:** learned deltas lacking their required pre/post and receiving-object evidence. **Required: exactly `0`.**
- **L4 fabrication rate:** downstream active cells when the excitatory relay spike set is empty. **Required: exactly `0`.**
- **Refractory violations:** interspike intervals below the configured refractory duration plus event/register/return mismatches. **Required: `0`.**
- **Abstention rate:** stratified by clean, noisy, ambiguous, novel, and relay-silent inputs; this is diagnostic, not inherently a minimization target.
- **Binding integrity:** patterns per neuron, symbols per neuron, owners per symbol, duplicate owners, and bindings without causal spikes.
- **Learning success:** episodes to criterion, held-out recognition, retention, and adaptation after sequence change.
- **Prediction:** top-1 accuracy, coverage-versus-accuracy under abstention, branching calibration, END accuracy, and Brier score or negative log likelihood where probabilities exist.
- **Noise/ambiguity:** false-positive representation, calibrated abstention, tie behavior, and novelty confidence.
- **E/I balance:** E/I spike counts, conductance/current ratio, sparsity, total-suppression rate, runaway excitation, and permanent silence.
- **Locality:** owner of every mutated object, connected presynaptic source, postsynaptic event, modulatory source, and global reads used in mutation decisions.
- **Permutation invariance:** performance and ownership distribution under neuron, catalog, and label order permutations.

Promotion evidence should use paired-seed distributions and confidence intervals, not one successful run of the fixed H1→V1→D0→D1 sequence.

## Staged no-code recommendation

1. **Causal gates:** separate input/modulation/relay spike fields; propagate authentic spike sets or abstention; block all learning, binding, prediction, and gain after abstention; enforce refractory truth and provenance.
2. **Actual-pattern and emergent binding:** stop discarding `Pattern`; reduce `line_id` to evaluation metadata; initialize representation neurons symmetrically and unbound; compare single-neuron ownership with population assemblies.
3. **Local recurrent synapses:** move transition mutation to receiving-neuron synapses; require causal pre/post events; compare bounded Hebbian, pair-STDP, triplet-STDP, and local eligibility.
4. **Graded E/I and local prediction:** replace loser decay and force/wipe defaults with explicit local inhibitory connections; derive uncertain prediction from locally learned recurrent input and permit abstention.
5. **Optional multiplicative lab:** only after causal safety passes, compare additive controls with conductance E/I, NMDA-like dendritic coincidence, and synapse-local eligibility × connected modulator.

This sequence is a research recommendation, not an implementation plan.

## Open doctrinal questions

1. Does “one pattern per neuron” permit a distributed assembly with one local binding owner?
2. Are multiple simultaneous authentic representation spikes valid ambiguity, or must ambiguity abstain?
3. Which network-level competition and read-only indexing are permissible under T9?
4. May refractory neurons integrate subthreshold synaptic input, or must membrane be clamped?
5. What event-time window operationalizes “fire together”?
6. Must a modulatory factor arrive over an explicit connection to count as local information?
7. How should prediction uncertainty be represented: no spike, plural spikes, latency, rate, or calibrated confidence?
8. What should novel patterns do: abstain, recruit, or revise an owner?
9. What saturation, forgetting, reconsolidation, and unbinding rules are permitted?
10. Can force modes remain clearly labeled nonbiological control profiles?
11. Does explicit episode END require a causal boundary event before transition learning?
12. Should exact ties remain plural/abstain, or may tracked biological noise resolve them?

## Anti-hardcoding warning

**Do not hardcode the sequence, representation owner, symbol binding, or winner.**

In particular, a compliant design must not:

- map `H1` directly to `asm_h1` or any fixed neuron;
- use `line_id`, catalog order, neuron order, or dictionary insertion order to settle a tie;
- convert sensory or modulated input into relay spikes when the relay is silent;
- choose `max(Vm)` below threshold;
- encode H1→V1→D0→D1 in topology, initial weights, gain, or acceptance tests;
- treat inhibition as permission for another neuron to fire;
- use global tables to decide local learning or ownership;
- use deterministic gain to guarantee a preferred threshold crossing.

Multiplication does not excuse these shortcuts. Multiplying hardcoded labels, global state, or preferred gains only makes forced selection less visible.

## Evidence index

### Authority and prior audit

- `Documents/tenants.txt`
- `Documents/architecture/hybrid_cortical_column_tenant_outline.md`

### Hybrid input and orchestration

- `backend/cognative_paradigm/cortical_column/cortical_column.py:HybridCorticalColumn.process_pattern`
- `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter.process`
- `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter.line_indices`
- `backend/cognative_paradigm/lines.py:LINE_IDS`
- `backend/cognative_paradigm/lines.py:LINE_INDICES`

### Hybrid representation and transition

- `backend/cognative_paradigm/cortical_column/context_assembly.py:ContextAssembly`
- `backend/cognative_paradigm/cortical_column/context_assembly.py:assembly_id_for_line`
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork.__post_init__`
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork._compete`
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork.integrate`
- `backend/cognative_paradigm/domain/context_transition_map.py:ContextTransitionMap.observe`
- `backend/cognative_paradigm/domain/column_state.py:ColumnState`

### Hybrid prediction and gain

- `backend/cognative_paradigm/cortical_column/next_line_predictor.py:NextLinePredictor.record_step`
- `backend/cognative_paradigm/cortical_column/next_line_predictor.py:NextLinePredictor.predict`
- `backend/cognative_paradigm/domain/sequence_transition_memory.py:SequenceTransitionMemory.observe`
- `backend/cognative_paradigm/domain/sequence_transition_memory.py:SequenceTransitionMemory.best_successor`
- `backend/cognative_paradigm/cortical_column/feedback_gain_controller.py:FeedbackGainController._gain_for_prediction`

### Production strict-profile evidence

- `backend/cognative_paradigm/simulation/wta_coordinator.py:WtaCoordinator`
- `backend/cognative_paradigm/simulation/nucleus_network.py:NucleusNetwork._apply_authentic_spiker_learning`
- `backend/cognative_paradigm/simulation/pretrained_inhibitor_exclusivity.py:PretrainedInhibitorExclusivityPolicy.force_central_fire`
- `backend/cognative_paradigm/simulation/pretrained_inhibitor_exclusivity.py:PretrainedInhibitorExclusivityPolicy.wipe_loser_membranes`
- `backend/cognative_paradigm/simulation/descending_inhibition.py:DescendingInhibition._graded_pair_inhibition`
- `backend/cognative_paradigm/simulation/descending_inhibition.py:DescendingInhibition._force_pair_inhibition`
- `backend/cognative_paradigm/simulation/bound_match_recall_policy.py:BoundMatchRecallPolicy`
- `backend/cognative_paradigm/domain/pattern_memory_snapshot.py:PatternMemorySnapshot.owner_for_pattern`
- `backend/cognative_paradigm/domain/symbol_registry.py:SymbolRegistry`
- `backend/cognative_paradigm/domain/feature_code_ownership.py:FeatureCodeOwnership`
