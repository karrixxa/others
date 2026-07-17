# Phase 33 — Causal Microstep L2 Race

**Status: implemented as a real, default-OFF `SimulationEngine` flag
(`causal_microstep_l2_race_enabled`). Flag-off byte-identical to `ffefd1f`,
verified directly. GATE A: FAIL at the preregistered K=20. Stopped per
explicit instruction — no parameter tuning, Gate B/C not run. Branch
`l2-ownership-recovery`, on top of `ffefd1f`. Nothing pushed.**

## Motivation

This phase's causal conclusion, established across Phases 27–32: frozen L2
competition fails before learning even starts; persistent first-responder
collisions precede weight compression (Gate 1's `DYNAMICAL_FAILURE_
PRECEDES_COMPRESSION` verdict); saturation is not the initiating cause;
shared L2I recruitment is dominated by an accumulation/pre-inhibition race
(the primary diagnosis from the frozen shared-inhibition causal audit).
Phase 33 tests a competition-TIMING fix directly targeting that race —
never touching prediction, decoder, centered-encoder, saturation-cap,
threshold, initialization, or learning equations.

## What was implemented

`causal_microstep_l2_race_enabled: bool = False` (new constructor param).
Reuses the existing `l2_charge_chunks` (K) concept — no new chunking
parameter. When enabled, `_resolve_l2_competition_causal_microstep`
replaces the existing K-chunk loop in `step()`:

- Divides the outer volley's feedforward delivery into K equal microsteps.
- **Never discards remaining feedforward mass after a spike** — every
  microstep still delivers its 1/K fraction regardless of earlier
  spikes, continuing the volley (the existing K-chunk path stops the
  instant any neuron crosses threshold — that behavior is completely
  unchanged when the flag is off, and completely bypassed when it is on).
- Every physical threshold crosser in a given microstep fires — exact
  co-crossers within the SAME microstep are ties and all fire together.
  Never an argmax, highest-potential selection, or index-order tiebreak.
- L2I's own threshold is checked EVERY microstep (not just once per
  chunk-loop), so it can fire multiple times within one volley; each
  firing schedules its own causally-timed delayed return-inhibition event
  in a NEW, separate microstep-granular queue (`_l2i_microstep_pending`),
  never touching the existing outer-step-granular `_l2i_pending` (which
  stays empty/inert while this path is active).
- The delay is expressed as `l2_inhibition_delay * K` microsteps, so the
  real-world latency of the existing delay parameter is unchanged.
- Leak/refractory-countdown/other outer-step updates run once per real
  outer step, never per microstep (matches the existing K-chunk
  convention exactly).
- Conservation accounting (`_causal_microstep_stats`): feedforward events
  scheduled/delivered (always 1:1, verified explicitly, never assumed)
  and inhibitory events scheduled/delivered/refractory-rejected (via
  `apply_delayed_inhibition`'s own existing `applied` flag).

Uses the existing shared L2I topology — no paired L2 interneurons
introduced. Paired prediction-column inhibition (`PC_i → I_i → S_i` in
Layer 1) is completely untouched.

## A bug found and fixed during implementation

The first version of `_resolve_l2_competition_causal_microstep` only let
L2I integrate this microstep's `l2e` vector when at least one L2E fired
that microstep (`if not eligible: continue`, skipping L2I entirely on
empty microsteps). This silently diverged from the existing K-chunk
path's own "not resolved" fallback, which ALWAYS lets L2I integrate
(even an all-zero vector) every chunk, giving it a chance to fire from
residual/decayed charge. Found via the mandatory "K=1 reproduces the
baseline" test (which failed until this was fixed) — L2I must integrate
every microstep unconditionally, not only on microsteps with a new spike.
Fixed directly; the corrected version passes that test exactly.

**A second, separate error was in the TEST itself, not the code**: an
initial K=1-vs-K=1 comparison used `DASHBOARD_PRESET` unchanged for the
"baseline" side, which silently carries `l2_charge_chunks=20` (its own
real default) — comparing K=20-old against K=1-new is not a valid K=1
control. Fixed by explicitly setting `l2_charge_chunks=1` on BOTH sides
of the comparison.

## Documented, not fixed: the centered-encoder saturation-cap mismatch

Per explicit instruction, the Gate 1 audit's finding (`CenteredEncoderRule`
reads `n.excitatory_saturation_cap`, `SignedSpikeRule` reads `n.weight_cap`
directly — a ~2,667× discrepancy in already-committed Phase 30 code) is
NOT corrected as part of this causal-timing experiment. It remains an
open, documented, separate issue.

## Mandatory tests (`test_phase33_causal_microstep_l2_race.py`, 14 tests, all passing)

Flag-off byte-identical to baseline (both the literal default and an
explicit `False`); flag-off never touches any of the new state (microstep
counter/pending queue/stats all stay at their zero/empty initial values);
no additional RNG consumption (initial weights byte-identical on vs. off,
same seed); K=1 reproduces the K=1 baseline exactly (single hold AND
across pattern switches); exact co-crossers remain ties (two neurons
forced to identical sub-threshold potential both fire together); no
argmax/index-tiebreak in the actual code (docstring excluded from the
scan); feedforward mass conservation (scheduled == delivered == K×N_OUT
every step, checked directly); inhibitory conservation accounting present
and internally consistent (scheduled == delivered + refractory-rejected,
with at least one real inhibition event observed across 300 steps);
L2E→L2I and L2I→L2E timestamps causally ordered (every scheduled delivery
strictly later than its own firing microstep; firing microsteps
monotonically non-decreasing); frozen runs leave every weight byte-
identical; passive telemetry reads never alter engine state; deterministic
replay; remaining chunks are never discarded after a spike (feedforward
event count stays at the full K×N_OUT even on steps where an earlier
microstep already produced a spike).

## Full test suite

`pytest -q`: **458 passed, 5 pre-existing failures** (393.30s / 0:06:33).
Exactly matches 444 (prior checkpoint) + 14 (this phase's new test file).
No new failures. The 5 failures are the same
`test_assembly_flow_credit.py`/`test_flow_rate.py` failures present since
before Phase 6, unrelated to this phase.

## Gate A: row/column two-pattern acquisition — **FAIL**

Configuration: centered encoder ON, loser depression OFF, prediction OFF
(all matching Phase 31's own condition B exactly), causal microstep L2
race ON at K=20 (the one preregistered value), compared against K=1 (the
exact baseline control) and the existing (non-causal-microstep) mechanism
at both K values. 3 fixed seeds (1, 2, 3). Patterns: `row 1`, `col 1`,
interleaved, 40 presentations per pattern (80 total), 20 steps each.

**Stable owner**: the same physical first responder on at least 8 of a
pattern's own final 10 presentations. **Pass condition**: both patterns
have a distinct stable owner in all 3 seeds.

| Condition | seed 1 | seed 2 | seed 3 | seeds passing |
|---|---|---|---|---|
| **causal_microstep, K=20 (candidate)** | L2E5 / L2E5 — **collision** | L2E0 / L2E3 — distinct | L2E5 / L2E5 — **collision** | **1/3** |
| causal_microstep, K=1 (control) | L2E3 / L2E2 — distinct | L2E0 / L2E3 — distinct | L2E5 / L2E3 — distinct | 3/3 |
| existing mechanism, K=1 | L2E3 / L2E2 — distinct | L2E0 / L2E3 — distinct | L2E5 / L2E3 — distinct | 3/3 |
| existing mechanism, K=20 | L2E4 / *no stable owner* | L2E0 / L2E3 — distinct | L2E7 / L2E7 — **collision** | 1/3 |

**Verdict: FAIL.** The preregistered candidate (causal microstep, K=20)
passes only 1 of 3 seeds. Per explicit instruction, this phase STOPS
here — K is not tuned, no other parameter is adjusted to try to force a
pass, and Gate B/C are not run.

### Causal event trace (seed 1, K=20 candidate — illustrates the failure mode)

```
t=7   pattern=row 1  L2E_fired=[5]  L2I_fired=True   (row 1's very first presentation)
t=15  pattern=row 1  L2E_fired=[5]  L2I_fired=True
t=22  pattern=col 1  L2E_fired=[5]  L2I_fired=True   (col 1's very first presentation -- ALREADY L2E5)
t=29  pattern=col 1  L2E_fired=[5]  L2I_fired=True
t=35  pattern=col 1  L2E_fired=[5]  L2I_fired=True
...   (L2E5 remains the ONLY observed first responder for BOTH patterns
       through every presentation checked, t=41 to t=197)
```

L2E5 wins `row 1`'s very first presentation (t=7) and then ALSO wins
`col 1`'s very first presentation (t=22, only 15 steps later) — a rapid,
early, complete takeover of both patterns by the same neuron. This
matches, and is not fixed by, the Gate 1 finding: collisions are decided
early by dynamical/timing factors, not by a slow accumulation window that
finer-grained delivery alone resolves.

### Reported observation (not further pursued, per the stop instruction)

Both K=1 conditions (causal-microstep and existing — identical by the
proven K=1 equivalence) pass 3/3 seeds; both K=20 conditions (causal-
microstep and existing) pass only 1/3. This suggests the CHUNKING
GRANULARITY itself, not specifically the discard-vs-continue difference
this phase targets, is what differs between the passing and failing
configurations here. This is reported as an honest observation from the
data already collected — it is explicitly NOT a basis for tuning K
further; per instruction, Gate A's failure at the one preregistered value
stops this investigation at this gate.

## Gates B and C

Not run — Gate A did not pass, and the instruction is explicit: "If Gate A
fails, stop. Do not tune K or other parameters."

## Configuration (exact, for reproducibility)

```python
dict(DASHBOARD_PRESET,
    centered_encoder_enabled=True, loser_depression=False,
    prediction_column_enabled=False,
    causal_microstep_l2_race_enabled=True, l2_charge_chunks=20,
    seed=<1|2|3>, topology_seed=1)
```

## Files

- `backend/simulation.py` (modified) — new constructor param, state init,
  `_resolve_l2_competition_causal_microstep`, `step()` wiring, TUNABLE/
  apply_config entries.
- `test_phase33_causal_microstep_l2_race.py` (new) — 14 mandatory tests.
- `phase33_gate_a_two_pattern_acquisition.py` (new) — Gate A harness.
- `phase33_gate_a_results.json` (new, committed) — full per-seed/per-
  condition results.

## Commit / branch status

Branch `l2-ownership-recovery`, on top of `ffefd1f`. Not pushed. `july14`,
`july14-integration`, and every backup branch untouched. No frontend code
modified.
