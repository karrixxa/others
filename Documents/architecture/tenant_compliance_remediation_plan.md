# Tenant Compliance Remediation Plan

## Status

- **Plan status:** authorized; Stages 0–7 runtime implementation **DONE** (Helbrecht, 2026-07-20).
- **Runtime implementation:** Stages 0–7 complete under profile isolation. Legacy `compatibility` / `hybrid_cortical` remain bit-compatible; all new causal behavior is gated on `hybrid_cortical_biological` + `ColumnCausalPolicy.is_biological`.
- **Authority source:** Tech-Priest Dominus RESEARCH_SUMMARY (tenant/no-forced-win → concrete staged remediation), converting approved research baselines into an implementation-ready, profile-isolated plan.
- **Scope of this document:** staged remediation plan; Stages 0–7 code is live behind `hybrid_cortical_biological` + `ColumnCausalPolicy`. Legacy `compatibility` / `hybrid_cortical` remain bit-compatible.

## Authority links

| Authority | Path | Role |
|---|---|---|
| Constitutional tenants | [`Documents/tenants.txt`](../tenants.txt) | T1–T9 normative authority |
| No-forced-win research | [`Documents/architecture/tenant_compliance_no_forced_win_research.md`](tenant_compliance_no_forced_win_research.md) | Causal chain, invariants, tenant matrix, benchmark gates |
| Multiplicative computation research | [`Documents/biology/multiplicative_computation_research.md`](../biology/multiplicative_computation_research.md) | Optional lab after causal safety; not required for basic sequence learning |
| Formal math draft | [`Documents/Math_breakdown.txt`](../Math_breakdown.txt) | Adopt / adapt / reject evaluation against T1–T9 |
| Prior hybrid outline | [`Documents/architecture/hybrid_cortical_column_tenant_outline.md`](hybrid_cortical_column_tenant_outline.md) | Earlier permissive audit; tightened by no-forced-win research |

## Executive summary

Direction is right: preserve `compatibility` as production default, isolate a strict biological hybrid profile, and remediate the hybrid column toward authentic causal semantics.

The blocker is the **causal forced-win chain**, not missing multiplicative computation. Fabricated L4 activity, below-threshold L2/3 winners, catalog-bound assemblies, unconditional transition learning, symbolic max-count prediction, and deterministic L6 gain convert non-firing (`Z`) into representation, learning, prediction, and feedback.

**Multiplicative / nonlinear lab mechanisms are optional and come only after Stage 6 causal safety passes.** Exact global sigma-pi is not a biological claim for this project.

Compact forced-win chain:

`line_id → fixed indices → fired_indices-or-modulated fallback → preassigned assembly template → max Vm + line tie-break → winner returned below threshold → unconditional transition map + active state → L5 symbolic transition count → max successor/insertion tie → L6 2.0/0.5 → next L4`

## Math_breakdown adopt / reject table

Exact Dominus evaluation of [`Documents/Math_breakdown.txt`](../Math_breakdown.txt):

### Adopt / adapt

| Equation / concept | Decision | Caveat |
|---|---|---|
| \(y_n(t)\in\{0,1\}\) from threshold crossing | Adopt | `y=1` only when `LifDynamics.try_spike()` succeeds. |
| Refractory forces \(y_n(t)=0\) | Adopt | Register, event log, return value, and reported active set must agree. |
| \(A_{L4}(t)=\{i\mid y_{L4_i}(t)=1\}\) | Adopt verbatim | This must be the downstream L4 authority. No fallback to input or gain-gated indices. |
| \(\tilde{x}=g\odot x\) | Adapt | Represents drive scaling only, never an active spike set. Gain must be bounded, connected, local, and neutral after abstention. |
| \(\Delta w_{ik}=\eta\, y_i y_k\) | Adapt | Weight belongs to the receiving synapse; clip to bounds and record pre/post/timing provenance. |
| Confidence and explicit `END` | Adopt conceptually | Confidence must permit unknown/plural outcomes. END learning requires a causal boundary event. |
| Silence threshold | Adopt as episode policy | Silence resets transient state; it must not manufacture an END prediction or transition by itself unless doctrine defines silence as a causal boundary signal. |

### Reject as written

| Math_breakdown mechanism | Conflict |
|---|---|
| Assemblies indexed by `H1/V1/D0/D1` | Preassigned identity violates T3/T6. |
| \(k^*=\arg\max D_k\) unconditionally | Forced winner violates T1. |
| \(D=D_{\mathrm{sens}}D_{\mathrm{trans}}D_{\mathrm{prior}}\) | A zero factor can erase authentic evidence; a large factor can guarantee a preferred winner. Factors are also global/symbolic. |
| \(\Delta w_{\mathrm{trans}}=\eta A_k\) | Missing causal presynaptic event. |
| Global \(C_{a\to b}\) tables | Global learning authority violates T9. |
| \(\hat{s}=\arg\max P\) without abstention | Forces ambiguity into one symbol. |
| Deterministic `2.0/0.5` symbolic gain | Can force or suppress candidates based on catalog identity. |
| “Inhibition encoded in WTA” | WTA is not an explicit inhibitory cell, weight, connection, or spike. |
| Claimed tenant compliance | Incorrect: the specification encodes forced WTA, catalog ownership, and global memory. |

