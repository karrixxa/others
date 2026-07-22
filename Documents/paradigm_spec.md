# Cognative Paradigm — Formal Specification

**Version:** 1.0.0  
**Status:** Implemented (biological flat workspace)  
**Authority:** `Documents/tenants.txt` — all design decisions MUST comply with the tenants listed there.

This document defines the computational paradigm for Cognative Paradigm. It is an original framework. External neuroscience and machine-learning ideas may inform design, but this spec is the source of truth for implementation — not backpropagation, not binary activation vectors, and not third-party SNN frameworks treated as ground truth.

---

## 1. Purpose

Cognative Paradigm models cognition as **event-based processing** over a graph of neurons. Information exists only when a neuron **fires** (registers a causal event). All other states are **Z** (unregistered). Learning is **local**, **continuous**, and **predictive**.

The first implementation milestone: **one neuron fires and learns one shape**.

---

## 2. Glossary

| Term | Symbol | Definition |
|------|--------|------------|
| **Event** | `1` | A registered causal spike at a discrete timestep. Propagates across edges. |
| **Unregistered** | `Z` | Default state. Not transmitted, not logged as information, not used in loss. |
| **Edge** | — | Directed connection between neurons carrying event eligibility only when presynaptic neuron fires `1`. |
| **Symbol** | `σ` | A named identity bound 1:1 to a learned pattern on a neuron. |
| **Pattern** | `P` | A sparse set of active input edges that consistently precede a postsynaptic event. |
| **Nucleus** | — | Sub-structure inside a neuron: 1 inhibitory center + 8 excitatory ring units gating pattern registration. |
| **Timestep** | `t` | Discrete clock index. All events occur at integer `t`. |
| **Refractory** | `R` | Post-spike interval during which a neuron cannot fire again. |

---

## 3. Tenants → Formal Rules

### Tenant 1 — Firing is causal; not firing is not causal (1 vs Z)

**Rule 1.1** — The only transmissible unit of information is event `1`.

**Rule 1.2** — State `Z` is the absence of registration. `Z` MUST NOT:
- be written to edge buffers,
- participate in plasticity updates,
- be encoded as numeric zero in event logs,
- contribute to output or decision registers.

**Rule 1.3** — Internal subthreshold membrane potential MAY exist as a hidden variable but MUST NOT be treated as a broadcast signal.

**Formal state per neuron per timestep:**

```
register_state ∈ { Z, 1 }
```

If `register_state == Z` at timestep `t`, the neuron produced no causal output at `t`.

---

### Tenant 2 — Conductance plasticity (ion-channel learning)

**Rule 2.1** — Synaptic weights are **ion-channel conductances**. Plasticity adjusts conductance toward charge/conductance equilibrium.

**Rule 2.2** — Excitatory update (on WTA winner spike, plasticity eligible):

```
Δw^E_i = η_E · (θ − A_inst) · (1 − (w^E_i / w^E_max)²) · in_i
A_inst = Σ w^E_j · in_j     (active presynaptic 1 events this tick)
```

**Rule 2.3** — Inhibitory update (on central I `1` after WTA arbitration):

```
Δw^I = η_I · (Q^I − w^I) · (1 − (w^I / w^I_max)²) · in
```

Per-competitor inhibitory channels from central I to ring E units.

**Rule 2.4** — Production remains on the phenomenological charge-gated
conductance rules above. Biological lab presets use recorded spike times and
the full Pfister–Gerstner \(r_1,r_2,o_1,o_2\) triplet rule as the primary
excitatory law. Pair STDP and conductance plasticity remain explicit ablations;
BCM is not the primary law.

**Rule 2.5** — Layer 1 homeostasis adjusts local I→E coupling via synaptic scaling (EMA firing rate). Input edge conductances are not scaled.

---

### Tenant 3 — Local learning; one pattern per neuron

**Rule 3.1** — Each neuron owns its synaptic weights. No global gradient, no backpropagation, no central optimizer.

**Rule 3.2** — Each neuron MAY bind **at most one** pattern `P` at a time.

**Rule 3.3** — Pattern binding occurs when an authentic spiker satisfies
**eligibility consolidation**:

1. Eligibility trace \(E \geq E_{\mathrm{th}}\) after repeated co-activation of the same edge set.
2. Optional weight evidence: normalized mean conductance on active edges \(\geq\) consolidation threshold.
3. Any pre-existing owner of the same edge set is recorded as an
   `OWNERSHIP_COLLISION` audit event. It does **not** block consolidation.

