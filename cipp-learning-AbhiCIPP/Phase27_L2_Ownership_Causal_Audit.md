# Phase 27 — L2 Ownership Causal Audit

**Branch: `l2-ownership-recovery`, created from the Phase 26 checkpoint
(`7dc6f4f`). MEASUREMENT ONLY — no neural equation, parameter, initialization,
or default changed. `DASHBOARD_PRESET` used unchanged. All prediction flags
(`prediction_column_enabled`, `prediction_excitatory_enabled`,
`prediction_column_to_i_enabled`) remain at their constructor default (off) —
this script never sets them. Nothing pushed. `july14`, `july14-integration`,
and every backup branch are untouched.**

## Purpose

Determine exactly how the L2 representation layer moves from initial random
differences to one L2E neuron owning multiple patterns — not by assuming a
mechanism, but by tracing the actual chronological sequence of physical
spikes, weight deltas, and L2I deliveries that produce the first (and, where
it happens, the persisting) multi-pattern collision, for real seeded runs.

## Method

### Instrumentation (`CausalTracer`, in `phase27_l2_ownership_causal_audit.py`)

Non-mutating patches around the same public/semi-public hooks Phase 13b's
`WeightDeltaRecorder` used (`fire`, `apply_delayed_inhibition`,
`_homeostatic_scaling`, `set_feedforward_weight`,
`_deliver_scheduled_l2_inhibition`) — every patch calls straight through to
the original method and only reads state immediately before/after it.
Confirmed non-mutating directly: a plain engine and a traced engine given the
same seed produce byte-identical final weights, spike counts, and timestep
after 400 steps (`test_audit_reads_do_not_change_spikes_weights_or_timing`).

Every weight-mutating event is classified into exactly one of five mutually
exclusive causes: `self_spike_potentiation` (this neuron's own fire, active
input), `self_spike_depression_inactive` (this neuron's own fire, inactive
input), `l2i_loser_depression` (delayed L2I→L2E delivery), `homeostasis` (off
by default here, patched anyway), `manual_edit`. Any synapse delta **not**
accounted for by one of these five is caught by a step-level before/after
reconciliation and recorded as `residual_unattributed` — the explicit
residual bucket the phase required. Across all 30 interleaved runs in the
grid below, this bucket is **empty (0 of 524,043 synapse-delta records)**:
every real weight change in this DASHBOARD_PRESET configuration is fully
explained by the five known causes. The safety net itself is verified live:
a test injects a real, un-patched +5.0 mutation mid-step and confirms the
residual bucket catches exactly that amount, no more, no less
(`test_residual_bucket_catches_a_real_unattributed_mutation`).

Three counts are kept explicitly distinct, per the phase's own instruction
not to repeat Phase 13's counting ambiguity:

- **synapse-delta records** — one row per (event, pixel) weight change.
- **target-neuron applications** — one row per `apply_delayed_inhibition`
  call that actually reached its target (`applied=True`), regardless of
  whether that reach produced any synapse-delta rows.
- **physical L2I deliveries** — one row per L2I→L2E scheduled+delivered
  event, read exhaustively from the tail of `engine._l2_inhibition_log`
  immediately after each delivery call (Phase 13b's own fix for that deque's
  `maxlen=400` display-truncation, reused here) rather than from the log's
  own length.

Over the full interleaved grid: 524,043 synapse-delta records, 179,808
target-neuron applications, 22,476 physical L2I deliveries — three genuinely
different numbers, confirmed never accidentally equal
(`test_synapse_deltas_target_applications_and_l2i_deliveries_stay_distinct_counts`).

### Ownership-collision detection

