# Cognative Paradigm (CIPP org / Paul_Model)

**Document:** `Documents/Paper/CIPP_Summery.md`  
**Role in internship:** Flagship / final-project briefing document — the primary technical story for Cognative Paradigm  
**Authority for current production truth:** `CHECKPOINT.md` + `ProductionForceCascadeDefaults` (prefer over stale narrative docs)  
**Branch / HEAD:** `Paul_Model` @ `7630733` (2026-07-21) · force-cascade ship `026616c`  
**Scope:** Project identity, biological paradigm vs today’s AI (especially CNNs), architecture, learning doctrine, hardware outlook, status, and operator pointers — **not** a promotion authorization for lab biology, and **not** a claim of current wall-clock superiority over GPU CNNs on conventional hardware.

---

## 1. Title / meta

| Field | Value |
|-------|--------|
| Document name | **CIPP_Summery.md** (intentional spelling: Summery) |
| Product name | **Cognative Paradigm** (intentional spelling: Cognative) |
| Dual title | Cognative Paradigm (CIPP org / Paul_Model) |
| Local workspace | `/home/prodrig/Documents/Paradigm_New` |
| Active branch | `Paul_Model` |
| Tip commit | `7630733` |
| Force-cascade ship | `026616c` |
| Period covered | 2026-07-04 → 2026-07-21 |
| Commits at tip | **73** |
| `main` freeze | `d0ba6c3` (2026-07-10); Paul_Model ~**31** ahead |
| Active remote | Faraday `git@faraday.lps.umd.edu:cipp/cipp-learning.git` |
| Package / API | `cognative_paradigm` (FastAPI) |
| Proposal contrast | Biological event-based CIPP model vs today’s CNN / dense deep-learning stack |

---

## 2. Introduction

**Cognative Paradigm** is the internship’s flagship product and the centerpiece of the final project proposal. It is an original *thinking / learning* workspace: a small, biologically flavored spiking system that learns a fixed visual catalog through **local competition and local plasticity** — without backpropagation, without a global loss function, and without a guided “bind gate” that forces the answer into existence.

The proposal story is not “we beat ImageNet.” It is:

> Today’s dominant AI — especially **CNN frameworks** — is extremely successful on dense matrix hardware (GPUs), but it learns and computes in a way that is far from biology. Cognative Paradigm is a **working miniature of a different paradigm**: sparse causal events (**1 vs Z**), local conductance learning, excitatory/inhibitory pathways, refractory timing, and emergent symbols. The long-term claim is that a **true biological CIPP model**, running on **hardware built for spikes and local updates**, can eventually be **faster and more reliable** for continuous, event-driven learning than forcing biology-shaped algorithms through von Neumann / GPU pipelines.

**What the system does today (software reality).**  
A catalog of four **center-cell 3×3** shapes — **H1, V1, D0, D1** — is presented by an auto-stim “retinal gate.” Sensory edges that fire as **ONE** drive **Layer 1** E/I relay pairs. Those relays feed a **nucleus**: four ring excitatory competitors plus a central inhibitory neuron (**NI**). The winner updates **its own** conductances and eligibility traces. When eligibility and weight evidence consolidate, the network binds the pattern and emits an emergent symbol **`sigma_k`**. At equilibrium the system owns **4/4** shapes — one pattern per ring neuron.

**What the system is building toward.**  
A biologically honest computational substrate: information only when something *fires*; silence is **Z** (not a numeric zero that still burns FLOPs in a dense layer); learning stays at the synapse/neuron; prediction and ownership emerge from dynamics. That substrate is simulated today in Python/FastAPI so we can *see* and *test* it. The proposal argues that the same paradigm, mapped onto neuromorphic or other spike-native hardware, is the path to speed and reliability at scale — not by making a bigger CNN.

**Where it lives.**  
Faraday organization **CIPP**, repo **`cipp/cipp-learning`**, branch **`Paul_Model`**, local folder **`Paradigm_New`**. Frontend Vite + Three.js; backend package **`cognative_paradigm`**. Normative docs: `tenants.txt`, `paradigm_spec.md`, `model_equations.md`, `biological_fidelity_spec.md`. Production handoff: **`CHECKPOINT.md`**.

**Briefing takeaway (one sentence).**  
Cognative Paradigm demonstrates a tenant-driven, event-based biological learning loop on a four-shape catalog, contrasts that loop with today’s CNN training paradigm, and positions spike-native hardware as the eventual route to a faster, more reliable true CIPP system.

---

## 3. Naming (keep short)

