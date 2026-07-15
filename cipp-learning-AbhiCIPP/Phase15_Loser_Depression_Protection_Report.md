# Phase 15 — Local Developmental Protection from L2I Loser Depression

**New default-off neural mechanism** (the first actual dynamics change since
Phase 10). Everything else preserved exactly per instruction: random
legacy-wide initialization (untouched, not balanced/equalized), physical
threshold crossings (Phase 6), delayed causal L2I inhibition (Phase 7), no
argmax/software WTA, no assigned owners/pattern labels/neuron-index rules/
global comparisons, current dashboard defaults unchanged unless this
experiment earns promotion later (it does not — see Conclusions).

## Mechanism

`Neuron._loser_depression_maturity()` (new):
```
maturity = clamp(self.ca / self.loser_depression_protection_ca_ref, 0, 1)
```
`self.ca` is the neuron's own slow EMA of its own physical spiking — already
computed **unconditionally** every step in `Neuron.update()` regardless of
the `homeostasis` flag (`self.ca += self.ca_rate * (spiked - self.ca)`), so
this phase reads an existing local signal and changes nothing about how it
is computed. `loser_depression_protection_ca_ref` (default 0.02, a single
documented constant, never swept per seed) is the ca value at which maturity
reaches 1.0.

In `apply_delayed_inhibition`, the structural weight-depression gain becomes:
```
gain = learning_rate * structural_gate * p_loss * competitive_reset_influence * maturity
```
`maturity` multiplies in alongside the existing factors — **only** the
plastic weight-depression term. The physical inhibitory transient
(`V = max(V - magnitude, resting_potential)`) is computed **unconditionally**,
after and independent of the depression branch — it never reads `maturity`
at all. Self-spike learning, distance/influence, leak, adaptive threshold,
L1I, and initialization are untouched (verified directly, see Tests).

Default OFF (`loser_depression_protection=False`): `maturity` is hardcoded to
`1.0`, so the gain is byte-for-byte what every prior phase computed.

## Tests (11, all passing — `test_loser_depression_protection.py`)

- `test_maturity_gate_formula` — the clamp/ramp formula itself.
- `test_zero_maturity_reduces_only_weight_depression` — ca=0 fully suppresses
  the weight change while the membrane transient still applies at full
  magnitude.
- `test_inhibition_changes_membrane_normally_regardless_of_flag` — the
  post-inhibition membrane value is identical across off / on-immature /
  on-mature.
- `test_maturity_approaches_normal_depression_smoothly` — depression
  magnitude rises **monotonically** as ca rises from 0 to `ca_ref`, and
  exactly matches the unprotected baseline once ca ≥ `ca_ref`.
- `test_experienced_competitor_fully_depressible` — ca ≫ ca_ref depresses
  identically to the flag being off.
- `test_protection_never_potentiates` — no ca value ever increases a weight
  in this branch.
- `test_isolation_between_neurons` — one neuron's maturity never affects
  another's.
- `test_flag_off_is_baseline_equivalent_unit_level` / `test_engine_flag_off_is_baseline_equivalent`
  — explicit-off and omitted-flag are byte-identical, at both the unit and
  full-150-step-engine-run level.