One-pattern-per-neuron remains enforced by `NeuronMemory`; cross-neuron
exclusivity is an observed ecology metric, not a hidden consolidator gate.

The legacy `N_bind` consecutive counter is **not** used in the nucleus path.

**Unbind protocol:** `POST /api/unbind` releases pattern ownership, clears neuron memory and prediction, and removes the symbol mapping so the pattern may compete again.

**Rule 3.4** — Once bound, pattern `P` is the neuron's sole learned representation until unbound.

**Data structure:**

```
NeuronMemory {
  bound_pattern: Pattern | null
  bind_confidence: float   // count-normalized, local only
}
```

---

### Tenant 4 — Excitatory and inhibitory weights and connections

**Rule 4.1** — Every connection has polarity:

```
polarity ∈ { EXCITATORY, INHIBITORY }
```

**Rule 4.2** — Excitatory input increases membrane potential toward threshold. Inhibitory input decreases it.

**Rule 4.3** — Weights are stored separately per polarity. A neuron MAY receive both E and I input on different edges.

**Rule 4.4** — Net drive at timestep `t`:

```
drive(t) = Σ(w_e · 1_pre_e) - Σ(w_i · 1_pre_i)
```

where `1_pre` is `1` if the presynaptic neuron fired at `t`, else contributes nothing (not zero — absent term).

**Rule 4.5** — Layer 1 E/I balance via **synaptic scaling** on local I coupling (`SynapticScalingHomeostasis`). Layer 2 uses conductance plasticity on central I per-competitor channels.

**Rule 4.6** — Only the WTA winner ring E spikes. That spike charges central I (collateral); when central I fires it enqueues **next-tick** ring feedback on losers. The winner spike also drives delayed shape-scoped L1 I feedback via descending inhibition.

---

### Tenant 5 — Refractory period

**Rule 5.1** — After a neuron registers `1` at timestep `t`, it enters refractory until `t + R`.

**Rule 5.2** — During refractory, even if `drive(t) ≥ threshold`, the neuron MUST output `Z`.

**Rule 5.3** — Refractory applies to the **register** (output event), not merely to hidden potential integration (implementation may freeze or leak potential — see v0.2).

Default:

```
R = 2 timesteps (minimum inter-event interval)
```

---

### Tenant 6 — 1:1 symbol to representation

**Rule 6.1** — When pattern `P` is bound on neuron `N`, exactly one symbol `σ` is assigned.

**Rule 6.2** — `σ` MUST NOT map to more than one pattern on the same neuron.

**Rule 6.3** — Recognition: if input at `t` matches bound pattern `P` within tolerance `ε` and neuron fires `1`, output register emits symbol `σ`.

**Rule 6.4** — Symbols are opaque identifiers (string or UUID). They carry no embedded feature vector in v0.1.

```
SymbolRegistry {
  σ_id   → { neuron_id, pattern_id }
}
```

Bijection enforced: one symbol ↔ one (neuron, pattern) pair.

---

### Tenant 7 — Continuous learning

**Rule 7.1** — No training phase / inference phase split. Plasticity is eligible when WTA winner conditions are met (probe API uses `inference_only`).

**Rule 7.2** — Learning gate (production): when ``emergent_autonomy_enabled`` is False, plasticity is suppressed on bound∧match rematch and relay drive is attenuated (`bound_match_recall_drive_gain`, default 0.7). **Labeled soft/graded control (Stage 14):** ``emergent_autonomy_enabled=True`` — rematch freeze/attenuation are off; authentic spikes may update locally; bind uses consolidator evidence (unique-spike credit + first-commit-wins per pattern).

**Rule 7.3** — New experiences MAY bind new neurons; existing bound neurons MUST NOT silently accumulate multiple patterns.

---

### Tenant 8 — Prediction

**Rule 8.1** — Each neuron maintains a local prediction of the next expected input pattern:

```
NeuronPrediction {
  expected_edges: Set<EdgeId>   // sparse expected active edges
}
```

**Rule 8.2** — Before registering output `1`, neuron compares incoming edge events to `expected_edges`.

**Rule 8.3** — Prediction error event `E_err` occurs when:

```
active_edges ≠ expected_edges  (symmetric difference non-empty)
```

**Rule 8.3a** — On match: minimal or no plasticity; emit recognition symbol if bound.

**Rule 8.3b** — On mismatch: conductance-based prediction-error LTD (PE-LTD) on active sensory edges; error forwarded to output column. Lab profile may enable `plasticity_mode` `stdp` or `triplet` instead of production conductance rules.

