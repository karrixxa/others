# Hybrid Cortical Column — Current Architecture and Tenant Outline

> **BANNER — Path H authority fork (read first)**
>
> - The **Path H tenant FAIL matrix in this outline** (T3/T6/T9 FAIL, catalog assemblies, prior bias, symbolic L5, L6 2.0/0.5) documents **legacy `hybrid_cortical`** only. It is **not** current Path H bio truth.
> - **Current Path H bio** is `hybrid_cortical_biological` Stages **8–10**: tenant audit **T1–T9 PASS**. The companion SVG is the **authoritative diagram** for bio current state.
> - Remediation live behind bio + `ColumnCausalPolicy.is_biological`: see [`tenant_compliance_remediation_plan.md`](tenant_compliance_remediation_plan.md) **Stages 8–10**.
> - Diagram: [`hybrid_cortical_column_current_architecture.svg`](hybrid_cortical_column_current_architecture.svg) · PNG: [`assets/images/hybrid_cortical_column_current_architecture.png`](../../assets/images/hybrid_cortical_column_current_architecture.png).

## Status, authority, and companion diagram

- **Status:** dual-path audit. Path H **bio** current truth lives in the SVG (Stages 8–10). Body sections below that still describe catalog / FAIL matrix remain **legacy `hybrid_cortical`** reference unless marked otherwise.
- **Tenant authority:** [`Documents/tenants.txt`](../tenants.txt), normalized only for spelling and clarity below.
- **Companion diagram:** [`hybrid_cortical_column_current_architecture.svg`](hybrid_cortical_column_current_architecture.svg) — **authority for `hybrid_cortical_biological`**.
- **Scope date:** current repository state at the time of this audit (banner updated for Stages 8–10).
- **Validation note:** tenant verdicts are biological-alignment validation findings, **not security vulnerabilities**.
- **Change boundary:** this document audits the implementation. It does not propose or implement runtime fixes.

## Executive verdict

The repository currently has two sequential but architecturally isolated execution paths:

1. **Path P, production nucleus:** By default `BrainSimulator.stimulate_pattern()` runs `step(pattern)` first (3×3 `Layer1Relay`, four-competitor `NucleusNetwork`, plasticity, symbols, descending inhibition). Exception: `column_only_stimulate` ∧ `hybrid_cortical_biological` skips the nucleus.
2. **Path H, hybrid lab column:** When a hybrid profile + lab are enabled, the simulator invokes an isolated `HybridCorticalColumn.process_pattern()`. Bio takes `Pattern` as sensory authority (`line_id` metadata); legacy `hybrid_cortical` still requires `line_id`. No shared relay/stores with Path P.

**Path H bio** (`hybrid_cortical_biological`, Stages 8–10): **T1–T9 PASS** — see companion SVG.  
**Path H legacy** (`hybrid_cortical`, body sections below): **PASS T7 · PARTIAL T1/T2/T4/T5/T8 · FAIL T3/T6/T9**.

**Path P:** **PASS T1–T8 · PARTIAL T9** (orchestration still consumes some cross-neuron snapshots/gates).

## Scope and dual-path model

### Invocation and ordering

`BrainSimulator.stimulate_pattern(pattern, line_id=...)` performs:

1. Optional replay-buffer recording.
2. **Default:** `result = self.step(pattern)` — the complete production nucleus pulse.
3. **Exception:** when `column_only_stimulate` is true **and** the profile is `hybrid_cortical_biological`, skip the nucleus and build a column-only stimulation result instead.
4. If a hybrid column exists:
   - **Bio** (`hybrid_cortical_biological`): `process_pattern(line_id, pattern, …)` — requires a `Pattern` (line_id is metadata).
   - **Legacy** (`hybrid_cortical`): `process_pattern(line_id, pattern)` only when `line_id` is not `None`.
5. Return the (production or column-only) `SimulationResult`.

Under the default dual-path order, the hybrid path is an isolated lab observer/learner after production. Under `column_only_stimulate` ∧ bio, the returned result is column-only (nucleus skipped).

### Isolation boundary

