# Plan of Action — Self-Paced, Unguided Biological Learning

**Date:** 2026-07-10  
**Branch target:** `Paul_Model` → `main`  
**Authority:** `Documents/tenants.txt`, `Documents/biological_fidelity_spec.md`, `Documents/three_way_repo_comparison.md`  
**Status:** Complete — legacy guided curriculum and `PatternOwnership` gate **removed** (2026-07-13)

---

## 1. Definition of done

The model is **self-paced and self-learning** when all of the following hold:

| Criterion | Meaning |
|-----------|---------|
| **No assignment oracle** | No code path assigns “pattern P → neuron k” before or during learning |
| **No curriculum oracle** | Stimulus stream does not read `PatternOwnership`, “learned” lists, or equilibrium state |
| **No bind gate** | Consolidation is continuous local plasticity; exclusivity comes from weights + inhibition |
| **No teacher events** | API does not inject winners, symbols, ownership, or drive boosts |
| **Ecological input** | Patterns arrive on a fixed schedule or stochastic stream independent of memory |
| **Stable exclusivity** | Under interleaved presentation, each pattern converges to one neuron via physics alone |
| **Auditable emergence** | `PatternMemorySnapshot` is **derived / read-only**, never blocks learning |
| **Dense time baseline** | Robustness stack (Phases 1–5) is **default ON** — biology does not toggle time modes |

**Not required for “zero guide”:** removing WTA, refractory, synaptic delays, fixed pool size, or local plasticity rules. Those are **structure**, not guidance.

---

## 2. Inventory — what guides learning today

| # | Mechanism | Location | Guiding behavior | Target |
|---|-----------|----------|------------------|--------|
| G1 | `PatternOwnership.can_bind()` | ~~`domain/pattern_ownership.py`~~ | Blocks neuron B from consolidating if A owns pattern | **Removed** |
| G2 | `PatternOwnership.claim()` on bind | ~~`nucleus_network.py`~~ | Writes global 1:1 map at bind time | **Removed** — `PatternMemorySnapshot` only |
| G3 | `CatalogAutoStimScheduler` | ~~`simulation/catalog_auto_stim.py`~~ | Holds random **unlearned** line until owner exists | **Removed** — `StimulusStream` only |
| G4 | `eligibility_threshold` (0.75) | `learning_dynamics.py`, `eligibility_consolidator.py` | Discrete bind ceremony | **Continuous maturation**; threshold from local homeostasis |
| G5 | `consolidation_weight_threshold` | `eligibility_consolidator.py` | Second global bind gate | **Neuron-local** readiness from conductance score |
| G6 | `learned_line_ids` / `remaining_line_ids` in API | `api/service.py` | Exposes curriculum state to UI | **Diagnostic only** or remove from stimulate path |
| G7 | Robustness stack default OFF | `learning_dynamics.py` | Discrete one-tick pulses unless user enables | **Default ON** |
| G8 | Fixed 4-neuron pool for 4 catalog lines | `nucleus_network.py`, `lines.py` | Structural 1:1 capacity hint | **Intentional scope** — 4 center-cell shapes only (no 8-pattern expansion) |
| G9 | Manual `line_id` stimulate | `api/brain_routes.py` | Experimenter override (OK for lab) | Keep for **probe/lab**; not default auto-stim |
| G10 | `POST /api/unbind` | `api/service.py` | Administrative memory wipe | Keep as **lab tool**; not part of learning loop |

---

## 3. Architecture target

```
                    ┌─────────────────────────────────────┐
  Ecological        │  StimulusStream (no memory read)   │
  input only   ───► │  rotation | i.i.d. | edge indices  │
                    └─────────────────┬───────────────────┘
                                      │ Pattern (edge_ids only)
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  L1 E/I → Ring E + Central I (NI)  │
                    │  WTA + delayed feedback             │
                    │  Local E/I plasticity (always on)   │
                    │  SimulationClock + flow (default)   │
                    └─────────────────┬───────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
   Conductance maturation    Inhibitory turnover          Assembly flow credit
   (winner sensory/relay)   (per-loser NI channels)      (E→I maturation)
          │                           │                           │
          └───────────────────────────┴───────────────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  Emergent exclusivity: losers cannot  │
                    │  win + cannot consolidate same edges │
                    └─────────────────┬───────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │  OwnershipObserver (read-only)        │
                    │  sigma_k when local memory matures  │
                    └─────────────────────────────────────┘
```