## No-forced-win invariants

Copied/adapted from [`tenant_compliance_no_forced_win_research.md`](tenant_compliance_no_forced_win_research.md); binding for every biological-profile stage:

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

## Confirmed forced-winner chain (code)

1. `HybridCorticalColumn.process_pattern()` discards `pattern`.
2. `Layer4Adapter.line_indices()` derives input from catalog `LINE_INDICES`.
3. `Layer4Adapter.process()` uses `fired_indices or modulated_indices`, fabricating downstream activation after relay silence.
4. `ContextAssemblyNetwork.__post_init__()` preassigns assemblies to `LINE_IDS`.
5. `ContextAssembly.template_indices` embeds catalog templates.
6. `_compete()` selects `max(...)` across all assemblies and favors matching `line_id`.
7. The selected identity is returned even when `Neuron.fire()` is not called.
8. Losers receive direct `membrane *= 0.5` without an inhibitory spike.
9. `integrate()` always mutates `ContextTransitionMap` and active state.
10. `NextLinePredictor.record_step()` updates global symbolic counts.
11. `SequenceTransitionMemory.best_successor()` always chooses one maximal successor; ties follow insertion order.
12. `_unknown_prediction()` emits a catalog placeholder.
13. `FeedbackGainController` applies symbolic fixed `2.0/0.5` gain.

Production excitatory WTA (`WtaCoordinator.run()`) can return `None` when no authentic E spikes. Strict-profile production exceptions (`force_central_fire`, `wipe_loser_membranes`, `_force_pair_inhibition`) remain legacy controls and must not be reachable from the biological-compliance profile. `_graded_pair_inhibition()` is the existing causal alternative.

---

## Stages 0–7

### Stage 0 — Doctrine and profile lock

**Goal / tenants:** Isolate strict T1–T9 behavior without changing production or existing hybrid results.

**Files / symbols**

- `backend/cognative_paradigm/simulation/learning_dynamics.py`
  - `COLUMN_ARCHITECTURE_PROFILES`
  - `validate_learning_dynamics`
  - `LearningDynamics.uses_hybrid_column`
  - Add explicit biological-profile query.
- `backend/cognative_paradigm/learning/lab_profile.py`
  - Add `BiologicalLabProfileFactory.hybrid_biological_dynamics`.
- `backend/cognative_paradigm/cortical_column/column_architecture_factory.py`
  - Build the column with an immutable causal policy object.
- Add `backend/cognative_paradigm/domain/column_profile.py`
  - `ColumnCausalPolicy` or equivalent immutable policy.
- `backend/cognative_paradigm/api/brain_routes.py`, `backend/cognative_paradigm/api/service.py`
  - Extend profile literals and validation.
- Frontend: `ParameterControlModel.js`, `HybridLabControlsPanel.js`, `ColumnStateModel.js`, corresponding tests and E2E profile tests.

**Invariants**

- Fresh `LearningDynamics()` remains byte-for-byte equivalent to current defaults.
- Legacy and biological learned state cannot leak into each other.
- Selecting the biological profile atomically enables the lab gate.
- Production force flags remain unchanged under `compatibility`.

**Acceptance metrics**

- Existing production-default tests pass unchanged.
- Profile-isolation tests prove distinct construction and serialization.
- API rejects biological profile without `lab_profile_enabled=True`.

**Tests to rewrite / add**

- Extend `test_column_profile_isolation.py`, `test_production_defaults_lock.py`, `test_api.py`, `test_parameters_api.py`.
- Frontend profile/model/E2E tests for both hybrid modes.

**Dependencies:** None.

**Do not**

- Do not silently redefine existing `hybrid_cortical`.
- Do not change production defaults.
- Do not expose strict claims for the legacy profile.

**Math adopt / adapt notes:** No equation change. Profile isolation only.

---

### Stage 1 — Causal L4 and abstention plumbing

**Goal / tenants:** T1, T5, T9. Make actual sensory input and authentic relay spikes authoritative.

**Files / symbols**

- `backend/cognative_paradigm/simulation/engine.py`
  - `BrainSimulator.stimulate_pattern`: invoke strict column for every supplied `Pattern`, even when `line_id=None`.
- `backend/cognative_paradigm/cortical_column/cortical_column.py`
  - `HybridCorticalColumn.process_pattern`: require `Pattern`; make `line_id` optional metadata; remove `del pattern`; use `indices_from_pattern(pattern)`.
- `backend/cognative_paradigm/cortical_column/layer4_adapter.py`
  - `Layer4Adapter.process`: remove `fired_indices or modulated_indices`; retire `line_indices()` from strict runtime use.
