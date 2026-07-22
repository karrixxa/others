# Cognative Paradigm — Model Equations (Biological Workspace)

**Scope:** Flat pipeline at `#/workspace` (`POST /api/stimulate`) — catalog sensory patterns → Layer 1 relay → nucleus ring WTA → eligibility consolidation → emergent symbols.

**Authority:** `Documents/tenants.txt`, `Documents/paradigm_spec.md`, `Documents/biological_fidelity_spec.md`  
**Implementation:** `backend/cognative_paradigm/`  
**Defaults:** `LearningDynamics` in `simulation/learning_dynamics.py`

This document is a **detailed outline** of every update rule the backend applies during learning. Auto-stim only selects **which catalog shape to present**; it does not inject winners, symbols, or binding shortcuts.

**Equation truth lock:**

- Production: phenomenological conductance LTP/LTD, mature frozen NI,
  force descending, exclusivity ON, scaling mutation OFF, mastery API default.
- Biological lab P2–FULL: full triplet excitatory timing; cumulative dual
  eligibility, Vogels iSTDP, scaling, graded descending, and replay gates.
- Biological benchmarks and fidelity claims use rotation. Mastery is a
  completion-scheduled demonstration curriculum.
- No AMPA/NMDA conductance-synapse model is claimed or implemented.

---

## Outline (how one pulse works)

**Default:** `temporal_integration_enabled = True` — one Auto-Stim pulse spans **40 ms** of sub-steps plus **960 ms** inter-pulse silence (when `auto_stim_interval_ms = 1000`).

1. **Inter-pulse silence** — leak all L1/L2 membranes for `silence_sub_steps()` at `lif_dt() × inter_pulse_leak_scale` per ms.
2. **Stimulus registration** — three grid edges register `ONE`; all others stay `Z`.
3. **Descending delivery (from \(t{-}1\))** — pending L2/nucleus charge drives shape-scoped L1 I units.
4. **Within-pulse substeps (×39)** — L1 subthreshold relay → L2 integrate relay → NI pool (soft competition; no force assists).
5. **Layer 1 final tick** — active cells integrate input, spike E relays toward nucleus.
6. **Synaptic scaling** — L1 I coupling is **saturated/frozen** at \(g_{\max}\) (EMA tracked only; no mutation).
7. **Competition pool** — four ring neurons; bound neurons only spike when pattern matches (Tenant 3/8).
8. **Ring feedback (from \(t{-}1\))** — pending central-I suppression hyperpolarizes loser ring neurons before integration.
9. **WTA final substep** — force exclusivity cascade (production): first authentic above-θ spike force-fires NI, wipes other L2E membranes, same-tick L1I. Labeled soft control (`pretrained_inhibitor_exclusivity_enabled=false`): all authentic spikes allowed; shared NI applies soft channel×scale suppression.
10. **Central I** — collateral + pool; **L2I channels always saturate** at mature \(\max(c_0, i_{\max})\) (I-channel plasticity frozen).
11. **Plasticity & eligibility** — authentic spikers update **L2E** sensory/relay + EP (L2E→L1E′) afferents. Production (`emergent_autonomy_enabled=false`): rematch drive 0.7 + BoundMatch freeze. Labeled soft/graded control with Stage 14 ``emergent_autonomy_enabled=true``: rematch freeze/attenuation **off**; eligibility/bind credit requires a **unique** authentic spike; consolidator is **first-commit-wins** per pattern (LTP still open). L1 InputEdge / L1I / L2I stay saturated.
12. **Consolidation** — when trace + weight evidence pass thresholds, `PATTERN_BOUND` per neuron; ownership collision is audit-only.
13. **Recognition** — bound spiker with matching prediction emits stored `sigma_k` symbol at half charge; still force-fires L2I/L1I.
14. **Descending** — L2E charges L1 E′; E′ threshold force-fires L1 I. Production force path: one L2E (`l2_to_l1_i_gain` ≥ θ_E′) guarantees same-tick E′→L1I on active shape cells.

**Legacy mode:** `temporal_integration_enabled = False` collapses steps 1 and 4–9 into a single discrete tick (backward compatible).

---

## Notation

| Symbol | Meaning |
|--------|---------|
| \(t\) | Discrete timestep (one Auto-Stim pulse = one `BrainSimulator.step`) |
| \(u_i[t]\) | Membrane potential of neuron \(i\) (**hidden**; not logged as causal) |
| \(r_i[t] \in \{1, Z\}\) | Register output — only `ONE` (\(1\)) is transmitted |
| \(\theta_i\) | Spike threshold of neuron \(i\) |
| \(w_e^{(k)}\) | Sensory conductance on grid cell \(e\) for ring neuron \(k\) (`SensoryConductanceMap`) |
| \(w_{\mathrm{baseline}}\) | Saturated L1 `InputEdge` gain (= \(e_{\max}\); non-plastic) |
| \(g_{\mathrm{I}\to\mathrm{E},g}\) | L1 local inhibition strength at grid cell \(g\) |
| \(c_k\) | Central inhibitory channel strength to ring neuron \(k\) |
| \(\tau_m\) | Membrane time constant (default **10.0**) |
| \(\Delta t\) | Sub-step size (default **1 ms** when temporal ON; **1 legacy tick** when OFF) |
| \(\delta t\) | Per sub-step fraction: `lif_dt()` = \(1/N_{\mathrm{stim}}\) (default **1/40**) |
| \(\lambda_{\mathrm{silence}}\) | `inter_pulse_leak_scale` × `lif_dt()` per ms of gap |
| \(R_i\) | Refractory period (steps) after a spike |
| \(\mathcal{A}_t\) | Active edge set (exactly three cells for catalog lines) |
| \(R_t\) | Set of L1 excitatory relay ids that fired at \(t\) |

**Tenant 1:** Only presynaptic `ONE` events contribute drive. `Z` is not transmitted, integrated, or logged.

**Catalog lines:** `H1`, `V1`, `D0`, `D1` — four center-cell 3-cell patterns on a 3×3 grid (`lines.py`). Auto-stim acts as an RGC gate (only center-crossing shapes).

---

## 1. Leaky integrate-and-fire (per neuron)

**Source:** `domain/lif_dynamics.py`, `domain/neuron.py`, `domain/spike_drive.py`

Each neuron maintains independent state \((u_i, \theta_i, r_i, t_{\mathrm{ref}})\). Coupling enters only through synaptic drive \(D_i[t]\).

### Parameters

| Symbol | Code | Default (engine) |
|--------|------|------------------|
| \(u_{\mathrm{rest}}\) | `resting_potential` | 0.0 |
| \(u_{\mathrm{reset}}\) | `reset_potential` | 0.0 |
| \(\tau_m\) | `membrane_tau` | **10.0** |
| \(\Delta t\) | `sim_dt_ms` | **1.0** (ms per sub-step) |

