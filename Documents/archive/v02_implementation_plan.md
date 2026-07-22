# v0.2 Implementation Plan

> **Archive:** Historical plan for bind-gate + EMA homeostasis era. Superseded by biological v1 (`Documents/biological_fidelity_spec.md`, `Documents/model_equations.md`). Bind gate and `InhibitoryHomeostasis` are removed from the active codebase.

**Authority:** `tenants.txt`, `paradigm_spec.md` §11 open questions 1 & 4  
**Status:** Superseded — see biological v1 implementation  
**Target:** Rule 4.5 (inhibitory homeostatic plasticity) + nucleus gating (center I suppression)

---

## Executive summary

| Track | Effort | Risk | Depends on |
|-------|--------|------|------------|
| **A — Nucleus gating** | Small–medium (~2–3 days) | Low — mostly clarifies existing WTA | Design decision §1.1 |
| **B — Rule 4.5 homeostasis** | Medium–large (~4–6 days) | Medium — tuning affects learning stability | Track A optional; shared `LearningDynamics` |

**Recommended order:** A first (tighten bind semantics, minimal new surface area), then B (new plasticity subsystem).

---

## 0. Prerequisites — design decisions (do before coding)

### 0.1 Nucleus I vs Layer-2 central I (resolve spec §11 Q1)

**Current code:** One physical `CentralInhibitoryNeuron` (`nucleus_i`) in `wta_coordinator.py` performs **global ring WTA**. Spec §4.3 also describes a **per-neuron nucleus shell** (1 I center + 8 E ring). Research doc §7 says these roles must not be merged.

**Decision options:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A (recommended)** | Treat `nucleus_i` as the **nucleus center I** for gating; ring = `nucleus_e_0..7`. Update spec text to match implementation. | No new neurons; gate logic plugs into existing WTA | Loses separate “Layer 2 pool outside nucleus” if we add more competitors later |
| **B** | Add inner shell I per ring neuron (8 small I units) + keep `nucleus_i` as global WTA | Closer to literal spec diagram | Large refactor; 3D model + state API churn |

**Action:** Pick **A** for v0.2; document in `paradigm_spec.md` §4.3 that the implemented nucleus is a **shared** center I + 8 E ring.

### 0.2 Gate open condition (resolve spec §11 Q1)

Proposed formal rule (aligns with spec §4.3 + `grid_and_layers_research.md` §7):

```
gate_open(t) :=
  ∃! winner ∈ ring : winner.register == 1
  AND central.register == Z
  AND wta_arbitration_completed(t) == true
```

Interpretation:
- **Single ring winner** — already checked.
- **Central I suppressed** — I did not register `1` this timestep (losers were membrane-clamped, not I-spike gated).
- **WTA completed** — `WtaCoordinator.run()` returned a winner after full leak→integrate→compete pass.

**Edge case:** When only one candidate crosses threshold, WTA spikes winner **without** central I firing. Gate should still open (ring E dominates; no competition needed).

**Action:** Write this into `paradigm_spec.md` §4.3 (replace “deferred to v0.2”).

### 0.3 Homeostasis rule (resolve spec §11 Q4)

Proposed **local firing-rate homeostasis** on inhibitory coupling (Tenant 4.5):

```
For each Layer 1 pair (E, I):
  ρ_E = exponential moving average of E.register == 1 over window W_h
  target ρ* (e.g. 0.15 spikes/timestep)
  Δw_I = η_h · (ρ_E - ρ*)
  w_I ← clip(w_I - Δw_I, w_min, w_max)   // stronger I when E too active
```

Apply `INHIBITION_STRENGTH` / `FEEDFORWARD_GAIN` as **per-pair tunable weights** instead of class constants in `layer1_pair_dynamics.py`.

**Scope v0.2:** Layer 1 pairs only. Nucleus central I gains optional `inhibition_strength` homeostasis in v0.2.1 if L1 proves stable.

**Action:** Add constants to `LearningDynamics`; document in spec §4.5.

---

## Track A — Nucleus gating (center I suppression)

### A1. Spec & docs

- [x] Update `paradigm_spec.md` §4.3 with formal `gate_open` rule (§0.2).
- [ ] Update `grid_and_layers_research.md` §7 to state implemented mapping (§0.1 option A).
- [ ] Close spec §11 Q1 in changelog.