| Name | Meaning |
|------|---------|
| **Cognative Paradigm** | This product (intentional spelling: Cognative) |
| **Paul_Model** | Faraday development branch |
| **Paradigm_New** | Local workspace folder only |
| **CIPP** | Faraday org / `cipp-learning` family name — not a synonym for “CNN competitor” |
| **Path P** | **Production** nucleus path (force exclusivity cascade) — default demo |
| **Path H** | Hybrid cortical **lab** column — labeled control only |

Early internship Paradigm folders (`Paradigm_Project`, `Paradigm_Fixed`) led into this productized CIPP phase. Sibling research on the same Faraday repo may exist; this briefing’s contrast target is **today’s CNN / dense deep-learning stack**, not internal sibling branches.

---

## 4. Biological paradigm vs today’s CNN frameworks

This section is the proposal’s conceptual core. Be precise: we claim an **architectural and energetic direction**, not a current benchmark win on GPUs.

### How today’s CNN frameworks typically work

Modern computer vision is dominated by **convolutional neural networks** (and denser successors) trained with **backpropagation** on **batched** data:

- **Dense activation.** Layers compute continuous activations for (almost) every unit every forward pass. “Silence” is still a number — often zero — that participates in matrix multiplies.
- **Global learning.** A loss at the output (cross-entropy, etc.) produces gradients that flow backward through the entire graph. Weight updates are coordinated by a **central optimizer** (SGD, Adam) with global learning-rate schedules.
- **Batch / offline culture.** Training usually assumes large labeled datasets, shuffled minibatches, and many epochs. Inference is a separate mode after training freezes.
- **Hardware fit.** The paradigm maps brilliantly onto **GPUs/TPUs**: dense GEMM/convolution kernels, high throughput for predictable, synchronous workloads. Reliability at scale comes from engineering (normalization, residual links, huge data) more than from biological constraints.
- **Cost of biology-shaped ideas on this stack.** If you implement spikes or sparse events *naïvely* on a GPU, you often still pay dense-like costs (padding, masking, irregular memory), so the biological *idea* does not automatically buy biological *efficiency*.

CNNs are the right tool for many problems **on current hardware**. Cognative Paradigm is arguing for a **different computational contract**, not pretending a four-shape toy replaces ResNet tomorrow.

### How Cognative Paradigm (biological CIPP model) works instead

Grounded in `Documents/tenants.txt` and `paradigm_spec.md`:

| Dimension | Typical CNN framework | Cognative Paradigm (Path P) |
|-----------|----------------------|-----------------------------|
| Information unit | Dense float activations | Causal event **1**; silence is **Z** (not transmitted, not plastic) |
| Learning rule | Global backprop + optimizer | **Local** conductance / eligibility at the neuron that fired |
| Teacher | Labeled loss over batches | Competition + consolidation; symbols **emerge** (`sigma_k`) |
| Connectivity | Shared conv filters, dense layers | Explicit **E and I** pathways, refractory timing, WTA nucleus |
| Time | Layer-synchronous forward/backward | Pulse / tick dynamics; leaky integrate-and-fire membranes |
| Pattern ownership | Implicit in weight matrices | Explicit bind: **one pattern per neuron** at equilibrium |
| Continuous learning | Usually retrain / fine-tune offline | Designed for **ongoing** catalog learning until 4/4 equilibrium |
| Shortcut policy | Data augmentation, big models | **No** bind gate, no global gradient, no injected winners from auto-stim |

**Reliability (conceptual).** In a CNN, reliability often means “low error on a test distribution” after centralized training. In Cognative Paradigm, reliability is framed as **tenant honesty**: exclusivity (force cascade), local ownership, prediction match vs `PREDICTION_ERROR`, and test-locked production defaults so demos do not silently cheat. That is a different reliability story — closer to “the organism’s rules still hold under competition” than “top-1 accuracy on ImageNet.”

**Speed (conceptual, today vs eventual).**  
- **Today:** the model runs as a **software simulation** on conventional CPUs (FastAPI backend). It will **not** outrun a tuned CNN on a GPU for large vision tasks; that comparison is the wrong scoreboard.  
- **Eventually:** a **true biological CIPP model** — the same event-driven, local-update rules — mapped onto **hardware that only works when spikes happen** (neuromorphic / event-based fabrics, or other spike-native designs) can avoid paying for silence, avoid global backward passes, and update only the synapses that participated. That is the path to being **faster and more energy-reliable** than simulating biology on dense accelerators.

### Why hardware matters for the proposal

Biology is not slow because “neurons are slow algorithms.” Biology is efficient because **computation and memory are co-located**, updates are **local**, and **inactive tissue costs little**. CNNs win on GPUs because they match **dense, synchronous, global-gradient** math.

