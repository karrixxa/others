# Three-Way Comparison — SNN Research vs Early Scaffold vs Cognative Paradigm

**Date:** 2026-07-10  
**Purpose:** Situate three related codebases that attack the same toy problem: learn line patterns on a 3×3 grid with from-scratch spiking neurons (LIF, signed E/I, WTA, local plasticity, no backprop).

| Repo / snapshot | Typical path | Role |
|-----------------|--------------|------|
| **Abhi SNN / CIPP** | `~/Documents/SNN` or Faraday `cipp-learning` branch `AbhiCIPP` | Mature research platform |
| **Early Paul scaffold** | Historical `cipp-learning` bootstrap (`core.py`, `GridMatcher`) | First runnable skeleton (~4 files) |
| **Cognative Paradigm** | `Paradigm_New` / Faraday `Paul_Model`, prodserver `main` | Productized learning workspace (current) |

All three share **tenant DNA** (`Documents/tenants.txt`): 1 vs Z event causality, no backprop, local plasticity, emergent or assigned representation. They differ in **maturity**, **architecture**, and **honesty about what is learned vs wired**.

---

## The shared scientific question

> Can a spiking network assign each visual line (row, column, diagonal) to a dedicated internal representation **without** a teacher hardcoding “neuron 3 = vertical line”?

- **Abhi SNN:** Yes, in principle — mapping should **emerge** from competition and plasticity (8-pattern scale; interleaved ownership still open).
- **Early scaffold:** No — `GridMatcher` assigns patterns to neuron indices by hand; demos are deterministic lookups.
- **Cognative Paradigm:** Yes — eligibility/consolidation + local exclusivity; proven **4/4** on the center-cell catalog; interleaved **4/4** with ecological rotation and robustness stack.

---

## Side-by-side at a glance

| Dimension | Abhi SNN / CIPP (`AbhiCIPP`) | Early Paul scaffold | **Cognative Paradigm (Paul_Model, 2026-07)** |
|-----------|------------------------------|---------------------|-----------------------------------------------|
| **Size / stage** | ~50+ files; `neuron_flexible.py` ~54KB / ~1000 lines | ~4 core files; `core.py` ~140 lines | Full stack: backend + frontend + docs + 166+ tests |
| **Maturity** | Deep research; many iterations & ablations | “Does the pipe run?” | Production learning workspace; robustness Phases 1–6 |
| **Catalog** | **8** line primitives (3 rows, 3 cols, 2 diags) | **8** (hard-wired in matcher) | **4** center-cell shapes (`H1`, `V1`, `D0`, `D1`) |
| **Architecture** | L1E/L1I → L2E integrators → shared L2I; multi-layer column | Flat: 8 neurons, one per shape | L1 E/I pairs → 4 ring E + **central I (NI)**; delayed descending + ring feedback |
| **Pattern→neuron** | Emergent (research goal) | **Assigned in code** (`GridMatcher`) | Emergent bind; `PatternMemorySnapshot` read-only |
| **Learning** | Signed-spike, confidence, loser depression, homeostasis, turnover, flow-rate | **None** — weights static | Conductance plasticity, eligibility, consolidation, optional robustness modes |
| **Symbols** | Catalog lines ≈ neuron roles | N/A | Emergent `sigma_k` (not `H1`/`V1` labels) |
| **Time model** | Dense discrete steps; exc flow-rate **default** | Wall-clock `time.time()` for leak | Discrete auto-stim pulses; optional **SimulationClock** + flow traces |
| **Interleaved multi-pattern** | Weak: 4–6 winners / 8; documented open problem | N/A (no learning) | **4/4** under rotation with robustness stack + descending/capture fixes; **~1–2/4** legacy discrete rotation |
| **Single held pattern** | Strong consolidation + L2I rhythm | Deterministic match | Strong; 4/4 equilibrium tests |
| **Tooling** | FastAPI + Three.js, ablation harness, many test scripts | Minimal `web_demo`, no tests | Workspace UI, rasters, checkpoints, Recognition Lab, e2e |
| **Rigor / audits** | Equation spec ↔ `neuron_flexible.py`; honest README on dominance | Tenants listed; not implemented | `model_equations.md`, `learning_integrity.py`, invariant stress harness |
| **Honesty about results** | README: ~0.34 sustained dominance; stage-4 tiling collapse | Demos “work” via hand wiring | Tests document discrete vs robust interleaved gap |

