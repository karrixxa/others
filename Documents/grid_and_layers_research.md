# Grid, Layers, LIF & Winner-Take-All — Research & Architecture

**Version:** 1.0  
**Authority:** `Documents/tenants.txt`, `Documents/paradigm_spec.md`  
**Status:** Implemented — see `Documents/model_equations.md` for the live equation reference

---

## 1. Purpose of the 3×3 Grid

The input grid is **not** a free-form pixel canvas. It encodes **line patterns** — each line is exactly **three squares** formed from combinations of the nine grid cells.

**Current implementation (RGC gate):** catalog auto-stim presents **four center-cell lines** (`H1`, `V1`, `D0`, `D1`) — each must include cell `(1,1)`. One unlearned line is held at random until bound; equilibrium is **4/4**.

The grid is the **sensory edge field**: the active line drives Layer 1 neuron pairs, which relay shape events to the nucleus ring where neurons **compete** via WTA to learn patterns (eligibility consolidation).

---

## 2. Catalog Lines (Formal Map)

> **Historical note:** §2.1 documents the original eight-line research grid. The live backend and UI use the four center-cell catalog in §2.2.

### 2.1 Eight-line reference grid (research)

Grid coordinates use `(row, col)` with origin at top-left:

```
(0,0) (0,1) (0,2)
(1,0) (1,1) (1,2)
(2,0) (2,1) (2,2)
```

| ID | Type | Cells | Symbol name |
|----|------|-------|-------------|
| `H0` | Horizontal | (0,0)(0,1)(0,2) | top row |
| `H1` | Horizontal | (1,0)(1,1)(1,2) | middle row |
| `H2` | Horizontal | (2,0)(2,1)(2,2) | bottom row |
| `V0` | Vertical | (0,0)(1,0)(2,0) | left column |
| `V1` | Vertical | (0,1)(1,1)(2,1) | center column |
| `V2` | Vertical | (0,2)(1,2)(2,2) | right column |
| `D0` | Diagonal ↘ | (0,0)(1,1)(2,2) | main diagonal |
| `D1` | Diagonal ↙ | (0,2)(1,1)(2,0) | anti-diagonal |

**Total: 8 lines** = 3 horizontal + 3 vertical + 2 diagonal.

### 2.2 Live four-shape catalog (center-cell gate)

| ID | Type | Cells (index) | Notes |
|----|------|---------------|-------|
| `H1` | Horizontal | 3, 4, 5 | middle row |
| `V1` | Vertical | 1, 4, 7 | center column |
| `D0` | Diagonal ↘ | 0, 4, 8 | main diagonal |
| `D1` | Diagonal ↙ | 2, 4, 6 | anti-diagonal |

**Total: 4 lines** — one L2 ring E neuron per shape; equilibrium **4/4**.

Each line pattern `P_line` is a set of three edge IDs:

```
P_line = { input_r{row}_c{col} for each cell in the line }
```

Example — middle row:

```
H1 = { input_r1_c0, input_r1_c1, input_r1_c2 }
```

### Overlap note

Cell `(1,1)` (center) appears in **V1**, **H1**, **D0**, and **D1**. Overlap is intentional: the **line identity** is the full triple, not any single cell. Tenant 6 (1:1 symbol) applies at Layer 2 — one symbol per learned **line**, not per cell.

---

## 3. Auto-Stim Behaviour

**Auto-Stim** continuously feeds **one selected line pattern** across timesteps.

| Property | Value |
|----------|-------|
| Mode | Continuous (repeats every tick while enabled) |
| Output per tick | `1` on the three edges of the active line; all other edges remain `Z` |
| Selection | One of `H1`, `V1`, `D0`, `D1` (random among unlearned; held until bound) |
| Layer 1 effect | Pairs at the three active grid positions receive excitation |
| Layer 2 effect | Aggregated shape drives competition |

Auto-Stim does **not** send `0`. Inactive edges are **`Z`** (unregistered), not an active zero.

---

## 4. Layer 1 — Relay Layer

### Structure (existing frontend)

- 3×3 grid of **E/I pairs** (18 outer neurons, 9 positions)
- One excitatory + one inhibitory sphere per cell