Proposal position:

1. **Software CIPP (now)** — prove the learning loop, tenants, and demos on Path P (`Paul_Model` @ `7630733`).  
2. **Paradigm clarity** — show, against CNN frameworks, *what changes* when you refuse backprop and dense activations.  
3. **Hardware thesis** — with correct spike-native / local-plasticity hardware, the same paradigm can scale toward systems that are **faster and more reliable** for continuous, event-driven learning than porting biological rules into CNN toolchains.

Do **not** claim we have already built that hardware. Claim we have built the **algorithmic and demo substrate** that makes the hardware thesis meaningful.

---

## 5. Framework (system reality)

### Stack (simulation platform)

| Layer | Technology |
|-------|------------|
| Frontend | Node.js, **Vite**, **Three.js** — workspace UI + population rasters |
| Backend | Python **FastAPI** + uvicorn; package **`cognative_paradigm`** |
| Environment | Conda (`paradigm_env` and/or `cognative_paradigm_env`) |
| CI / locks | GitLab CI; `test_production_defaults_lock.py` and related |

### Path P (production) vs Path H (lab)

**Path P** is the briefing default: catalog auto-stim → Layer 1 E/I relays → four-ring + NI nucleus → eligibility + conductance binding → emergent `sigma_k` → 4/4 equilibrium. Production exclusivity is the **force cascade** (L2E spike → force NI → wipe other L2E → same-tick L1 E′ → force L1 I). Locked knobs: exclusivity ON, `descending_mode=force`, autonomy OFF, `l2_to_l1_i_gain=0.26`, `plasticity_mode=conductance`, `column_architecture_profile=compatibility`.

**Path H** (`hybrid_cortical` / `hybrid_cortical_biological`) is **lab only** — soft race, graded descending, Stage 14 autonomy, bio roadmap stages. Never present Path H as the production biological claim in a final proposal unless explicitly labeled as control.

### Production signal flow

```
Catalog auto-stim (H1 / V1 / D0 / D1)
  → Input edges register ONE (silence = Z)
  → Layer 1 E/I pairs + lateral inhibition
  → Nucleus ring WTA (4 E + central NI)
  → Eligibility + conductance binding on winner
  → Emergent sigma_k + pattern ownership
  → Equilibrium at 4/4
```

### Workspace UI

Three columns: Input (auto-stim, reset, unbind, Recognition Lab) · 3D Layer 1 + nucleus · Nucleus ring cards + rasters. Rasters also on port **5174** (`npm run dev:rasters`).

---

## 6. Tenants and production doctrine

**Purpose.** Demonstrate unguided, biologically flavored learning on a minimal catalog: winners, symbols, and ownership emerge from competition and local plasticity — not from a guided bind gate and not from a global CNN-style optimizer.

**Tenants (paraphrased from `tenants.txt`).** (1) Firing is causal; not firing is **Z**. (2) Fire together, wire together. (3) Local learning; one pattern per neuron. (4) Separate E/I pathways. (5) Refractory period. (6) 1:1 symbol to representation. (7) Continuous learning. (8) Prediction. (9) No global teacher — only information from local connections.

**Binding.** Eligibility trace + weight evidence (backend consolidation weight threshold **0.28**; prefer `learning_dynamics.py` over older narrative “~0.25”). Recognition Lab probes without learning.

**Hard briefing rules.** Do not claim lab biology is production. Soft/graded/autonomy = labeled control. Autonomy cannot combine with force/exclusivity. This document does not authorize lab→production promotion. Do not claim current software CIPP is faster than GPU CNNs on large vision tasks.

---

## 7. Chronological progress (proposal timeline)

| Era | Theme | Dates | Briefing note |
|-----|--------|-------|---------------|
| **0** | Bootstrap | 2026-07-04 | Paul_Model scaffold on Faraday CIPP |
| **1** | Workspace + nucleus | 2026-07-05 | Nucleus / ring foundations |
| **2** | UI + Recognition Lab | 2026-07-06–07 | Interactive demo surface |
| **3** | Biological flat path | 2026-07-08–09 | Eligibility / conductance direction |
| **4** | Robustness + `main` freeze | 2026-07-10 | `main` @ `d0ba6c3` |
| **5** | Unguided / integrity | 2026-07-13–15 | Mastery stimulus; integrity probes |
| **6** | Bio roadmap (lab) | 2026-07-16–17 | Lab phases — not production claims |
| **7** | Hybrid cortical lab | 2026-07-20 | Path H Stages — labeled control |
| **8** | Production force restore | 2026-07-21 | Force cascade + rasters; tip `7630733` |