Derived leak coefficients per integration call with scale \(\delta\):

\[
\lambda = 1 - \frac{\delta \cdot \Delta t}{\tau_m}, \qquad
\rho = u_{\mathrm{rest}}\cdot\frac{\delta \cdot \Delta t}{\tau_m}
\]

With defaults and \(\delta = 1/40\): \(\lambda \approx 0.9975\), \(\rho = 0\) per sub-step.

### Subthreshold update (each integration)

**Leak:**

\[
u_i \leftarrow \lambda\, u_i + \rho
\]

**Excitatory drive** (`SpikeDrive.apply_excitatory`):

\[
u_i \leftarrow u_i + D
\]

**Inhibitory drive** (`SpikeDrive.apply_inhibitory`):

\[
u_i \leftarrow u_i - D
\]

### Spike rule

\[
\text{if } t < t_{\mathrm{ref}}: \text{ no spike}
\]
\[
\text{elif } u_i \geq \theta_i:\quad
r_i \leftarrow 1,\;
u_i \leftarrow u_{\mathrm{reset}},\;
t_{\mathrm{ref}} \leftarrow t + R_i
\]

Otherwise \(r_i = Z\).

---

## 1b. Temporal integration (`SimulationClock`)

**Source:** `simulation/simulation_clock.py`, `simulation/engine.py`

When `temporal_integration_enabled = True` (default):

| Quantity | Formula / code |
|----------|----------------|
| Stimulus sub-steps | \(N_{\mathrm{stim}} = \mathrm{round}(\texttt{stim\_duration\_ms} / \texttt{sim\_dt\_ms})\) → **40** |
| Silence sub-steps | \(N_{\mathrm{gap}} = \mathrm{round}((\texttt{auto\_stim\_interval\_ms} - \texttt{stim\_duration\_ms}) / \texttt{sim\_dt\_ms})\) → **960** |
| Per sub-step dt fraction | `lif_dt()` = \(1 / N_{\mathrm{stim}}\) |
| Silence leak scale | `silence_dt_scale()` × `inter_pulse_leak_scale` per ms |

**Inter-pulse silence** (start of each pulse, before stimulus):

\[
u_i \leftarrow \text{leak}(u_i,\; \delta = \texttt{lif\_dt()} \times \texttt{inter\_pulse\_leak\_scale})
\]

repeated \(N_{\mathrm{gap}}\) times. Default `inter_pulse_leak_scale = 0.045` → total gap leak ≈ **1.08 legacy ticks** (not the full 24× real-time gap).

**Within-pulse substeps:** L1 relay and L2 integration run for \(N_{\mathrm{stim}} - 1\) subthreshold substeps, then one final L1 spike + WTA substep. All leak and drive calls use `dt_scale = lif_dt()`. Relay `drive_gain` is always identity (**1.0**).

> **Removed (not merely OFF):** stimulus-completion ramp, unbound-capture boost, latency WTA arbiter, substep lateral suppression, synthetic recall drive, competition pool boost, and shared-relay plasticity scale have been **deleted from the codebase**.

### 1c. Flow-rate traces (Abhi-aligned, default ON)

**Sources:** `domain/excitatory_flow_trace.py`, `domain/inhibitory_flow_trace.py`

When `excitatory_flow_rate_enabled = True`, synaptic drive injects into trace \(I\) with decay \(d =\) `exc_trace_decay` (default **0.8**). Lazy advance over \(\Delta t\) idle micro-steps:

\[
V \mathrel{+}= I \cdot \frac{1 - d^{\Delta t}}{1 - d}, \qquad I \mathrel{\leftarrow} I\,d^{\Delta t}
\]

Normalized spike injection: \(I \mathrel{+}= g(1-d)\) so total delivered charge equals instantaneous \(g\).

When `inhibitory_flow_rate_enabled = True`, inhibitory discharge injects \(J\) and drains each step: \(V \mathrel{\leftarrow} \max(V-J, R)\), \(J \mathrel{\leftarrow} d_{\mathrm{inh}} J\).

These kernels are **equation-identical** to Abhi CIPP §Excitatory/Inhibitory Flow-Rate (see §20).

---

### Per-unit thresholds and refractory

| Unit | \(\theta\) | \(R\) | Source |
|------|-----------|-------|--------|
| L1 E relay \(E_g\) | 0.45 | 1 | `l1_excitatory_threshold` |
| L1 I \(I_g\) | 0.26 | 1 | `l1_inhibitory_threshold` |
| Nucleus ring E\(_k\) | 1.05 | 2 | `nucleus_threshold` |
| Central I (temporal ON) | 1.1 | 1 | `central_inhibitor_threshold_temporal` |
| Central I (temporal OFF) | 0.8 | 1 | `central_inhibitor_threshold` |

---

## 2. Input grid → sensory edges

For pattern \(P\) with active grid indices (catalog line or arbitrary 3-cell set):

\[
\text{edge } e \text{ registers ONE at } t \;\Leftrightarrow\; e \in P
\]

Each of nine grid positions has an `InputEdge` with conductance \(w_e\):

- **Initial weight:** 0.5 (`input_edge.py`)
- **Learned** via excitatory conductance plasticity (§9) on **each authentic spiker** (not a sole diagnostic winner)
- **Not** modified by synaptic scaling (§4)

---

## 3. Layer 1 — E/I relay pairs

**Source:** `simulation/layer1_network.py`, `simulation/layer1_pair_dynamics.py`, `simulation/layer1_lateral.py`

Nine grid positions \(g \in \{0,\ldots,8\}\). Each has pair \((E_g, I_g)\) and coupling \((g_{\mathrm{ff}}, g_{\mathrm{I}\to\mathrm{E},g}, g_{\mathrm{coll}})\).

| Coupling field | Code default | Used in dynamics? |
|----------------|--------------|------------------|
| \(g_{\mathrm{I}\to\mathrm{E}}\) | 0.28 (`inhibition_strength`) | **Yes** — local I→E |
| \(g_{\mathrm{ff}}\) | 0.40 (`l1_feedforward_gain`) | Stored only; **not** applied to L1 I in active path |
| \(g_{\mathrm{coll}}\) | 0.40 (`e_collateral`) | Stored only; **not** read |

### 3.1 Step order within Layer 1

1. Reset all L1 registers to `Z`.
2. **Apply pending descending charge** to shape-scoped \(I_g\) (§11); try_spike each charged \(I_g\).
3. For each grid cell:
   - **Inactive cell:** leak \(E_g, I_g\).
   - **Active cell** (edge fired at \(t\)):
     1. Leak \(E_g, I_g\).
     2. \(u_{E_g} \mathrel{+}= w_{\mathrm{in},g}\) (input conductance).
     3. If \(I_g\) register was `ONE` from step 2 (same tick): \(u_{E_g} \mathrel{-}= g_{\mathrm{I}\to\mathrm{E},g}\).
     4. `try_spike` on \(E_g\) only → relay `l1_e_g` if fired.