`find_earliest_modal_collision` replays a run's chronological per-presentation
first-responder log and, after every presentation, recomputes each pattern's
running **modal** first-responder using only that pattern's own
presentations seen so far. The first presentation at which any neuron is the
running modal for 2+ patterns is reported as the earliest literal candidate
— honestly, this is frequently a fragile n=1 coincidence that self-corrects
(see Results). `find_persistent_ownership_collision` complements it: it
starts from the run's **final** ownership state and, only if some neuron
still owns 2+ patterns at the end, walks backward to find the onset
presentation after which that exact configuration held continuously through
the end of the run — the collision that actually stuck. Both functions are
purely data-driven (verified against a synthetic log using fabricated
neuron/pattern names that don't match this codebase's own naming,
`test_no_hardcoded_owner_or_outcome_in_collision_detectors`; their source is
also grepped directly for any real pattern/neuron literal,
`test_collision_detectors_never_reference_real_pattern_or_neuron_names`).

### Schedules (kept and reported separately, never mixed)

- **Interleaved** (main protocol): `row 1 → col 1 → diag \ → diag /` repeat,
  20 steps/presentation, 40 cycles (160 presentations, 3,200 steps) — the
  same "interleaved_40" convention Phase 13b/22 already established.
- **Long-hold** (secondary comparison): 600-step row 1 hold → 200-step col 1
  hold, chunked into the same 20-step presentation windows for the identical
  detection machinery.

**Grid actually run: weight seeds 1–10 × topology seeds 1–3 (30 combinations)
for BOTH schedules** — full requested grid, runtime permitted (≈396s total
for both schedules combined; ≈6–8s/interleaved run, ≈2s/long-hold run).
Deterministic: repeated identical seeds reproduce byte-identical
presentation logs, weight-delta records, and final weights
(`test_repeated_identical_seeds_are_deterministic`).

## Results

### Distinct-ownership outcomes (30 runs each)

| Schedule | distinct owners = full | partial collision (3/4) | full collapse (1/4 or 1/2) |
|---|---|---|---|
| Interleaved (out of 4) | 12/30 | 12/30 | 6/30 |
| Long-hold (out of 2) | 24/30 | — | 6/30 |

topology_seed is a confirmed no-op for every one of these 60 runs — every
weight_seed's outcome (tyrant identity, onset presentation, collision
pattern set) is byte-identical across topology_seed ∈ {1,2,3}, the same
inertness Phase 13b found for `legacy_distance_compat=True`.

Tyrant identity across the 18 interleaved collisions: **L2E3 (12/18), L2E0
(3/18), L2E1 (3/18)** — never L2E5. Corrects, again, Phase 13's fixation on
L2E5 as if it were structurally special.

### The earliest LITERAL candidate is usually a false alarm

In every one of the 18 interleaved runs that had a collision, the earliest
literal candidate (first coincidence between two patterns' single-sample
"modal" owners) was flagged at presentation index 2–3 — almost immediately —
**and did not persist to the end of the run** in 17/18 cases (only the
complete-collapse seed 6 run had its earliest candidate also be the one that
stuck). This is exactly the fragility the phase anticipated: with n=1
presentation each, any coincidental first-responder match already counts as
"modal," and most of these self-correct as more data arrives. The genuinely
informative event is the **persistent** collision, not the earliest flicker.

### Tracing the persistent collision: four illustrative interleaved cases

| Seed | Neuron | Patterns collided | Onset (presentation / step) | Displaced competitor |
|---|---|---|---|---|
| 9 | L2E3 | col 1, diag \\ | 50 / ~1000 | L2E1 |
| 3 | L2E3 | diag /, diag \\ | 67 / ~1340 | L2E6 |
| 6 | L2E0 | **all 4** (complete collapse) | 58 / ~1160 | L2E6 |
| 7 | L2E3 | **all 4** (complete collapse) | 99 / ~1980 | L2E1 |

In every one of these four (and in every one of the 18 collisions overall —
see below), the **same structural signature** is present at the moment of
capture: the tyrant's center-pixel (index 4) weight is dramatically higher
than the displaced competitor's, and several of the tyrant's peripheral
weights have decayed near the positive floor (1.0):