- Production owns `BrainSimulator._layer1`, `BrainSimulator._nucleus`, `BrainSimulator._descending`, `BrainSimulator._symbols`, production plasticity, and production input edges.
- Hybrid owns a fresh `Layer1Relay`, its own input edges, `Layer4Adapter`, `ContextAssemblyNetwork`, `NextLinePredictor`, `FeedbackGainController`, and `ColumnState`.
- `ColumnArchitectureFactory` creates the hybrid object only when `LearningDynamics.uses_hybrid_column()` is true.
- There is **no shared relay** between Path P and Path H.
- **Bio:** `Pattern` is sensory authority; `line_id` is metadata. **Legacy `hybrid_cortical`:** catalog `line_id` / `LINE_INDICES` remain authoritative and the passed `pattern` may be discarded (v1).

### Verified production ring count

`NUCLEUS_RING_SIZE = len(LINE_IDS)`. `LINE_IDS` is `("H1", "V1", "D0", "D1")`, so the current production nucleus ring contains **4 excitatory competitors**, not 8.

## Current component inventory

### Path P — production

- **`BrainSimulator`**
  - Owns the production simulation clock, Layer 1 relay, nucleus, descending inhibition, input edges, symbol registry, plasticity, event log, replay buffer, and optional hybrid column.
  - Runs production before hybrid by default; skipped under `column_only_stimulate` ∧ bio.
- **`Layer1Relay`**
  - Maps the 3×3 sensory input into nine E/I/E′ relay motifs.
  - Receives production descending inhibition from the preceding pulse.
- **`NucleusNetwork`**
  - Contains four `NucleusRingCompetitor` excitatory neurons, associated inhibitory flow, winner-take-all coordination, conductance maps, timing traces, and learning machinery.
- **Production learning**
  - Conductance plasticity and configured lab plasticity update neuron-associated relay and sensory conductances.
  - Eligibility traces and `NeuronMemory` support ongoing adaptation and binding.
- **`SymbolRegistry`**
  - Enforces production symbol ownership/binding for the winning neuron representation.
- **`DescendingInhibition`**
  - Converts production activity into inhibition applied to the production relay on the next pulse.

### Path H — hybrid L4

- **`Layer4Adapter`**
  - Wraps an isolated `Layer1Relay`.
  - Looks up catalog indices from `LINE_INDICES`.
  - Applies the previous tick's `CellGainMap` to ephemeral copies of input edges.
  - Never mutates its persistent input-edge weights when applying gain.
  - Runs relay spiking and returns fired indices, falling back to modulated indices if no excitatory relay index is returned.
  - The pending gain is consumed immediately after this L4 processing.

### Path H — hybrid L2/3

- **`ContextAssemblyNetwork`**
  - Instantiates exactly four catalog-aligned assemblies: `asm_h1`, `asm_v1`, `asm_d0`, and `asm_d1`.
  - Computes each assembly drive as sensory overlap plus learned transition bias plus `0.20` prior-active bias.
  - Uses LIF leak and synaptic integration to update membrane floats.
  - Selects the maximum-membrane assembly, with the observed catalog line as tie-break preference.
  - Calls `Neuron.fire()` if the selected membrane meets threshold.
  - Multiplies every losing membrane by `0.5`; this is scalar suppression, not an inhibitory-neuron graph.
  - Records the selected assembly in `ContextTransitionMap`, adding `0.25` to the `(prior line, current line, winner assembly)` entry.

### Path H — hybrid L5

- **`NextLinePredictor`**
  - Records the previous observed line to current observed line transition.
  - Records `END` when `end_episode()` is called.
  - Uses `SequenceTransitionMemory` frequency counts.
  - Predicts the most frequent successor and sets confidence to `best_count / total_count`.
  - Returns a confidence-zero catalog placeholder when no evidence exists.
  - This is symbolic table prediction, not neuron-local `NeuronPrediction`.

### Path H — hybrid L6

- **`FeedbackGainController`**
  - Maps a confident line prediction to per-cell gain.
  - Uses gain `2.0` on predicted catalog cells and `0.5` on all others.
  - Uses unity gain for confidence `0` or an `END` prediction.
  - Stores the result in `ColumnState.pending_gain` for one-shot use by the next hybrid L4 tick.
  - This is deterministic scalar modulation, not a spiking E/I network.

### Path H — state and reset

- **`ColumnState`**
  - Contains transient episode ID, sequence index, previous input, active assembly ID, compact context code, prediction, pending gain, and accumulated silence.
  - Explicitly excludes learned weights, conductances, synapses, eligibility, and predictor tables.