4. **Synaptic scaling** on \(g_{\mathrm{I}\to\mathrm{E},g}\) (§4).
5. **Lateral inhibition** among neighbors (§3.2).

**Important:** L1 I is **not** charged by the sensory stimulus directly. I charge comes from **descending inhibition** (§11) only.

### 3.2 Lateral inhibition

Strength \(s_{\mathrm{lat}} = 0.12\) (`layer1_lateral.STRENGTH`).

For each firing cell \(g\) and 4-connected neighbor \(h \notin R_t^{\mathrm{grid}}\):

\[
u_{E_h} \leftarrow u_{E_h} - s_{\mathrm{lat}}
\]

### 3.3 Relay output

\[
R_t = \{ \texttt{l1\_e\_}g \mid E_g \text{ fired at } t \}
\]

Relay count \(|R_t| \leq 3\) for catalog lines (one relay per active cell).

---

## 4. Synaptic scaling (L1 I — frozen saturated)

**Source:** `learning/synaptic_scaling.py` (active in `layer1_network.process_step`).

Production doctrine: **initial L1E / L1I / L2I are saturated and frozen**.
`InhibitoryCoupling.inhibition_strength` initializes at \(g_{\max}=0.5\)
(= `homeostasis_i_max`). Scaling still tracks EMA of E firing for diagnostics,
but **`update` is a no-op** on coupling and `InputEdge` weights
(`scaling_eta = 0`).

| Parameter | Code | Default |
|-----------|------|---------|
| Target rate \(\rho^*\) | `scaling_target_rate` | 0.15 |
| Step \(\eta\) | `scaling_eta` | **0.0** (disabled) |
| \(g_{\min}\) | `homeostasis_i_min` | 0.1 |
| \(g_{\max}\) | `homeostasis_i_max` | **0.5** (L1I create/reset value) |
| \(w_{\mathrm{baseline}}\) | `sensory_baseline_weight` | **2.0** (L1E InputEdge; membrane-scale, not tied to `e_max_weight=1000`) |

**Plastic remain:** L2E sensory/relay conductances; L2E→L1E′ EP afferents.

---

## 5. Nucleus competition pool

**Source:** `simulation/nucleus_line_competition.py`

Before WTA, resolve which ring neurons enter the pool:

| Condition | Pool | Phase label |
|-----------|------|-------------|
| Pattern \(P\) has **no** owner | All **unbound** ring E neurons | `learning` |
| Pattern \(P\) **has** owner | **All eight** ring E neurons | `equilibrium` |

There is **no** synthetic drive boost to the owner neuron. Recall at equilibrium emerges from learned conductances and WTA dynamics, not an injected recognition bonus.

---

## 6. Nucleus relay drive

**Source:** `simulation/nucleus_ring_competitor.py`, `simulation/l1_relay_broadcast.py`

For ring neuron \(k\) receiving relay set \(R_t\):

\[
D_k = |R_t| \cdot w_{\mathrm{relay}}
\]

| Parameter | Code | Default |
|-----------|------|---------|
| \(w_{\mathrm{relay}}\) | `nucleus_relay_weight` | **0.075** |
| \(w_{\mathrm{up}}\) | `upstream_relay_weight` | 1.25 |

Each substep integrates \(D_k\) with `dt_scale = lif_dt()` where
\(\mathrm{lif\_dt} = 1 / N_{\mathrm{stim}}\) (default \(1/40 = 0.025\)).
For a full catalog line (\(|R_t| = 3\)):

\[
D_k \approx 3 \times 0.075 = 0.225 \quad \text{(raw relay drive before } \mathrm{dt\_scale}\text{)}
\]

\[
\Delta V_{\mathrm{sub}} \approx D_k \cdot \mathrm{lif\_dt} \approx 0.0056 \text{ per ms sub-step}
\]

One 40 ms pulse therefore contributes about one legacy tick of charge
(\(\sum \mathrm{dt\_scale} = 1\)), so membranes climb toward
\(\theta_{\mathrm{nucleus}} = 1.05\) over **several pulses**. Energy rasters
sample decimated frames (`energy_frame_stride = 5`). The final WTA sub-step
uses the same `lif_dt` (not `dt_scale = 1`).

---

## 7. Loser suppression (learning / recall I cascade)

**Sources:** `simulation/wta_coordinator.py`, `simulation/pretrained_inhibitor_exclusivity.py`, `simulation/bound_match_recall_policy.py`, `simulation/ring_feedback_inhibition.py`

**Production — force cascade (`pretrained_inhibitor_exclusivity_enabled=true`, `descending_mode=force`):**

1. First authentic ring E spike forces central NI to fire (membrane driven to \(\theta\)).
2. All other L2 E membranes are wiped to **0**; further authentic spikes abort that tick.
3. Same-tick L1 I force-fire for active shape cells (one L2E → E′ → L1I when gain ≥ θ_E′).
4. After `PATTERN_BOUND`, rematch uses `bound_match_recall_drive_gain=0.7` + BoundMatch spike/plasticity gates (`emergent_autonomy_enabled=false`).

**Labeled control (`pretrained_inhibitor_exclusivity_enabled=false` — soft race + graded):**

1. Soft channel×scale loser suppress when NI fires (no membrane wipe).
2. Multi-spike honest recording allowed; `WtaOutcome.winner` is diagnostic only.
3. Graded descending L1 I (integrator).
4. Optional Stage 14 autonomy (`emergent_autonomy_enabled=true`): full drive (1.0) and open rematch LTP; bind credit only on unique-spike pulses; first consolidator commit wins the pattern seat.

**Delayed ring feedback** (both modes, when NI fires and same-tick feedback is off):

\[
s = \min\!\left(1,\; \frac{Q_{\mathrm{central}}}{\theta_{\mathrm{central}}}\right) \cdot g_{\mathrm{ring}}
\]

\[
P_k \leftarrow P_k + s \cdot c_k
\]

- \(Q_{\mathrm{central}}\) = central membrane at fire time
- \(c_k\) = per-channel inhibitory strength (pre-trained mode: held at mature \(i_{\max}\))
- \(g_{\mathrm{ring}}\) = `ring_feedback_gain` = **1.15**

At the **start** of nucleus step \(t\), before WTA integration:

\[
u_{\mathrm{ring},k} \leftarrow u_{\mathrm{ring},k} - P_k, \quad P_k \leftarrow 0
\]

---

## 8. Winner-take-all (WTA)