---

## Architecture (conceptual)

### Abhi SNN / CIPP

```
3×3 pixels → L1 E/I encoders → L2E competitors → shared L2I
                    ↑______________________________|
              learned inhibitory gates, same-tick or flow-rate paths
```

- Rich inhibitory plasticity (turnover, optional flow-rate drain).
- **Risk:** `l1i_immediate_relay`, signed OFF depression, `eta_loss=10` — strong on one held line, fragile on switch/interleave.

### Early Paul scaffold

```
3×3 grid → GridMatcher → pick neuron index 0..7 → spike display
```

- No layers, no plasticity, no ownership — a **UI proof**, not a learning system.

### Cognative Paradigm (current)

```
Catalog pattern (3 edges) → L1 E relay (+ L1 I integrator via delayed L2→L1)
         → 4 ring E (per-neuron sensory + relay maps) → WTA + central I
         → eligibility / bind → sigma_k; local exclusivity enforces 1:1
```

- **1-tick delays** on descending inhibition and ring feedback (biological synaptic delay analogue).
- **NI** charged from mean ring pool + winner relay collateral (not winner membrane alone).

---

## Learning & binding philosophy

| Mechanism | Abhi SNN | Early scaffold | Cognative Paradigm |
|-----------|----------|----------------|---------------------|
| Hebbian / local rules | Signed-spike, confidence consolidation | — | Conductance free-energy on winner’s own synapses |
| Loser handling | Depression on FF gates (`eta_loss`) | — | Membrane suppress + delayed feedback; **no** OFF-pixel depression |
| Bind gate | Competition + weights | Hardcoded index | Eligibility + weight evidence + local exclusivity |
| Ownership map | Implicit / collision-prone | Explicit cheat | **`PatternMemorySnapshot`** read-only |
| Inhibitory learning | Turnover on E→I gates (sophisticated) | — | Central channels: saturating or **turnover** (Phase 3) |
| E→I maturation | Assembly flow credit (L2I rhythm) | — | Assembly credit on NI + descending (Phase 4) |

---

## Time & robustness (2026-07 status)

Cognative Paradigm adopted Abhi’s **time physics** in layered defaults (temporal integration **on** by default):

| Phase | Feature | Abhi | Paradigm (Paul_Model) |
|-------|---------|------|------------------------|
| 1 | SimulationClock, inter-pulse leak, sustained volley | Dense `input_period` | `temporal_integration_enabled` (default ON) |
| 2 | Excitatory flow-rate + lazy advance | Default ON | `excitatory_flow_rate_enabled` (default ON) |
| 3 | Inhibitory turnover on central→loser channels | Default ON | `inhibitory_turnover_enabled` (default ON) |
| 4 | Assembly flow credit on E→I | Opt-in | `assembly_flow_credit_enabled` (default ON) |
| 5 | Inhibitory flow-rate drain | Opt-in | `inhibitory_flow_rate_enabled` (default ON) |
| 6 | Interleaved stress tests | Open at 8 patterns | **`test_interleaved_robustness.py`** — 4/4 robust, ~1–2/4 legacy discrete |

**Phase 6 finding (verified 2026-07-10):** True catalog rotation (H1→V1→D0→D1→…) with **legacy discrete** dynamics often binds **only the first pattern** (sometimes two after cross-pattern descending protection). With the **full robustness stack** plus **cross-pattern descending** (skip shared-center suppression when the prior pulse was a different line) and **unbound capture gain** (boost relay drive when only free ring slots compete), rotation reaches **4/4 unique owners in ~38 pulses** (seeds 0/7/42; see `tests/test_interleaved_robustness.py`). Backend regression: **194 tests** pass on `Paul_Model`.