### A2. Core logic

**Files:**

| File | Change |
|------|--------|
| `simulation/nucleus_binding_gate.py` | Remove `del central`. Implement §0.2: require `central.neuron.register == Z`, single ring spiker, winner is that spiker. |
| `simulation/wta_coordinator.py` | Return structured outcome: `{ winner, central_fired: bool, candidate_count }` instead of bare winner (or attach metadata on coordinator). |
| `simulation/nucleus_network.py` | Pass WTA metadata into gate; set `_last_gate_open` from new logic; **block STDP + binding** when `gate_open` is false (already gated at L327 — verify no bypass). |

**Pseudocode:**

```python
def permits_binding(winner, central, ring, *, wta_central_fired: bool) -> bool:
    if winner is None or winner.register != ONE:
        return False
    ring_spikers = [c for c in ring if c.register == ONE]
    if len(ring_spikers) != 1 or ring_spikers[0] is not winner:
        return False
    if central.register == ONE:
        return False  # I fired — binding blocked this tick
  return True
```

Note: If we later want “I must fire to suppress losers, then gate opens next tick”, defer to v0.3; v0.2 uses same-timestep rule above.

### A3. Tests

**File:** `tests/test_nucleus_binding_gate.py`

| Test | Assert |
|------|--------|
| `test_gate_closed_when_central_i_fired` | central `register=1`, single ring spiker → `permits_binding` false |
| `test_gate_open_single_winner_no_central` | central `Z`, one ring spiker → true |
| `test_gate_closed_multi_spikers` | (existing) |
| `test_no_bind_when_gate_closed_during_stim` | Integrate: force gate false over N steps → bind count unchanged |
| `test_gate_open_in_api_state` | After clean WTA win, `state["nucleus"]["gate_open"]` true |

**Regression:** Existing `test_nucleus_wta.py`, `test_v01_milestone.py` must still pass (may need bind event count tuning if gate stricter).

### A4. API / frontend (optional v0.2)

- [x] Expose `wta_central_fired` in `nucleus` state JSON (debug).
- [x] Ring card hint when `gate_open` false during learning: “Competing…”
- [x] 3D: brief center I pulse when `wta_central_fired`

### A5. Acceptance (Track A)

- [x] Binding only when `gate_open` true in simulation tests.
- [x] Central I spike on multi-candidate timesteps; no bind that same tick.
- [x] Single-candidate timesteps still learn at prior rate.
- [x] Spec §12 checklist unchanged for other tenants.

---

## Track B — Rule 4.5 inhibitory homeostatic plasticity

### B1. Data model

**New file:** `domain/inhibitory_synapse.py` (or extend `layer1_pair.py`)

```python
@dataclass
class InhibitoryCoupling:
    feedforward_gain: float      # E→I recruitment
    inhibition_strength: float   # I→E subtractive shunt
    e_collateral: float          # E spike → I drive
```

**New file:** `learning/inhibitory_homeostasis.py`

```python
class InhibitoryHomeostasis:
    def __init__(self, target_rate, eta, window, w_min, w_max): ...
    def record_spike(self, neuron_id, timestep): ...
    def update(self, coupling: InhibitoryCoupling, neuron_id) -> InhibitoryCoupling: ...
```

**Files to modify:**

| File | Change |
|------|--------|
| `simulation/layer1_pair.py` | Hold `InhibitoryCoupling` per pair; serialize in state |
| `simulation/layer1_pair_dynamics.py` | Read coupling from pair, not class constants |
| `simulation/learning_dynamics.py` | Add `homeostasis_target_rate`, `homeostasis_eta`, `homeostasis_window`, I weight bounds |
| `simulation/engine.py` | Instantiate homeostasis; call after L1 timestep |
| `api/service.py` + `main.py` | PATCH parameters for homeostasis fields |

### B2. Timestep integration

Insert after Layer 1 `process_active_pair` / `leak_idle_pair` in `engine.py` (or `layer1_network.py`):

```
for each pair:
  if E fired this tick:
    homeostasis.record_spike(pair.excitatory.id, t)
  coupling = homeostasis.update(pair.coupling, pair.excitatory.id)
  pair.set_coupling(coupling)
```

Homeostasis runs **every timestep** (Tenant 7 continuous), not only on STDP events.

