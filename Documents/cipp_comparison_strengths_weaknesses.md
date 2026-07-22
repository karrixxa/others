# CIPP (Abhi) vs Cognative Paradigm — Strengths & Weaknesses

**Date:** 2026-07-15 (Abhi-align 1A + 2B)  
**Their branch:** `AbhiCIPP` on `git@faraday.lps.umd.edu:cipp/cipp-learning.git`  
**Our branch:** `Paul_Model`  
**Decision:** Import Abhi **time + I plasticity** into our 4-ring stack; **reject** `eta_loss`, signed OFF, and production `l1i_immediate_relay`.

---

## Alignment status (1A / 2B)

| Abhi feature | Tenant-safe? | Our status |
|--------------|--------------|------------|
| Excitatory / inhibitory flow-rate | Yes | **Default ON** |
| Inhibitory turnover + assembly credit | Yes | **Default ON** (I plastic) |
| Soft NI / same-tick loser suppress | Yes | **NI 0.62 / 1.0**; ring feedback same-tick |
| Dense temporal pulse | Yes | **Default ON** |
| `eta_loss` FF depression | No (2/3/9) | **Not imported** |
| Signed OFF depression | No (2) | **Not imported** |
| `l1i_immediate_relay` | No (4/9) | **Not production**; delayed descending default |
| Membrane-wipe exclusivity | Lab only | Flag **OFF** by default |

---

## At a glance

| Dimension | CIPP (Abhi) | Cognative Paradigm (ours) |
|-----------|-------------|---------------------------|
| Catalog | 8 line primitives | 4 center-cell shapes |
| L2 pool | 8 L2E + 1 L2I | 4 ring E + central NI |
| Time / I kernels | Native flow + turnover + assembly | **Aligned defaults** (1A/2B) |
| Binding | Competition + depression | Eligibility + weight + local exclusivity |
| Symbols | Line primitives as identity | Emergent `sigma_k` |

**Do not import:** signed-spike OFF depression, `eta_loss=10`, L1I immediate relay, global weight budget, `lasting_inhibition`.

---

## At a glance

| Dimension | CIPP (Abhi) | Cognative Paradigm (ours) |
|-----------|-------------|---------------------------|
| Catalog | 8 line primitives (rows, cols, diags) | 4 center-cell shapes (H1, V1, D0, D1) |
| L2 pool | 8 L2E, one per primitive | 4 ring E + central I (NI) |
| Time model | Dense steps; **excitatory flow-rate default** | Discrete pulse default; **optional robustness stack** (Phases 1–5) |
| Binding | Competition + depression (no ownership map) | Eligibility + weight evidence + local exclusivity |
| Symbols | Line primitives as identity | Emergent `sigma_k` |
| Single held pattern | Strong (clean consolidation + L2I rhythm) | Strong (4/4 equilibrium tested) |
| Interleaved multi-pattern | Weak (4–6 winners / 8 patterns) | **4/4 unguided ecological rotation** (robustness on); legacy discrete ~1/4 |

---

## Their strengths vs ours

| # | Their strength | Why it matters | Our status |
|---|----------------|----------------|------------|
| 1 | **Excitatory flow-rate (default)** — current trace \(I\), lazy \(d^{\Delta t}\) advance | Membrane can integrate between spikes; crosses threshold without new input; biophysical PSP kernel | **Implemented** (`excitatory_flow_rate_enabled`; default off) |
| 2 | **Inhibitory flow-rate (optional)** — trace \(J\) drains over steps | Sustained suppression vs one-shot clamp | **Implemented** (`inhibitory_flow_rate_enabled`; default off) |
| 3 | **Inhibitory turnover plasticity** — per-target gate \(u = w/G\) | Gates differentiate by how much each loser was charged (~260 spread vs ~4 saturating) | **Implemented** (`inhibitory_turnover_enabled`; default off) |
| 4 | **Assembly flow credit** on E→I synapses | Habitual winner's E→I path matures; fixes L2I firing rhythm (~16-step cycle) | **Implemented** on NI + descending (`assembly_flow_credit_enabled`) |
| 5 | **Loser depression** on feedforward gates | Strong symmetry-breaker for a **held** pattern | Loser membrane suppress + delayed ring feedback; no FF weight depression |
| 6 | **Dense simulation** — `input_period`, volleys, cycle boundaries | Sustained sensory drive; pattern held across steps | **Phase 1** temporal integration + sustained volley (optional) |
| 7 | **8-pattern catalog** | Full 3×3 line coverage | 4-shape subset; less assignment stress |
| 8 | **Documented equation spec** cross-checked to `neuron_flexible.py` | Reproducible lab notebook for plasticity flags | `model_equations.md` + integrity auditor |
| 9 | **Rich experimental knobs** | Chunked charge, distance weighting, confidence, inh/exc flow flags | Tuning scripts exist; fewer temporal modes |

