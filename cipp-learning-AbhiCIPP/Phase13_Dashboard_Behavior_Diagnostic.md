# Phase 13 — Dashboard Behavior Diagnostic (july14-integration)

**MEASUREMENT ONLY.** No neural mechanism was changed and no parameter was
tuned to fix anything in this phase; every number below comes from running
the existing engine (`backend/simulation.py`) through
`dashboard_behavior_diagnostic.py` (new, this phase — read-only
instrumentation, same non-mutating-observer discipline as
`diagnostic_schedule.py`/`phase11_validation.py`).

## Reported symptom

> "when I'm running the simulation, it seems that only 3 neurons are actively
> participating with a tyrant, unsure as to why, I want more of the neurons
> to be recruited."

## Method

Seed = 1 (the same first seed used in every prior sweep — Phase 5's baseline,
Phase 11's validation). Three configs, identical seed and pattern timing:

| Config | distance_weighting | adaptive_threshold | Everything else |
|---|---|---|---|
| **default** | True (dashboard default) | False (dashboard default) | `DASHBOARD_PRESET` |
| **A** | False | False | `DASHBOARD_PRESET` |
| **B** | False | True | `DASHBOARD_PRESET` |

Two reproductions, both instrumented:
1. **Hold/switch** — reset → hold `row 1` for 20 steps → switch to `col 1`
   for 20 steps (steps 1–3 of the report).
2. **Equal-interleaved schedule** — the brief's fixed cycle (`row 1 → col 1 →
   diag \ → diag /`, 20 steps each — `diagnostic_schedule.PRESENTATION_STEPS`/
   `CYCLE_ORDER`, Phase 5/11 precedent), 40 full rotations (3,200 steps),
   reused directly rather than reimplemented.

Every `Neuron.fire()`, `Neuron.apply_delayed_inhibition()`,
`Neuron._homeostatic_scaling()`, and
`SimulationEngine.set_feedforward_weight()` call on every L2E neuron was
wrapped (calls the original unchanged, only observes before/after weight
arrays and the method's own already-returned diagnostic dict) to record,
for every L2E feedforward weight delta: timestep, pattern, neuron, whether
that neuron itself spiked this step, cause, L2I delivery source/time (the
scheduled delivery record's own `fire_t`/`contributors` — never re-derived),
V_pre, threshold, effective_threshold, p_loss, active input pixel indices,
and weight before/delta/after. Raw counts: 15,728 / 13,048 / 10,177 records
(default/A/B) across both reproductions combined. Full per-event logs are
disposable diagnostic artifacts (tens of MB) and were written to
`/tmp` rather than committed, per this repo's own commit-hygiene rule
(`CLAUDE.md`); `dashboard_behavior_diagnostic_summary.json` (committed) has
every aggregate figure quoted below, plus example records like the two
shown here.

Example self-spike record (default, hold scenario, t=7, `row 1`):
```json
{"t": 7, "pattern": "row 1", "neuron": "L2E5", "spiked": true,
 "cause": "self_spike_exact_fe", "pixel": 0, "pixel_active": false,
 "v_pre": 8041.517, "threshold": 8000.0, "effective_threshold": 8000.0,
 "active_inputs": [3, 4, 5], "w_before": 168.1497, "delta": -38.082,
 "w_after": 130.0677}
```
Example loser-depression record (same run, t=11):
```json
{"t": 11, "pattern": "row 1", "neuron": "L2E0", "spiked": false,
 "cause": "l2i_loser_depression", "pixel": 3, "pixel_active": true,
 "v_pre": 7900.767, "threshold": 8000, "p_loss": 0.9876,
 "active_inputs": [3, 4, 5], "l2i_source": ["7:L2E5", "9:L2E4", "10:L2E3"],
 "l2i_time": [10], "w_before": 98.0304, "delta": -3.2554, "w_after": 94.775}
```

## RF UI vs. backend weights

`topology()`'s serialized synapse `weight` field is read from the exact same
`_all_weights()` dict the engine itself uses internally — there is no
separate UI-side computation path. Verified directly (not just by reading
the code): every `ff{i}->{j}` synapse's UI value was diffed against
`engine.l2.excitatory_neurons[j]._weights_array[i]` for both reproductions,
all three configs. **Exact match in every case (0 mismatches, 216 synapses
checked per run × 6 runs).**

## Findings, in the order asked

### 1–2. Non-spiking L2E weight increases / how much is loser depression

**Zero non-spiking L2E weight increases in any config, any run.** Every
recorded delta on a neuron that did NOT itself spike this step is a
**decrease**, and **100% of non-spiking weight changes are
`l2i_loser_depression`** (9,497 / 8,347 / 5,906 events for default/A/B; the
other two possible causes, homeostasis and manual edit, are both silent by
construction — `homeostasis=False` in every config here and no RF panel
edits occur in a scripted run). This follows directly from the code: the
only two weight-mutating paths on L2E are `fire()`'s own self-spike rule
(which by definition only runs on a spike) and `apply_delayed_inhibition`'s
structural depression branch, which only ever subtracts (`signal=-1`,
`bounded_signed_update` clipped at `[w_min, w_cap]`). There is no
non-spiking potentiation path in this engine as currently configured.

### 3. Does L2E5 form the union of row 1 and col 1?

**No — this is the central finding, and the naive "union" test is
misleading.** After the full interleaved run, L2E5's feedforward weights
(default config) are:

| pixel | 0 | 1 | 2 | 3 | 4 (center) | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| weight | 1.0 | 1.0 | 230.8 | 1.0 | **2362.85** | 1.0 | 230.8 | 1.0 | 1.0 |

row 1 ∪ col 1 = pixels {1, 3, 4, 5, 7}. Averaging that set gives 473.4 vs.
115.9 for the rest — which LOOKS like a union receptive field, but that
average is entirely an artifact of including pixel 4. Excluding pixel 4,
the genuine row/col-distinguishing pixels {1, 3, 5, 7} are all sitting at
**1.0 — the hard floor** (`L2E_MIN_WEIGHT_FLOOR`/`pos_weight_floor`), while
the two off-union diagonal pixels {2, 6} sit at 230.8. **L2E5 has not formed
a union of row 1 and col 1; it has collapsed onto the one pixel shared by
every pattern (the center) and let its actual distinguishing pixels atrophy
to the floor.** Same qualitative shape in configs A and B (center pixel
dominant, distinguishing pixels near-floor), confirmed at both 10 and 40
interleaved cycles — this is not a transient.

**Why:** pixel 4 (center) is active in all four trained patterns (row 1,
col 1, diag \, diag /) — every one of PATTERNS' vectors has index 4 set.
Any time this neuron fires, under ANY pattern, pixel 4 is always
"participating" so it always gets the `+1` (potentiate) signal and never
the `-1` (depress) signal from `SignedSpikeRule`'s OFF-gate branch. A
pattern-specific pixel (e.g. 3 or 5, only active during row 1) gets `+1`
only on a row-1-triggered fire and `-1` on every OTHER pattern's fire by
this same neuron — a tug-of-war that nets toward depression for any neuron
that isn't a clean single-pattern specialist. The center pixel has no such
opponent process, so it ratchets up unopposed while a mixed-identity
neuron's real receptive field gets squeezed to the floor.

### 4. Do exact-FE-capped weights become unable to depress?

**Structurally yes (confirmed by direct code reading); not fully triggered
within the measured run length, but the predicted slowdown is already large
and measurable.** `exact_local_free_energy_update` (self-spike path, gated
by `structural_free_energy=True`, the dashboard default) uses envelope
`(1 - w/w_max)^2`, symmetric and → 0 at `w_max` in BOTH directions — a
weight at the cap literally cannot move via this path until it decays.
`apply_delayed_inhibition`'s loser depression uses the DIFFERENT
`bounded_signed_update` kernel, whose downward branch `H_down(q) = 1 - (1-q)^2`
is REFLECTED — maximal (not zero) at the cap.

A 150-cycle extended run (default config, L2E5's center pixel, beyond the
40-cycle headline number) pushed that weight to 2590.74 out of a
`weight_cap` of 2666.67 (97.2% of cap) with 0 events recorded as a literal
"stuck exactly at cap" (delta=0) — no weight fully saturated within this
run's duration. But the two kernels' envelope VALUES at that same weight are
already starkly different:
- self-spike exact-FE envelope: `(1 - 2590.74/2666.67)^2 ≈ 0.0008` — throttled
  to **~0.08%** of its unsaturated rate.
- loser-depression `H_down(q)` at the same weight: `1 - (1-0.9715)^2 ≈ 0.999`
  — still **~99.9%** of its maximum.

**A >1000x asymmetry at the same weight value.** As training continues past
this run's length, the self-spike path for a habitually-participating pixel
(like the center) will keep climbing toward the cap and then effectively
freeze there, while loser depression (whenever this neuron is a
delayed-inhibition target) keeps depressing that SAME weight at nearly full
strength — a structural, not tuned-parameter, asymmetry between the two
mechanisms.

### 5. Does legacy distance amplification give the center pixel excessive influence?

Read directly from `pathway_influence_report()['l1e_l2e']` (never
recomputed ad hoc): mean influence for the center pixel (L1E4) is **2.1277**
across all 8 L2E targets (uniform — L1E4 sits at the ring's geometric center,
equidistant from every L2E home in the legacy/symmetric layout, so this
factor is identical for every neuron), vs. **1.9414** mean for the other 8
pixels. That's a real but modest ~9.6% relative amplification, not by
itself "excessive." **The center pixel's dominance in finding 3 is driven
far more by its 100% duty cycle (active in all 4 trained patterns vs. 1–2
for any other pixel) than by this ~10% distance boost.** Confirms this is
NOT primarily a distance-weighting bug — turning `distance_weighting` off
(configs A/B) did not fix recruitment; it made it measurably WORSE (see
finding 6).

### 6. Why do L2E6/L2E7 (or other neurons) remain unrecruited?

**Depends heavily on config, and this is where the reported symptom is
reproduced almost exactly.** Final evidence-based RF status
(`_l2e_status`, built only from actually-observed spikes, after the full
40-cycle interleaved run):

| Config | unrecruited | quiet | active | active count |
|---|---|---|---|---|
| **default** | L2E0, L2E1 | L2E2, L2E3 | L2E4, L2E5, L2E6, L2E7 | **4/8** |
| **A** (distance off, adaptive off) | L2E0, L2E1, L2E6 | L2E2, L2E3, L2E5, L2E7 | **L2E4 only** | **1/8** |
| **B** (distance off, adaptive on) | L2E0, L2E1, L2E6 | L2E2, L2E7 | L2E3, L2E4, L2E5 | **3/8** |

**Config B reproduces the reported symptom almost exactly: 3 actively
participating neurons, with L2E4 as the tyrant** (it is active and dominant
in every config, always the first/heaviest-recruiting neuron). Config A is
worse still — a single tyrant (L2E4) and nothing else. The DEFAULT
(dashboard-shipped) config is the best of the three at 4/8, still short of
full recruitment but recruiting L2E6/L2E7 too (which A/B never do at all —
`spikes_total=0` for L2E6 in both A and B, vs. 167 spikes/"active" in
default).

L2E0/L2E1 stay `unrecruited` (spikes_total=0) in **every** config — never
close to firing at any point in any run. This is consistent with initial
condition + entrenchment: `legacy_wide_feedforward_init` draws each neuron's
9 weights independently and uniformly from [50, 200] (no task structure at
init), so some neurons start with weak weights on the pixels that matter for
any pattern purely by chance; once a handful of OTHER neurons (L2E4 first,
generally) start winning consistently, `loser_depression` steadily erodes
the losers' participating weights every time L2I fires (9,497 such events in
the default run alone, ALL on non-spiking neurons per finding 1–2) while the
current winners keep climbing via self-spike potentiation — a
rich-get-richer dynamic with no mechanism in this engine to specifically
rescue a neuron that never got an early lead. **Turning distance_weighting
off removes what little differentiating signal existed and makes the
lock-in worse, not better** — this is the opposite of what one might guess
("distance weighting must be biasing things"), and is a genuinely useful,
non-obvious result from this measurement.

### 7. Do all nine L1I units remain synchronized?

**Yes, in every config, exactly as documented since Phase 9.** Directly
verified two ways: (a) all nine `L1I{i}.weights` vectors are
byte-identical (`np.allclose`) at the end of every run — expected, since
`_build()` assigns every L1I neuron a COPY of the SAME
`l1i_feedback_init` vector and none of the changes in configs A/B (distance,
adaptive threshold) touch L1I's own weights or its `infl_l2e_l1i` flag
(off in all three configs); (b) the "all nine fire together" rate across
every step in which at least one L1I fired is **exactly 1.0** in every
config. This is a structural fact of the current wiring (identical init +
identical input + identical dynamics = identical output), not a bug and not
something distance/adaptive-threshold toggles can change.

## Direct answer to "why only 3 neurons, and how do I get more recruited?"

This measurement does not implement a fix (out of scope, per instruction),
but the diagnostic identifies the mechanism precisely:

1. The center pixel (active in all 4 patterns, ~10% distance-amplified) has
   no opponent process in the signed-spike rule and ratchets up unopposed in
   every neuron that ever fires, crowding out genuine per-pattern receptive
   fields (finding 3).
2. `loser_depression` uniformly erodes every non-firing neuron's currently-
   active-pixel weights every time L2I fires (finding 1–2), with no rescue
   mechanism for a neuron that never got an early lead — a rich-get-richer
   dynamic (finding 6).
3. Once a weight from #1 approaches the exact-FE cap, self-spike learning on
   it slows by >1000x relative to the still-strong loser-depression pressure
   on the SAME weight (finding 4) — reinforcing whichever pattern-agnostic
   feature already won.
4. Turning `distance_weighting` off (the naive "maybe distance is the
   culprit" fix) makes recruitment **measurably worse** (4/8 → 1/8 or 3/8) —
   ruling that out as the lever to pull. `adaptive_threshold` on its own
   (config B vs A) helps somewhat (1/8 → 3/8) but does not restore what the
   dashboard default already achieves (4/8).

## Final commit chain / working-tree status

This diagnostic continues directly from the Phase 12 checkpoint (`e4ee1f9`).
No engine file (`backend/simulation.py`, `neuron_flexible.py`, `snn/*`,
`backend/api.py`) was touched. New files this phase:
`dashboard_behavior_diagnostic.py` (the instrumented, reusable measurement
script) and `dashboard_behavior_diagnostic_summary.json` (the compact,
committed aggregate data backing every number above — the full per-event
log is a disposable `/tmp` artifact, not committed). Branch
`july14-integration`; `july14` untouched; not pushed, not merged, no PR.