- `backend/cognative_paradigm/cortical_column/interfaces.py`
  - Update L4 contract to accept pattern-derived indices and optional metadata.
- `backend/cognative_paradigm/domain/column_signal.py`
  - Replace ambiguous fields with `input_cell_indices`, `gain_gated_input_indices`, `relay_spike_indices`; add explicit abstention/causal-result representation.
- `backend/cognative_paradigm/domain/column_state.py`
  - Permit no current representation.
- Serialization methods in `HybridCorticalColumn`: version payload; read legacy fields but emit truthful strict fields.

**Invariants**

- `relay_spike_indices == {i | L4 neuron register is ONE this tick}`.
- Empty relay spikes remain empty downstream.
- `line_id` mismatch cannot alter spikes.
- Novel noncatalog patterns can enter the strict column.
- Refractory relay neurons cannot appear in the spike set.

**Acceptance metrics**

- L4 fabrication rate exactly `0`.
- Event/register/returned-spike mismatches `0`.
- Mismatched `line_id` versus `Pattern` produces the same strict L4 result as the pattern with no label.
- Zero-gain or low-drive relay silence produces explicit abstention.

**Tests to rewrite / add**

- Rewrite `test_layer4_adapter.py` around three separate sets.
- Add mismatch, novel-pattern, relay-silent, and refractory tests.
- Extend `test_hybrid_cortical_column.py` and `test_column_state.py`.

**Dependencies:** Stage 0.

**Do not**

- Do not infer spikes from positive gain.
- Do not call `LINE_INDICES` from strict sensory processing.
- Do not treat metadata as neural drive.

**Math adopt / adapt notes:** Adopt \(A_{L4}=\{i\mid y_i=1\}\); adapt \(\tilde{x}=g\odot x\) strictly as drive.

---

### Stage 2 — Causal L2/3 competition

**Goal / tenants:** T1, T4, T5. A representation exists only after an authentic L2/3 spike.

**Files / symbols**

- `backend/cognative_paradigm/cortical_column/context_assembly.py`
  - Replace `integrate()` with refractory-safe integration followed by `LifDynamics.try_spike()`; reset register each tick.
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py`
  - `_compete()` returns an `AssemblyCompetitionResult`, not an unconditional string.
  - Remove `line_id` tie preference, below-threshold identity, and loser `membrane *= 0.5`.
  - `integrate()` updates active state only from authentic spikers.
- `backend/cognative_paradigm/domain/column_signal.py`
  - Add `AssemblyCompetitionResult` with authentic spiker IDs and nullable unique representation.
- `backend/cognative_paradigm/domain/column_state.py`
  - Abstention means empty active IDs and compact code `0`.

**Ambiguity policy (interim until doctrine decides otherwise)**

- zero spikers → abstain;
- one spiker → unique representation;
- multiple spikers → preserve authentic spike evidence but classify symbolic readout as ambiguous/abstained.

**Invariants**

- No threshold crossing means no winner.
- Exact ties are never settled by labels, catalog order, assembly order, or dictionary insertion.
- Inhibition cannot create a winner.
- Refractory neurons never report spikes.
- Abstention produces compact context code `0`.

**Acceptance metrics**

- False-winner rate exactly `0`.
- Refractory violations `0`.
- Permuting labels, neurons, or catalog ordering does not alter abstention or spike-count distributions.
- Subthreshold exact ties produce abstention.

**Tests to rewrite / add**

- Rewrite `test_context_assembly_network.py`: replace “matching line wins” and catalog-biased tests; add below-threshold, tie, plural-spike, refractory, and permutation tests.
- Extend `test_column_layer_composition.py`.

**Dependencies:** Stage 1.

**Do not**

- Do not choose `max(Vm)` among silent candidates.
- Do not call `Neuron.fire()` directly.
- Do not suppress losers without explicit inhibitory events.

**Math adopt / adapt notes:** Adopt threshold/refractory equations; reject unconditional `argmax`.

---

### Stage 3 — Gate L5/L6 on authentic representation

**Goal / tenants:** T1, T7, T8, T9. Abstention must terminate all downstream causal effects.

**Files / symbols**

- `backend/cognative_paradigm/cortical_column/cortical_column.py`
  - `process_pattern`: only bind, learn, predict, or create gain after a causal unique representation.
  - `end_episode`: learn END only from an authentic prior representation plus explicit boundary event.
- `backend/cognative_paradigm/cortical_column/next_line_predictor.py`
  - Return `None`/unknown instead of a catalog placeholder; remove `_placeholder_line`.
- `backend/cognative_paradigm/cortical_column/feedback_gain_controller.py`
  - Abstention, unknown, ambiguity, and END always produce unity gain.
- `backend/cognative_paradigm/domain/column_signal.py`
  - Permit nullable prediction or define an explicit unknown prediction without a catalog line.
- `backend/cognative_paradigm/domain/column_state.py`
  - Track previous authentic representation separately from evaluation metadata.
- `backend/cognative_paradigm/domain/sequence_transition_memory.py`
  - Retain only as a legacy/shadow oracle at this stage.
- `backend/cognative_paradigm/cortical_column/episode_stream.py`
  - Keep canonical stream as fixture only, not architecture authority.

**Strict-profile interim rule:** Until Stage 5, the biological profile should expose no operational table-driven prediction. The count table may run as a read-only comparison oracle, but it must not alter state or gain.

**Invariants**

- Abstained ticks change no learned object.
- Abstention yields no prediction confidence and unity gain.
- Unknown prediction has no placeholder symbol.
- Silence reset clears transient state without inventing END.
- Explicit END is not learned without an authentic predecessor.

**Acceptance metrics**

- Learning-without-causal-provenance exactly `0`.
- Gain after abstention equals unity in every cell.
- Predictor mutation count after abstention exactly `0`.
- Equal count evidence yields unknown/plural, never insertion-order selection.

**Tests to rewrite / add**

- Rewrite unknown behavior in `test_next_line_predictor.py`.
- Rewrite fixed boost expectations in `test_feedback_gain_controller.py`.
- Add abstention chain tests to `test_hybrid_cortical_column.py`.
- Update serialization tests for nullable prediction.

**Dependencies:** Stage 2.

**Do not**

- Do not allow prediction to validate its own END boundary.
- Do not emit `LINE_IDS[0]` for unknown.
- Do not apply non-unity gain after ambiguous evidence.

**Math adopt / adapt notes:** Adopt confidence/END concepts only with abstention and causal boundary requirements.

---

### Stage 4 — Emergent binding and local sensory learning

**Goal / tenants:** T2, T3, T6, T7, T9. Remove `asm_h1`, `asm_v1`, `asm_d0`, and `asm_d1` as preassigned identities.

**Requires user doctrine answers** (see Open doctrine questions) before implementation.

**Files / symbols**

- `backend/cognative_paradigm/cortical_column/context_assembly.py`
  - Replace `line_id`, `template_indices`, and scalar `sensory_weight`.
  - Use neutral representation IDs and neuron-owned binding state; store incoming sensory synapses on the receiver.
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py`
  - Initialize symmetric, unbound candidates; route authentic L4 spikes; do not consult catalog templates.