### B3. Initial values & stability

Seed from current constants:

| Parameter | Current location | Initial value |
|-----------|------------------|---------------|
| `feedforward_gain` | `FEEDFORWARD_GAIN` | 0.65 |
| `inhibition_strength` | `INHIBITION_STRENGTH` | 0.28 |
| `e_collateral` | `E_SPIKE_COLLATERAL` | 0.4 |
| `target_rate` | new | ~0.12–0.18 (tune) |
| `eta` | new | 0.01 |

**Tuning protocol:** Run `scripts/chart_metrics_probe.py` + curriculum to 8/8; adjust `eta` until bind times do not drift >20% vs baseline.

### B4. Tests

**New file:** `tests/test_inhibitory_homeostasis.py`

| Test | Assert |
|------|--------|
| `test_i_strength_increases_when_e_overfires` | Artificially spike E every tick → `inhibition_strength` rises |
| `test_i_strength_decreases_when_e_silent` | No E spikes → strength decays toward floor |
| `test_bounds_respected` | w stays in `[w_min, w_max]` |
| `test_homeostasis_does_not_log_z` | No Z events in event log from homeostasis |

**Integration:** `tests/test_layer1_pair_dynamics.py` — after long run, E/I spike ratio within band.

### B5. API & observability

- [x] `GET /api/state` → `layer1.pairs[i].inhibitory_coupling` (or aggregate stats).
- [x] PATCH `/api/parameters` for `homeostasis_target_rate`, `homeostasis_eta`, `homeostasis_window`.
- [ ] Optional chart: mean `inhibition_strength` over time (frontend v0.2.1).

### B6. Acceptance (Track B)

- [x] Spec Rule 4.3: I weights stored separately from E (input STDP edges).
- [x] Spec Rule 4.5: local homeostasis adjusts I coupling from firing rate.
- [x] Curriculum still reaches 8/8 equilibrium with default tuned params.
- [x] No global gradient / batch phase introduced.

---

## Cross-cutting work

### C1. Parameters surface

Extend `LearningDynamics.serialize()` and frontend `ParametersOverlayPanel` only if new knobs are user-facing:

| Parameter | Track | UI? |
|-----------|-------|-----|
| `homeostasis_target_rate` | B | Optional (advanced) |
| `homeostasis_eta` | B | Optional |
| `central_inhibition_strength` | A | Already implicit; expose if tuning needed |

### C2. CI

- [ ] Add `npm run test:unit` to `.gitlab-ci.yml` (orthogonal but recommended before v0.2 merge).
- [ ] All new pytest modules in `backend/tests/`.

### C3. Documentation

- [ ] Update `README.md` roadmap table when each track ships.
- [ ] Tick spec §12 compliance items linked to test names.

---

## Suggested sprint breakdown

### Sprint 1 — Gating (Track A)

1. Design sign-off §0.1 + §0.2 (30 min).
2. `WtaCoordinator` outcome metadata (2 hr).
3. `NucleusBindingGate` rewrite + tests (3 hr).
4. Integration test + fix regressions (2 hr).
5. Spec doc update (1 hr).

### Sprint 2 — Homeostasis core (Track B)

1. Design sign-off §0.3 (30 min).
2. `InhibitoryCoupling` + `InhibitoryHomeostasis` + unit tests (4 hr).
3. Wire Layer 1 pairs + engine loop (3 hr).
4. Parameter API + defaults (2 hr).

### Sprint 3 — Stabilize & ship

1. Tune homeostasis until curriculum stable (4 hr).
2. Integration tests + CI (2 hr).
3. Optional UI for `gate_open` / I weights (3 hr).
4. README + spec closure (1 hr).

---

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Stricter gate slows binding | Benchmark N_bind timesteps before/after; relax only if >25% regression |
| Homeostasis destabilizes L1 relay | Start with small `eta`; bound weight changes per tick |
| Spec ambiguity resurfaces | Lock decisions in §0 before implementation PRs |
| Frontend drift | Track A/B are backend-first; UI is optional slice |

---

## Out of scope (v0.3+)

- Per-neuron nucleus shell I (spec option B).
- Inhibitory STDP (only homeostatic scaling in v0.2).
- Pattern overwrite beyond existing unbind API.
- Tolerance ε for noisy re-recognition (spec §11 Q3).