**Rule 8.4** — Prediction is updated only from locally observed spike timing, not from global labels.

---

## 4. Core Data Structures

### 4.1 Edge

```
Edge {
  id:            EdgeId
  source_id:     NeuronId
  target_id:     NeuronId
  polarity:      EXCITATORY | INHIBITORY
  weight:        float ≥ 0
  last_event_t:  int | null   // last time source fired 1
}
```

### 4.2 Neuron

```
Neuron {
  id:              NeuronId
  polarity:        EXCITATORY | INHIBITORY   // outer neuron type
  membrane:        float                      // hidden, subthreshold
  threshold:       float
  refractory_until: int | null
  register:        Z | 1                      // output this tick
  memory:          NeuronMemory
  prediction:      NeuronPrediction
  nucleus:         Nucleus | null
  incoming:        EdgeId[]
  outgoing:        EdgeId[]
}
```

### 4.3 Nucleus

```
Nucleus {
  center:          InhibitoryUnit // 1 × I at center
  ring:            ExcitatoryUnit[8]  // 8 × E in ring
  competition_phase: learning | equilibrium
}
```

**WTA rule (v1):** Exactly one ring E registers `1` per tick — the WTA winner. Central I receives collateral from the winner spike; when it fires, it enqueues **next-tick** ring feedback on losers (`RingFeedbackInhibition`). Binding follows eligibility consolidation on the winner, not a separate bind gate.

The implemented nucleus uses one shared center I plus eight ring E competitors (`nucleus_e_0`…`nucleus_e_7`).

**Event-driven propagation (v0.8.1):** All synaptic drive follows Tenant 4.4 — only presynaptic `1` events contribute. Subthreshold membrane `u` is never broadcast. Implementation uses `SpikeDrive` (`domain/spike_drive.py`) to integrate weighted excitatory or inhibitory drive.

**Layer 1 relay triad:** Input grid `1` drives shape E only. Nucleus / L2 ring E spikes charge shape-scoped **L1 E′** (`l2_to_l1_i_gain`, default **0.26**; central I excluded). Charge meets `l1_secondary_excitatory_threshold` (**0.26**) in one L2E delivery under production force; when E′ spikes it force-fires paired \(I_g\), which suppresses shape \(E_g\). Lateral relay `1` events from one grid cell apply inhibitory drive to neighboring E relays.

**Nucleus WTA:** Ring E integrate L1 relay `1` events via LIF (+ optional membrane noise). Candidates above threshold enter WTA; one winner spikes. Winner collateral charges central I; central fire enqueues delayed loser suppression and L1 descending charge on the active shape.

### 4.4 Timestep Event Log

Only `1` events are logged:

```
EventLogEntry {
  t:         int
  neuron_id: NeuronId
  type:      SPIKE | PATTERN_BOUND | PREDICTION_ERROR | SYMBOL_RECOGNIZED
  symbol:    σ_id | null
}
```

No entries for `Z`.

---

## 5. Simulation Loop (Per Timestep)

```
for each timestep t:
  1. Register input edge events (catalog pattern or probe)
  2. Apply pending descending + ring-feedback charge from t−1
  3. Layer 1 relay, lateral inhibition, synaptic scaling
  4. Nucleus WTA on relay set; single winner spike
  5. Conductance plasticity (+ lab `plasticity_mode` `stdp`/`triplet`) + eligibility trace on winner
  6. Consolidate → PATTERN_BOUND when trace + weight evidence pass
  7. Recognition symbol if bound winner matches prediction
  8. Enqueue descending + ring feedback for t+1
  9. Log SPIKE / PATTERN_BOUND / PREDICTION_ERROR / SYMBOL_RECOGNIZED events
```

---

## 6. Input Grid (Frontend Column 1)

The 3×3 grid encodes **line patterns** (not 9 independent cells). The **live catalog** uses **four center-cell shapes** that pass the retinal-ganglion gate (cell `(1,1)` must be active):

| ID | Description |
|----|-------------|
| `H1` | Center horizontal — cells 3, 4, 5 |
| `V1` | Center vertical — cells 1, 4, 7 |
| `D0` | Main diagonal (↘) — cells 0, 4, 8 |
| `D1` | Anti-diagonal (↙) — cells 2, 4, 6 |

See `Documents/grid_and_layers_research.md` for the full grid map and historical eight-line reference.

Grid coordinates map to edge IDs:

```
Grid[row, col] → EdgeId("input_r{row}_c{col}")
```