- **`ColumnStateResetPolicy`**
  - Produces a boundary on explicit `END` or accumulated silence greater than or equal to `episode_silence_reset_ms` (default `5000 ms`).
- **`reset_transient()`**
  - Replaces `ColumnState` with a new episode state.
  - Clears L2/3 membranes, register state, and refractory timestamps.
  - Preserves `ContextTransitionMap` and `SequenceTransitionMemory`.
- **`full_reset()`**
  - Also resets the isolated L4 relay and timestep.
  - The current implementation still preserves the two learned table stores unless the column object itself is recreated.

### Frontend visualization

- **`ColumnStateModel`**
  - Defensively normalizes serialized backend state for presentation.
- **`CorticalColumnScene` and layer visuals**
  - Render L2/3, L4, predictor, feedback, and flow state through Three.js.
  - Consume state via `applyState`; they do not participate in backend neural computation or learning.
- **Boundary**
  - Frontend visualization is read-only presentation and must not be counted as neural architecture.

## Complete connection inventory

Each item records **source → target; establishment; persistence; locality; signal model; evidence**.

### Entry and fork

1. **3×3 input pattern → `BrainSimulator.step()`**
   - Establishment: static call path.
   - Persistence: per pulse.
   - Local/global: simulator orchestration.
   - Signal: sensory edge set into spiking production path.
   - Evidence: `backend/cognative_paradigm/simulation/engine.py:BrainSimulator.stimulate_pattern`.

2. **`line_id` + input pattern → optional `HybridCorticalColumn.process_pattern()`**
   - Establishment: static call path gated by hybrid column existence and non-null `line_id`.
   - Persistence: per eligible pulse.
   - Local/global: simulator orchestration; path remains state-isolated.
   - Signal: catalog symbol; passed `pattern` is discarded by hybrid v1.
   - Evidence: `backend/cognative_paradigm/simulation/engine.py:BrainSimulator.stimulate_pattern`; `backend/cognative_paradigm/cortical_column/cortical_column.py:HybridCorticalColumn.process_pattern`.

### Production connections

3. **Input edges → production `Layer1Relay`**
   - Establishment: static 3×3 topology.
   - Persistence: relay and input-edge objects persist until simulator reset.
   - Local/global: cell/relay topology under simulator ownership.
   - Signal: spiking E/I/E′ relay activity.
   - Evidence: `backend/cognative_paradigm/simulation/engine.py:BrainSimulator.__init__`; `backend/cognative_paradigm/simulation/layer1_network.py:Layer1Relay`.

4. **Production `Layer1Relay` → `NucleusNetwork`**
   - Establishment: static relay-to-ring wiring with neuron-associated conductance maps.
   - Persistence: learned conductances persist during simulator lifetime/checkpoint semantics.
   - Local/global: primarily neuron-owned conductance state.
   - Signal: relay spikes and weighted synaptic drive.
   - Evidence: `backend/cognative_paradigm/simulation/engine.py:BrainSimulator.step`; `backend/cognative_paradigm/simulation/nucleus_network.py:NucleusNetwork`; `backend/cognative_paradigm/simulation/nucleus_ring_competitor.py:NucleusRingCompetitor`.

5. **Sensory/relay evidence → each `NucleusRingCompetitor`**
   - Establishment: static candidate neurons; learned relay and sensory conductance values.
   - Persistence: conductance maps and eligibility state persist until reset.
   - Local/global: owned by each ring competitor.
   - Signal: spiking timing and conductance plasticity.
   - Evidence: `backend/cognative_paradigm/simulation/nucleus_ring_competitor.py:NucleusRingCompetitor.apply_relay_spike_plasticity`; `NucleusRingCompetitor.apply_sensory_spike_plasticity`.

6. **Nucleus winner → `NeuronMemory` / `SymbolRegistry`**
   - Establishment: learned binding under production winner/binding rules.
   - Persistence: binding persists until unbind/reset/checkpoint behavior.
   - Local/global: neuron memory is neuron-associated; registry is a simulator-level ownership index.
   - Signal: winner identity and symbolic binding.
   - Evidence: `backend/cognative_paradigm/domain/neuron_memory.py:NeuronMemory`; `backend/cognative_paradigm/domain/symbol_registry.py:SymbolRegistry`; `backend/cognative_paradigm/simulation/nucleus_network.py:NucleusNetwork`.