- `test_locality_no_cross_neuron_or_pattern_state` — AST-based proof (same
  technique as Phase 8's structural-FE locality test) that
  `_loser_depression_maturity`'s executable body references nothing but
  `self.ca`/`self.loser_depression_protection_ca_ref` — no rival neuron, no
  `self.winner`, no pattern identity, no membrane voltage.
- `test_engine_protection_does_not_touch_l1i_or_distance_or_self_spike` — L1I
  weights and the distance/influence pathway report are byte-identical with
  the flag on or off.

Full suite: **276 passed, 5 failed** (the same pre-existing flow-rate
failures documented since before Phase 6 — unaffected).

## Comparison method

Configs, identical weight/topology seeds, everything else `DASHBOARD_PRESET`:
- **A** — current default (`loser_depression_protection` omitted/False).
- **B** — protection enabled (`loser_depression_protection=True`,
  `ca_ref=0.02`, the single documented default — never tuned per seed).

Grid: weight seeds 1–5 × topology seeds 1–3 (15 combinations) × 2 scenarios ×
2 configs = 60 runs (`phase15_loser_depression_protection.py`):
1. **20-step equal interleaving**, 40 rotations (reuses
   `diagnostic_schedule.CYCLE_ORDER`/`_present_and_record`/`summarize`
   directly, same precedent as Phase 11/13b).
2. **Long row-hold then column switch** — 600 steps `row 1`, 200 steps `col 1`.

## Findings

### Recruitment breadth (active/quiet/unrecruited, mean over 15 combos)

| Scenario | Config | active | quiet | unrecruited |
|---|---|---|---|---|
| long_hold_switch | A | 1.40 | 1.60 | 5.00 |
| long_hold_switch | B | 1.20 | 1.80 | 5.00 |
| interleaved_40 | A | 3.60 | 1.80 | 2.60 |
| interleaved_40 | B | **3.80** | 2.20 | **2.00** |

A small, real improvement in the **interleaved** schedule (fewer
unrecruited, more active) — **no improvement, slightly worse**, in the
**long-hold** schedule.

### Distinct, stable ownership (Phase-11-style, interleaved_40)

| Config | per-seed distinct_owners | mean | mean collisions | mean forgetting | mean ambiguity |
|---|---|---|---|---|---|
| A | 4,4,4,4,4,4,3,3,3,4,4,4,3,3,3 | 3.6 | 0.40 | 1.00 | 0.0312 |
| B | 4,4,4,3,3,3,3,3,3,2,2,2,4,4,4 | **3.2** | **0.60** | **1.60** | **0.0363** |

**Protection makes stable ownership WORSE, not better**, on the metric that
actually matters most (Phase 11's own success criterion). This is the key
tension in this phase's results: more neurons participate at all (previous
table) but the competition among them is measurably less stable — more
collisions, more forgetting between visits, slightly more same-step
ambiguity. **Recruitment breadth and ownership stability move in opposite
directions here.**

### Tyrant share (mean)

| Scenario | A | B |
|---|---|---|
| long_hold_switch | 0.465 | 0.468 |
| interleaved_40 | 0.538 | 0.553 |

**Essentially unchanged, if anything very slightly worse under B.**
Protection does **not** meaningfully reduce how dominant the single
most-firing neuron is — it does not address tyranny.

### Loser-depression magnitude grouped by local maturity (aggregated, all B runs, both scenarios)

| Maturity bucket | n events | mean \|Δw\| |
|---|---|---|
| 0.00–0.25 | 59,961 | 0.0074 |
| 0.25–0.50 | 864 | 0.7813 |
| 0.50–0.75 | 558 | 1.5277 |
| 0.75–1.00 | 37,668 | 2.7817 |

A clean, monotonic ramp across 60 runs and ~99,000 depression events — the
maturity gate produces smoothly graduated depression exactly as designed,
not a step function. (The top bucket's 2.78 magnitude matches config A's
unprotected depression scale, confirming full-strength depression is
preserved for mature/experienced competitors, per
`test_experienced_competitor_fully_depressible`.)

### Do protected neurons eventually fire and specialize?

**No — 0 of 75** neurons that had never fired at the row-1 hold's halfway
checkpoint (600 steps in) ever fired by the end of the run (200 more steps
of `col 1`), under **either** config. Protection alone, within this
timeframe, does not rescue a neuron that has already fallen behind — reduced
depression is not the same as an active recruitment signal. This is an
honest negative result for the specific question asked.

### Does protection merely create excessive simultaneous firing?

**No.** Mean same-step multi-firer rate is essentially unchanged, if
anything marginally lower under B:

| Scenario | A | B |
|---|---|---|
| long_hold_switch | 0.1730 | 0.1682 |
| interleaved_40 | 0.0107 | 0.0096 |

Protection does not destabilize the network into excessive concurrent
firing — the mild ownership-instability seen above (more collisions/
forgetting) is not explained by more simultaneous winners.

### Physical inhibition events — unchanged where expected, diverges where expected

The **mechanism** itself is unconditional and provably unaffected by the
flag (unit-tested directly, see Tests). At the **network** level, comparing
`physical_inhibition_applied_count` for identical seed/topology pairs:

- **`long_hold_switch`: 0 mismatches across all 15 seed/topology combinations
  — byte-identical between A and B.** In this scenario the never-fired
  neurons' reduced depression never changes who wins or when L2I fires.
- **`interleaved_40`: all 15 combinations diverge** (e.g. seed 1: 5392 (A)
  vs. 5536 (B); seed 3: 6064 (A) vs. 5264 (B)). This is **expected, not a
  violation** of "physical inhibition must remain unchanged": protection
  changes which weights survive depression, which changes future charge
  accumulation, which changes future spike timing, which changes when L2I
  itself fires — a closed feedback loop. The instantaneous mechanism (the
  transient math for any single delivery) is identical A vs. B always,
  proven at the unit level; the network's downstream *trajectory* of when
  deliveries occur legitimately diverges once repeated interleaved exposure
  gives the mechanism room to compound. This is reported precisely rather
  than claiming a false global invariant.

## Conclusions — negative result, not promoted

The protection mechanism does exactly what it was designed to do
mechanically (smooth, local, correctly-scoped, unit-proven, zero side
effects on every other mechanism) but **does not solve the recruitment
problem it was aimed at**, and introduces a real trade-off:

1. A small, genuine improvement in raw recruitment breadth under the
   interleaved schedule (fewer permanently-unrecruited neurons).
2. A real **degradation** in ownership stability under the same schedule
   (fewer distinct owners, more collisions, more forgetting).
3. **No effect** on tyrant dominance in either schedule.
4. **No effect** on rescuing neurons that already failed to fire within a
   presentation window.
5. No unwanted side effect of excessive simultaneous firing.
6. Physical inhibition timing is provably unaffected instantaneously, and
   empirically unaffected in the long-hold schedule specifically, diverging
   only where the mechanism's own compounding effect is expected to reach.

**Per this phase's own instruction ("current dashboard defaults unless this
experiment later earns promotion"): it has not earned promotion.** The
mechanism is implemented, tested, and measured — left as an opt-in,
default-off experiment (`loser_depression_protection=False`), not adopted as
a new default. This is consistent with every prior phase's finding that the
central one-to-one ownership-consolidation problem remains open; local
developmental protection alone, at this reference scale, is not the fix.

## Files

- `neuron_flexible.py`: `_loser_depression_maturity()`, the two new
  attributes, and the `apply_delayed_inhibition` gain change (see docstring
  updates in that method).
- `backend/simulation.py`: two new constructor params (`TUNABLE`-registered),
  L2E-only wiring in `_build()`, `maturity` exposed in
  `dynamic_state()['l2_inhibition']`'s per-target records.
- `backend/api.py`: two new `CONFIG_SPEC` entries (advanced panel, matching
  Phase 7/10 precedent).
- `test_loser_depression_protection.py` (new) — 11 tests, see above.
- `phase15_loser_depression_protection.py` (new) — the A/B comparison
  script.
- `phase15_loser_depression_protection_summary.json` (new, committed) — the
  60-run grid backing every table above.
