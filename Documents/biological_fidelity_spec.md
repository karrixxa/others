# Biological Fidelity Specification

**Status:** Production phenomenology + gated biological lab stack  
**Date:** 2026-07-13  
**Authority:** `Documents/tenants.txt`, `Documents/paradigm_spec.md`, `Documents/model_equations.md`, `Documents/archive/self_paced_learning_plan.md`

**Catalog scope:** 4 center-cell shapes only (`H1`, `V1`, `D0`, `D1`) — no 8-pattern expansion.

---

## 1. Summary

The flat workspace runs a stable **phenomenological production learner**.
Biological alignment mechanisms are exposed only through named
`BiologicalLabProfile` presets (`P2` through `FULL`).

| Former shortcut | Current behavior |
|-----------------|------------------|
| Bind gate (`NucleusBindingGate`) | **Removed** — WTA + plasticity + memory exclusivity |
| `N_bind` consecutive counter | **Removed** — eligibility trace + weight consolidation |
| EMA `InhibitoryHomeostasis` | **Removed** — `SynapticScalingHomeostasis` on L1 I-strength |
| `PatternOwnership.can_bind()` / `claim()` | **Removed** — `PatternMemorySnapshot` is read-only |
| Guided hold-until-learned curriculum | Retained as mastery UI/demo mode; excluded from biology claims |
| `recognition_drive_boost` | **Removed** — recall from learned conductances |
| Pyramid L2→L3→L4 pipeline | **Removed** from workspace |
| Catalog line labels in binding | **Emergent** `sigma_k` symbols only |
| Discrete one-tick time (default) | **Removed** — robustness stack (Phases 1–5) **on by default** |

Auto-stim never injects winners, symbols, weights, or ownership. The production
mastery scheduler does read completion state to advance and is therefore
curriculum scheduling, not the unguided biology benchmark.

---

## 2. Causality chain (implemented)

```
Input edges (ONE) — 3 active cells
  → [Optional] SimulationClock sub-steps + inter-pulse leak (default ON)
  → Descending L1 I (from t−1 nucleus spikes on active shape)
  → L1 E relay + lateral inhibition + synaptic scaling on I-strength
  → Excitatory / inhibitory flow-rate traces (default ON)
  → Nucleus WTA (+ membrane noise, fair ties)
  → Ring feedback from central I (t−1 → t on losers)
  → Inhibitory turnover + assembly flow credit on central channels (default ON)
  → Winner postsynaptic ONE
  → Production: local conductance plasticity; lab: full triplet STDP
  → Eligibility trace update (co-active input + winner spike)
  → Consolidation when trace ≥ threshold AND weight score ≥ threshold
  → PATTERN_BOUND + NeuronMemory.bind + emergent sigma_k
  → OWNERSHIP_COLLISION if two neurons bind same edge set (audit event)
  → Enqueue descending charge for t+1
```

---

## 3. Binding criteria

Consolidation (`EligibilityConsolidator.try_consolidate`) requires:

1. Neuron not already bound.
2. Eligibility trace \(E \geq\) `eligibility_threshold` (default **0.80**).
3. `last_active_edges` matches current active edge set.
4. Normalized **per-neuron sensory** weight score \(\geq\) `consolidation_weight_threshold` (default **0.25**).

Cross-neuron duplicate ownership is recorded as `OWNERSHIP_COLLISION` and is
audit-only; it is not a consolidator exclusivity block.

Production sensory LTP uses aggregate free energy \(F_E = \theta_s - \sum w_{\mathrm{active}}\) with `sensory_plasticity_threshold` \(\theta_s\) (default **1600**) so 3-edge patterns can plateau near mean \(w \approx 533\) (score \(\approx 0.53\) vs `e_max_weight` **1000**), leaving headroom above the consolidation gate (0.25 default; room above 0.40). Relay LTP keeps a separate membrane-scale `e_plasticity_threshold` (**1.85**) so L1→L2 drive stays viable. Plastic sensory weights init above 1 (`sensory_init_weight` **240**) and clamp to `[1, 1000]`.

Every `PATTERN_BOUND` is audited by `diagnostics/learning_integrity.py`.

---

## 4. Homeostasis

**Active:** `SynapticScalingHomeostasis` adjusts L1 `inhibition_strength` from E firing-rate EMA when `scaling_eta > 0`.

**Production default:** `scaling_eta = 0` — L1 I-strength frozen at `homeostasis_i_max` (see `model_equations.md` §4).

**Not scaled:** input edge conductances (learned only via conductance plasticity on winner spikes).

---

## 5. Stimulus (mastery production default; rotation biology benchmark)

**Default auto-stim** (`POST /api/stimulate {}`), mode `mastery`
(**completion-scheduled demo curriculum** — not a biological-learning claim):

1. Present one catalog shape repeatedly until `PatternMemorySnapshot` shows a bind.
2. Advance immediately to the next shape in catalog order (`H1 → V1 → D0 → D1`).
3. After all shapes finish, enter **`probe`**: random catalog order forever (no bind-state reads) to test post-learning owner firing.

The scheduler reads bind state **only** to detect completion — it never injects winners, symbols, or weights.