---

## 4. Phased implementation

### Phase 0 — Baseline & metrics (1–2 days)

**Goal:** Measure how much today’s guides contribute before removing them.

| Task | Action | Files |
|------|--------|-------|
| 0.1 | Add `guide_score` harness: run interleaved rotation with guides ON vs OFF | `tests/test_guide_ablation.py` (new) |
| 0.2 | Document baseline: 4/4 with guides + robustness; ?/4 with guides off | `tests/test_interleaved_robustness.py` |
| 0.3 | Add `unguided_mode` flag (default `false` until Phase D) | `learning_dynamics.py`, API |
| 0.4 | CI gate: existing 166 tests pass; new ablation tests recorded not gating until Phase D | `.gitlab-ci` / local pytest |

**Acceptance:** Reproducible table: {guides on/off} × {robustness on/off} × {rotation, hold-until-learned}.

---

### Phase A — Implicit exclusivity (remove G1, G2 as gates)

**Goal:** One pattern → one neuron enforced by plasticity + inhibition, not `can_bind()`.

| Task | Action | Files |
|------|--------|-------|
| A.1 | Introduce `OwnershipObserver` — records `pattern → winner_id` when bind evidence fires; **never** blocks | `domain/ownership_observer.py` (new) |
| A.2 | Under `unguided_mode`: skip `can_bind` check; always run plasticity on WTA winner | `nucleus_network.py` |
| A.3 | Strengthen loser suppression path when `unguided_mode`: ensure turnover + flow-rate drain active | `inhibitory_turnover.py`, `wta_coordinator.py` |
| A.4 | Winner-only sensory/relay plasticity: verify losers’ conductances on shared edges do not cross consolidation | `conductance_plasticity.py`, tests |
| A.5 | Collision detector: if two neurons bind same `edge_ids`, emit `OWNERSHIP_COLLISION` event (fail test) | `diagnostics/learning_integrity.py` |
| A.6 | Migrate `pattern_ownership` API to observer snapshot; deprecate `claim()` / `can_bind()` | `pattern_ownership.py` → observer |

**Tests:**

| Test | Pass criterion |
|------|----------------|
| `test_unguided_single_pattern_100x` | One stable winner; no collision event |
| `test_unguided_two_patterns_sequential` | Two distinct owners without `can_bind` |
| `test_unguided_interleaved_rotation_4` | 4/4 unique owners, 500 rounds, robustness on |

**Acceptance:** Interleaved 4/4 with `unguided_mode=true`, `can_bind` unused.

---

### Phase B — Ecological stimulus (remove G3, G6)

**Goal:** Input stream never reads learning state.

| Task | Action | Files |
|------|--------|-------|
| B.1 | Add `StimulusStream` interface: `next(timestep) -> Pattern \| None` | `simulation/stimulus_stream.py` (new) |
| B.2 | Implement `RotatingStimulusStream` — fixed cycle H1→V1→D0→D1→… | same |
| B.3 | Implement `StochasticStimulusStream` — i.i.d. catalog line each pulse | same |
| B.4 | Implement `EdgeIndexStimulusStream` — random 3-edge subsets (no catalog IDs) | same |
| B.5 | Wire `POST /api/stimulate {}` to stream only; **remove** `resolve_stimulus_line(ownership)` from hot path | `api/service.py` |
| B.6 | Retire `CatalogAutoStimScheduler` or restrict to **legacy mode** behind `guided_curriculum_enabled=false` default | `catalog_auto_stim.py` |
| B.7 | UI: replace “learned / remaining” curriculum display with “observed owners” from observer | `ParametersOverlayPanel.js`, training snapshot |

**Tests:**

| Test | Pass criterion |
|------|----------------|
| `test_stimulus_stream_no_ownership_import` | Stream module has zero imports of `PatternOwnership` |
| `test_rotation_never_calls_learned_line_ids` | Mock ownership — stimulate 100×, ownership never queried |
| `test_ecological_interleaved_4_4` | Rotation + unguided + robustness → 4/4 |