**Arc:** prove a biological learning loop in software → lock a demoable Path P → use that substrate to argue the CNN contrast and the hardware thesis.

---

## 8. Major capabilities (what we can show)

Interactive workspace (3D + ring cards), auto-stim without injected winners, Recognition Lab, population rasters, learning-dynamics API, checkpoint/reset/unbind, production lock tests, and (optionally, labeled) lab Path H contrasts. These are **demo evidence for the paradigm**, not ImageNet scorecards.

---

## 9. Where we are / proposal status

**Verdict (2026-07-21):** Production Path P is the **force exclusivity cascade** at tip **`7630733`**. Lab paths remain labeled control.

**What the final project proposal should claim**

1. **Problem** — Dominant AI (CNN frameworks) is optimized for dense GPU math, not for biological event-driven learning; we need a credible alternate paradigm and a path to hardware that matches it.  
2. **Approach** — Cognative Paradigm: 1 vs Z causality, local conductance/eligibility learning, L1 relays + four-ring nucleus, emergent `sigma_k` on a four-shape catalog.  
3. **System delivered** — Full-stack Path P demo on Faraday `Paul_Model`, test-locked production doctrine.  
4. **CNN contrast** — Dense backprop vs sparse causal events and local updates (see §4).  
5. **Hardware thesis** — A true biological CIPP model on spike-native / local-plasticity hardware can eventually be **faster and more reliable** for continuous event-driven learning than simulating biology inside CNN toolchains.  
6. **Evidence now** — 4/4 equilibrium under production defaults, Recognition Lab, rasters, production lock suite.

**What not to claim without new evidence**

- Current software CIPP beats GPU CNNs on large benchmarks or wall-clock throughput.  
- Lab biology already *is* production.  
- Neuromorphic hardware already shipped for this product.  
- That this Paper document authorizes lab→production promotion.

**Suggested next (CHECKPOINT-aligned; not implementation orders)**  
Live UI smoke under production rasters; residual labeled-control lab work; threshold UI/backend drift polish; hardware-facing roadmap discussion for the proposal (architecture requirements for spike-native CIPP) — separate from promoting Path H.

---

## 10. How to run / verify

```bash
# API
cd /home/prodrig/Documents/Paradigm_New/backend
conda run -n paradigm_env --no-capture-output \
  uvicorn cognative_paradigm.api.main:app --reload --port 8000 --host 127.0.0.1

# Workspace UI → http://127.0.0.1:5173
cd /home/prodrig/Documents/Paradigm_New/frontend && npm run dev

# Population rasters → http://127.0.0.1:5174
npm run dev:rasters
```

```bash
cd backend && PYTHONPATH=. conda run -n paradigm_env python -m pytest \
  tests/test_production_defaults_lock.py \
  tests/test_pretrained_inhibitor_exclusivity.py \
  tests/test_emergent_autonomy.py \
  tests/test_secondary_l1e_descending.py \
  tests/test_graded_descending_ecology.py -q

cd frontend && node --test src/app/charts/rasterCharts.test.js
```

Env names: `paradigm_env` (CHECKPOINT) and `cognative_paradigm_env` (`environment.yml`) both appear — use whichever is installed. See also `checkpoints/CONTINUE-TOMORROW.md`.

---

## 11. Source appendix

| Path | Role |
|------|------|
| `CHECKPOINT.md` | Production handoff / doctrine |
| `Documents/tenants.txt` | Constitutional tenants |
| `Documents/paradigm_spec.md` | Formal spec (event-based, no backprop) |
| `Documents/model_equations.md` | Equations |
| `Documents/biological_fidelity_spec.md` | Fidelity / removed shortcuts |
| `Documents/system_overview.md` | Layer narrative |
| `Documents/grid_and_layers_research.md` | LIF vs binary ANN notes |
| `Documents/biological_training_foundations.md` | Bio training principles vs global BP |
| `backend/.../learning_dynamics.py` | `ProductionForceCascadeDefaults` |
| `backend/tests/test_production_defaults_lock.py` | Production lock |
| Faraday `cipp/cipp-learning` · `Paul_Model` | Source remote |
| `Internship_Summery.md` | Earlier internship context |

**Active remote:** `git@faraday.lps.umd.edu:cipp/cipp-learning.git`

---

*End of CIPP_Summery. Filename spelling intentional. Prefer `CHECKPOINT.md` when production knobs disagree. This Summery supports final-project briefing: biological CIPP vs CNN frameworks, plus a hardware thesis for eventual speed and reliability — it does not claim current GPU-beating performance or authorize lab→production promotion.*