7. **Production pulse activity → `DescendingInhibition` → production `Layer1Relay` next pulse**
   - Establishment: static feedback topology with configurable gains/modes and learned afferent behavior where enabled.
   - Persistence: pending effect crosses one pulse; configured/learned state persists per component semantics.
   - Local/global: production-network feedback.
   - Signal: inhibitory modulation.
   - Evidence: `backend/cognative_paradigm/simulation/engine.py:BrainSimulator._configure_descending`; `BrainSimulator._wire_inhibitory_flow`; `backend/cognative_paradigm/simulation/descending_inhibition.py:DescendingInhibition`.

### Hybrid connections

8. **Catalog `line_id` → `Layer4Adapter.line_indices()`**
   - Establishment: static `LINE_INDICES` catalog.
   - Persistence: immutable module mapping.
   - Local/global: global catalog lookup.
   - Signal: symbolic line ID converted to cell indices.
   - Evidence: `backend/cognative_paradigm/lines.py:LINE_INDICES`; `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter.line_indices`.

9. **Prior `ColumnState.pending_gain` → ephemeral hybrid L4 input edges**
   - Establishment: deterministic rule.
   - Persistence: one tick; persistent input edges are not mutated.
   - Local/global: column-wide nine-cell gain map.
   - Signal: scalar sensory-drive modulation.
   - Evidence: `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter._ephemeral_edges`.

10. **Ephemeral hybrid L4 input edges → isolated `Layer1Relay`**
    - Establishment: static isolated relay.
    - Persistence: relay state persists until `full_reset`; ephemeral edges exist for the tick.
    - Local/global: hybrid-column local.
    - Signal: E/I relay spiking.
    - Evidence: `backend/cognative_paradigm/cortical_column/cortical_column.py:HybridCorticalColumn.__init__`; `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter.process`.

11. **L4 activation → each L2/3 `ContextAssembly`**
    - Establishment: static catalog templates and sensory weight `0.35`.
    - Persistence: templates are fixed; membranes are transient.
    - Local/global: per-assembly membrane integration, but template identity is preassigned globally.
    - Signal: overlap count converted to scalar drive.
    - Evidence: `backend/cognative_paradigm/cortical_column/context_assembly.py:ContextAssembly.sensory_drive`.

12. **`ContextTransitionMap` → each L2/3 assembly drive**
    - Establishment: online learned count increments of `0.25`.
    - Persistence: survives episode transient reset and is serialized.
    - Local/global: shared column-level table.
    - Signal: symbolic key lookup to scalar transition bias.
    - Evidence: `backend/cognative_paradigm/domain/context_transition_map.py:ContextTransitionMap`; `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork._compete`.

13. **Prior active assembly → same candidate's L2/3 drive**
    - Establishment: fixed rule with `prior_active_bias = 0.20`.
    - Persistence: prior active ID is transient.
    - Local/global: shared `ColumnState` lookup.
    - Signal: scalar bias.
    - Evidence: `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork._compete`.

14. **L2/3 candidate membranes → WTA winner**
    - Establishment: fixed maximum rule with observed-line tie break.
    - Persistence: membranes persist within episode; loser membranes are multiplied by `0.5`.
    - Local/global: network-level competition.
    - Signal: membrane floats; selected neuron fires only if threshold is met.
    - Evidence: `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork._compete`.

15. **L2/3 winner + prior/current line → `ContextTransitionMap`**
    - Establishment: learned online observation.
    - Persistence: persistent table.
    - Local/global: shared column-level store.
    - Signal: symbolic tuple and scalar increment.
    - Evidence: `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork.integrate`; `backend/cognative_paradigm/domain/context_transition_map.py:ContextTransitionMap.observe`.

16. **Prior observed line → current observed line/END → `SequenceTransitionMemory`**
    - Establishment: learned online count.
    - Persistence: survives transient reset and is serialized.
    - Local/global: shared L5 table.
    - Signal: symbolic transition/count.
    - Evidence: `backend/cognative_paradigm/cortical_column/next_line_predictor.py:NextLinePredictor.record_step`; `backend/cognative_paradigm/domain/sequence_transition_memory.py:SequenceTransitionMemory.observe`.