**Acceptance:** Default auto-stim uses rotation or stochastic stream; equilibrium is **observed**, not **scheduled**.

---

### Phase C — Continuous maturation (remove G4, G5 as global gates)

**Goal:** No discrete “bind API”; memory matures from local traces and weights.

| Task | Action | Files |
|------|--------|-------|
| C.1 | Add `NeuronReadiness` — per-neuron score from eligibility EMA + sensory weight score | `learning/neuron_readiness.py` (new) |
| C.2 | Replace `try_consolidate` threshold checks with readiness crossing (hysteresis: bind high, unbind low) | `eligibility_consolidator.py` |
| C.3 | Move `eligibility_threshold` / `consolidation_weight_threshold` to **per-neuron adaptive** targets via `SynapticScalingHomeostasis` | `synaptic_scaling_homeostasis.py` |
| C.4 | `PATTERN_BOUND` event fires when readiness crosses upward; not a separate code path from plasticity | `nucleus_network.py` |
| C.5 | Tenant 8: recall via `neuron.prediction` only; no external recognition drive | `recall_drive_integrator.py` (verify inference-only) |
| C.6 | Update `model_equations.md` with continuous maturation equations | `Documents/model_equations.md` |

**Tests:**

| Test | Pass criterion |
|------|----------------|
| `test_no_instant_bind_first_pulse` | No `PATTERN_BOUND` on pulse 1 |
| `test_bind_follows_weight_growth` | Bind only after sensory score monotonic rise |
| `test_prediction_recall_without_line_id` | Probe recognizes without catalog label in learning path |

**Acceptance:** Removing global `eligibility_threshold` from API does not break 4/4 ecological test.

---

### Phase D — Default biology & flag flip (G7)

**Goal:** Production defaults match biological baseline; guided mode is opt-in legacy.

| Task | Action | Files |
|------|--------|-------|
| D.1 | Set `temporal_integration_enabled`, `excitatory_flow_rate_enabled`, `inhibitory_turnover_enabled`, `assembly_flow_credit_enabled`, `inhibitory_flow_rate_enabled` → **true** in `LearningDynamics` | `learning_dynamics.py` |
| D.2 | Set `unguided_mode=true`, `guided_curriculum_enabled=false` as defaults | same |
| D.3 | Frontend: “Guided curriculum (legacy)” toggle, default off | `LearningDynamics.js`, `ParametersOverlayPanel.js` |
| D.4 | Rename API training fields: `observed_owners` not `learned_line_ids` | `api/service.py` |
| D.5 | Update `biological_fidelity_spec.md`, `three_way_repo_comparison.md` | Documents |

**Acceptance:** Fresh reset brain reaches 4/4 under rotation with **zero parameter changes**.

---

### Phase E — 8-pattern scale — **out of scope**

**Decision (2026-07-10):** Paradigm stays on the **4 center-cell catalog** (`H1`, `V1`, `D0`, `D1`) with a **4-neuron ring**. No expansion to Abhi’s 8 line primitives.

| Rationale | Detail |
|-----------|--------|
| Product focus | Prove self-paced unguided learning on a minimal, auditable catalog |
| Architecture fit | 4 E + central I matches 4 shapes by design — not a temporary limit |
| Success criterion | **4/4** injective ownership under ecological rotation (implemented) |

Abhi’s 8-pattern stress remains a useful **external benchmark** in comparison docs only; it is not a roadmap item for this repo.

---

## 5. Explicit rejections (stay tenant-true)

Do **not** adopt these as shortcuts — they trade guidance for cheating or tenant violations:

| Rejected | Reason |
|----------|--------|
| `GridMatcher` / index assignment | Lookup, not learning |
| Signed-spike OFF depression | Tenant 2 — unwires silent inputs |
| `eta_loss = 10` loser FF depression | Erases cross-pattern readiness |
| `l1i_immediate_relay` | L1 I is not a relay neuron |
| Global weight budget renormalization | Tenant 9 — non-local |
| `lasting_inhibition` shared field | Pattern-blind collapse |
| Injecting winner / symbol from API | Teacher forcing |

---

## 6. Migration & compatibility