**Auto-Stim** continuously feeds one locked catalog line: three edges register `1`, all others remain `Z`. Equilibrium is **4/4** learned shapes.

**Pipeline:** Auto-Stim → Layer 1 E/I pairs (relay) → Layer 2 WTA learning (first neuron to bind wins).

---

## 6.1 Layer Architecture (v0.2 target)

| Layer | Role | Learning |
|-------|------|----------|
| Layer 1 | 3×3 E/I pairs relay active line to Layer 2 | No symbol binding |
| Layer 2 | Competitor pool + central inhibitory WTA | One pattern per neuron; first bind wins |
| Central I | Global feedback inhibition across L2 | Suppresses losers |

Neurons use **Leaky Integrate-and-Fire (LIF)** dynamics for membrane potential (hidden); only threshold crossings register `1`. See `Documents/grid_and_layers_research.md` §6.

---

## 7. Layer Topology (Current Frontend)

| Layer | Structure | Spec status |
|-------|-----------|-------------|
| Layer 1 | 3×3 grid of E/I neuron pairs | Defined |
| Layer 2 | 4 E ring + 1 central I (WTA) | Implemented |
| Nucleus | 4 E ring + central I, transparent shell | Implemented |

Layer 1 pairs are spatially distributed. Each outer neuron MAY contain a nucleus sub-structure per future binding.

---

## 8. Milestone v0.1 — One Neuron, One Shape

### Scope

1. One excitatory neuron in Layer 1.
2. One shape defined as sparse 3×3 edge pattern.
3. Stimulus presented for `N_stim` timesteps.
4. Neuron binds pattern `P` via conductance plasticity.
5. Symbol `σ` assigned 1:1.
6. Re-present shape → neuron fires `1`, output column shows `σ`.
7. Present different shape → prediction error, no false symbol.

### Acceptance criteria

- [ ] Event log contains only `1` entries, never `Z`.
- [ ] No weight update when presynaptic input is `Z`.
- [ ] Neuron cannot fire twice within `R` timesteps.
- [ ] Second pattern on same neuron rejected or ignored.
- [ ] Output column displays symbol on recognition only.

### Out of scope for v0.1

- Layer 2
- Nucleus gating logic
- Inhibitory plasticity / homeostasis
- Python backend (specified here; implemented next)
- Multi-neuron competition

---

## 9. Non-Goals (Explicit Rejections)

The following MUST NOT be used as the core paradigm:

| Rejected | Reason |
|----------|--------|
| Backpropagation | Violates Tenant 3 (local learning) |
| Binary 0/1 activation vectors | Violates Tenant 1 (Z is not 0) |
| Softmax / cross-entropy on dense logits | Not event-based |
| Batch train/test split | Violates Tenant 7 |
| Global loss function over all weights | Violates Tenant 3 |
| Rate coding without event structure | Misses causal timing (Tenant 2) |

Third-party SNN libraries MAY be referenced for engineering convenience but MUST NOT override this spec.

---

## 10. Backend / Frontend Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Frontend** | Visualize neurons, nucleus, grid stimulus, output symbols, event log |
| **Backend (Python)** | Timestep simulation, conductance plasticity, eligibility consolidation, symbol registry, prediction |
| **API** | `POST /api/stimulate`, `GET /api/state`, `POST /api/probe`, `PATCH /api/parameters` |

---

## 11. Resolved (v1)

1. Nucleus competition: WTA + delayed central-I ring feedback (no bind gate).
2. Pattern binding: eligibility trace + weight consolidation (`EligibilityConsolidator`).
3. Homeostasis: synaptic scaling on L1 I-strength only.
4. Auto-stim: ecological catalog rotation (`StimulusStream`); does not read bind state.

## 12. Compliance Checklist

Before merging any feature, verify:

- [ ] Only `1` events propagate and log
- [ ] Production uses conductance plasticity; timing laws are lab-profile only
- [ ] Learning is local to the neuron
- [ ] E and I weights handled separately
- [ ] Refractory enforced after every spike
- [ ] Symbol bijection maintained
- [ ] No guided winner/symbol injection during auto-stim
- [ ] Prediction comparison precedes recognition output

---

## 13. References (Informative, Not Normative)

- Hebb (1949) — causal co-activation
- Bi & Poo — STDP timing windows
- Berry et al. — firing events separated by silence
- Quiroga et al. — sparse selective coding
- Predictive coding literature — error-driven learning

These inform the paradigm. **`tenants.txt` and this spec override them when they conflict.**