17. **`SequenceTransitionMemory` → L5 prediction**
    - Establishment: deterministic maximum-frequency rule over learned counts.
    - Persistence: result stored transiently; counts persist.
    - Local/global: shared L5 table.
    - Signal: symbolic successor/END plus confidence.
    - Evidence: `backend/cognative_paradigm/domain/sequence_transition_memory.py:SequenceTransitionMemory.best_successor`; `backend/cognative_paradigm/cortical_column/next_line_predictor.py:NextLinePredictor.predict`.

18. **L5 prediction → L6 `CellGainMap`**
    - Establishment: fixed `2.0`/`0.5`/unity rule.
    - Persistence: pending for one subsequent hybrid tick.
    - Local/global: column-wide deterministic transform.
    - Signal: symbolic prediction converted to nine scalar gains.
    - Evidence: `backend/cognative_paradigm/cortical_column/feedback_gain_controller.py:FeedbackGainController`.

19. **Serialized hybrid state → frontend `ColumnStateModel` → `CorticalColumnScene`**
    - Establishment: static API/presentation mapping.
    - Persistence: UI snapshot only.
    - Local/global: presentation boundary.
    - Signal: serialized state and visual animation state.
    - Evidence: `frontend/src/app/cortical/ColumnStateModel.js:ColumnStateModel`; `frontend/src/app/cortical/visualization/CorticalColumnScene.js:CorticalColumnScene`.

## Tenant-by-tenant audit

### T1 — Firing is causal; not firing is non-causal (1 versus Z)

- **Normalized tenant:** learning and downstream causal influence should follow actual firing events; non-firing should not be treated as equivalent evidence.
- **Path P verdict: PASS.**
- **Path P evidence:** PASS is grounded in **1/Z spike-register output causality**: a firing event writes the causal output register, while a non-firing state does not. Production relays and nucleus competitors also use refractory behavior, event timing, winner selection, and spike-linked plasticity. Hot-nonspiker LTD is complementary depression of an active-but-nonfiring competitor; it does not create causal output from non-firing.
- **Path H verdict: PARTIAL.**
- **Path H evidence:** hybrid L4 uses a spiking `Layer1Relay`. L2/3 integrates LIF membrane values but always chooses a maximum membrane candidate, records that winner, and returns it even when the selected neuron does not cross threshold. L5 and L6 are symbolic/deterministic.
- **Exact gap location:** `ContextAssemblyNetwork._compete()` returns `winner_id` regardless of threshold crossing; `NextLinePredictor` and `FeedbackGainController` do not use firing events.
- **Gap class:** hybrid neural-causality incompleteness.
- **Later plan question:** Must every L2/3 transition observation and every L5/L6 effect require an actual spike, and what should a no-spike tick mean?

### T2 — Neurons that fire together wire together

- **Normalized tenant:** co-firing should alter the synaptic relationship between participating neurons.
- **Path P verdict: PASS.**
- **Path P evidence:** production conductance plasticity provides co-active potentiation for firing relationships, alongside heterosynaptic LTD on inactive inputs and configured competitive/prediction-error LTD. These complementary depression paths sharpen competition without replacing the core fire-together potentiation rule; eligibility machinery updates neuron-associated sensory and relay conductances from timing/activity evidence.
- **Path H verdict: PARTIAL.**
- **Path H evidence:** hybrid learning is continuous and activity-associated, but `ContextTransitionMap` and `SequenceTransitionMemory` increment symbolic count tables rather than neuron-owned synaptic conductances driven by pre/post spikes.
- **Exact gap location:** `ContextTransitionMap.observe()` and `SequenceTransitionMemory.observe()`.
- **Gap class:** learning representation mismatch.
- **Later plan question:** Which hybrid transitions must be represented as explicit pre/post synapses, and what timing window defines co-firing?

### T3 — Each neuron controls local learning and owns only one pattern

- **Normalized tenant:** each neuron must own its learning state locally and bind to no more than one pattern.
- **Path P verdict: PASS.**
- **Path P evidence:** each `NucleusRingCompetitor` owns its neuron, sensory conductances, relay conductances, and eligibility trace; production symbol ownership enforces one representation owner.
- **Path H verdict: FAIL.**
- **Path H evidence:** L2/3 assemblies are created directly from the four catalog line IDs and therefore begin preassigned. Learned transition state is stored in shared maps rather than in the selected neuron's own synapses.
- **Exact gap location:** `ContextAssemblyNetwork.__post_init__()` constructs `ContextAssembly(line_id=...)` for all `LINE_IDS`; `ContextAssembly.assembly_id` is derived from the line; shared stores live in `ContextTransitionMap` and `SequenceTransitionMemory`.
- **Gap class:** preassignment and non-local ownership.
- **Later plan question:** Should hybrid assemblies begin unbound, and what event establishes an irreversible or revisable one-pattern ownership relation?