### Role in the pipeline

Layer 1 is a **relay / encoding layer**, not the learning winner layer.

```
Auto-Stim line → 3 active grid edges → 3 E/I pairs at those positions fire
                                         ↓
                              shape vector forwarded to Layer 2
```

**Per active cell `(r,c)` on the stimulated line:**

1. Input edge registers `1` → excitatory neuron at `(r,c)` integrates weighted drive
2. Input `1` drives **E only** — local I is **not** driven by the stimulus
3. If local I has fired (from delayed L2 descending charge), inhibitory drive suppresses paired E before relay spike
4. If E fires `1`, it propagates on its **Layer 1 → Layer 2** edge
5. Neighboring pairs: a relay `1` applies lateral inhibitory drive to adjacent E relays (event-driven, not membrane clamp)
6. **Delayed descending feedback:** Layer 2 / nucleus ring E SPIKE events at \(t\) charge the **three L1 I neurons paired with the active shape** at \(t+1\) (`l2_to_l1_i_gain`; central I excluded). Charge accumulates until \(I_g\) reaches threshold, then fires.

**Shape forwarded to Layer 2** = the identity of which line is active (8-way code), encoded by **which three Layer 1 E neurons fired**, not by raw grid bits.

Layer 1 neurons do **not** bind the line symbol (Tenant 3 reserved for Layer 2 competitors). Layer 1 may use LIF dynamics but does not participate in WTA binding.

---

## 5. Layer 2 — Competition & Learning Layer

### Structure (implemented)

- Pool of **excitatory competitor neurons** (each with one-pattern memory + symbol slot)
- **One central inhibitory neuron** (global WTA controller)
- Nucleus: shared center I + 8 E ring (`nucleus_e_0`…`nucleus_e_7`); gating v0.2

### Winner-Takes-All (WTA)

**Goal:** Given a continuous line stimulus, Layer 2 neurons compete. The **first neuron to successfully bind** the line pattern wins; others are suppressed and cannot bind that pattern.

#### Biological basis

Cortical WTA circuits use:

- Several **excitatory** pyramidal neurons
- **Shared inhibitory pool** (one or few interneurons)
- Excitatory neurons drive the inhibitor; inhibitor feeds back to **all** excitatory competitors

The neuron (or group) with the **strongest net excitation** drives the inhibitor hardest, which **hyperpolarizes / suppresses** the others. Only the winner maintains sustained `1` output suitable for binding.

References: Douglas & Martin (cortical microcircuits), Maass (WTA computation), PLOS Comp Bio (STDP in WTA installs online learning).

#### Our WTA rules (Cognative Paradigm)

| Step | Rule |
|------|------|
| 1 | All Layer 2 E neurons receive input from Layer 1 shape events |
| 2 | Each integrates via **LIF** (see §6) |
| 3 | Competitors that cross threshold enter the WTA candidate set |
| 4 | **Winner selected** (peak membrane; fair tie-break) |
| 5 | **Only the winner spikes** (sole ring ONE / SPIKE) |
| 6 | Winner spike collateral **charges** central I |
| 7 | When central I reaches threshold it fires and inhibits **all other ring E** |
| 8 | Winner spike (next tick) charges shape-scoped L1 I → L1 I inhibits paired L1 E |
| 8 | Sole ring spiker when `gate_open` → STDP binding proceeds |
| 9 | **First** L2 E to complete `N_bind` for this line wins |
| 10 | Winner assigned symbol `σ`; when a line is **owned**, central I fires on each recognition pulse to keep other ring E silent |

**Tie-break:** Equal peak membrane → lowest ring index (`nucleus_e_0` first). Implemented in `wta_coordinator.py`.

**Winner lock:** Once neuron `N_w` binds line `H1`, other Layer 2 neurons cannot bind `H1`. They remain available for other lines in future training.

---

## 6. Leaky Integrate-and-Fire (LIF) — Research & Our Use

### What LIF is (biology / computation)

The **Leaky Integrate-and-Fire** model treats a neuron as an RC circuit:

```
τ_m · du/dt = −(u − u_rest) + I(t)
```

- `u` = membrane potential (hidden, subthreshold)
- `I(t)` = sum of weighted **incoming events** at time `t`
- `τ_m` = membrane time constant (~10–20 ms in cortex)
- When `u ≥ θ` (threshold) → emit spike `1`, reset `u → u_reset`, enter refractory

**Leak** = passive decay of `u` toward rest when input stops. Without leak, charge accumulates indefinitely (non-physical). Leak **disperses energy** across time so only recent causal events matter.

Sources: Gerstner & Kistler (*Neuronal Dynamics*), EPFL online Ch.1.3; Nature Communications (adaptive LIF in SNNs).

### Why LIF fits our paradigm (not binary ANN)

| Concept | Binary ANN | LIF + 1/Z |
|---------|------------|-----------|
| Hidden state | Activation `a ∈ [0,1]` broadcast | `u` subthreshold, **not broadcast** (Tenant 1.3) |
| Output | Every step meaningful | Only threshold crossing = `1`; else `Z` |
| Energy | Accumulates in activations | **Leak dissipates** unused potential |
| Timing | Optional | Input history weighted by recency |

LIF is the standard bridge between **continuous biophysics** and **discrete event output** — exactly our `1` vs `Z` model.

### Discrete LIF update (implementation target)

Per timestep `t`, for each neuron:

```
# Leak
u[t] ← u[t-1] · (1 − dt/τ_m) + u_rest · (dt/τ_m)

# Integrate ONLY from presynaptic ONE events (Z contributes nothing)
for each incoming edge e where pre fired ONE at t:
    u[t] += w_e   (excitatory) or u[t] -= w_i (inhibitory)

# Fire check
if u[t] ≥ θ and not refractory:
    register ← ONE
    u[t] ← u_reset
    refractory_until ← t + R
else:
    register ← Z
```

**Key:** Between spikes, `u` may be non-zero internally, but the network only sees `Z` until threshold — consistent with Tenant 1.

### Energy dispersion intuition

- **Short line pulse:** `u` rises, may fire once, leak drains excess
- **Continuous Auto-Stim:** `u` equilibrates under leak + constant drive — steady sparse `1` event rate, not saturation
- **Refractory + leak:** prevent epileptic runaway (all neurons firing) — supports sparse coding

Without LIF leak, our v0.1 backend used instant threshold on raw drive — adequate for prototype, **insufficient for Layer 2 WTA timing**. LIF is required for v0.2.

---

## 7. Central Inhibitory Neuron — Role in Layer 2

### What “central inhibitor” means here

One **dedicated inhibitory neuron** (or the nucleus center **I** elevated to layer scope) that:

1. Receives excitatory input from **all** Layer 2 competitor neurons
2. When its threshold is crossed, fires `1`
3. Projects inhibitory weights to **every** Layer 2 excitatory competitor

This is **global feedback inhibition** — the canonical WTA motif (Amari 1977; Douglas & Martin; Rutishauser & Douglas).

### Functional roles

| Role | Mechanism |
|------|-----------|
| **Competition** | Strongest E drives I most → I suppresses weaker E neurons |
| **Sparsity** | Only one (or k) winners active at steady state |
| **Binding gate** | STDP binding only meaningful on neurons that **win** competition |
| **Contrast enhancement** | Similar lines overlap (e.g. share center cell) — I amplifies difference in total drive |
| **Stability** | Prevents all Layer 2 neurons from binding the same pattern simultaneously |

### Relation to nucleus (1 I + 8 E ring)

| Structure | Scope | Role |
|-----------|-------|------|
| Nucleus center **I** | Inside one neuron | Local gating of pattern registration (v0.2) |
| Layer 2 central **I** | Across competitors | **Global WTA** — selects which neuron may learn |

These are **different inhibitory roles**. Do not merge them in v0.2:

- **Layer central I** = competition between Layer 2 neurons
- **Nucleus I** = internal gate within a single neuron

The 8 excitatory ring units in the nucleus may later encode **line orientation family** (horizontal / vertical / diagonal) — open for v0.3.

### Central I dynamics (proposed)

