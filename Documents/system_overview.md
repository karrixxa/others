# Cognative Paradigm — System Overview

**One-page summary of the biological workspace:** how layers connect, how neurons behave, and what we tuned in this iteration.

---

## What this system does

Cognative Paradigm is a spiking neural workspace that learns four fixed 3-cell patterns through the center grid cell (`H1`, `V1`, `D0`, `D1` on a 3×3 grid). Each pulse presents one catalog shape; the network must **compete**, **learn locally**, and **bind** each pattern to exactly one nucleus ring neuron. Recognition emits emergent symbols (`sigma_0`, `sigma_1`, …) — not catalog labels. Auto-stim acts as a retinal-ganglion gate: it only presents center-cell shapes; it does not inject winners, weights, or binding shortcuts.

**Recent work:** stable L2 excitatory ramp and WTA cycle; central inhibitory neuron (NI) charged by relay collateral and pool drive (not winner membrane alone); loser depletion on every winner tick; descending L2→L1 inhibition; four center-cell catalog shapes with four ring E neurons; frontend/backend parameter sync; population rasters (E red, I green) with event markers on the shared time axis only. Full test suite passing; biology/tenant invariants verified.

---

## Layer architecture

```
Catalog pattern (3 active grid cells)
        │
        ▼
┌───────────────────────────────────────┐
│  INPUT — nine sensory edges (w_e)     │  Only fired edges register ONE; silence = Z
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│  LAYER 1 — nine E/I pairs (E0–I0 …)   │  E relays sensory drive; I from descending L2
│  + lateral inhibition among neighbors  │  Homeostasis scales local I→E strength only
└───────────────────────────────────────┘
        │  L1 E relays (≤3 per shape)
        ▼
┌───────────────────────────────────────┐
│  LAYER 2 — four ring E (N0–N3)        │  WTA: one winner per tick
│           + central I (NI)              │  Winner → plasticity + eligibility
└───────────────────────────────────────┘
        │  delayed ring feedback (losers)     delayed descending charge (active shape)
        └──────────────────┬──────────────────────────────┘
                           ▼
                    back to L1 I (next tick)
```

**Key connections**

| Path | Direction | Role |
|------|-----------|------|
| Sensory → L1 E | Same tick | Input conductance drives active-cell relays |
| L1 E → L2 E | Same tick (substeps) | Relay count × `nucleus_relay_weight` (0.066) × completion ramp |
| L2 E → central I | Same tick | Mean ring membrane + winner relay collateral (`collateral_gain` 0.45) |
| Central I → L2 E losers | Same tick + next tick | Immediate suppression; delayed ring feedback on losers |
| L2 E spikes → L1 E′ → L1 I | Same-tick under force exclusivity | Descending (`l2_to_l1_i_gain` 0.26 ≥ E′ θ 0.26), shape-scoped |

L1 inhibitory units are **not** driven directly by the stimulus (`l1_feedforward_gain = 0`). Membrane time constant **τ = 10.0**, completion ramp + inter-pulse leak (`inter_pulse_leak_scale = 0.045`) make ring charge climb gradually over **~6 pulses** to threshold and bind over **~18–90 pulses** depending on rotation vs hold. L1 relays fire each presentation; binding requires eligibility + conductance evidence.

---

## How neurons work

Every unit is a **leaky integrate-and-fire (LIF)** neuron with hidden membrane potential, spike threshold, and refractory period. Only the **register** (`ONE` or `Z`) is transmitted — tenant rule: firing is causal; silence is not.

**Per pulse (temporal ON):** inter-pulse silence leak → 40 ms of sub-step integration → final WTA tick.

| Unit | Threshold | Refractory | Notes |
|------|-----------|------------|-------|
| L1 E relay | 0.45 | 1 step | Fires toward nucleus when shape cell is active |
| L1 I | 0.26 | 1 step | Accumulates descending charge across ticks |
| L2 ring E | 1.05 | 2 steps | ~5–6 pulses to first threshold cross (current defaults) |
| Central I (NI) | 1.1 (temporal) | 1 step | Fires from accumulated pool + collateral |

**WTA (Layer 2):** latency WTA — first threshold crossing within pulse wins; at most **one** ring E emits `ONE` per pulse. Losers hyperpolarized immediately; delayed feedback when NI fires.

**Learning (local only):** Authentic ring-E spikers update **their own** sensory and relay conductances. Eligibility trace accumulates on repeated pattern; consolidate when trace ≥ **0.80** and weight evidence ≥ **0.25**. One pattern per neuron at equilibrium.

**Recognition:** a bound winner whose prediction matches the stimulus emits `SYMBOL_RECOGNIZED`; a mismatch emits `PREDICTION_ERROR`.

---

## Normative rules

Implementation follows `Documents/tenants.txt`: event-based causality (1 vs Z), fire-together-wire-together, per-neuron local learning, separate E/I pathways, refractory periods, 1:1 symbol binding, continuous catalog learning until 4/4 equilibrium, and prediction — with **no global loss, backprop, or shortcut binding**.

For full equations and defaults see `Documents/model_equations.md`.