| Milestone | User-visible change | Rollback |
|-----------|---------------------|----------|
| Phase A | New `unguided_mode` param (default off) | `unguided_mode=false` |
| Phase B | Auto-stim behavior changes when `guided_curriculum_enabled=false` | Legacy scheduler flag |
| Phase D | **Breaking:** defaults flip to unguided + robustness | `guided_curriculum_enabled=true` + discrete defaults |

**Checkpoint migration:** Store `schema_version`; on load, if guided checkpoint, map `pattern_ownership` → observer snapshot only.

---

## 7. Success metrics (track every phase)

| Metric | How measured | Target (4-pattern v1) |
|--------|--------------|------------------------|
| **Injective ownership** | Unique pattern → neuron map | 4/4 |
| **Collision rate** | `OWNERSHIP_COLLISION` events | 0 |
| **Guide dependence** | 4/4 with guides off / with guides on | Ratio → 1.0 |
| **Time to 4/4** | Pulses under ecological rotation | ≤ 50 (tune) |
| **Bind integrity** | `learning_integrity_probe.py` clean | 100% |
| **No curriculum reads** | Static analysis / import graph | 0 ownership imports in stimulus path |
| **Recall without labels** | Probe on `edge_ids` only | Correct owner |

---

## 8. Suggested execution order

```
Week 1   Phase 0 + Phase A (ablation harness, observer, remove can_bind)
Week 2   Phase B (stimulus streams, retire scheduler from hot path)
Week 3   Phase C (continuous maturation, equation doc)
Week 4   Phase D (default flip, UI, docs, full regression) — **complete**
```

**Critical path:** A → B → D (complete). **Catalog scope:** 4 patterns only — no Phase E.

**Status:** Phases 0–D implemented; 4/4 unguided ecological rotation is the production target.

---

## 9. File checklist (new / major touch)

| File | Phase |
|------|-------|
| `domain/ownership_observer.py` | A |
| `simulation/stimulus_stream.py` | B |
| `learning/neuron_readiness.py` | C |
| `tests/test_guide_ablation.py` | 0 |
| `tests/test_ecological_stimulus.py` | B |
| `tests/test_unguided_exclusivity.py` | A |
| `simulation/nucleus_network.py` | A, C |
| `api/service.py` | B, D |
| `simulation/learning_dynamics.py` | D |
| `Documents/biological_fidelity_spec.md` | D |
| `Documents/model_equations.md` | C |

---

## 10. One-sentence summary

**Stop telling the network what it has learned and which pattern to show next; turn on dense time by default; let winner plasticity and per-loser inhibitory maturation enforce exclusivity; record ownership only as a read-only audit of what emerged.**

---

## 11. Ecological purity matrix (Phase 1 — biological roadmap)

| Mode | Reads `PatternMemorySnapshot`? | Injects winners/weights? | Strict unguided benchmark? |
|------|-------------------------------|--------------------------|----------------------------|
| `rotation` | **No** | **No** | **Yes** — primary Phase 8 metric |
| `stochastic` | **No** | **No** | **Yes** |
| `mastery` | **Yes** (completion only) | **No** | No — completion-scheduled demo |
| `mastery` probe phase | **No** | **No** | Partial — post-learning recall only |
| Manual `line_id` API | No | No | Lab override (experimenter) |

**Import guards:** `tests/test_ecological_purity.py` asserts rotation/stochastic stimulus modules never call `owner_for_pattern`.

**Baseline harness:** `scripts/baseline_ecology_benchmark.py` — rotation vs mastery on production `DEFAULT_LEARNING_DYNAMICS`, seeds 0/7/42, guide-dependence ratio ≥ 0.95.

**Roadmap:** full phased plan in `Documents/biological_learning_roadmap.md`.

---

## Related documents

| Document | Role |
|----------|------|
| `Documents/tenants.txt` | Non-negotiable causality |
| `Documents/biological_fidelity_spec.md` | Current bind chain (to be revised in Phase D) |
| `Documents/three_way_repo_comparison.md` | Context vs Abhi / early scaffold |
| `Documents/cipp_comparison_strengths_weaknesses.md` | Safe borrow list |
| `tests/test_interleaved_robustness.py` | Rotation stress reference |
