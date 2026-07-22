# Validation report — 2026-07-14

## Test results

| Suite | Result |
|---|---|
| Backend pytest (full) | **208 passed** (after sensory/relay θ split) |
| Frontend unit | **51 passed** |
| Playwright e2e smoke | blocked (Chromium not installed in env) |
| Live API/mastery 4/4 | **ok** (binds each catalog line) |

Services checked: `:8000` backend, `:5173` workspace, `:5174` rasters.

## Root calculation bug (fixed)

Sensory LTP free energy `F_E = θ − ∑w_active` used **θ = 1.85**. For 3-edge catalog shapes, weights plateau at **mean ≈ 0.617** (score ≈ 0.308 of `e_max=2.0`). That is why heatmaps stuck near ~0.60 and consolidation >0.31 never bound — **not** because of soft-sat to `e_max`.

**Fix:** split thresholds:
- `e_plasticity_threshold = 1.85` — relay LTP (keeps L1 fire-rate viable)
- `sensory_plasticity_threshold = 3.2` — sensory/heatmap LTP (plateau mean ≈ 1.07, score ≈ 0.53)

## Other integrity fixes shipped

- Wire plasticity θ from `LearningDynamics` into the learner (was hardcoded / unwired)
- FE/BE default sync (`membrane_noise_std`, `recall_drive_gain`, energy fallbacks)
- Checkpoint restores `eligibility_last_active_edges` (was wiped on next spike)
- Energy raster rewind uses `timestep <= last` (aligned with spike history)
- `reset_neuron` uses live dynamics, not hardcoded defaults

## Remaining / lower priority

- No UI slider for `sensory_plasticity_threshold` yet (serialized in parameters)
- Playwright browsers not installed (`npx playwright install`)
- `Documents/model_equations.md` still lists some stale defaults
- Spike-time energy bar still shows full when `register=1` while membrane reset to 0 (display choice)