---

## Their weaknesses vs ours

| # | Their weakness | Evidence / impact | Our advantage |
|---|----------------|-------------------|---------------|
| 1 | **No stable interleaved ownership** | 4–6 distinct winners across 8 patterns; open problem in their doc | Local exclusivity + 4/4 ecological rotation tests |
| 2 | **Cold start on pattern switch** | OFF-pixel signed depression + loser depression → gates at floor | No OFF depression; inactive edges stay at baseline |
| 3 | **`l1i_immediate_relay` default** | L1I fires on any L2E feedback — not an integrator | L1 I from descending charge, next-tick, shape-scoped |
| 4 | **No emergent symbol layer** | Neurons tied to line primitives | `sigma_k` registry; catalog labels presentation-only |
| 5 | **No bind integrity auditor** | Binds implied by weights/competition | `learning_integrity.py` audits every `PATTERN_BOUND` |
| 6 | **`eta_loss = 10` (dashboard)** | Over-depresses across patterns; leaves some ownerless | Gentler competition; ownership gate separate from depression |
| 7 | **`refractory = 0` (dashboard)** | No dead time after spike | Nucleus refractory = 2 steps; L1 refractory = 1 |
| 8 | **Zero-delay spike delivery** | L1→L2→L2I→L1I same timestep | 1-tick descending + ring feedback queues |
| 9 | **`lasting_inhibition` field** | Documented as failed (pattern-blind collapse) | Not used |
| 10 | **Weaker end-to-end product** | Dashboard + experiments focus | Workspace UI, checkpoints, Recognition Lab, rasters |

---

## Our strengths vs theirs

| # | Our strength | Why it matters | Their gap |
|---|--------------|----------------|-----------|
| 1 | **Tenant-strict 1/Z causality** | Only `ONE` transmits; `Z` not logged or learned | Same event model, but more plasticity paths blur ON/OFF |
| 2 | **Hidden membrane doctrine** | Subthreshold state not broadcast (Tenant 1.3) | Membrane used directly in WTA argmax (OK) but more graded machinery |
| 3 | **Eligibility + weight consolidation** | Bind requires trace ≥ 0.75 + conductance evidence | Competition + depression only; no formal bind gate |
| 4 | **Read-only pattern snapshot** | Observed 1:1 map from neuron memory; never blocks learning | Collision under interleaved presentation |
| 5 | **Emergent symbols (`sigma_k`)** | 1:1 symbol ↔ representation (Tenant 6) | Catalog line = neuron role |
| 6 | **L1 I as true inhibitory integrator** | Descending L2→L1, not stimulus-driven | Immediate relay default |
| 7 | **NI pool + collateral charging** | Central I from mean ring + relay bump, not winner membrane alone | Single L2I with weight=threshold history (since fixed) |
| 8 | **Delayed feedback architecture** | Biological synaptic delay analogue | All same-tick |
| 9 | **Auto-stim contract** | Ecological rotation; never reads bind state | Similar intent; less formal API/test surface |
| 10 | **Checkpoint save/load** | Persist trained brain | Not in their AbhiCIPP tree |
| 11 | **Full test + integrity pipeline** | 166+ backend tests, learning integrity probe, interleaved robustness, e2e | Strong unit tests on competition; weaker bind audit |

---

## Our weaknesses vs theirs

