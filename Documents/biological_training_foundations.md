# Biological Training Foundations

**Status:** Normative research baseline (Dominus-approved)  
**Date:** 2026-07-17  
**Authority:** Triad research summary; external neuroscience consensus cited in §7  
**Scope:** Formulas and unguided neuron-level learning criteria. Not an implementation plan.

**Related:** [`biological_alignment_audit.md`](biological_alignment_audit.md) · [`biological_alignment_plan.md`](biological_alignment_plan.md) · [`biological_learning_roadmap.md`](biological_learning_roadmap.md)

---

## Contents

1. [Neuron-level dynamics](#1-neuron-level-dynamics)
2. [Unguided local learning rules](#2-unguided-local-learning-rules)
3. [Network-level unguided organization](#3-network-level-unguided-organization)
4. [Definition: unguided neuron-level learning](#4-definition-unguided-neuron-level-learning)
5. [Biological plausibility checklist (BP1–BP10)](#5-biological-plausibility-checklist-bp1bp10)
6. [True biological training in a computer system](#6-true-biological-training-in-a-computer-system)
7. [Sources](#7-sources)

---

## 1. Neuron-level dynamics

### 1.1 Current-based LIF

Membrane (continuous):

\[
\tau_m \frac{du}{dt} = -(u - u_{\mathrm{rest}}) + R\,I(t)
\]

Discrete leak + drive:

\[
u \leftarrow \lambda u + \rho + D,\quad
\lambda = 1 - \frac{\Delta t}{\tau_m},\quad
\rho = u_{\mathrm{rest}}\frac{\Delta t}{\tau_m}
\]

**Spike / refractory / reset:** if \(u \ge \theta\) and not refractory → emit spike, \(u \leftarrow u_{\mathrm{reset}}\), refractory for \(R\) steps.

This is the consensus discrete form used in many SNN engines and matches Paradigm’s current-based membrane update.

### 1.2 Conductance-based LIF (biophysical standard)

Not required for every engineering system, but the biophysical default:

\[
C\frac{du}{dt} = -g_L(u-E_L) - g_{\mathrm{AMPA}}(u-E_{\mathrm{AMPA}}) - g_{\mathrm{NMDA}}(u-E_{\mathrm{NMDA}}) - g_{\mathrm{GABA}}(u-E_{\mathrm{GABA}})
\]

Synaptic conductances typically jump on spike and decay exponentially (AMPA fast; NMDA voltage-gated; GABA inhibitory). **This form is not present in the Paradigm codebase** (additive charge drive only).

---

## 2. Unguided local learning rules

| Rule | Canonical form | Role in unguided learning |
|------|----------------|---------------------------|
| **Classic Hebb** | \(\Delta w_{ij} \propto x_j y_i\) | Co-activation strengthens; unstable without normalization |
| **Oja** | \(\Delta w_{ij} = \eta y_i(x_j - y_i w_{ij})\) | Normalized Hebb; PCA-like; weight growth bounded |
| **BCM** | \(\Delta w_{ij} = \eta x_j\, y_i(y_i - \theta_i)\), \(\theta_i\) slides with \(\langle y_i^2\rangle\) | Selectivity via sliding threshold (Bienenstock, Cooper, Munro 1982) |
| **Pair STDP** (Bi & Poo; Song et al. 2000) | \(\Delta t = t_{\mathrm{post}}-t_{\mathrm{pre}}\): \(\Delta w = A_+\mathrm{e}^{-\Delta t/\tau_+}\) if \(\Delta t>0\); \(\Delta w = -A_-\mathrm{e}^{\Delta t/\tau_-}\) if \(\Delta t<0\) | Causal pre→post LTP; reverse LTD; typically \(\tau_\pm\sim 10{-}20\,\mathrm{ms}\) |
| **Triplet STDP** (Pfister & Gerstner 2006) | Traces \(r_1,r_2\) (pre), \(o_1,o_2\) (post). At \(t_{\mathrm{pre}}\): \(w \leftarrow w - o_1[A_2^- + A_3^- r_2]\). At \(t_{\mathrm{post}}\): \(w \leftarrow w + r_1[A_2^+ + A_3^+ o_2]\). | Frequency-dependent LTP/LTD; rate equivalent ≈ BCM |
| **Synaptic scaling** (Turrigiano) | Multiplicative \(w \leftarrow w\cdot(1+\eta(\rho^*-\bar{r}))\) or \(w\leftarrow w\cdot\rho^*/\bar{r}\) | Homeostatic rate set-point; slow, global-to-cell, local to synapses of that cell |
| **Heterosynaptic depression** | Active path LTP + mild LTD on inactive co-afferent synapses | Competitive sparse coding without labels |
| **iSTDP** (Vogels et al. 2011) | For an inhibitory \(I\!\rightarrow\!E\) synapse with decaying traces: at an inhibitory presynaptic spike, \(\Delta w=\eta(x_{\mathrm{post}}-\alpha)\); at an excitatory postsynaptic spike, \(\Delta w=\eta x_{\mathrm{pre}}\), typically with \(\alpha=2\rho_0\tau\) | Symmetric near-coincidence potentiation plus constant depression on inhibitory presynaptic spikes drives postsynaptic firing toward target rate \(\rho_0\) and establishes detailed E/I balance |
| **Eligibility + three-factor** (Frémaux / neoHebbian) | Synaptic eligibility \(e_{ij}\) from local spike coincidence; \(\Delta w_{ij} \propto e_{ij}\, M(t)\) | \(M(t)\): local neuromodulator (DA/ACh-like), **not** an external label vector |
| **Backprop** | Global error through arbitrary graph | **Not** biologically local/causal at synapses; **rejected** as primary bio training |

---

## 3. Network-level unguided organization

- **WTA / lateral inhibition:** sparse coding via E competition + I; assemblies form as attractors of co-active neurons.
- **Assembly / attractor dynamics:** repeated co-activation + recurrence → stable ensembles.
- **Kohonen SOM:** computational cousin (neighborhood + winner); biologically distant (global neighborhood schedule). Acceptable to omit for bio fidelity.
- **Sleep / offline consolidation:** replay of recent activity during quiescence; eligibility/weight consolidation without new sensory labels (Diekelmann & Born; hippocampal–cortical replay literature).

---

## 4. Definition: unguided neuron-level learning

Weight change depends only on:

1. Local pre/post spikes or rates  
2. Optionally local neuromodulator / calcium eligibility  
3. Homeostatic feedback from the cell’s own activity  

**Forbidden as learning signals:** teacher labels, global loss, nonlocal credit through deep graphs.

Stimulus **schedule** may present patterns (ecological input). The network must not inject winners, weights, or symbols as the learning rule.

---

## 5. Biological plausibility checklist (BP1–BP10)

| ID | Criterion | Pass condition |
|----|-----------|----------------|
| BP1 | **Locality** | \(\Delta w\) uses only pre, post, and optionally local \(M\) / cell-rate |
| BP2 | **Causality / timing** | Updates respect spike order or biologically motivated traces |
| BP3 | **Online** | Continuous updates; no batch global optimizer |
| BP4 | **Spike- or rate-analog** | Events or rates with clear bio analogs |
| BP5 | **No global backprop** | No error derivatives through arbitrary graphs |
| BP6 | **No label teacher as learning signal** | Stimulus schedule may present patterns; must not inject winners/weights/symbols |
| BP7 | **E and I plasticity** | Inhibitory synapses learn or are justified as mature/frozen with lab ablation |
| BP8 | **Homeostasis** | Long-run rates bounded without hand-tuning every threshold |
| BP9 | **Competition emerges from E/I** | Soft lateral/central inhibition preferred over procedural membrane wipe / force-fire |
| BP10 | **Credit assignment** | Eligibility + local \(M\); not sole aggregate free-energy heuristics |

Production systems may use **phenomenological** approximations. Claiming “true bio alignment” requires BP1–BP10 as the bar for **must-fix** vs **engineering keep** (see alignment plan).

---

## 6. True biological training in a computer system

A computer SNN is “true biological training” when:

- Synaptic updates are local and causal (BP1–BP2, BP5–BP6).  
- Learning is online and event/rate-analog (BP3–BP4).  
- Both E and I pathways can adapt or are explicitly frozen with ablation honesty (BP7).  
- Homeostasis and competition arise from physiology, not procedural force (BP8–BP9).  
- Credit uses eligibility ± local neuromodulation, not a global teacher (BP10).

Phenomenological rules that solve a catalog task without satisfying BP2/BP7–BP10 are **engineering success**, not biological training.

---

## 7. Sources

**External**

- Bi & Poo (1998/2001) — experimental STDP windows  
- Song, Miller & Abbott (2000) — competitive pair STDP  
- Pfister & Gerstner (2006) — triplet STDP  
- Bienenstock, Cooper, Munro (1982) — BCM  
- Oja (1982) — normalized Hebb  
- Turrigiano — synaptic scaling  
- Vogels et al. (2011) — inhibitory STDP / E–I balance  
- Frémaux et al. — neoHebbian three-factor / eligibility  
- Gerstner & Kistler — LIF / neuronal dynamics  

**Internal**

- `Documents/model_equations.md`  
- `Documents/biological_fidelity_spec.md`  
- `Documents/biological_learning_roadmap.md`  
- `Documents/paradigm_spec.md`, `Documents/tenants.txt`  
- `backend/cognative_paradigm/domain/lif_dynamics.py`  
- `backend/cognative_paradigm/learning/` (plasticity modules)