- Add `backend/cognative_paradigm/domain/local_synapse.py`
  - `LocalSensorySynapse`, bounded weight update, pre/post timestamps, immutable `PlasticityProvenance`.
- Reuse or adapt: `domain/neuron.py`, `domain/neuron_memory.py`, `domain/pattern.py`.
- `backend/cognative_paradigm/domain/context_transition_map.py`
  - Remove from strict mutation authority; retain legacy deserialization/oracle support.
- `backend/cognative_paradigm/cortical_column/cortical_column.py`
  - Serialize learned binding by neutral representation ID and actual pattern.

**Binding rule**

- Bind only after repeated authentic L4→L2/3 pre/post evidence.
- Bind the actual `Pattern`, not `line_id`.
- Attach a symbol label only as metadata after pattern ownership exists.
- Require exactly one eligible authentic representation for first binding; plural activity remains ambiguous and does not create duplicate ownership.

**Local sensory update**

\[
\Delta w_{ij}=\eta\, y^{L4}_i(t)\, y^{L2/3}_j(t)
\]

with receiver-owned weight, explicit timing window, bounds, and provenance.

**Invariants**

- All representation neurons begin unbound.
- No neuron owns two patterns.
- No accepted pattern has duplicate owners.
- No binding without authentic pre/post spikes.
- Label and pattern permutations do not preselect an owner.
- Every delta identifies receiver, source, pre-event, post-event, and time.

**Acceptance metrics**

- Bindings without causal spikes `0`.
- Duplicate owners `0`.
- Patterns per neuron ≤ `1`.
- Label/catalog permutation invariance passes paired seeds.
- Novel patterns either abstain or recruit according to an explicit doctrine policy.

**Tests to rewrite / add**

- Rewrite: `test_context_assembly_network.py`, `test_hybrid_cortical_column.py`, `test_column_profile_isolation.py`.
- Add: `test_column_emergent_binding.py`, `test_column_local_synapse.py`, permutation and mismatch suites.

**Dependencies:** Stages 1–3; **doctrine answers for questions 1–2, 4–7, 10**.

**Do not**

- Do not encode catalog shape in initial weights.
- Do not name neutral neurons by symbols.
- Do not let a global registry decide a synaptic delta.
- Do not bind on metadata alone.

**Math adopt / adapt notes:** Adopt the sensory Hebbian equation with bounds and provenance; reject catalog assembly indexing.

---

### Stage 5 — Local recurrent prediction

**Goal / tenants:** T2, T7, T8, T9. Replace shared transition tables with receiving-neuron recurrent synapses.

**Requires user doctrine answers** before implementation.

**Files / symbols**

- Extend `backend/cognative_paradigm/domain/local_synapse.py`
  - `LocalRecurrentSynapse` owned by the postsynaptic representation.
