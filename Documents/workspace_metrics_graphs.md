# Workspace Metrics Graphs

This document explains the metrics panels for the stable Cognative Paradigm workspace (`#/workspace`). Charts update every stimulation step from `/api` state via `SpikeRasterHistory`, `EnergyRasterHistory`, and `MetricsChartsPanel`.

**Workspace UI:** controls on the left, all charts stacked on the right (rolling ~240-step window):

| Left | Center | Right |
|---|---|---|
| Input | 3D brain | L1 Excitatory Raster |
| Nucleus Ring | | L1 Inhibitory Raster |
| | | Nucleus Raster |
| | | Energy Raster |

Hover a graph title for a short tooltip; this file is the full guide.

---

## Shared rules

- **X-axis (rasters):** simulation timestep `t` (rolling window ~240 steps).
- **Y-axis (rasters):** one fixed neuron row per train in that layer catalog.
- **Marker:** a vertical tick = one `SPIKE` event (`type === "SPIKE"`).
- **Reset / timestep 0:** spike and energy history clear; rasters go empty until the next stim.

---

## Spike rasters (three layer panels)

Industry convention: time on X, one spike train per neuron on Y, marker = event only (no waveform). Rows stay visible even when quiet so empty trains are obvious at this small N.

Backend SPIKE coverage (visualization log; learning / WTA winner selection unchanged):

- Every L1 E relay that fired (`l1_e_*`)
- Every L1 I that fired (`l1_i_*`)
- Only the **WTA winner** ring E that registered ONE this tick (`nucleus_e_*`)
- Central I when its register is ONE (`nucleus_i`)

### 1. L1 Excitatory Raster

| | |
|---|---|
| **Rows** | `l1_e_0` … `l1_e_8` |
| **Color** | Red (excitatory) |

Shows which grid relays spiked. A stimulated 3-cell line often lights three rows together; incomplete biology shows fewer.

### 2. L1 Inhibitory Raster

| | |
|---|---|
| **Rows** | `l1_i_0` … `l1_i_8` |
| **Color** | Green (inhibitory) |

Local pair inhibition. I often fires with (or just after) its E partner on active cells.

### 3. Nucleus Raster

| | |
|---|---|
| **Rows** | `nucleus_e_0` … `nucleus_e_7`, then `nucleus_i` |
| **Colors** | Red (ring E), green (central I) |

Ring competition and central arbitration. At most **one** ring E row per timestep (the WTA winner); `I` ticks = central WTA fired.

### How to read the three together

1. Pattern stim → L1 E ticks on the three active cells.  
2. Matching L1 I ticks on those cells’ local inhibitors.  
3. Nucleus E / I ticks as WTA settles a learner.

---

## 4. Energy Raster

| | |
|---|---|
| **Type** | Time × neuron heatmap |
| **Source** | `layer1.pairs[*].{excitatory,inhibitory}_membrane`, `nucleus.ring[*].membrane`, `nucleus.central_inhibitor_membrane` |
| **Rows** | Same catalog as all spike rasters combined (L1 E, L1 I, nucleus E, nucleus I) |
| **Color** | Blue (low energy) → red (near / above threshold) |

Shows **subthreshold membrane accumulation** each unit is carrying. Normalized per neuron type against its threshold (L1 E 0.45, L1 I 0.28, ring E 1.2, central I 0.8). NI subthreshold display is capped at 98% of threshold until spike.

**Why separate from spike rasters:** spikes are discrete events (vertical ticks); energy is continuous. Overlaying both clutters timing. Side-by-side rasters + energy heatmap keeps spikes crisp while showing buildup.

### How to read energy vs spikes

1. Energy raster warms (blue → red) on a row as that neuron integrates drive.  
2. When energy crosses threshold, the matching **spike raster** shows a tick on that row at the same `t`.  
3. Central I warming in the bottom band often precedes green `nucleus_i` ticks in the nucleus spike raster.

---

## Implementation pointers

| Concern | Location |
|---|---|
| Chart layout | `frontend/src/app/charts/MetricsChartsPanel.js` |
| Spike history + layer catalogs | `frontend/src/app/charts/SpikeRasterHistory.js` |
| Raster drawing | `frontend/src/app/charts/SpikeRasterChart.js` |
| Energy history + extraction | `frontend/src/app/charts/EnergyRasterHistory.js` |
| Energy heatmap drawing | `frontend/src/app/charts/EnergyRasterChart.js` |
| Side-column layout | `frontend/src/app/charts/MetricsChartsPanel.js` |
| Tooltips | `frontend/src/app/ui/sectionDescriptions.js` |
| Population SPIKE logging | `wta_coordinator.py`, `competitive_layer.py`, `nucleus_network.py`, `layer1_network.py` |