| # | Our weakness | Impact | Their advantage |
|---|--------------|--------|-----------------|
| 1 | **Discrete pulse time (default)** | Inter-stimulus interval invisible unless robustness on | Flow-rate + dense steps (their default) |
| 2 | **Smaller catalog (4 shapes)** | Less stress on assignment at scale | 8 primitives, closer to full grid |
| 3 | **Legacy I-plasticity when robustness off** | Central channels may saturate uniformly | Turnover rule differentiates per loser |
| 4 | **Gentler symmetry breaking (discrete mode)** | Interleaved rotation ~1/4 without robust stack | `eta_loss=10` + signed-spike sharpens fast |
| 5 | **Smaller catalog (4 shapes)** | By design — center-cell subset, less assignment stress than Abhi’s 8 | 8 primitives (their research scale; not our target) |
| 6 | **Less plasticity documentation surface** | Fewer flags than Abhi methodology doc | Full methodology doc + Claude prompt guides |

---

## Tenant alignment: safe to borrow vs reject

### Safe to adopt (robustness, tenant-compatible)

| Feature | Tenants served | Notes |
|---------|----------------|-------|
| Excitatory flow-rate + lazy advance | 1.3, 7 | Hidden trace; events still 1/Z |
| Simulation clock + inter-pulse leak | 7 | Continuous learning in time |
| Sustained stimulus volley | 7 | Hold pattern ON across sub-steps |
| Inhibitory turnover on central channels | 4, 9 | Event-local; no global average |
| Assembly / flow credit on E→I | 2, 7, 9 | Per-neuron trace φᵢ |
| Inhibitory flow-rate drain (optional) | 4 | Sustained suppression |
| Refractory in ms | 5 | Never zero refractory |

### Reject (misaligned with `tenants.txt`)

| Feature | Tenants violated | Reason |
|---------|------------------|--------|
| `l1i_immediate_relay` | 4, 9 | L1 I is not an inhibitory neuron |
| Signed-spike OFF depression | 2 | Unwires silent inputs — not “fire together wire together” |
| `eta_loss = 10` loser depression on FF weights | 2, 3, 9 | Erases readiness for other patterns |
| Global weight budget renormalization | 9 | Redistributes across all positive synapses |
| `refractory = 0` | 5 | No refractory period |
| `lasting_inhibition` shared field | 9 | Pattern-blind global suppression |
| Binding without ownership claim | 3, 6 | No enforced 1:1 pattern↔neuron |
| Catalog label as neuron identity | 6 | No emergent symbol |

---

## Recommended adoption order (robustness)

```
Phase 1  SimulationClock + inter-pulse leak + sustained volley          [done]
Phase 2  Excitatory flow-rate (lazy advance)                            [done]
Phase 3  Inhibitory turnover on central→loser channels                  [done]
Phase 4  Assembly flow credit on NI / descending paths                  [done]
Phase 5  Optional inhibitory flow-rate                                  [done]
Phase 6  Interleaved stress tests                                       [done — see test_interleaved_robustness.py]
Scope    **4-pattern catalog only** (H1, V1, D0, D1) — no 8-pattern expansion [decided 2026-07-10]
```

**Three-way context:** `Documents/three_way_repo_comparison.md` (Abhi SNN vs early scaffold vs Paradigm).

**Do not import:** signed-spike OFF depression, `eta_loss=10`, L1I immediate relay, global weight budget, `lasting_inhibition`.

---

## Summary

| | CIPP (Abhi) | Cognative Paradigm |
|--|-------------|-------------------|
| **Best at** | Continuous excitatory dynamics, inhibitory plasticity sophistication, single-pattern competition | Event causality, binding doctrine, ownership, symbols, delayed inhibition, product/test rigor |
| **Worst at** | Interleaved 8→8 assignment, pattern-switch cold start, L1I biology (relay default) | Fast symmetry breaking without robust modes (mitigated by default robustness stack) |
| **Convergence path** | Borrow their **time physics** and **I-plasticity**; keep our **ownership, eligibility, L1/L2 delay, and symbol layer** |

---

## Related documents

- `Documents/three_way_repo_comparison.md` — **Abhi SNN vs early scaffold vs Paradigm** (this comparison family)
- `Documents/system_overview.md` — our one-page architecture
- `Documents/model_equations.md` — our implemented equations
- `Documents/biological_fidelity_spec.md` — bind criteria and causality chain
- Their `Current_Implementation_Methodology_Equations.md` — Abhi branch equation spec
