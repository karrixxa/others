# Cortical Column Design — Hybrid Architecture

**Status:** Phases 0–6 implemented (domain contracts + layer adapters + engine hook); Phase 7 metrics scaffold  
**Authority:** Locked defaults from Thulle (2026-07-17), `Documents/archive/cortical_column_implementation_prompt.txt`, `assets/images/map.webp`

---

## 1. Mission

Introduce a **hybrid cortical-column processing path** that maps the existing 3×3 grid / four-line catalog (H1, V1, D0, D1) onto laminar roles while preserving the **production compatibility path** (current `NucleusNetwork` + conductance plasticity stack).

Functional learning comes first: column contracts describe *what* each layer exposes; wiring into `BrainSimulator` is deferred to later phases.

---

## 2. Locked design defaults

| Parameter | Value | Notes |
|-----------|-------|-------|
| Architecture mode | **Hybrid** | Production path remains default; column path opt-in later |
| Episode line order | **H1 → V1 → D0 → D1 → END** | Canonical catalog sequence |
| L5 role | **Next-line prediction** | Predict upcoming line id or `END` |
| ColumnState model | **Hybrid** | Active assembly ids + compact context code |
| L6 role | **Cell-specific gain on next input** | Nine immutable per-cell gains |
| Episode reset | **Explicit END** or **episode silence** | Normal ~960 ms inter-pulse gaps do **not** reset |
| Episode silence threshold | **`episode_silence_reset_ms = 5000.0`** | Configurable on `ColumnStateResetPolicy` |
| Learning priority | **Functional learning first** | Ports before plasticity integration |

---

## 3. Map interpretation (`assets/images/map.webp`)

The six-layer schematic informs port boundaries (not a literal neuron mesh in Phase 1):

| Layer | Biological role | Paradigm mapping |
|-------|-----------------|------------------|
| **L4** | Primary thalamic input | Sensory line event → `Layer4Port` |
| **L2/3** | Integration / assemblies | `ContextAssemblyPort` + `ColumnState` |
| **L5** | Subcortical / column output | `NextInputPredictorPort` → `ColumnPrediction` |
| **L6** | Thalamic feedback | `FeedbackGainPort` → `CellGainMap` on next L4 input |
| **L1** | Apical context | Folded into compact context code (Phase 2+) |
| **Modulatory** | Brain-stem gain | Deferred; neuromod hooks exist in lab stack |

**Input flows (diagram):**

- Thalamus (yellow) → L4 and L6 — matches line stimulus + feedback gain loop.
- Cortical feedback (orange) → L1/L2/L4/L5 — future cross-column context.
- Modulatory (green) → all layers — lab / Phase 7+.

---

## 4. Processing loop (target)

```
for each line in episode (H1, V1, D0, D1):
    L4_input  = encode(line)
    L4_input  = apply_gain(L4_input, state.pending_gain)   # L6 from prior step
    L4_out    = Layer4Port.process(L4_input)               # L4 microcircuit
    state     = ContextAssemblyPort.integrate(state, L4_out)  # L2/3
    prediction = NextInputPredictorPort.predict(state)     # L5
    next_gain  = FeedbackGainPort.compute(state)           # L6 for *next* line
    state     = state.advance(prediction, next_gain, line_id)

on explicit END or silence >= episode_silence_reset_ms:
    state = ColumnStateResetPolicy.clear_transient(state)
```

`ColumnState` holds **transient episode context only**. Learned weights, conductance maps, and assembly stores live behind ports — never inside `ColumnState`.

---

## 5. Domain contracts (Phase 1)

Package: `backend/cognative_paradigm/cortical_column/`

| Type | Responsibility |
|------|----------------|
| `ColumnState` | Episode id, sequence index, assemblies, compact code, prediction, pending gain, silence accumulator |
| `ColumnPrediction` | Predicted line id or `END`, confidence, episode-end flag |
| `CellGainMap` | Nine non-negative finite gains; unity factory |
| `Layer4Activation` | Sparse 3×3 activation after L4 |
| `ColumnStepResult` | Immutable bundle after one column tick |
| `EpisodeBoundary` | Why an episode ended (explicit vs silence) |
| `ColumnStateResetPolicy` | Silence threshold + transient clear |

**Ports (interfaces only):**

- `Layer4Port` — sensory microcircuit
- `ContextAssemblyPort` — L2/3 integration
- `NextInputPredictorPort` — L5 readout
- `FeedbackGainPort` — L6 gain for next input

---

## 6. Phased implementation plan

| Phase | Scope | Status |
|-------|-------|--------|
| **0** | Docs layout, archive superseded plans, move papers/scripts | **Done** |
| **1** | Domain contracts + unit tests (no engine) | **Done** |
| **2** | L4 adapter on Layer1Relay with ephemeral gain | **Done** |
| **3** | L2/3 context assembly network + transition map | **Done** |
| **4** | L5 next-line predictor + sequence memory | **Done** |
| **5** | L6 feedback gain controller | **Done** |
| **6** | `HybridCorticalColumn` + engine hook + lab preset | **Done** |
| **7** | Plasticity integration (STDP / 1-Z / conductance bridge) | Planned |
| **8** | Benchmarks + lab promotion checklist | Planned |

---

## 7. Separation of concerns

```
┌─────────────────────────────────────┐
│ ColumnState (transient, per episode)│
│  episode_id, sequence_index,        │
│  assemblies, compact_code,          │
│  prediction, pending_gain, silence  │
└─────────────────────────────────────┘
              ▲ read/write per step
┌─────────────────────────────────────┐
│ Learned stores (persistent)         │
│  conductance maps, assembly weights,│
│  predictor tables — behind ports    │
└─────────────────────────────────────┘
```

Reset clears **ColumnState** fields only. Learned parameters survive episode boundaries unless a separate consolidation policy says otherwise.

Reset clears **ColumnState** fields only. Learned parameters survive episode boundaries unless a separate consolidation policy says otherwise.

---

## 9. Engine wiring (Phase 6)

| Component | Role |
|-----------|------|
| `HybridCorticalColumn` | Composes L4/L2/3/L5/L6; isolated `Layer1Relay` |
| `ColumnArchitectureFactory` | Creates column when `hybrid_cortical` + lab enabled |
| `OrderedColumnEpisodeStream` | H1→V1→D0→D1→END for lab episodes |
| `BrainSimulator` | Optional hook on `stimulate_pattern` + silence advance |
| `BiologicalLabProfileFactory.hybrid_column_dynamics()` | Distinct lab preset (not P2–P7) |

**Production default:** `column_architecture_profile="compatibility"` — no column instance, no `get_state()["cortical_column"]` key.

**Checkpoint v1:** `cortical_column` block in `get_state()` is optional; production brain restore may omit it. Predictor + transition map restore supported; full membrane restore deferred.

**Metrics (Phase 7 scaffold):** `diagnostics/column_metric_pack.py` — next-line accuracy after training episodes.

---

## 10. References

- Prompt archive: `Documents/archive/cortical_column_implementation_prompt.txt`
- Normative tenants: `Documents/tenants.txt`
- Biological stack: `Documents/biological_fidelity_spec.md`
- Layer diagram: `assets/images/map.webp`
- Production dynamics lock: `backend/tests/test_production_defaults_lock.py`