**Strict unguided modes** (`ecological_stimulus_mode`):

- `rotation` — fixed hold count per shape (**ignores bind state**; benchmark for biological roadmap)
- `stochastic` — random shape each pulse (**ignores bind state**)

---

Biological benchmark documentation and metric gates use `rotation`; the API
default remains `mastery`.

## 6. API surface

| Endpoint | Learning? |
|----------|-----------|
| `POST /api/stimulate` `{}` | Yes — mastery completion schedule by production default |
| `POST /api/stimulate` `{ line_id }` | Yes — manual line override (lab) |
| `POST /api/stimulate` `{ active_indices }` | Yes — raw 3-edge pattern |
| `POST /api/probe` | No — inference-only |
| `POST /api/unbind` | Administrative release (not learning) |

Training snapshot includes: `observed_line_ids`, `learned_line_ids` (same as observed), `remaining_line_ids`, `ecological_stimulus_mode`, `ownership_collisions`.

---

## 7. Default parameters

| Flag | Default |
|------|---------|
| `ecological_stimulus_mode` | `mastery` |
| `ecological_stimulus_hold_steps` | `5` (rotation mode only) |
| `temporal_integration_enabled` | `true` |
| `excitatory_flow_rate_enabled` | `true` |
| `inhibitory_turnover_enabled` | `true` |
| `assembly_flow_credit_enabled` | `true` |
| `inhibitory_flow_rate_enabled` | `true` |
| `plasticity_mode` | `conductance` (lab: `stdp` \| `triplet`) |
| `eligibility_alpha` | **0.45** |
| `eligibility_threshold` | **0.80** |
| `consolidation_weight_threshold` | **0.25** |
| `bound_match_recall_drive_gain` | **0.7** |
| `pretrained_inhibitor_exclusivity_enabled` | **true** (production force cascade; false = labeled soft race) |

Production inhibitory channels are intentionally mature, saturated, and
frozen. This is an engineering choice, not a claim of living inhibitory
plasticity. Lab P4+ disables force exclusivity and enables Vogels iSTDP.

---

## 8. Test coverage

| Test / tool | Criterion |
|-------------|-----------|
| `test_unguided_exclusivity.py` | 4/4 interleaved without global bind gate |
| `test_ecological_stimulus.py` | Rotation stream; no curriculum reads |
| `test_guide_ablation.py` | Ecological rotation ablation |
| `test_unguided_pattern_learning.py` | Emergent single-owner stabilization |
| `test_biological_integrity_stress.py` | Full catalog + API bind audit |
| `test_interleaved_robustness.py` | Rotation stress at 4-pattern scale |
| `test_model_stress.py` | Long-run invariants |
| `scripts/learning_integrity_probe.py` | CLI bind evidence audit |
| `tests/test_production_defaults_lock.py` | Production/lab policy lock |
| `tests/test_triplet_plasticity.py` | Four-trace frequency dependence |
| `tests/test_inhibitory_stdp.py` | Vogels updates + soft-NI lab gate |
| `scripts/baseline_ecology_benchmark.py` | Rotation metric pack; mastery ablation |
| `e2e/biological-integrity.spec.js` | UI: no instant bind |

---

## 9. UI contract

- Input panel: controls + status only (shapes visible in Layer 1 3D).
- Ring cards: eligibility trace, emergent symbols, mini grids when bound.
- Parameters overlay: **Robustness (time & flow)**, eligibility, scaling, WTA noise.

---

## 10. Engineering approximations (explicit)

- The four-neuron ring and four-shape catalog are task constraints, not
  anatomical claims.
- The production conductance learner is a phenomenological free-energy rule,
  not AMPA/NMDA/GABA conductance dynamics.
- Membranes are current-based LIF; reversal potentials and receptor kinetics
  are absent by policy for this mission.
- Soft saturation \(1-(w/w_{\max})^2\) is an engineered weight bound, not Oja's
  learning rule.
- Eligibility and neuromodulator values are local state proxies, not simulated
  calcium or dopamine chemistry.
- `sigma_k` symbols and ownership snapshots are bookkeeping abstractions.
- Mastery auto-stim is a UI curriculum. Rotation is the normative unguided
  benchmark; synthetic pulse fractions survive only as a timing ablation
  fallback when clock recordings are unavailable.
- Soft NI independent race is a **labeled control** (`pretrained_inhibitor_exclusivity_enabled=false` + `descending_mode=graded`), not production doctrine. Production uses force NI + membrane wipe + same-tick L1I (`descending_mode=force`, autonomy OFF). Frozen inhibitory channels remain a stability mechanism. The `FULL` lab preset evaluates plastic NI, scaling, and replay under soft-graded ecology.

---

## Related

- `Documents/biological_learning_roadmap.md` — phased path to true biological synaptic learning
- `Documents/archive/self_paced_learning_plan.md` — unguided implementation plan (complete; legacy paths removed)
- `Documents/model_equations.md` — full equation reference
- `Documents/three_way_repo_comparison.md` — vs Abhi SNN and early scaffold
- `Documents/paradigm_spec.md` — formal tenant rules