**Source:** `simulation/wta_coordinator.py`  
**Doctrine (learning/recall cascade):** Force NI / membrane wipe / same-tick L1I (production). Soft independent L2E race + graded descending + Stage 14 ``emergent_autonomy_enabled`` remain **labeled control**. Ownership collision stays audit-only.

For each competitor \(k\) in the pool:

1. Leak; skip if refractory.
2. \(u_k \leftarrow u_k + D_k[t]\).
3. Optional noise (learning): \(u_k \leftarrow u_k + \mathcal{N}(0, \sigma^2)\), \(\sigma =\) `membrane_noise_std` = **0.01** (silenced in inference-only probe).
4. Candidate if \(u_k \geq \theta_{\mathrm{nucleus}}\).

### Spike attempts (emergent)

Among candidates (`CompetitionPolicy`):

1. Every authentic candidate above θ **attempts** `try_spike` (fair shuffle of attempt order when `wta_fair_ties`).
2. Multi-spike is recorded honestly in `population_spike_ids`.
3. `WtaOutcome.winner` (`primary_among_spikers`) is **diagnostic only** — it does **not** gate LTP, eligibility, or consolidation.
4. No latency-preferred inject; no `membrane = threshold` clamp.
5. Functional NI (no authentic ring spikes): channel×scale on **all** targets (`spared=∅`). No max(Vm) hottest-spare.

### Central I pool charge and collateral

Each relay tick, before spike attempts, central I leaks and integrates **mean ring-E membrane** (pool drive from all eight competitors):

\[
u_{\mathrm{central}} \leftarrow \text{leak}(u_{\mathrm{central}})
\]
\[
u_{\mathrm{central}} \leftarrow u_{\mathrm{central}} + \gamma_{\mathrm{pool}} \cdot \frac{\bar{u}_{\mathrm{ring}}}{\theta_{\mathrm{nucleus}}}, \quad
\bar{u}_{\mathrm{ring}} = \frac{1}{8}\sum_k u_k
\]

\(\gamma_{\mathrm{pool}} =\) `central_pool_gain` = **0.62** (Abhi-like held-pattern NI drive). Pool gain scale is identity (competition pool boost **removed**).

When a ring E spikes, add relay collateral (not winner membrane):

\[
u_{\mathrm{central}} \leftarrow u_{\mathrm{central}} + \gamma \cdot W_{\mathrm{recv}}, \quad
\gamma = \texttt{collateral\_gain} = 0.45
\]

Central I **spikes** only when \(u_{\mathrm{central}} \geq \theta_{\mathrm{central}}\). Loser suppression (§7) runs **only when central I actually fires**, via channel×scale — never a procedural floor wipe.

> Footnote: former force assists (capture gain, loser floor, latency clamp, substep lateral, pool boost, completion ramp, shared-relay mute, recall drive) are **removed**, not merely OFF.

---

## 9. Production and lab plasticity

**Production source:** `learning/conductance_plasticity.py`  
Production uses charge-gated soft-saturated updates. Timing-based laws are
available only through `BiologicalLabProfile`; the production singleton remains
`plasticity_mode="conductance"`.

Plasticity runs when:

- Not `inference_only`
- Authentic ring E spiked (`population_spike_ids` non-empty)
- For **each** authentic spiker independently (own sensory/relay maps + eligibility trace)
- `_plasticity_eligible` gates **sensory LTP, relay LTP, and consolidator** per neuron when BoundMatch soft gates are active. **Production autonomy:** soft gates off — any authentic spiker may LTP; eligibility/bind use unique-spike + first-commit evidence. **Labeled recall freeze:** skip when bound ∧ match. PE-LTD on bound∧mismatch stays active.
- Active edge set non-empty
- Cross-neuron ownership collision is **audit-only** (`OWNERSHIP_COLLISION`); it never blocks consolidation. Tenant 3 (one pattern per neuron) remains via per-neuron memory bind.

> Footnote: Force assists **removed** — capture gain / loser floor / latency clamp / substep lateral / pool boost / hottest-spare / primary-only LTP / shared-relay mute / synthetic recall gain / consolidation collision blocker. See §8.

### 9.1 Excitatory (grid input edges)

Let \(\mathcal{A}_t\) be edges that fired at \(t\). Instantaneous aggregate conductance:

\[
A_{\mathrm{inst}} = \sum_{e \in \mathcal{A}_t} w_e
\]

Free energy:

\[
F_E = \theta_E - A_{\mathrm{inst}}, \quad \theta_E = 1.85 \;\;(\texttt{e\_plasticity\_threshold};\;\mathrm{relay})
\]

Soft saturation:

\[
S(w) = 1 - \left(\frac{w}{w_{\max}}\right)^2, \quad w_{\max} = 1000
\]

Per active edge:

\[
\Delta w_e = \eta_E \cdot F_E \cdot S(w_e), \quad \eta_E = 0.016
\]
\[
w_e \leftarrow \mathrm{clip}(w_e + \Delta w_e,\; w_{\min},\; 1000)
\]

Sensory maps use \(w_{\min}=1\) and \(\theta_s=1600\) (`sensory_plasticity_threshold`). Relay maps keep membrane-scale \(w_{\min}=0.01\) and \(\theta_E=1.85\).

Skip if \(|F_E| < 10^{-12}\).

### 9.2 Inhibitory (central I → ring channels)

**Default path:** `InhibitoryAssemblyLearner` (hot-gated turnover with strengthen headroom).  
**Fallback** (turnover OFF): charge free-energy update below.

#### 9.2.1 Hot-gated inhibitory assembly (default)

Normalized gate \(u = c_k / G\) with \(G = \sqrt{c_{\max}}\), \(c_{\max} = \texttt{i\_max\_weight} = 2.25\) so \(G \approx 1.5\).

Hot gate (PV-like; reuse `central_competition_hot_fraction` = 0.88):