### T4 — Excitatory and inhibitory weights and connections

- **Normalized tenant:** architecture should represent explicit excitatory and inhibitory cells/connections with independently meaningful weights.
- **Path P verdict: PASS.**
- **Path P evidence:** production Layer 1 uses E/I/E′ relay motifs; the nucleus and descending path include explicit inhibitory flow and configurable excitatory/inhibitory conductance behavior.
- **Path H verdict: PARTIAL.**
- **Path H evidence:** hybrid L4 inherits E/I relay behavior. L2/3 competition suppresses losing membrane values by multiplying by `0.5` rather than routing activity through inhibitory neurons/connections. L5 and L6 have no E/I graph.
- **Exact gap location:** `ContextAssemblyNetwork._compete()` loser loop; all of `NextLinePredictor`; all of `FeedbackGainController`.
- **Gap class:** missing laminar E/I topology.
- **Later plan question:** Which inhibitory interneuron roles and weighted connections are required in L2/3, L5, and L6 while preserving the current laminar responsibilities?

### T5 — Refractory period

- **Normalized tenant:** a neuron that fires must be prevented from firing again during its refractory interval.
- **Path P verdict: PASS.**
- **Path P evidence:** production spiking paths use neuron refractory state through their firing/integration flow.
- **Path H verdict: PARTIAL.**
- **Path H evidence:** hybrid L4 honors relay refractory behavior. L2/3 creates neurons with `refractory_period=1` and `Neuron.fire()` sets refractory state, but `ContextAssembly.integrate()` directly leaks and integrates without checking `is_refractory` or using a refractory-gated `try_spike` path.
- **Exact gap location:** `ContextAssembly.integrate()` and `ContextAssemblyNetwork._compete()`.
- **Gap class:** refractory state exists but is not enforced during L2/3 integration/selection.
- **Later plan question:** At which point must refractory gating occur—before integration, before WTA eligibility, or both?

### T6 — One-to-one symbol to representation

- **Normalized tenant:** each symbol must bind one-to-one to a learned neural representation.
- **Path P verdict: PASS.**
- **Path P evidence:** `SymbolRegistry` and production binding logic map symbols to winning neuron identities with ownership semantics.
- **Path H verdict: FAIL.**
- **Path H evidence:** `asm_h1`, `asm_v1`, `asm_d0`, and `asm_d1` are static aliases derived from catalog labels. The hybrid path has no emergent symbol-binding mechanism.
- **Exact gap location:** `assembly_id_for_line()` and `ContextAssemblyNetwork.__post_init__()`.
- **Gap class:** hardcoded representation identity.
- **Later plan question:** Should hybrid symbols bind to individual neurons, assemblies, or another representation unit, and when is uniqueness enforced?

### T7 — Continuous learning

- **Normalized tenant:** learning remains active online as observations arrive rather than occurring only in a separate batch phase.
- **Path P verdict: PASS.**
- **Path P evidence:** production conductance, eligibility, and binding behavior update during stimulation.
- **Path H verdict: PASS.**
- **Path H evidence:** every eligible `process_pattern()` can update both the context transition map and sequence transition memory; `end_episode()` also records END evidence.
- **Exact gap location:** none for the stated continuous-learning requirement.
- **Gap class:** none.
- **Later plan question:** What stability, saturation, or forgetting constraints must later acceptance criteria place on always-on hybrid learning?

### T8 — Prediction

- **Normalized tenant:** learned neural state should predict future input or sequence state.
- **Path P verdict: PASS.**
- **Path P evidence:** production includes neuron prediction machinery and predictive/descending influence within the biological engine.
- **Path H verdict: PARTIAL.**
- **Path H evidence:** hybrid L5 predicts successor or END from observed frequencies, computes confidence, and L6 modulates the next L4 tick. Prediction exists functionally, but it is a shared symbolic frequency table rather than neuron-local `NeuronPrediction`.
- **Exact gap location:** `NextLinePredictor` and `SequenceTransitionMemory`.
- **Gap class:** prediction mechanism is non-neural/global.
- **Later plan question:** What neural substrate should own prediction, and how should its confidence emerge from local activity?