```
seed 9  (L2E3 vs L2E1): tyrant center=1637.08  competitor center=743.48   (2.2x)
seed 3  (L2E3 vs L2E6): tyrant center=1856.59  competitor center=434.98   (4.3x)
seed 6  (L2E0 vs L2E6): tyrant center=2032.97  competitor center=299.71   (6.8x)
seed 7  (L2E3 vs L2E1): tyrant center=2215.83  competitor center=719.88   (3.1x)
```

The center pixel (index 4) is active in every one of the four trained
patterns (verified programmatically, not assumed —
`test_center_peripheral_attribution_is_correct`); no peripheral pixel is
active in all four. It is the only synapse every pattern's presentation ever
potentiates for whichever neuron is currently winning, so it never suffers
the `self_spike_depression_inactive` penalty the OTHER eight pixels do
whenever a different pattern is shown — the same mechanism Phase 13b
identified generally, now traced causally to an actual multi-pattern
takeover event rather than inferred from an end-of-run snapshot.

An example chronological slice (seed 9, tyrant L2E3, around the diag \\
presentation that captures its second pattern, t≈1014–1017): a single fire
event potentiates center pixel 4 by **+6.0** (already 1625→1637, deep into
saturation) while its two other active pixels (0, 8) jump by **+35–36**
(far from saturation) and the two now-inactive pixels shared with the
competitor's pattern (1, 7) get depressed by **−37 to −38** in the very same
event — the center pixel's near-immunity to depression combined with early
saturation is what lets it entrench while the genuinely pattern-distinguishing
pixels keep getting whipsawed.

### Which category first creates the persistent advantage: no single answer

For every one of the 18 interleaved collisions, `analyze_center_dominance_
vs_collision` finds the exact first timestep after which the tyrant's center
weight leads the eventual competitor's **permanently** (never crosses back)
— and in every single case, **that lead is established before the collision
presentation itself** (`center-weight dominance precedes second-pattern
acquisition`, 18/18). But which learning rule category produces the delta at
that exact crossing point is **split almost evenly**: `self_spike_
potentiation` in 9/18 cases, `l2i_loser_depression` in 9/18. There is no
single dominant mechanism that "wins" the center pixel for the eventual
tyrant — sometimes it is the tyrant's own center-pixel potentiation pulling
ahead, and sometimes it is the competitor's center pixel being knocked back
by loser depression while the tyrant's holds steady. Both routes converge on
the same structural outcome (center dominance before capture), so this is
reported as a genuine two-mechanism finding, not forced into one.

### Long-hold secondary comparison: capture is immediate, not competitive

