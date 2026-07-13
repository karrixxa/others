# Four-Pattern Debugging Notes — 2026-07-13

These notes record the current lecture guidance and the corresponding debugging
order for the CIPP/FCSI integration. They are an experiment specification, not a
claim that any proposed mechanism is already validated.

## Immediate goal: make one pattern work

Hold one center-crossing pattern and use a fixed random seed while diagnosing the
dynamics. Do not modify several learning equations at once.

A successful one-pattern run should eventually show:

1. Exactly the three expected L1E sensory cells repeatedly spike.
2. L2E cells initially accumulate charge and compete.
3. The shared L2I neuron is recruited by L2E activity and inhibits competitors.
4. One L2E cell becomes the repeatable winner; the remaining cells may retain
   subthreshold charge but should stop physically spiking for that pattern.
5. Feedback learns the represented pattern and suppresses the corresponding L1
   activity, reducing its firing frequency rather than suppressing unrelated
   sensory cells.

## Four input patterns

All four orientations pass through sensory index 4:

- `row 1`: 3, 4, 5
- `col 1`: 1, 4, 7
- `diag \\`: 0, 4, 8
- `diag /`: 2, 4, 6

The latest lecture suggests retaining eight L2E cells as spare representational
capacity even though there are four patterns. The current branch instead uses four
L2E cells. Treat `N_OUT=4` versus `N_OUT=8` as an explicit architecture decision;
do not change it as part of a parameter sweep.

## Observed failure modes

- Two or more L2E cells can converge to nearly identical receptive fields.
- Close competitors can reach the excitatory weight cap and remain tied.
- The working four-cell baseline can collapse all patterns onto one owner.
- Runner-up inhibition may learn too slowly to break a close race.
- Random initialization can decide the outcome, which is unacceptable as the
  final robustness mechanism.
- L1 inhibitory feedback must be checked for selectivity; synchronized firing of
  all nine L1I cells is not automatically the desired predictive behavior.

## How to read the spike raster

- Time moves left to right. A short vertical dash means that neuron fired at that
  engine step; blank space means no spike, not missing data.
- Each labeled row is one neuron. Turquoise is excitatory and pink is inhibitory.
- A faint numbered grid line marks every 25 engine steps. A stronger vertical line
  marks an input-pattern change. The header always names the currently held
  pattern, even when its boundary has scrolled out of view.
- Several dashes aligned in one column mean those neurons fired synchronously.
- `Hide silent lanes` is on by default to remove the large empty gaps in the
  screenshot. Turn it off when checking whether a supposedly silent cell ever
  participates.
- The left firing-rate bar summarizes the visible/history window; it is not a
  membrane-potential or weight measurement.

In the 2026-07-13 screenshot, `L1E3`, `L1E4`, and `L1E5` fire repeatedly, which is
the correct sensory encoding for `row 1`. All nine pink L1I rows fire together,
showing broadcast feedback. Sparse turquoise spikes on several L2E rows show that
competition is rotating rather than settling on a single owner. Those latter two
features are model behavior exposed by the raster, not canvas rendering errors.

## Equations and state to inventory before changing learning

For every experiment, record the active form and parameter values of:

### Membrane integration

`V(t+1) = (1 - leak) * V(t) + delivered_charge(t)`

### Distance attenuation, when enabled

`delivered_charge = stored_weight / max(distance, distance_min)^distance_power`

### Current signed-spike L2E rule

`delta_w = eta * p * (1 - (w / w_cap)^2) * signal`

where `signal` is positive for currently participating inputs and negative for
non-participating inputs. Record the exact implementation of `p` from
`neuron_flexible.py`; do not infer it from a UI label.

### Inhibitory learning

Record the active inhibitory rule mode, the target's pre-discharge charge, learning
rate, cap, and resulting `delta_w` for every L2I-to-L2E discharge. The core question
is whether the closest runner-up receives the strongest useful inhibitory update.

## Controlled experiment order

1. Fix one seed and one pattern.
2. Measure the unchanged baseline to a predetermined step limit.
3. Inspect raster, normalized charge (`V/theta`), receptive fields, and exact weight
   trajectories together.
4. Check for cap saturation and runner-up inhibitory updates.
5. Change only one variable: inhibitory learning rate, initialization range,
   distance attenuation, weight cap, or charge subdivisions.
6. Repeat the same seed and compare.
7. After a mechanism works, restore multiple seeds and require robustness.

## Minimum metrics

- First and modal L2E winner
- Winner share of L2E spikes over a late window
- Runner-up share and winner/runner-up margin
- Time to stable winner, or explicit failure by the step limit
- L2I spike count and discharge count
- Per-target inhibitory weight before/after
- L2E feedforward weights and fraction of cap
- Pairwise receptive-field cosine similarity
- L1E firing rate before/after feedback
- Which L1I cells fire for the learned pattern

## Measured constructor baseline — `row 1`, seed 1, 8,000 steps

This measurement uses the defaults of `SimulationEngine(...)`, including
`eta_loss=0.01` and `l2e_weight_cap_frac=1.0`. It is **not** the dashboard preset
created in `backend/api.py`, which currently overrides several mechanisms (notably
`eta_loss=10` and `l2e_weight_cap_frac=1/3`). Always record which preset produced
a graph; otherwise two visually different runs can both be mistakenly called the
"baseline."

The unchanged four-L2E baseline does **not** reach one-pattern WTA:

- late L2E spikes: `L2E0=500`, `L2E2=250`, `L2E3=500`
- late modal share: `0.400`; winner/runner-up margin: `0`
- three L2E cells reach their feedforward cap
- all nine L1I cells fire the same number of times, so feedback is broadcast,
  not selective to sensory cells 3, 4, and 5

Increasing turnover `inhibitory_eta_up` from `0.02` through `0.16` changes the
stored inhibitory gates but leaves the late spike trajectory identical. Increasing
the gate equilibrium alone is also ineffective. Therefore the baseline failure is
not simply an inhibitory learning-rate shortage.

Allowing sub-rest inhibition changes early timing slightly but does not break the
late tie. A per-synapse feedforward cap of `theta/3` prevents the `3*theta` drive
extreme but makes all four receptive fields identical for this held pattern; it is
not a standalone solution.

The existing close-loser depression mechanism *does* create a one-pattern winner:

- `eta_loss=1.0`: no stable winner for seed 1
- `eta_loss=1.2`: stable for some, but not all, seeds
- `eta_loss=2.0`: 100% late winner share across seeds 1–5 in the 8,000-step
  single-pattern diagnostic

This does not establish `eta_loss=2` as the four-pattern default. Strong loser
depression can erase cells needed for later patterns, and the short interleaved
four-pattern harness showed no improvement. Keep it as a one-pattern experimental
condition until retention/recruitment is demonstrated.

## Reproduce the diagnostic

From `cipp-learning-AbhiCIPP/` with the virtual environment active:

```bash
PYTHONNOUSERSITE=1 PYTHONPATH=. python single_pattern_diagnostic.py \
  --pattern "row 1" --seed 1 --steps 8000
```

Compare one variable while keeping the pattern, seed, and duration fixed:

```bash
PYTHONNOUSERSITE=1 PYTHONPATH=. python single_pattern_diagnostic.py \
  --pattern "row 1" --seed 1 --steps 8000 --eta-loss 2
```