- Add `backend/cognative_paradigm/cortical_column/recurrent_prediction_network.py`
  - Routes authentic representation spikes; aggregates only read-only prediction diagnostics.
- Refactor `backend/cognative_paradigm/cortical_column/next_line_predictor.py`
  - Predict from authentic recurrent spikes or locally thresholded predictive activity.
- `backend/cognative_paradigm/cortical_column/context_assembly.py`
  - Own incoming recurrent synapses.
- `backend/cognative_paradigm/cortical_column/cortical_column.py`
  - Route prior/current spike events and explicit boundary events.
- `context_transition_map.py`, `sequence_transition_memory.py`
  - Legacy oracle only; never strict mutation authority.

**Learning rule**

A recurrent synapse changes only when its presynaptic representation and receiving postsynaptic representation satisfy the selected local timing rule. Compare: (1) bounded same-window Hebbian; (2) pair STDP; (3) triplet STDP; (4) later eligibility-based rule. The Math_breakdown transition equation is insufficient because it lacks the presynaptic event.

**Prediction behavior**

- No causal predecessor spike → no prediction.
- No predictive receiver spike → unknown.
- Equal/plural predictive spikes → plural/unknown, not arbitrary top-1.
- Confidence derives from causal local population evidence, latency, or rate—not a global frequency table.

**Acceptance metrics**

- Global-state-based learned deltas exactly `0`.
- No predecessor spike → no prediction.
- Equal evidence never resolves by insertion/catalog order.
- Held-out branching prediction reports calibrated coverage and accuracy.
- END accuracy uses an explicit causal boundary representation/event.

**Tests to rewrite / add**

- Rewrite `test_next_line_predictor.py`; retain legacy oracle tests under explicit legacy naming.
- Add `test_local_recurrent_prediction.py`; branching, reversed, shuffled, repeated-symbol, delayed-context, and permutation tests.

**Dependencies:** Stage 4; **doctrine answers for questions 4, 8–11**.

**Do not**

- Do not promote \(C_{a\to b}\) into strict runtime state.
- Do not normalize through a global denominator to decide firing.
- Do not force a top-1 answer when local evidence is tied or silent.

**Math adopt / adapt notes:** Reject global count tables and unconditional \(\arg\max P\); require causal pre/post for transition learning.

---

### Stage 6 — Graded explicit E/I

**Goal / tenants:** T1, T4, T5, T9. Replace direct scalar suppression and force/wipe behavior in the biological profile.

**Files / symbols**