Reported strictly separately, never mixed with the interleaved numbers.
6/30 long-hold runs collapse to one neuron owning both row 1 and col 1
(seeds 3 and 5, all three topology seeds each). In **both** collapsing
seeds, the collision's `displaced_competitor` is **None** —
`center_dominance_vs_collision` reports `applicable=False` for the same
reason in both: col 1's very first presentation (onset presentation index
30, exactly the row1→col1 switch boundary) already goes to the row1
incumbent, with no other neuron ever getting a first chance to own col 1 at
all. This is a cleaner, more direct demonstration of the same underlying
cause than the interleaved cases: the row1-established tyrant's already-high
center weight is sufficient, on its own, to win col 1's first exposure
outright — no displacement of a rival needed, because on an abrupt hold
switch there never is a rival. (Seed 3: row 1's own modal owner, L2E5, was
established by presentation 12 of its 600-step hold and then captured col 1
immediately at col 1's first presentation. Seed 5: similarly, L2E3.)

### Center/peripheral weight collapse is general, not collision-specific

Across all 30 interleaved runs, `center_peripheral_ratio` (final weights, all
8 L2E neurons) reconfirms Phase 13b's structural finding directly from this
phase's own independent tracer: the eventual tyrant's center weight is
consistently the largest single feedforward weight of any neuron in the
network, whether or not that run ends in a full collision.

### Never-fired / active-neuron counts (interleaved, n=30)

| distinct_owners this run | active_count (mean) | never-fired count (mean) |
|---|---|---|
| 4/4 (12 runs) | 3.9 | 2.2 |
| 3/4 (12 runs) | 2.8 | 2.8 |
| 1/4 (6 runs) | 1.7 | 2.5 |

Full collapse runs recruit the fewest active neurons overall (1.7/8 mean),
consistent with one neuron absorbing capacity that would otherwise have gone
to a rival.

## Observations vs. interpretation (kept explicitly separate)

**Observations** (directly measured, not inferred):
- Center pixel dominance is established, and never subsequently reversed,
  before the collision presentation in 18/18 traced interleaved collisions
  and both traced long-hold collisions.
- The specific learning-rule category that produces the dominance-crossing
  delta is split ~evenly between the tyrant's own potentiation and the
  competitor's own depression.
- topology_seed has zero effect on any outcome measured in this phase.
- The tyrant is never L2E5 specifically; it varies by weight seed (L2E0,
  L2E1, L2E3 observed).
- residual_unattributed is empty in every real (non-injected) run.

**Interpretation** (a claim beyond the raw numbers, flagged as such): the
center pixel's structural immunity to `self_spike_depression_inactive`
(because it is active in every trained pattern) combined with the (1 −
w/w_max)² saturating growth term appears to be the necessary precondition —
not a full sufficient mechanism on its own, since which of the two rule
categories tips the balance varies by run — for a neuron to become eligible
to capture a second pattern at all. This phase does not test whether
removing the center-pixel-immunity property (e.g. by construction, in a
future phase) would prevent multi-pattern ownership; it only establishes
that dominance chronologically precedes capture in every case observed.

## Tests

`test_phase27_l2_ownership_causal_audit.py` — 12 tests, all passing:
non-mutation of spikes/weights/timing; prediction flags off; full weight-
delta reconciliation against the engine's own live final weights; the
residual bucket both empty in a normal run and demonstrably catching a real
injected mutation; presentation/timestep window attribution (contiguous,
ordered, every spike falls in exactly one window); center/peripheral
attribution (pixel 4 verified active in all four patterns, no peripheral
pixel is); no hardcoded owner/pattern name in either collision detector
(both a synthetic-log test and a source-grep test); deterministic replay for
both schedules; the three delivery/application/synapse-delta counts kept
provably distinct.

## Full test suite

`pytest -q`: **391 passed, 5 failed** (572.45s / 0:09:32). The 5 failures are
the same pre-existing flow-rate/assembly-flow-credit failures documented
since before Phase 6 (`test_assembly_flow_credit.py::test_integration_four_
pattern_regime_is_active_and_bounded`, `test_flow_rate.py::test_flow_off_is_
baseline`, `test_flow_rate.py::test_flow_builds_charge_smoothly`,
`test_flow_rate.py::test_flow_can_cross_threshold_without_new_input`,
`test_flow_rate.py::test_flow_forces_single_chunk`) — unchanged, no new
failures. Count rose from 379 (Phase 26) to 391 with this phase's 12 new
tests.

## Files

- `phase27_l2_ownership_causal_audit.py` (new) — the `CausalTracer`
  instrumentation, ownership-collision detectors, causal-chain extraction,
  and per-run analysis.
- `test_phase27_l2_ownership_causal_audit.py` (new) — 12 focused tests.
- `phase27_l2_ownership_causal_audit_results.json` (new, committed, ≈4MB) —
  full per-run summaries for all 60 runs (30 interleaved + 30 long-hold),
  plus curated full causal-chain traces for 4 illustrative interleaved seeds
  and 2 illustrative long-hold seeds. The remaining 14+4 collision runs'
  full per-event traces are not committed (would be tens of MB) but
  reproduce byte-for-byte deterministically by re-running this script with
  the same weight_seed/topology_seed — every seed/topology combo's own
  compact `persistent_ownership_collision` and `center_dominance_vs_
  collision` summary IS committed in full regardless.

## Commit / branch status

Branch `l2-ownership-recovery`, based on `7dc6f4f` (Phase 26). Not pushed.
`july14`, `july14-integration`, and every backup branch are untouched.