UI: Parameters overlay → **Robustness (time & flow)** toggles and sliders.

---

## What each codebase is *for*

| If you need… | Use |
|--------------|-----|
| Maximum biological knobs, 8-pattern stress, plasticity research | **Abhi SNN / `AbhiCIPP`** |
| Fastest “does spike + grid + UI work?” | Early scaffold (historical only) |
| Reliable 4-shape learning, ownership audits, product demo, checkpoints | **Cognative Paradigm** |
| Interleaved 4/4 without hand assignment | Paradigm + **robustness stack** |
| Interleaved 4/4 emergent assignment (unguided) | **Solved** at 4-pattern scale (`test_unguided_exclusivity.py`, ecological rotation) |
| Interleaved 8/8 (Abhi scale) | Open problem in Abhi’s repo — **not a Paradigm goal** |

---

## Evolution story (how the three relate)

```text
Early Paul scaffold          Cognative Paradigm (Paul_Model)         Abhi SNN / CIPP
──────────────────          ───────────────────────────────         ───────────────
GridMatcher cheat     →     Real L1/L2 + plasticity + ownership  ←  Same research lineage
No learning                 4-shape catalog + tests + UI               8-shape + equation lab
Wall-clock time             Discrete pulses + optional flow modes      Dense steps + flow default
```

The scaffold was a **bootstrap**, not the destination. **Paradigm_New** is the intentional middle path: stricter binding doctrine than Abhi’s open 8→8 assignment, smaller catalog, full test/integrity pipeline — while **importing** Abhi’s temporal and inhibitory sophistication where tenants allow.

---

## Safe to borrow vs reject (cross-repo)

Detailed tables live in `Documents/cipp_comparison_strengths_weaknesses.md`. Short version:

**Adopted in Paradigm (tenant-safe):** exc flow-rate, simulation clock, sustained volley, inhibitory turnover, assembly credit, inhibitory flow-rate.

**Reject for Paradigm:** signed-spike OFF depression, `eta_loss=10` loser depression, `l1i_immediate_relay`, global weight budgets, `lasting_inhibition`, hand-assigned `GridMatcher` mapping.

---

## Summary matrix

| | Abhi SNN / CIPP | Early scaffold | Cognative Paradigm |
|--|-----------------|----------------|---------------------|
| **Best at** | Continuous dynamics, I-plasticity depth, 8-pattern ambition | Runnable demo with zero setup | Ownership, bind audits, 4/4 equilibrium, product + tests |
| **Worst at** | Stable interleaved 8→8, cold-start on switch, L1I relay default | Not a learning system | Smaller catalog by **design** (4 shapes); not pursuing 8-pattern scale |
| **Convergence** | — | Superseded by Paradigm | Borrow Abhi **time + I physics**; keep **ownership, eligibility, delays, symbols** |

---

## Related documents

| Document | Content |
|----------|---------|
| `Documents/cipp_comparison_strengths_weaknesses.md` | Paradigm ↔ AbhiCIPP pairwise strengths/weaknesses + adoption order |
| `Documents/system_overview.md` | One-page Paradigm architecture |
| `Documents/model_equations.md` | Implemented update rules |
| `Documents/tenants.txt` | Non-negotiable causality doctrine |
| `Documents/biological_fidelity_spec.md` | Bind criteria and causality chain |
| Abhi `Current_Implementation_Methodology_Equations.md` | Faraday `AbhiCIPP` equation authority |

---

## Repo pointers

| Name | Git (typical) |
|------|----------------|
| Cognative Paradigm | `gitlab.prodserver.net/telepathboy/cognative_paradigm` — `main`; Faraday `Paul_Model` |
| CIPP / Abhi | `git@faraday.lps.umd.edu:cipp/cipp-learning.git` — `AbhiCIPP` |
| Local SNN research tree | `~/Documents/SNN` (if present on workstation) |

*When this doc disagrees with an old two-column table that describes Paul’s repo as “4 files, no plasticity,” trust this doc and the `Paradigm_New` tree — that table refers to the early scaffold, not current `Paul_Model`.*