### T9 — Learning occurs in the neuron using only connected information; nothing global

- **Normalized tenant:** learning must be neuron-local and based only on information arriving through that neuron's connections; no shared/global learning authority.
- **Path P verdict: PARTIAL.**
- **Path P evidence:** ring competitors own neuron-specific conductance maps and eligibility traces, including explicitly documented neuron-local sensory plasticity. However, production coordination includes cross-neuron snapshots, network winner/gating decisions, and a simulator-level `SymbolRegistry`.
- **Path P uncertainty:** the exact boundary between acceptable network competition and prohibited global learning needs a tenant-level interpretation. The current evidence supports PARTIAL rather than an unqualified PASS.
- **Path H verdict: FAIL.**
- **Path H evidence:** `ContextTransitionMap` and `SequenceTransitionMemory` are shared column-level dictionaries keyed by symbolic IDs. L2/3 WTA and L6 gain are network-wide deterministic operations.
- **Exact gap location:** `ContextTransitionMap`, `SequenceTransitionMemory`, `ContextAssemblyNetwork._compete()`, and `FeedbackGainController`.
- **Gap class:** global/shared learning and control state.
- **Later plan question:** Which network-level operations remain permissible if all mutable learned state must move behind neuron/synapse ownership?

## Persistence and reset semantics

### Persists across normal hybrid ticks

- Isolated L4 relay transient dynamics and timestep.
- L2/3 assembly membranes and refractory fields within the episode.
- `ColumnState` episode context.
- `ContextTransitionMap` learned float counts.
- `SequenceTransitionMemory` learned integer counts.

### Cleared on explicit END or silence ≥ 5000 ms

- Previous input ID.
- Active assembly IDs.
- Compact context code.
- Current prediction.
- Pending gain.
- Accumulated silence.
- L2/3 assembly membranes, registers, and refractory timestamps.
- Sequence index is reset through replacement with a new initial `ColumnState`.
- Episode ID increments.

### Preserved on transient reset

- `ContextTransitionMap`.
- `SequenceTransitionMemory`.
- Hybrid L4 relay state and timestep, unless a full reset is invoked.

### Full simulator reset

- Production simulation components are reset through `BrainSimulator.reset()`.
- If the hybrid column exists, `HybridCorticalColumn.full_reset()` clears transient hybrid state and resets the isolated L4 relay.
- The current `full_reset()` method does not explicitly clear the two hybrid learned table stores.

### Serialization

- Hybrid checkpoint state serializes transient `ColumnState`, predictor memory, transition map, L4 timestep, current prediction, and last activation.
- Restore reconstructs the transition map and predictor from payloads and rebuilds transient state defensively.

## Known non-goals and planned gaps

The following are current architectural boundaries or acknowledged gaps, not implemented commitments:

- The hybrid path does not replace the production path.
- The hybrid path does not share the production relay, nucleus, symbol registry, or learned conductance maps.
- Frontend rendering is not part of the neural model.
- Hybrid v1 uses only four center-crossing catalog line patterns.
- Hybrid v1 treats `line_id` as authoritative and discards its passed `Pattern`.
- Hybrid L2/3 uses one neuron object per catalog-aligned assembly; it does not model a multi-neuron biological assembly.
- Hybrid L5 prediction and L6 feedback are functional abstractions rather than spiking laminar networks.
- Hybrid count-table learning has no documented saturation, decay, or forgetting rule.
- This audit does not choose a remediation architecture, migration sequence, or acceptance threshold.

## Plan-of-action questions only