\[
\mathrm{hot\_line} = 0.88\,\theta_E,\quad
\kappa = \mathrm{clip}\!\left(\frac{v_{\mathrm{pre}}-\mathrm{hot\_line}}{\theta_E-\mathrm{hot\_line}}, 0, 1\right)
\]
\[
\kappa_{\mathrm{eff}} = \kappa_{\min} + (1-\kappa_{\min})\kappa,\quad \kappa_{\min} = 0.15
\]
\[
p_t = \mathrm{clip}(v_{\mathrm{pre}}/\theta_E, 0, p_{\max})\cdot\kappa_{\mathrm{eff}}
\]
\[
\Delta u = \eta_\uparrow\,p_t\,(1-u) - \eta_\downarrow\,u,\quad
\eta_\uparrow = 0.03,\; \eta_\downarrow = 0.005
\]
\[
c_k \leftarrow \mathrm{clip}(u' G,\; 0.1,\; 2.25)
\]

Initial channels remain `central_inhibition_strength` = **1.1** (day-0 PV punch unchanged; headroom is in \(c_{\max}\)).

#### 9.2.2 Fallback charge free-energy (turnover OFF)

\[
F_I = Q_{\mathrm{central}} - c_k,\quad
\Delta c_k = \eta_I \cdot F_I \cdot S_I(c_k)
\]

#### 9.2.3 Vogels iSTDP (lab P4+)

**Source:** `learning/inhibitory_stdp.py`

For each NI→ring-E channel, \(x_{\mathrm{pre}}\) is the decaying inhibitory
trace and \(x_{\mathrm{post}}\) the decaying excitatory trace:

\[
\text{on NI spike:}\quad \Delta w = \eta(x_{\mathrm{post}}-\alpha)
\]
\[
\text{on ring-E spike:}\quad \Delta w = \eta x_{\mathrm{pre}}
\]

Lab presets P4+ disable phenomenological inhibitory turnover, enable plastic
NI channels and this Vogels rule, and disable force exclusivity. Production NI
channels remain mature, saturated, and frozen.

#### 9.3 Heterosynaptic / prediction-error LTD

**Source:** `learning/heterosynaptic_depression.py`  
Neuron-local only. **Not** Abhi signed-OFF / `eta_loss` on loser FF weights.

\[
\eta_{\mathrm{LTD}} = \texttt{ltd\_eta\_scale}\,\eta_E = 0.40\,\eta_E,\quad
S(w)=1-(w/w_{\max})^2
\]

| Site | Default | Trigger | Update |
|------|---------|---------|--------|
| **A PE-LTD** | ON | Authentic spike ∧ bound ∧ ¬match | \(\Delta w_e = -\eta_{\mathrm{LTD}} S(w_e) I_{\mathrm{norm}}(e)\) for \(e\in\mathcal{A}_t\); **no** LTP / eligibility / consolidate |
| **C heterosynaptic** | ON | After eligible LTP | Mild depress \(e\notin\mathcal{A}_t\) at \(\eta_{\mathrm{LTD}}\) |
| **B hot non-spiker** | ON | Inhibited ∧ hot ∧ not bound∧match rematch | Mild active LTD at \(\eta_B = 0.20\,\eta_E\) (above init floor). Bound∧match rematch is frozen. |
| **D co-active partner** | ON | \(k\geq 2\) authentic spikers on \(\mathcal{A}_t\) | Soft competitive LTD: \(r_i=\eta_{\mathrm{cross}}(1-A_i/\sum A)\) with \(A_i=\sum_{e\in\mathcal{A}_t}w_e\), \(\eta_{\mathrm{cross}}=0.55\,\eta_E\) (Stage 14). Bound∧match rematch skipped only under labeled control. |

**Recall freeze (production, `emergent_autonomy_enabled=false`):** bound ∧ match → **no LTP and no LTD** (including Sites B/D), drive gain \(=0.7\). **Labeled soft autonomy:** rematch LTP/LTD follow ordinary spike eligibility; consolidator uses unique-spike + first-commit-wins. Bound∧mismatch keeps PE-LTD at full drive.

#### 9.4 Full Pfister–Gerstner triplet STDP (lab P2+)

**Sources:** `domain/triplet_trace.py`,
`learning/triplet_plasticity.py`,
`simulation/pulse_spike_time_recorder.py`

Each synapse carries fast/slow presynaptic traces \(r_1,r_2\) and
postsynaptic traces \(o_1,o_2\), decayed using absolute simulation-clock
times. Immediately before trace increments:

\[
\text{on pre:}\quad \Delta w=-o_1(A_2^-+A_3^-r_2),\qquad r_1,r_2\leftarrow r_1+1,r_2+1
\]
\[
\text{on post:}\quad \Delta w=r_1(A_2^++A_3^+o_2),\qquad o_1,o_2\leftarrow o_1+1,o_2+1
\]

The engine records pulse-onset sensory events, actual L1 relay event times,
and L2 postsynaptic spike times. Assigned 5%/85% pulse fractions remain only
as an explicit fallback when a recording is unavailable.

---

## 10. Eligibility traces and pattern consolidation

**Source:** `domain/eligibility_trace.py`, `learning/eligibility_consolidator.py`, `simulation/nucleus_network.py`

Binding uses **eligibility + weight evidence**, not a fixed pulse counter (`bind_required_events` in `neuron.py` is legacy and unused in the nucleus path).

### 10.1 Trace decay (start of every nucleus step)

For each ring competitor trace \(E\):

\[
E \leftarrow E \cdot \max(0,\; 1 - \beta), \quad \beta = \texttt{eligibility\_decay} = 0.05
\]

### 10.2 Trace increment (on each authentic spiker, if eligible)

If `active_edges` equals `last_active_edges`:

\[
E \leftarrow \min(1,\; E + \alpha), \quad \alpha = \texttt{eligibility\_alpha} = 0.40
\]

Else (new pattern presented to this neuron):

\[
E \leftarrow \alpha, \quad \texttt{last\_active\_edges} \leftarrow \mathcal{A}_t
\]

Each authentic spiker updates **its own** trace independently. Diagnostic `WtaOutcome.winner` does **not** monopolize eligibility or LTP.
### 10.3 Consolidation (`try_consolidate`)

`PATTERN_BOUND` occurs only when **all** hold:

1. Neuron not already bound.
2. \(E \geq E_{\mathrm{th}} = 0.80\) (`eligibility_threshold`).
3. `last_active_edges == \(\mathcal{A}_t\)`.
4. Weight evidence (when `consolidation_weight_threshold` is set, default **0.25**):

\[
\mathrm{score} =
\frac{\sum_{e \in \mathcal{A}_t} w_e}{w_{\max} \cdot |\mathcal{A}_t|}
\geq 0.25
\]

On success:

- `NeuronMemory.bind(pattern)`
- Emergent symbol created (§12)
- `prediction` updated from \(\mathcal{A}_t\)
- Trace reset

**Audit:** `diagnostics/learning_integrity.py` verifies every `PATTERN_BOUND` event against these rules.

---

## 11. Descending inhibition (nucleus → L1 E′ → L1 I)

**Source:** `simulation/descending_inhibition.py`

Ring L2E spikes do **not** charge L1 I directly. They charge shape-scoped
**L1 E′** (`l1_ep_*`). When E′ spikes it **force-fires** the paired L1 I.

### Soft delayed path (exclusivity OFF)

At end of timestep \(t\), from nucleus population ring-E spikes (central I id excluded):

\[
N_{\mathrm{spike}} = \#\{\text{ring E spikes in population}\}
\]

For each active shape grid index \(g \in \mathcal{A}_t^{\mathrm{grid}}\):

\[
Q_g \leftarrow Q_g + N_{\mathrm{spike}} \cdot g_{\downarrow}, \quad
g_{\downarrow} = \texttt{l2\_to\_l1\_i\_gain} = 0.18
\]

At delivery (start of \(t{+}1\), or same-tick under exclusivity), scale by plastic EP weight:

\[
u_{E',g} \leftarrow u_{E',g} + Q_g \cdot w_g^{\mathrm{EP}}, \quad Q_g \leftarrow 0
\]

Defaults: \(w^{\mathrm{EP}}_{\mathrm{init}}=1.0\), \(w^{\mathrm{EP}}_{\max}=1.5\)
→ production \(0.26\cdot1.0=0.26\) meets \(\theta_{E'}=0.26\) in **one** L2E pop;
soft/graded labs may lower gain for multi-pop climb. EP weights learn via `AssemblyFlowCreditLearner`
on E′→force-I fire (**even under exclusivity**). NI assembly credit stays frozen.

Then `try_spike` on \(E'_g\). If \(E'_g\) fires → force \(I_g\) to \(\theta_I\) and
`try_spike`; I→E couples onto shape \(E_g\). Subthreshold E′ charge
**accumulates** across ticks until \(\theta_{E'}\)
(`l1_secondary_excitatory_threshold`, default **0.26**).

### Production exclusivity path (flag ON — default)

After authentic nucleus ring-E spikes at \(t\), for each active shape grid index \(g\):

1. Enqueue the same L2E→E′ charge and deliver **same tick** (× \(w_g^{\mathrm{EP}}\)).
2. When \(E'_g\) reaches \(\theta_{E'}\) and spikes → force \(I_g\) membrane to \(\theta_I\) and `try_spike`.
3. Wipe paired \(E_g\) membrane to **0** (when wipe flag ON).
4. Apply local I→E coupling while \(I_g\) register is ONE.

I plasticity on NI channels is **always frozen** (saturated to \(i_{\max}\)); EP afferents remain plastic.

---

## 12. Pattern memory snapshot and symbol generation

**Source:** `domain/pattern_memory_snapshot.py`, `domain/symbol_registry.py`

### Observed assignments (read-only)

`PatternMemorySnapshot` derives pattern → neuron mappings from per-neuron `NeuronMemory` after consolidation. It never blocks learning (Tenant 9).

\[
\text{key}(P) = \texttt{",".join(sorted(edge\_ids))}
\]

- `binders_for_pattern(P)`: **all** ring neuron ids with `bound_pattern == P` (plural / dual-bind ground truth)
- `owner_for_pattern(P)`: first / canonical binder (API compat); training/ecology may use binders
- `as_dict()`: canonical (first) owner per pattern key for diagnostics
- Collision remains **audit-only** — never blocks consolidation (Tenant 9)
- One pattern per neuron; one neuron per pattern at equilibrium (enforced by local plasticity + inhibition)

### Emergent symbols

On consolidation:

\[
\text{symbol\_id} = \texttt{sigma\_}\{k\}, \quad k = 0, 1, 2, \ldots
\]

Bijection: each neuron receives at most one symbol; symbols are **not** catalog labels (`H1`, `V1`, `D0`, `D1`). Catalog ids are presentation labels only.

---

## 13. Recognition and inference

**Source:** `simulation/nucleus_network.py`, `api/recognition_probe.py`

### During training (bound authentic spiker, matching pattern)

If an authentic spiker is bound and `prediction.matches(\(\mathcal{A}_t\))`:

- Emit `SYMBOL_RECOGNIZED` with stored `bound_symbol_id` (`sigma_k`)
- No new plasticity or binding
- Diagnostic `winner` is irrelevant — recognition follows bound match, not sole monopoly

### Prediction errors

Bound neurons stimulated with a **different** pattern emit `PREDICTION_ERROR`.

### Inference-only probe

`POST /api/probe` runs forward pass with `inference_only=True`:

- No excitatory plasticity
- No eligibility consolidation / new binds
- WTA membrane noise silenced

---

## 14. Ecological stimulus stream

**Source:** `simulation/stimulus_stream.py`, `api/service.py`

### What it does (logic only)

- Rotates catalog lines `H1`, `V1`, `D0`, `D1` (default) or presents them stochastically
- Holds each line for `ecological_stimulus_hold_steps` pulses (default 5) before advancing
- Does **not** read `PatternMemorySnapshot`, learned lists, or equilibrium state

### What it does **not** do (no equations)

- No membrane, spike, weight, or trace updates
- No timestep integration on the backend (`auto_stim_interval_ms` paces **frontend** HTTP pulses only)
- No stimulus gain modulation, noise injection, or winner assignment
- No gradients, loss, or reward
- No direct plasticity — only selects which `Pattern` is passed to `BrainSimulator.stimulate_pattern`

---

## 15. End-to-end flow (one pulse, temporal ON)

```
Inter-pulse silence (960 × leak at lif_dt × inter_pulse_leak_scale)
    │
    ▼
Catalog pattern P (3 edges → ONE)
    │
    ▼
[1] Register input events; apply descending pending (t−1) on L1 I
    │
    ▼
[2] Substeps 0..38: L1 subthreshold relay → L2 integrate relay drive
    │                 NI pool integrate (soft NI; no force assists)
    │
    ▼
[3] Final substep: L1 E spike → relays R_t; synaptic scaling; lateral inhibition
    │
    ▼
[4] Nucleus: decay eligibility; apply ring-feedback pending (t−1)
    │          resolve pool; authentic spikers + NI collateral (winner diagnostic only)
    │
    ▼
[5] Plasticity + eligibility + consolidate / recognize (per authentic spiker)
    │
    ▼
[6] Enqueue descending charge on active shape I cells (t+1)
```

---

## 16. Default parameter summary

Synced to `LearningDynamics` in `simulation/learning_dynamics.py` (2026-07-14).

| Parameter | Code | Default | Role |
|-----------|------|---------|------|
| Temporal integration | `temporal_integration_enabled` | **true** | 40 ms substeps + gap leak |
| Stim duration | `stim_duration_ms` | 40.0 | Within-pulse window (ms) |
| Sim dt | `sim_dt_ms` | 1.0 | Sub-step size (ms) |
| Inter-pulse leak | `inter_pulse_leak_scale` | **0.045** | Fraction of per-ms gap leak |
| Membrane τ | `membrane_tau` | **10.0** | LIF leak speed |
| Nucleus threshold | `nucleus_threshold` | **1.05** | Ring E spike threshold |
| Nucleus refractory | `nucleus_refractory_period` | 2 | Ring E refractory steps |
| Relay weight | `nucleus_relay_weight` | **0.075** | Drive per L1 relay |
| Upstream relay | `upstream_relay_weight` | 1.25 | Non-L1 relay drive |
| Collateral gain | `collateral_gain` | 0.45 | Winner relay → central I |
| Central pool gain | `central_pool_gain` | **0.62** | Mean ring → NI (Abhi-like) |
| NI discharge fraction | `central_competition_ni_discharge_fraction` | **1.0** | Functional NI full θ line |
| Central threshold (temporal) | `central_inhibitor_threshold_temporal` | **1.1** | NI spike when temporal ON |
| Central threshold (legacy) | `central_inhibitor_threshold` | 0.8 | NI spike when temporal OFF |
| Central channel init | `central_inhibition_strength` | 1.1 | Per-loser channel \(c_k\) |
| Pre-trained I exclusivity | `pretrained_inhibitor_exclusivity_enabled` | **true** | Force NI + wipe; labeled control: soft NI race |
| Bound rematch drive | `bound_match_recall_drive_gain` | **0.7** | Production rematch attenuation (autonomy OFF) |
| Emergent autonomy | `emergent_autonomy_enabled` | **False** | Labeled soft/graded control: BoundMatch soft gates retire |
| Ring feedback gain | `ring_feedback_gain` | **1.15** | Delayed loser suppression |
| Membrane noise σ | `membrane_noise_std` | **0.01** | Stochastic membrane jitter |
| Fair ties | `wta_fair_ties` | true | Shuffle among equal candidates |
| Eligibility α | `eligibility_alpha` | **0.45** | Trace increment per match |
| Eligibility β | `eligibility_decay` | **0.05** | Per-step trace decay |
| Eligibility threshold | `eligibility_threshold` | **0.80** | Minimum trace to bind |
| Weight evidence | `consolidation_weight_threshold` | **0.25** | Normalized conductance gate |
| E learning rate | `e_learning_rate` | **0.016** | Conductance plasticity |
| I learning rate | `i_learning_rate` | 0.012 | Central channel plasticity |
| E plasticity θ | `e_plasticity_threshold` | **1.85** | Relay target aggregate (membrane-scale) |
| Sensory plasticity θ | `sensory_plasticity_threshold` | **1600** | Sensory target aggregate (evidence-scale) |
| E min / max weight | `e_min_weight` / `e_max_weight` | **1.0** / **1000** | Plastic sensory evidence bounds |
| Sensory init | `sensory_init_weight` | **240** | Random init center (±20% spread) |
| LTD scale (A/C) | `ltd_eta_scale` | **0.40** | η_LTD = scale · η_E |
| Site B hot-nonspiker | `hot_nonspiker_ltd_enabled` | **true** | Mild active LTD on hot losers |
| Site B η scale | `hot_nonspiker_ltd_eta_scale` | **0.20** | η_B = scale · η_E |
| Site D co-active partner | `coactive_partner_ltd_enabled` | **true** | Soft LTD among k≥2 authentic co-spikers |
| Site D η scale | `coactive_partner_ltd_eta_scale` | **0.30** | η_cross = scale · η_E |
| Exc flow-rate | `excitatory_flow_rate_enabled` | **true** | Lazy geometric I trace |
| Exc trace decay | `exc_trace_decay` | 0.8 | Flow-rate decay \(d\) |
| Inh flow-rate | `inhibitory_flow_rate_enabled` | **true** | Sustained suppression drain |
| Inh assembly | `inhibitory_turnover_enabled` | **true** | Hot-gated NI→E with `i_max_weight=2.25` |
| Assembly credit | `assembly_flow_credit_enabled` | **true** | E→I maturation traces |
| Scaling target ρ* | `scaling_target_rate` | 0.15 | L1 E rate target |
| Lateral strength | `layer1_lateral.STRENGTH` | 0.12 | Neighbor suppression |
| L1 I→E init | `DEFAULT_INHIBITION_STRENGTH` | 0.28 | Local pair inhibition |
| L1 E / I θ | `l1_excitatory_threshold` / `l1_inhibitory_threshold` | 0.45 / **0.26** | L1 spike thresholds |
| Descending gain | `l2_to_l1_i_gain` | **0.26** | Nucleus → L1 E′ (≥ θ_E′ one-shot; soft labs may lower) |
| L1 feedforward | `l1_feedforward_gain` | 0.0 | **Not** used for I charging |
| Plasticity mode | `plasticity_mode` | **conductance** | Lab: `stdp` \| `triplet` (roadmap Phase 2) |
| Lab profile | `lab_profile_enabled` | **false** | Enables Phase 3–7 lab flags when true |
| Dual eligibility | `dual_eligibility_enabled` | **false** | Separate LTP/LTD traces + M(t) gate (Phase 3) |
| LTD eligibility α | `eligibility_ltd_alpha` | **0.25** | LTD trace increment |
| Neuromod learn floor | `neuromod_learn_floor` | **0.1** | Minimum M_learn to consolidate |
| Plastic NI (lab) | `plastic_ni_enabled` | **false** | NI channels learn; production frozen |
| Inhibitory STDP (lab) | `inhibitory_stdp_enabled` | **false** | iSTDP on NI→loser channels |
| Scaling lab | `scaling_lab_enabled` | **false** | L1 I + L2 sensory homeostasis |
| Scaling lab η | `scaling_lab_eta` | **0.001** | Slow multiplicative steps |
| Descending mode | `descending_mode` | **force** | Labeled control: `graded` (soft ecology) |
| Auto-stim interval | `auto_stim_interval_ms` | 1000 | Frontend pulse pacing (ms) |

---

## 17. UI ↔ equations map

| Workspace UI | What it reflects |
|--------------|------------------|
| Layer 1 (3D) | Which grid relays fired; E/I pair activity on the shape |
| Ring neuron cards | Eligibility trace / bind progress, owner status, WTA winner |
| L1 / nucleus rasters | `ONE` register events per timestep |
| Weight grid chart | Input conductances \(w_e\) |
| Energy raster | Membrane-derived metrics for active learner |
| Input status line | Current catalog line id + training progress (`n/8`) |
| Output panel | `sigma_k` recognition or learning / prediction-error state |
| Parameters overlay | Live `LearningDynamics` fields (§16) |

---

## 18. Verification tooling

| Tool | Purpose |
|------|---------|
| `tests/test_biological_integrity_stress.py` | Full-catalog + API auto-stim bind audit |
| `tests/test_model_stress.py` | Per-tick invariant auditor (membranes, WTA, ownership) |
| `tests/test_unguided_pattern_learning.py` | Emergent ownership without guided shortcuts |
| `scripts/learning_integrity_probe.py` | CLI audit of `PATTERN_BOUND` evidence |
| `frontend/e2e/biological-integrity.spec.js` | UI contract: no instant bind, stable auto-stim line |

---

## 19. Provenance and references

### What this document is

The equations in §1–§16 are the **implemented update rules** in `backend/cognative_paradigm/`. They are **not** transcribed from a single published model, third-party SNN library, or parameter table in the literature.

**Normative authority** (in order):

1. `Documents/tenants.txt`
2. `Documents/paradigm_spec.md`
3. This file and `Documents/biological_fidelity_spec.md`

Informative neuroscience references in `Documents/grid_and_layers_research.md` §12 and `Documents/paradigm_spec.md` §13 **inform** design choices but **do not override** the tenants or this spec when they conflict.

### One-line summary

Cognative Paradigm uses **phenomenological spiking-network rules** inspired by LIF integration, winner-take-all competition, homeostatic scaling, and eligibility-gated consolidation — but the **exact update equations and all default constants** are defined by this project, tuned via simulation tests, not copied from an external source.

### Component provenance

| Component | Conceptual inspiration | Implementation status |
|-----------|------------------------|------------------------|
| LIF leak, integrate, spike | Standard discrete LIF (e.g. Gerstner & Kistler, *Neuronal Dynamics*) | Same **equation form**; thresholds, \(\tau_m\), and refractory periods are **project constants** |
| Winner-take-all | Lateral inhibition / competitive learning (e.g. Amari 1977; Maass 2000) | **Custom** pipeline: collateral → central I, **next-tick** ring feedback on losers, fair ties, membrane noise |
| Conductance plasticity | Ion-channel / homeostatic plasticity (charge toward equilibrium) | **Original phenomenological rule** in `conductance_plasticity.py` — not classical STDP |
| Eligibility trace | Calcium eligibility / three-factor learning (analogy only) | **Simplified project rule**: decay + increment on matching edge set — not a published three-factor equation |
| Synaptic scaling | Firing-rate homeostasis (common in computational neuroscience) | EMA on L1 I-strength; \(\rho^*\), \(\eta\), window **tuned for the 3×3 catalog task** |
| Descending inhibition | Top-down feedback (concept) | **Engineered** one-timestep delay, shape-scoped L1 I charging |
| Catalog auto-stim | — | **Software scheduler only** — no neural dynamics |
| Emergent `sigma_k` symbols | Sparse coding / grandmother-cell ideas (informative) | **Project symbol registry** — opaque ids, not catalog labels |

### Explicitly not used in the live backend

- **Classical STDP** (Bi & Poo–style \(\Delta t\) windows) — removed; was never the binding gate in the current nucleus path
- **Backpropagation, rate codes without events, global loss** — rejected in `paradigm_spec.md` §9
- **Third-party SNN frameworks as ground truth** — may be referenced for engineering convenience only

### How parameters were chosen

Defaults in `LearningDynamics` (§16) were set by **iterative simulation and test validation**, including:

- Single- and multi-pattern binding (`test_unguided_pattern_learning.py`)
- Long-run invariants (`test_model_stress.py`)
- Bind evidence audit (`learning_integrity_probe.py`, `test_biological_integrity_stress.py`)
- Full catalog equilibrium 4/4 (`test_catalog_auto_stim.py`)

Constants such as `eligibility_threshold = 0.80`, `collateral_gain = 0.45`, and `nucleus_threshold = 1.05` are **stability targets for this workspace**, tuned via simulation tests — not literature-standard biophysical values.

### Informative bibliography (non-normative)

See `Documents/grid_and_layers_research.md` §12 and `Documents/paradigm_spec.md` §13 for the full informal reading list (Hebb, Bi & Poo, Gerstner, Maass, Amari, predictive coding, etc.). Cite those documents for background; cite **this file + `paradigm_spec.md`** for what the code actually implements.

---

## 20. Cross-repo equation alignment (Abhi CIPP vs Paradigm)

**Abhi authority:** `Current_Implementation_Methodology_Equations.md` on branch `AbhiCIPP` (`cipp-learning`).  
**Decision (2026-07-15):** Abhi-align **1A + 2B** — 4-ring mechanism import of tenant-safe kernels only.

### Shared equation kernels (aligned — default ON)

| Kernel | Abhi | Paradigm | Match? |
|--------|------|----------|--------|
| Excitatory flow-rate lazy advance | \(V \mathrel{+}= I(1-d^{\Delta t})/(1-d)\); \(I \mathrel{\leftarrow} Id^{\Delta t}\) | `ExcitatoryFlowTrace` — same formula | **Yes** |
| Normalized injection | \(I \mathrel{+}= g(1-d)\) | `exc_trace_normalized = True` | **Yes** |
| Inhibitory flow-rate drain | \(V \mathrel{\leftarrow} \max(V-J,R)\); \(J \mathrel{\leftarrow} dJ\) | `InhibitoryFlowTrace` | **Yes** |
| Inhibitory turnover | \(u = w/G\); \(\eta_\uparrow,\eta_\downarrow\) | `InhibitoryTurnoverPlasticity` | **Yes** |
| Assembly flow credit | E→I maturation trace φ | `assembly_flow_credit_enabled` on NI + descending | **Yes** |
| Refractory gating | No integrate while \(r>0\) | `Neuron.is_refractory` | **Yes** |
| Soft NI competition | Shared L2I rhythm | `central_pool_gain=0.62`, `ni_discharge=1.0` | **Aligned** |

### Explicitly rejected (2B tenant filter)

| Abhi knob | Why blocked |
|-----------|-------------|
| `eta_loss` FF loser depression | Erases cross-pattern readiness |
| Signed OFF / `eta_off` | Silence is not a teach signal (Tenant 2) |
| `l1i_immediate_relay` | L1 I must integrate descending charge (Tenant 4/9) |

Production defaults use force exclusivity (`pretrained_inhibitor_exclusivity_enabled=true`, `descending_mode=force`) with ``emergent_autonomy_enabled=false`` (BoundMatch rematch freeze + 0.7 drive). Soft NI race + graded descending + Stage 14 autonomy remain labeled control (`exclusivity=false`, `descending_mode=graded`, `emergent_autonomy_enabled=true`).

### Structural differences (keep)

| Topic | Abhi CIPP | Cognative Paradigm |
|-------|-----------|-------------------|
| Catalog | 8 line primitives | 4 center-cell shapes |
| L2 pool | 8 L2E + 1 shared L2I | 4 ring E + central I (NI) |
| Binding gate | Competition + depression | Eligibility + weight evidence + local exclusivity |
| Symbols | Catalog identity | Emergent `sigma_k` |

**Verdict:** We converge on Abhi’s **time + I plasticity** defaults while retaining ownership/eligibility and refusing FF wipe / OFF depression / L1I relay.
---

## Related documents

- `Documents/tenants.txt` — normative rules (authority)
- `Documents/paradigm_spec.md` — formal spec
- `Documents/biological_fidelity_spec.md` — biological learning requirements
- `Documents/grid_and_layers_research.md` — LIF & WTA research notes