```
# Central inhibitory neuron
u_I[t] += Σ (w_Ie · 1_Ei[t])   for each Layer 2 E that fired
if u_I ≥ θ_I:
    fire I → 1
    deliver inhibitory ONE to all Layer 2 E competitors
```

Inhibitory `1` events subtract from competitor membrane potentials (Tenant 4).

**Tuning:** Inhibition strength must exceed cross-excitation so that multiple winners cannot coexist (WTA condition: `w_inhib > w_exc` between competitors via disynaptic path).

---

## 8. End-to-End Flow (One Timestep)

```
┌─────────────────────────────────────────────────────────────┐
│  AUTO-STIM: one line (e.g. H1) → 3 edges fire ONE, rest Z  │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: 3 E/I pairs at active cells                       │
│  LIF integrate → E fires ONE → forward shape to Layer 2     │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: N competitor E neurons                            │
│  LIF integrate shape input                                  │
│  Strongest E → drives CENTRAL I → inhibits others           │
│  Winner E: STDP + pattern bind → symbol σ                   │
│  Losers: Z (suppressed), no bind                            │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT: symbol σ (line name) or prediction error             │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Mapping to Tenants

| Tenant | Grid / Layer manifestation |
|--------|---------------------------|
| 1 (1 vs Z) | Grid edges: 3 ONE, 6 Z; Layer output only on spike |
| 2 (Fire together) | STDP on Layer 2 winner between L1 shape + L2 spike |
| 3 (One pattern) | First L2 neuron to bind line wins; one pattern per neuron |
| 4 (E/I) | E/I pairs in L1; central I in L2; separate weights |
| 5 (Refractory) | LIF reset + R after every ONE |
| 6 (1:1 symbol) | Each line → one σ on winning neuron |
| 7 (Continuous) | Auto-Stim never stops; plasticity always eligible on winner |
| 8 (Prediction) | L2 predicts expected line; error on mismatch |

---

## 10. Implementation Milestones

### v0.2 — Grid lines + Auto-Stim

- [x] Replace arbitrary shapes with 8 line patterns in backend + frontend grid UI
- [x] Highlight active line on 3×3 grid during Auto-Stim
- [x] Auto-Stim loop in frontend (continuous feed)

### v0.3 — Layer 2 WTA + LIF

- [x] LIF neuron model (leak, integrate, threshold, reset)
- [x] Layer 2 competitor pool (nucleus ring: 8 E neurons)
- [x] Central inhibitory neuron with global feedback
- [x] WTA competition each timestep
- [x] First-bind-wins + symbol assignment

### v0.4 — Layer 1 → Layer 2 wiring

- [x] Layer 1 pair firing drives nucleus input edges
- [x] Full pipeline from Auto-Stim to Output column

### v0.8 — Inspection + unbind

- [x] STDP weight grid exposed via `/api/state` and frontend heatmap
- [x] Unbind protocol (`POST /api/unbind`) for line overwrite / re-learning
- [x] Bind progress chart (N_bind ratio over time)
- [x] GitLab CI (pytest + frontend build)

---

## 11. Open Design Questions

1. **Layer 2 size:** 9 neurons (one per grid position) vs fewer/more competitors?
2. **Soft vs hard WTA:** Allow 2 winners during learning, collapse to 1 on bind?
3. **Overlapping lines:** When Auto-Stim switches from `H1` to `V1`, both share `(1,1)` — how fast should central I clear previous winner state?
4. **L1 inhibitory role:** Local I suppresses E within pair only, or participates in lateral inhibition?
5. **Nucleus 8 E ring:** Map one ring neuron to each line family (H/V/D)?

---

## 12. References (Informative)

- Gerstner et al., *Neuronal Dynamics* — LIF model, leak, refractory
- Douglas & Martin — cortical microcircuits, WTA
- Maass (2000) — WTA as computational primitive
- Rutishauser et al. — STDP in WTA circuits, online learning
- Amari (1977) — competitive learning via inhibition
- Nature Communications (2024) — spike sequences in population bursts

**Normative authority:** `tenants.txt` and `paradigm_spec.md` override all references.