1. What exact interpretation of T9 distinguishes permissible network competition from prohibited global learning?
2. Must hybrid representations begin unbound, and what local event binds one pattern to one neuron or assembly?
3. Is an L2/3 assembly intended to remain one representative neuron or become a population with explicit internal connectivity?
4. Must L2/3 state transition recording require a threshold-crossing spike?
5. How should no-spike ticks propagate to L5 prediction and L6 feedback?
6. Which explicit excitatory and inhibitory neuron classes and connections are required in L2/3, L5, and L6?
7. Where must refractory gating occur in the hybrid integration and WTA sequence?
8. What local synaptic mechanism should replace or constrain `ContextTransitionMap`?
9. What neural owner should replace or constrain `SequenceTransitionMemory`?
10. How should prediction confidence emerge from local neural state?
11. Should L6 remain a gain abstraction, or must its gain arise from an explicit spiking feedback circuit?
12. Should `full_reset()` clear learned hybrid stores, and how should that differ from episode reset and checkpoint restore?
13. What saturation, decay, forgetting, and conflict rules are required for continuous learning?
14. Should hybrid input be derived from the actual `Pattern` rather than only from catalog `line_id`, and how are non-catalog inputs handled?
15. What measurable acceptance criteria determine PASS for each currently partial or failed tenant?

## Evidence index

### Canonical tenant and catalog

- `Documents/tenants.txt`
- `backend/cognative_paradigm/lines.py:LINE_IDS`
- `backend/cognative_paradigm/lines.py:LINE_INDICES`
- `backend/cognative_paradigm/lines.py:LINES`

### Dual-path orchestration

- `backend/cognative_paradigm/simulation/engine.py:BrainSimulator.__init__`
- `backend/cognative_paradigm/simulation/engine.py:BrainSimulator.stimulate_pattern`
- `backend/cognative_paradigm/simulation/engine.py:BrainSimulator.reset`
- `backend/cognative_paradigm/cortical_column/column_architecture_factory.py:ColumnArchitectureFactory`
- `backend/cognative_paradigm/cortical_column/cortical_column.py:HybridCorticalColumn`

### Production path

- `backend/cognative_paradigm/simulation/layer1_network.py:Layer1Relay`
- `backend/cognative_paradigm/simulation/nucleus_network.py:NucleusNetwork`
- `backend/cognative_paradigm/simulation/nucleus_ring_competitor.py:NUCLEUS_RING_SIZE`
- `backend/cognative_paradigm/simulation/nucleus_ring_competitor.py:NucleusRingCompetitor`
- `backend/cognative_paradigm/simulation/descending_inhibition.py:DescendingInhibition`
- `backend/cognative_paradigm/domain/neuron_memory.py:NeuronMemory`
- `backend/cognative_paradigm/domain/symbol_registry.py:SymbolRegistry`

### Hybrid L4–L6

- `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter`
- `backend/cognative_paradigm/cortical_column/context_assembly.py:ContextAssembly`
- `backend/cognative_paradigm/cortical_column/context_assembly.py:assembly_id_for_line`
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork`
- `backend/cognative_paradigm/cortical_column/next_line_predictor.py:NextLinePredictor`
- `backend/cognative_paradigm/cortical_column/feedback_gain_controller.py:FeedbackGainController`

### Hybrid state and learned stores

- `backend/cognative_paradigm/domain/column_state.py:ColumnState`
- `backend/cognative_paradigm/domain/column_state.py:ColumnStateResetPolicy`
- `backend/cognative_paradigm/domain/context_transition_map.py:ContextTransitionMap`
- `backend/cognative_paradigm/domain/sequence_transition_memory.py:SequenceTransitionMemory`
- `backend/cognative_paradigm/domain/column_signal.py:CellGainMap`
- `backend/cognative_paradigm/domain/column_signal.py:ColumnPrediction`

### Frontend presentation

- `frontend/src/app/cortical/ColumnStateModel.js:ColumnStateModel`
- `frontend/src/app/cortical/visualization/ColumnSceneStateMapper.js`
- `frontend/src/app/cortical/visualization/CorticalColumnScene.js:CorticalColumnScene`

## Uncertainty and interpretation notes

- **Ring count:** resolved, not uncertain. The current ring count is 4 because `NUCLEUS_RING_SIZE` derives from the four-entry `LINE_IDS` tuple.
- **Path P T9:** remains interpretive. Production has strong neuron-owned conductance and eligibility evidence, but its cross-neuron snapshots, winner/gating coordination, and simulator-level ownership registry prevent an unqualified PASS under the strict “nothing global” wording.
- **“One pattern per neuron”:** the tenant text does not define whether a multi-neuron assembly can be the representation owner. Later planning must settle that before selecting hybrid acceptance criteria.
- **“Causal”:** the tenant source spells this “casual.” This audit normalizes it to “causal” based on the parenthetical firing-versus-non-firing distinction.