- Add `backend/cognative_paradigm/cortical_column/context_inhibitory_network.py`
  - Explicit inhibitory neurons and local weighted connections.
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py`
  - Route E spikes into inhibitory circuitry and inhibitory spikes back through local couplings.
- Reuse: `domain/inhibitory_coupling.py`, `domain/spike_drive.py`, `domain/lif_dynamics.py`.
- `backend/cognative_paradigm/learning/lab_profile.py`
  - Biological hybrid sets `pretrained_inhibitor_exclusivity_enabled=False`, `descending_mode="graded"`.
- `backend/cognative_paradigm/simulation/learning_dynamics.py`
  - Validate strict profile cannot enable force exclusivity.
- Legacy production files remain operational only outside strict profile:
  - `simulation/pretrained_inhibitor_exclusivity.py`
  - `simulation/descending_inhibition.py`
  - `simulation/wta_coordinator.py`

**Invariants**

- Every suppression delta traces to an inhibitory spike/conductance.
- Inhibition can suppress all candidates.
- Inhibition never elevates or assigns identity.
- No fabricated inhibitory firing during refractory.
- No direct membrane wipe in strict profile.

**Acceptance metrics**

- Force-path invocations under biological profile exactly `0`.
- Refractory I-event mismatches `0`.
- E/I spike and conductance ratios remain bounded.
- Runaway excitation and permanent silence stay below declared limits.
- False-winner and L4-fabrication rates remain `0`.

**Tests to rewrite / add**

- Add `test_column_graded_inhibition.py`.
- Extend `test_pretrained_inhibitor_exclusivity.py` with strict-profile non-reachability.
- Extend `test_graded_descending_ecology.py`, `test_production_defaults_lock.py`, and profile isolation tests.

**Dependencies:** Stages 2–5.

**Do not**

- Do not delete force modes; preserve them as labeled controls.
- Do not call refractory inhibition “fired.”
- Do not zero membranes as a substitute for weighted inhibitory input.

**Math adopt / adapt notes:** Replace “WTA encodes inhibition” with explicit conductance/current equations.

---

### Stage 7 — Optional multiplicative laboratory

**Goal / tenants:** Evaluate local nonlinear interactions only after causal safety passes. Not required for basic sequence learning.

**Allowed experiments**

1. Bounded local gain: \(I_{\mathrm{eff}}=g_{\mathrm{local}} I_{\mathrm{sensory}}\)
2. Conductance E/I: \(I_{\mathrm{syn}}=g(t)(E_{\mathrm{rev}}-V)\)
3. NMDA-like branch coincidence: \(I_N=g_N s(t) B(V)(E_N-V)\)
4. Synapse-local eligibility × connected modulator: \(\dot{w}_{ij}=\eta M_j e_{ij}\)

**Files**

- Add optional OOP mechanisms under `cortical_column/` or `learning/`, one profile per experiment.
- Extend `learning/lab_profile.py` and `learning_dynamics.py`.
- Extend `diagnostics/column_metric_pack.py` and benchmark scripts.

**Promotion gates**

All prior causal metrics must remain perfect, and the experiment must improve held-out noisy/ambiguous performance over paired-seed additive controls without reducing abstention honesty, stability, retention, or permutation invariance.

**Dependencies:** Stages 1–6 fully passing.

**Do not**

- Do not implement exact global sigma-pi as a biological claim.
- Do not multiply labels, tables, or simulator-global factors.
- Do not use gain to guarantee threshold crossing or zero all alternatives.

**Math adopt / adapt notes:** Optional lab only; reject Math_breakdown’s product-of-symbolic-drive WTA as biological architecture.

---

## Migration / profile strategy

1. Keep **`compatibility`** unchanged and **default** across backend, API, and frontend.
2. Preserve current behavior under **`hybrid_cortical`** as the **legacy hybrid** profile (optionally expose `hybrid_cortical_legacy` as a clearer alias before later deprecation).
3. Add **`hybrid_cortical_biological`** as explicit lab-only strict profile.
4. Add profile policy and tests without changing behavior first (Stage 0).
5. Preserve existing `hybrid_cortical` checkpoints as legacy schema version 1.
6. Introduce strict state schema version 2 with explicit spike, abstention, provenance, and neutral representation fields.
7. Permit v1 read/restore only into legacy mode or a diagnostic migration adapter; never reinterpret fabricated v1 activity as authentic strict spikes.
8. Promote biological hybrid only after all exact-zero safety gates pass across paired seeds.
9. Keep legacy force profiles selectable and clearly labeled nonbiological controls.

## Benchmark / metric gates

Expand `diagnostics/column_metric_pack.py` and `test_column_metric_pack.py` beyond canonical-chain accuracy.

| Metric | Required gate |
|---|---|
| False-winner rate | exactly `0` |
| L4 fabrication rate | exactly `0` |
| Learning without causal provenance | exactly `0` |
| Refractory violations | `0` |
| Register/event/return mismatches | `0` |
| Binding duplicates / uncaused bindings | `0` |
| Global-state-based learned deltas | `0` |

Additional diagnostic (not minimization-by-default) metrics: abstention rate stratified by clean/noisy/ambiguous/novel/silent input; prediction coverage-versus-accuracy, END accuracy, branching calibration, Brier/NLL; E/I balance, sparsity, total suppression, runaway excitation, permanent silence; paired-seed label/catalog/neuron permutation invariance; retention and adaptation after sequence changes.

Canonical `H1→V1→D0→D1` accuracy is **insufficient** promotion evidence. Use paired-seed distributions and confidence intervals.

### Test migration map

- `test_layer4_adapter.py`: rewrite around input/gain/spike separation.
- `test_context_assembly_network.py`: remove catalog winner assumptions; add abstention and authentic spikers.
- `test_next_line_predictor.py`: remove placeholder and insertion-order top-1 behavior.
- `test_feedback_gain_controller.py`: fixed symbolic boosts become legacy-only.
- `test_hybrid_cortical_column.py`: split legacy behavior from strict causal behavior.
- `test_column_layer_composition.py`: assert downstream gating after abstention.
- `test_column_state.py`: nullable representation/prediction and serialization migration.
- `test_column_metric_pack.py`: add normative safety metrics.
- `test_column_profile_isolation.py`: prove compatibility, legacy hybrid, and biological hybrid isolation.
- `test_production_defaults_lock.py`: production defaults must remain unchanged.
- `test_api.py`, `test_parameters_api.py`: add biological profile validation.
- Frontend profile/model/E2E tests: recognize both hybrid modes and display abstention truthfully.

## Open doctrine questions

Thulle must obtain user answers **before Stages 4–5 implementation**:

1. Does “one pattern per neuron” permit distributed assemblies with one local binding owner?
2. Should multiple authentic representation spikes mean ambiguity, plural representation, or mandatory abstention?
3. May refractory neurons integrate subthreshold input, or must membrane be clamped?
4. What timing window defines “fire together”?
5. May a read-only network index detect ownership collisions without violating T9?
6. Should novel patterns abstain, recruit a new owner, or revise an existing owner?
7. What evidence permits unbinding/reconsolidation?
8. Must modulatory factors arrive through explicit modeled connections?
9. Is silence itself a causal END signal, or only a reset condition?
10. Are exact ties always plural/abstained, or may tracked biological noise resolve them?
11. What confidence representation is authorized: no spike, plural spikes, latency, rate, or calibrated population evidence?
12. Can force modes remain indefinitely as explicitly nonbiological controls?

(Questions 3 and 12 also inform Stage 2/6 policy but are listed here as doctrine locks for the binding/prediction stages.)

## Evidence index

### Authority and prior audit

- `Documents/tenants.txt`
- `Documents/architecture/tenant_compliance_no_forced_win_research.md`
- `Documents/biology/multiplicative_computation_research.md`
- `Documents/Math_breakdown.txt`
- `Documents/architecture/hybrid_cortical_column_tenant_outline.md`

### Hybrid input and orchestration

- `backend/cognative_paradigm/cortical_column/cortical_column.py:HybridCorticalColumn.process_pattern`
- `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter.process`
- `backend/cognative_paradigm/cortical_column/layer4_adapter.py:Layer4Adapter.line_indices`
- `backend/cognative_paradigm/lines.py:LINE_IDS`
- `backend/cognative_paradigm/lines.py:LINE_INDICES`
- `backend/cognative_paradigm/simulation/engine.py:BrainSimulator.stimulate_pattern`

### Hybrid representation and transition

- `backend/cognative_paradigm/cortical_column/context_assembly.py:ContextAssembly`
- `backend/cognative_paradigm/cortical_column/context_assembly.py:assembly_id_for_line`
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork.__post_init__`
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork._compete`
- `backend/cognative_paradigm/cortical_column/context_assembly_network.py:ContextAssemblyNetwork.integrate`
- `backend/cognative_paradigm/domain/context_transition_map.py:ContextTransitionMap.observe`
- `backend/cognative_paradigm/domain/column_state.py:ColumnState`
- `backend/cognative_paradigm/domain/column_signal.py`

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

### Profile and diagnostics

- `backend/cognative_paradigm/simulation/learning_dynamics.py:COLUMN_ARCHITECTURE_PROFILES`
- `backend/cognative_paradigm/learning/lab_profile.py`
- `backend/cognative_paradigm/cortical_column/column_architecture_factory.py`
- `backend/cognative_paradigm/diagnostics/column_metric_pack.py`

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

## Authorization boundary

Stages 0–7 are implemented under Thulle authorization (2026-07-20). Force modes stay reachable only outside `hybrid_cortical_biological`. Stage 7 ships multiplicative lab stubs only (default OFF); NMDA / eligibility×modulator / sigma-pi remain unshipped.

## Stage 8+ — Emergent remediation (sequential paths)

**Status:** complete (2026-07-20). Plan authority: Cursor plan `Emergent Bio Remediation`.

| Path | Goal | Status |
|------|------|--------|
| 0 | Regression lock for Stages 0–3 causal gates (`test_biological_causal_regression_lock.py`) | done |
| 1 | Emergent multi-unbound recruitment + N=2 bind evidence | done |
| 2 | Local END evidence; remove catalog-terminal D1 gate | done |
| 3 | Retire biological `prior_active_bias` | done |
| 4 | L5 predictive spikes via `try_spike` | done |
| 5 | `column_only_stimulate` lab flag (claim boundary) | done |
| Final | Re-audit T1–T9 under bio profile | done |

**Locks:** Legacy `compatibility` / `hybrid_cortical` remain bit-compatible. All Stage 8+ behavior stays behind `ColumnCausalPolicy.is_biological`.

**Audit notes (bio profile):**
- T1–T5, T7: PASS (regression lock + causal safety pack exact zeros).
- T3/T6: PASS under multi-unbound race + N=2 bind; no `min(assembly_id)` recruit.
- T8: PASS — L5 authority is authentic predictive `try_spike`; weight map diagnostic.
- T9: PASS — END is receiver-owned `boundary_end_evidence`; no `LINE_IDS[-1]` gate.
- Dual-path claim: nucleus still runs by default; `column_only_stimulate` opts out for pure column optics.

## Stage 9 — Dendritic coincidence + forced-learning retirement

**Goal / tenants:** Sole binders and learning emerge from basal×apical coincidence + graded E/I (T3/T9), not consolidator veto, wipe, or BoundMatch soft gates.

**Authority:** [`forced_learning_inventory.md`](forced_learning_inventory.md); plan `Biological Learning + Forced-Win Removal`.

| Path | Goal | Status |
|------|------|--------|
| 0 | Living forced-learning inventory + dispositions | done |
| 1 | Column `DendriticCoincidenceGate` + `dendritic_coincidence_enabled` (bio ON; eligibility-only) | done |
| 2 | Nucleus `nucleus_dendritic_coincidence_enabled` (lab; soft-gate bypass) | done |
| 3 | Soft retirement: owned→owner∪unbound under coincidence; BoundMatch bypass opt-in; orphaned claim APIs raise | done |
| 4 | Security + Tyborc green gate | done |

**Stage 9 ship note:** Column coincidence gates bind eligibility. Stage 10 retires remaining soft drive routing under bio+coincidence (see below). `nucleus_dendritic_coincidence_enabled` stays opt-in.

**Tyborc gate (Phase 3):** backend green; frontend unit 109 passed.

**Do not:** reintroduce `PatternOwnership.can_bind/claim`; change production force defaults in the same change set; claim exact sigma-pi as biology.

## Stage 10 — Soft drive-routing retirement (bio column)

**Goal / tenants:** Sensory shapes are the only external guidance; sole winners and binders emerge from population race + graded E/I + coincidence eligibility + local mismatch attenuation (T3/T9). No registry owner/unbound filters under bio+coincidence.

**Authority:** [`forced_learning_inventory.md`](forced_learning_inventory.md) §G.

| Path | Goal | Status |
|------|------|--------|
| 0 | Inventory soft gates still steering bio winners/binds | done |
| 1 | Full-pop drive when bio + `dendritic_coincidence_enabled` | done |
| 2 | Stronger bio graded I + always-run E→I after race | done |
| 3 | Local bound-mismatch basal attenuation (×0.12) | done |
| 4 | L5 END: episodic catalog training (no continuous wrap STDP) | done |
| 5 | Security + Tyborc green gate | done |

**Stage 10 ship note:** Full population under coincidence ON; somatic amp still OFF. Mismatch attenuation replaces the old unbound-only soft filter that protected specialization. Continuous catalog without `end_episode` still learns wraparound D1→H1; END wins on D1 only after episodic boundary deposits. Validator forbids `dendritic_coincidence_enabled=False` under bio (Security Medium remediated).

**Tyborc / Security:** PASS (causal + L5/dendrite/mastery clusters green; coincidence disable locked).

**Do not:** reintroduce owner-only / unbound-only soft filters under bio+coincidence; auto-enable nucleus dendritic coincidence; bump END deposit to hard-beat wrap.

## Stage 11 — Honest apical + eligibility selectivity (A+D staged)

**Goal / tenants:** Coincidence eligibility is selective — basal-only / ambient-only cannot bind; apical is self-prior + unique prediction / L6 excess (T1/T3/T9). No somatic amp (Option C deferred).

**Authority:** [`forced_learning_inventory.md`](forced_learning_inventory.md) §H.

| Path | Goal | Status |
|------|------|--------|
| A1 | Retire ambient; self-prior apical; threshold 0.05 | done |
| A2 | Wire prediction / pending-gain into apical (bio L6 unity → prediction path) | done |
| D | Eligibility selectivity; bind gate may block unique winners | done |
| B/C | Plasticity scale / somatic amp | deferred / forbidden |

**Stage 11 ship note:** `ApicalContextDrivePolicy` combination apical; ambient retired; somatic amp still OFF; nucleus coincidence still opt-in.

## Stage 12 — Hybrid C emergent ownership (RF / spike evidence)

**Goal / tenants:** Primary column ownership from local RF concentration + unique-spike consistency (`EmergentOwnershipEvidence`). Optional `bind_pattern` is a revisable readout latch (UI/checkpoint/NeuronMemory sync) after evidence + coincidence eligibility — never invents winners, never soft-filters recruitment under bio+coincidence. Mastery advances on emergent evidence or latch or nucleus bind (prefer evidence). Nucleus bind remains separate. Do not copy AbhiCIPP argmax WTA.

**Authority:** [`forced_learning_inventory.md`](forced_learning_inventory.md) §I.

| Path | Goal | Status |
|------|------|--------|
| C1 | Receiver-owned `EmergentOwnershipEvidence` (observe / maturity / revise) | done |
| C2 | Continuous RF–sensory PE (~0.12); RF top-k sensory mask | done |
| C3 | Demote bind to revisable latch; mastery prefers evidence | done |
| C4 | Docs + emergent / L5 / dendritic / causal / production locks | done |

**Stage 12 ship note:** Latch revisable on sustained mismatch; plural→abstain and full-pop bio+coincidence preserved; somatic amp OFF; nucleus dendritic still opt-in.

## Stage 13 — Option A plastic column I→E gates

**Goal / tenants:** Borrow AbhiCIPP *gate turnover* onto bio `ContextInhibitoryNetwork` without argmax WTA. Per-assembly plastic I→E gates update on authentic I discharge (V_pre/θ); ceiling subthreshold vs E θ so saturated gates cannot lock identity. `_compete_authentic` still yields unique|plural|abstain from authentic spike count. Legacy hybrid keeps fixed scalars.

**Authority:** [`forced_learning_inventory.md`](forced_learning_inventory.md) §J; Dominus competition deep-dive Option A.

| Path | Goal | Status |
|------|------|--------|
| A1 | `ColumnIeGatePlasticity` + `InhibitoryTurnoverPlasticity` reuse | done |
| A2 | Bio factory enables plastic gates; legacy fixed | done |
| A3 | Race collateral + Stage 6 discharge read/update gates | done |
| A4 | Unit + regression locks (no invented unique on 2 spikes) | done |

**Stage 13 ship note:** Option B (loser FF depression) and Option C (shared L2I) deferred. AbhiCIPP `_resolve_l2_competition` argmax remains forbidden.
