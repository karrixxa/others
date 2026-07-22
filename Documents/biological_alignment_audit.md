# Biological Alignment Audit

**Status:** Dominus-approved audit (Helbrecht document pass)  
**Date:** 2026-07-17  
**Authority:** [`biological_training_foundations.md`](biological_training_foundations.md) (BP1–BP10); codebase evidence below  
**Scope:** Production vs biology comparison. No knob flips in this document.

**Related:** [`biological_alignment_plan.md`](biological_alignment_plan.md) · [`biological_learning_roadmap.md`](biological_learning_roadmap.md)

---

## Contents

1. [Production defaults](#1-production-defaults)
2. [Comparison matrix](#2-comparison-matrix)
3. [Production vs lab (one-line)](#3-production-vs-lab-one-line)
4. [Gaps and risks (claim vs do)](#4-gaps-and-risks-claim-vs-do)
5. [What is done correctly (keep)](#5-what-is-done-correctly-keep)
6. [Evidence index](#6-evidence-index)

**Verdict legend:** `ALIGNED` | `PARTIAL` | `MISALIGNED` | `MISSING`

---

## 1. Production defaults

From `LearningDynamics` (`backend/cognative_paradigm/simulation/learning_dynamics.py`):

| Knob | Production default |
|------|--------------------|
| `plasticity_mode` | `"conductance"` |
| `lab_profile_enabled` | `False` |
| STDP / triplet / dual-eligibility / iSTDP / scaling-lab / offline / plastic-NI | **OFF** |
| `pretrained_inhibitor_exclusivity_enabled` | `True` |
| `scaling_eta` | `0` |

Lab biology ships behind flags. Production learning law is phenomenological conductance plasticity plus engineered exclusivity.

---

## 2. Comparison matrix

| Mechanism | Biology (formula/behavior) | Our implementation | Verdict | Evidence |
|-----------|----------------------------|--------------------|---------|----------|
| LIF membrane | \(\tau_m \dot u = -(u-u_r)+RI\) | Discrete leak + additive drive; reset; refractory | **ALIGNED** (current-based; params project-tuned) | `domain/lif_dynamics.py` (leak/integrate/try_spike); `Documents/model_equations.md` §1 |
| Conductance-based synapses (AMPA/NMDA/GABA) | \(g(t)(u-E_{\mathrm{rev}})\) | Additive charge drive; no reversal potentials | **MISSING** | No AMPA/NMDA/GABA in `backend/cognative_paradigm` |
| Pair STDP | \(A_\pm\exp(\pm\Delta t/\tau_\pm)\) | Lab `SpikeTimingPlasticityLearner.delta_w` matches Song-style pair rule | **PARTIAL** (lab only; timing often synthetic) | `learning/spike_timing_plasticity.py`; default mode conductance in `learning_dynamics.py` |
| STDP timing source | Measured \(t_{\mathrm{pre}},t_{\mathrm{post}}\) | `PulseSpikeTimeRecorder` captures pulse input, L1 relay, and L2 spike times from the engine clock; pulse fractions remain explicit fallback only | **ALIGNED** (lab timing path) | `simulation/pulse_spike_time_recorder.py`; `nucleus_network.py` |
| Triplet STDP | Full Pfister–Gerstner \(r_1,r_2,o_1,o_2\) + pair + triplet amps | Full four-trace event rule with \(A_2^\pm,A_3^\pm\), absolute-time decay, and frequency-dependence tests | **ALIGNED** (lab) | `domain/triplet_trace.py`; `learning/triplet_plasticity.py`; `tests/test_triplet_plasticity.py` |
| Conductance / free-energy plasticity | Not a standard published STDP/Hebb law | \(\Delta w=\eta(\theta-A_{\mathrm{inst}})S(w)\) on authentic spikers | **PARTIAL** (phenomenological; works for task; not bio STDP) | `learning/conductance_plasticity.py`; `model_equations.md` §9 |
| Classic Hebb / Oja / BCM | See foundations §2 | No BCM; no Oja PCA rule; co-active LTD claims “Oja-style” soft competition only | **MISSING** (BCM/Oja); co-active LTD **PARTIAL** | `learning/coactive_partner_depression.py`; no BCM symbols in repo |
| Heterosynaptic LTD | Inactive-afferent depression | Sites A/B/C/D soft-saturated LTD | **ALIGNED** (phenomenological rates) | `learning/heterosynaptic_depression.py`; `model_equations.md` §9.3 |
| Synaptic scaling (Turrigiano) | Multiplicative rate homeostasis | EMA toward \(\rho^*\); **production \(\eta=0\)** (frozen); lab re-enable | **PARTIAL** (lab) / production **MISALIGNED** vs living homeostasis | `learning/synaptic_scaling.py`; `learning_dynamics.py` (`scaling_eta`, `scaling_lab_*`) |
| Eligibility (calcium-like) | Spike-coincidence eligibility | Scalar edge-set match + decay; not ms coincidence | **PARTIAL** | `domain/eligibility_trace.py` |
| Dual eligibility + \(M(t)\) | Frémaux three-factor | Lab dual LTP/LTD traces + per-neuron neuromod gate | **PARTIAL** (lab; \(M\) is state proxy not DA dynamics) | `domain/dual_eligibility_trace.py`; `learning/neuromodulator_gate.py` |
| iSTDP (Vogels) | Symmetric near-coincidence potentiation plus constant depression on each inhibitory presynaptic spike: \(\Delta w_{\mathrm{pre}}=\eta(x_{\mathrm{post}}-\alpha)\), \(\Delta w_{\mathrm{post}}=\eta x_{\mathrm{pre}}\) | Lab `VogelsInhibitorySTDP` implements both trace events on clocked E/I spikes. Production NI remains deliberately frozen/saturated | **ALIGNED** (lab) / production mature-frozen engineering approximation | `learning/inhibitory_stdp.py`; `nucleus_network.py`; `learning/lab_profile.py` |
| Inhibitory turnover / assembly | PV maturation | Hot-gated turnover equations present; exclusivity path re-saturates NI | **PARTIAL** | `model_equations.md` §9.2; roadmap Phase 4 |
| WTA / lateral inhibition | Soft E/I competition | Soft path exists; **production** force NI + wipe losers to 0 | **PARTIAL** soft / **MISALIGNED** force-wipe vs emergent WTA | `simulation/pretrained_inhibitor_exclusivity.py`; `wta_coordinator.py` |
| Descending inhibition | Graded corticothalamic-like feedback | Production force E′→L1I + wipe; lab `graded` | **PARTIAL** | `simulation/descending_inhibition_mode.py`; `learning_dynamics.py` |
| Offline replay | Sleep consolidation | Lab quiescence decay + replay buffer | **PARTIAL** (lab) | `learning/offline_consolidator.py` |
| Assembly / attractor | Recurrent co-activation | Ring WTA + binding; EP assembly credit | **PARTIAL** | `learning/assembly_flow_credit.py` |
| Kohonen SOM | Neighborhood map | Not implemented | **MISSING** (acceptable; not required for bio) | — |
| Backprop / global loss | Nonlocal credit | Explicitly rejected; none found in learning path | **ALIGNED** (absence correct) | `Documents/paradigm_spec.md` Rule 3.1 / §9 |
| Label / guide teacher | External winner/symbol injection | Rotation/stochastic: no ownership read; **mastery default** reads bind to advance | **PARTIAL** (mastery is curriculum schedule, not weight teacher) | `biological_fidelity_spec.md` §5; stimulus stream / ecological purity tests |
| Binding exclusivity | Competition + local rules | Rule 3.3 and code both define cross-neuron collision as **audit-only**; one-pattern-per-neuron remains enforced | **ALIGNED** (documented audit semantics) | `paradigm_spec.md`; `eligibility_consolidator.py`; `nucleus_network.py` OWNERSHIP_COLLISION audit |

---

## 3. Production vs lab (one-line)

Production achieves **unguided pattern ownership** via phenomenological conductance LTP/LTD + eligibility + engineered exclusivity. Named lab presets provide full triplet timing, dual eligibility, Vogels iSTDP, scaling, graded soft competition, and replay; none silently replace the production law.

---

## 4. Gaps and risks (claim vs do)

| Claim (docs / tenants) | Reality | Risk |
|------------------------|---------|------|
| “Biological learning” / fidelity implemented | Phenomenological + force-I cascade; STDP deprecated in `paradigm_spec` Rule 2.4 while roadmap Phase 2–7 ships lab STDP | Spec contradiction; false bio confidence |
| Cross-neuron exclusivity | Explicitly audit-only in spec and code | Dual-bind remains observable; zero collisions is a benchmark metric |
| Synaptic scaling active | \(\eta=0\) production | No living homeostasis; thresholds hand-tuned |
| I plastic (Tenant 4) | NI / L1I saturated frozen production | E-only learning; E/I imbalance fixed by engineering |
| STDP / triplet “integrated” | Behind lab `plasticity_mode`; clock recorder with synthetic fallback | Production remains phenomenological by policy |
| Mastery = ecological | Reads bind state to advance | Guide-dependence; not strict unguided ecology |
| Triplet = Pfister–Gerstner | Full four-trace lab implementation | Requires ecology-level tuning before any promotion |
| Eligibility = three-factor | Scalar edge-set; \(M\) lab-only | Credit not spike-local |

---

## 5. What is done correctly (keep)

- No backprop  
- Event/register causality (ONE/Z)  
- Per-neuron weight ownership  
- Authentic multi-spiker plasticity (winner diagnostic-only)  
- Heterosynaptic / PE-LTD sites  
- LIF + refractory  
- Rotation unguided emergence proven by tests (`test_unguided_*`, biological integrity)

---

## 6. Evidence index

| Path | Role |
|------|------|
| `backend/cognative_paradigm/domain/lif_dynamics.py` | Current-based LIF |
| `backend/cognative_paradigm/learning/spike_timing_plasticity.py` | Pair STDP (lab) |
| `backend/cognative_paradigm/simulation/pulse_spike_time_recorder.py` | Recorded engine-clock timing + explicit fallback |
| `backend/cognative_paradigm/learning/triplet_plasticity.py` | Full triplet rule (lab) |
| `backend/cognative_paradigm/learning/conductance_plasticity.py` | Production phenomenological law |
| `backend/cognative_paradigm/learning/heterosynaptic_depression.py` | Heterosynaptic LTD |
| `backend/cognative_paradigm/learning/synaptic_scaling.py` | Scaling (η=0 production) |
| `backend/cognative_paradigm/learning/inhibitory_stdp.py` | iSTDP (lab) |
| `backend/cognative_paradigm/simulation/pretrained_inhibitor_exclusivity.py` | Force NI / wipe |
| `backend/cognative_paradigm/simulation/learning_dynamics.py` | Defaults / flags |
| `Documents/model_equations.md` | Normative equations |
| `Documents/paradigm_spec.md` | Spec claims (incl. Rule 2.4 / 3.3) |
