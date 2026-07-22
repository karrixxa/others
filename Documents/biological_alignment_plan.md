# Biological Alignment Plan of Action

**Status:** Dominus-approved phased plan (Helbrecht document pass)  
**Date:** 2026-07-17  
**Authority:** [`biological_training_foundations.md`](biological_training_foundations.md), [`biological_alignment_audit.md`](biological_alignment_audit.md)  
**Scope:** Phases P0–P8. Lab implementation and documentation; no production
equation promotion.

**Related:** [`biological_learning_roadmap.md`](biological_learning_roadmap.md)

**Policy resolution (locked):** full Pfister–Gerstner triplet is the primary
lab excitatory law; BCM is deferred; Rule 3.3 is audit-only; no AMPA/NMDA
synapses are in scope; mastery remains the API default while rotation is the
benchmark; synthetic timing is fallback-only; promotion is dry-run only.

---

## Contents

1. [Keep as engineering approximation](#1-keep-as-engineering-approximation)
2. [Must fix for true bio alignment](#2-must-fix-for-true-bio-alignment)
3. [Critical path](#3-critical-path)
4. [Phases P0–P8](#4-phases-p0p8)
5. [Open questions](#5-open-questions)
6. [Sources](#6-sources)

---

## 1. Keep as engineering approximation

Document explicitly; do **not** pretend these are biology:

| Item | Rationale |
|------|-----------|
| Catalog / ring size 4 | Task scope lock |
| Auto-stim as RGC gate | Sensory presentation, not synaptic law |
| Soft saturation \(S(w)=1-(w/w_{\max})^2\) | Soft weight bound (Oja-like **intent**, not Oja) |
| Emergent `sigma_k` registry | Symbol bookkeeping |
| Current-based LIF | Until late optional biophysics (AMPA/NMDA/GABA) |
| Mastery auto-stim | **UI demo mode**, not biology benchmark |

---

## 2. Must fix for true bio alignment

| Priority | Fix |
|----------|-----|
| 1 | Production learning law → **timing-based** or **rate-BCM-equivalent** local rule |
| 2 | Replace force NI + membrane wipe as **primary** competition (or confine to optional hard-exclusivity lab with honesty labels) |
| 3 | Living **E and I** plasticity + homeostasis under rotation |
| 4 | Resolve consolidator exclusivity **doc/code** drift |
| 5 | **Real spike times** for STDP (or continuous traces), not assigned pulse fractions |
| 6 | Full triplet **or** justified BCM rate rule |

---

## 3. Critical path

```
P0 → P1 → P2 → P3 → P4 → P6 → P5 → P7 → P8
```

P5 (homeostasis) may run in parallel after P1 once excitatory law is in flight; Dominus critical path places P5 after P6 for circuit honesty before rate set-points under soft competition. Prefer Dominus order unless Thulle reorders.

---

## 4. Phases P0–P8

### Phase 0 — Freeze / measurement

| Item | Action | Why | Risk | Acceptance |
|------|--------|-----|------|------------|
| P0.1 | Lock production knobs; all bio work under `lab_profile` | Prevent regression | Low | Production 4/4 rotation regression green |
| P0.2 | Normative metric pack: rotation 4/4 ≤300 pulses (seeds 0,7,42); 0 collisions; integrity 100%; spike-rate band; guide_dependence_ratio ≥0.95 | Proves fidelity | Medium | Harness: `baseline_ecology_benchmark.py` + `@biological` gate |
| P0.3 | Doc truth table: production equations vs lab equations | Stops claim drift | Low | `model_equations.md` ↔ `LearningDynamics` byte-synced |
| P0.4 | Label mastery as non-bio curriculum | Honest ecology | Low | Default benchmark mode = `rotation` in fidelity docs |

### Phase 1 — Spec purification (dependency for all later)

| Item | Change | Why | Risk | Acceptance |
|------|--------|-----|------|------------|
| P1.1 | Reconcile `paradigm_spec` Rule 2.4 (STDP deprecated) with roadmap Phase 2 | Spec purity | Doc churn | Single normative plasticity doctrine |
| P1.2 | Fix Rule 3.3 exclusivity: either implement local block or rewrite to audit-only (match `model_equations.md`) | Claim vs code | Behavior change if blocking | Spec = code; tests updated |
| P1.3 | Deliverable docs (foundations, audit, plan) | Helbrecht handoff | Low | Paths exist, cross-linked |

**P1.3 status:** foundations, audit, plan, fidelity spec, paradigm spec, and
model equations are cross-linked and reconciled. Rule 3.3 now documents
collision auditing without a consolidator exclusivity block.

### Phase 2 — Excitatory synaptic law (highest impact)

| Item | Change | Why | Risk | Acceptance |
|------|--------|-----|------|------------|
| P2.1 | Promote `plasticity_mode=triplet` (or BCM rate equivalent) to lab default profile | Bi & Poo / Pfister–Gerstner | Slower/fragile bind | Held pattern ≤2× conductance pulses; rotation 4/4 |
| P2.2 | Replace `build_pulse_timing` with recorded L1/L2 spike times from engine clock | Causality BP2 | Timing bugs | \(\Delta t\) distribution matches stim latency, not fixed 5%/85% |
| P2.3 | Upgrade triplet to full \(r_1,r_2,o_1,o_2\) + pair/triplet amplitudes **or** adopt BCM with sliding \(\theta\) | Literature fidelity | Complexity | Frequency-dependence test (high-rate LTP) |
| P2.4 | Keep conductance mode as ablation baseline | Engineering keep | Low | Flag switch only |

### Phase 3 — Three-factor eligibility

| Item | Change | Why | Risk | Acceptance |
|------|--------|-----|------|------------|
| P3.1 | Enable dual eligibility + neuromod under lab profile | Frémaux | Over-gating | No bind pulse 1 (100 seeds); 4/4 rotation |
| P3.2 | Tie \(M_{\mathrm{error}}\) to PE-LTD only (already partial) | Local error without labels | Low | Bound mismatch does not wipe other patterns |

### Phase 4 — Inhibitory biology

| Item | Change | Why | Risk | Acceptance |
|------|--------|-----|------|------------|
| P4.1 | `plastic_ni_enabled` + iSTDP with exclusivity OFF | Vogels | Instability | Soft ecology ≥3/4 without wipe |
| P4.2 | Production path: either mature-frozen I with ablation proof **or** slow plastic I under exclusivity ON | Tenant 4 honesty | High if ON | Documented tradeoff + metrics |

### Phase 5 — Homeostasis

| Item | Change | Why | Risk | Acceptance |
|------|--------|-----|------|------------|
| P5.1 | `scaling_lab_enabled` η≤0.001; optional sensory scaling | Turrigiano | Drift | 500-pulse rates ∈[0.05,0.35]; 4/4 held |
| P5.2 | Optional BCM threshold as alternative/homeostat | Selectivity | Overlap with triplet | Ablation: BCM vs triplet |

### Phase 6 — Circuit de-engineering

| Item | Change | Why | Risk | Acceptance |
|------|--------|-----|------|------------|
| P6.1 | Default lab `descending_mode=graded` | BP9 | Slower L1I | Graded + Phases 2–5: 4/4 ≤80 pulses |
| P6.2 | Soft NI competition as primary; force-wipe optional | Emergent WTA | Multi-spike chaos | Soft 4/4 without membrane wipe |
| P6.3 | Keep force cascade as production lock until P6.2 passes | Doctrine | Low | Production unchanged until gate |

### Phase 7 — Offline consolidation

| Item | Change | Why | Risk | Acceptance |
|------|--------|-----|------|------------|
| P7.1 | Replay enabled in lab; measure pulse savings | Sleep biology | Overfitting buffer | ≥15% fewer pulses to 4/4 (10 seeds); no ownership read |

### Phase 8 — Validation gate → production promotion

| Item | Change | Why | Risk | Acceptance |
|------|--------|-----|------|------------|
| P8.1 | Promote lab profile knobs only after Phase 0 metrics | No silent bio theater | High | CI `@biological` + Abhi compare |
| P8.2 | Explicit “engineering approximations” appendix in fidelity spec | Honesty | Low | Reviewed by Tyborc later |

---

## 5. Open questions

From Dominus §8 — require Thulle / user policy before production promotion:

Resolved for this mission:

1. A certified lab stack is evaluated separately; production remains
   phenomenological.
2. Full Pfister–Gerstner triplet is primary; BCM is deferred.
3. Current-based LIF is retained; AMPA/NMDA is out of scope.
4. Soft NI/graded descending are lab-only; production force exclusivity stays.
5. Mastery stays the API default; rotation is normative for benchmarks/docs.
6. Rule 3.3 is audit-only and matches code.

---

## 6. Sources

**External**

- Bi & Poo (1998/2001); Song, Miller & Abbott (2000); Pfister & Gerstner (2006)  
- Bienenstock, Cooper, Munro (1982); Oja (1982); Turrigiano; Vogels et al. (2011); Frémaux et al.; Gerstner & Kistler  

**Internal**

- `Documents/biological_training_foundations.md`  
- `Documents/biological_alignment_audit.md`  
- `Documents/model_equations.md`, `Documents/paradigm_spec.md`, `Documents/tenants.txt`  
- `Documents/biological_fidelity_spec.md`, `Documents/biological_learning_roadmap.md`  
- `backend/cognative_paradigm/learning/`  
- `backend/cognative_paradigm/domain/lif_dynamics.py`, `eligibility_trace.py`, `dual_eligibility_trace.py`, `triplet_trace.py`  
- `backend/cognative_paradigm/simulation/wta_coordinator.py`, `pretrained_inhibitor_exclusivity.py`, `learning_dynamics.py`
