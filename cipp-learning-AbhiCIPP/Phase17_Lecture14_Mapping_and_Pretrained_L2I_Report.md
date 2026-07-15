# Phase 17 — LPS Lecture 14 Architecture Mapping and Isolated Pre-Trained L2I Competition Experiment

**Continues from the Phase 15 checkpoint on `july14-integration`** (a
divergent branch was reconciled first — see "Working-tree / branch notes"
at the end). Note: this session had already used the name "Phase 16" for a
prior, unrelated factorial experiment (`030fffe`); this work is filed as
**Phase 17** to avoid overwriting that record.

## 1. Lecture 14 mapping

Read in full: `LPS_Lecture_14_Detailed_Summary.txt`,
`LPS_Lecture_14_Expanded_Chronological_Notes.txt`. Treated as conceptual
research context, not an equation/topology spec (no prediction-neuron
topology, decoder equation, frequency/free-energy equation, or synapse-
level maturity rule was invented — all remain explicitly deferred, see §10).

| # | Lecture 14 proposal | Classification |
|---|---|---|
| 1 | Inhibitory competition should be pre-trained rather than learned | **Partially implemented.** L2I's OUTGOING side (magnitude, delay, uniform delivery) was already fixed since Phase 7 — see §2 below, a coincidental pre-existing match. L2I's INCOMING (recruitment) side was learned; this phase adds an isolated, default-off, fixed-recruitment mode for it (Part 2). L1I's incoming/outgoing sides remain fully learned, untouched, per explicit instruction. |
| 2 | The first representation spike should physically recruit inhibition | **Already implemented.** Phase 7's causal chain (physical L2E spike → real L2E→L2I event → L2I's own physical threshold crossing → scheduled delayed physical inhibition) is exactly this, built well before this lecture, for unrelated reasons (`July_14_Geometric_Influence_Temporal_Winner_Brief.txt` SS9). |
| 3 | A separate excitatory prediction/decoder population should eventually exist | **Absent — explicitly deferred**, not designed or implemented (§10). |
| 4 | Free energy may depend on temporal firing frequency | **Absent, and cautioned by measurement.** The existing `structural_free_energy` gate depends on weight-sum vs. threshold, never frequency. A dedicated measurement (§5) shows raw frequency reaching exactly 0.5 under mere synchronized global suppression, with zero selective prediction — a concrete demonstration of why frequency alone is an unsafe "learning complete" signal. |
| 5 | Learning maturity may belong to individual synapses | **Absent.** Phase 15's `loser_depression_protection` is a related but distinct NEURON-level (not synapse-level) maturity gate, and its own report found a negative ownership result — not promoted, and not re-promoted here per explicit instruction. |
| 6 | Explicit temporal dynamics may be required | **Underspecified / absent.** No equation was proposed in the source material beyond "may be unavoidable"; nothing invented here (§10). |

## 2. Audit (measurement only, current baseline, before any new mechanism)

Script: `phase17_lecture14_audit.py`, 5 weight seeds, `DASHBOARD_PRESET`,
40-rotation equal-interleaving.

1. **L2E→L2I synapses currently learn** via `ChargeBasedRule` (potentiation-
   only; `signed_spike_learning`/`assembly_flow_credit` are both False for
   L2I under `DASHBOARD_PRESET`, so `select_excitatory_rule` returns the
   plain charge-based branch).
2. **L2I's outgoing behavior is already entirely fixed**: no learned gate
   exists on the L2I→L2E pathway at all (Phase 7 removed it) — magnitude
   (`l2_inhibition_frac × threshold_l2`), delay (`l2_inhibition_delay`), and
   uniform whole-pool delivery are all constants.
3. **L1I's incoming (L2E→L1I) synapses learn** via `AssemblyFlowCredit`,
   unconditionally forced True for every L1I regardless of config
   (`_build()`'s `if nid.startswith('L1'): n.assembly_flow_credit = True`).
4. **L1I's output inhibition is NOT fixed.** `NeuronConfig.apply_to()`
   applies `inhibitory_delta_rule` uniformly to every neuron, including
   L1E's own inhibitory gate (index 0, from its paired L1I) — under
   `DASHBOARD_PRESET` (`inhibitory_delta_rule=False`) this gate still uses
   the **legacy saturating** `apply_inhibition` plasticity rule
   (`dw = eta·p·(1 − w²/w_max)`), which is a genuine, live learning rule,
   not a constant.
5. **L2E-first-spike → L2I-threshold-crossing latency**: mean 0.57–1.08
   steps across 5 seeds (near-immediate).
6. **L2I-fire → inhibition-delivery latency**: exactly 1.0 step, every
   seed (= the configured `l2_inhibition_delay`, deterministic).
7. **Contributor count per L2I delivery**: mean 1.4–1.7 L2E firers per
   event across 5 seeds (mostly single or a couple of contributors).
8. **Per-population firing frequency** (mean over a 40-rotation
   interleaved run): L1E≈0.24, L1I≈0.28, L2E≈0.05, L2I≈0.21–0.25.
9. **Frequency≈0.5 incidence in the interleaved schedule**: near-zero
   (0.0–0.075 of presentation-windows across 5 seeds) — under this specific
   multi-pattern schedule, frequencies mostly sit well below 0.5, not near
   it.
10. **Frequency≈0.5 correlation check — the required false-positive
    control.** A dedicated sustained-hold measurement (`row 1` held
    constant) shows L1E's active-pixel frequency converging from ~0.80 down
    to **exactly 0.5** by step ≈800 and staying there for the rest of a
    2,000-step hold — via mere **synchronized global L1I suppression**, with
    **zero selective, pattern-specific prediction** (L1I units are, and
    remain, 100% synchronized — Phase 9's structural finding, reconfirmed).
    **This is precisely the required false-positive control: frequency=0.5
    here reflects rhythmic suppression, not "prediction complete," and must
    not be read as a learning-stop signal** (see §6 and Part 6's dedicated
    test).
11. **L2E→L2I recruitment-weight trajectories**: see §4 below.
12. **Single-spike sufficiency at start/mid/end of training**: **NO at
    start** (max weight ≈1,240–1,320, vs. `thr_l2i`=2,666.67) → **YES by
    the midpoint** (max weight reaches exactly `thr_l2i`, capped) → **YES at
    the end**, in **every one of the 5 seeds tested.** The learned baseline
    already converges to exactly the state Lecture 14 proposes to hard-code
    from the start — this phase's experiment isolates what changes if that
    convergence period is skipped entirely.

## 3. Exact implemented mechanism (Part 2)

New default-off flag `pretrained_l2i_recruitment` (+ no new reference
constant needed — the fixed value is the engine's own already-resolved
`thr_l2i`). In `SimulationEngine._build()`:

- **Off (default):** byte-identical to every prior phase — verified
  directly (Part 6, tests 1–2).
- **On:** every L2E→L2I synapse initializes to exactly `thr_l2i` (audited:
  `infl_l2e_l2i`, the only thing that would attenuate this specific
  delivery, stays off and untouched, so no unit conversion was needed — the
  raw stored weight IS the delivered charge on a single spike). L2I's own
  `learning_rate` is pinned to `0.0`, so `ChargeBasedRule`'s
  `dw = eta·p·(1−w²/w_max)` is always exactly 0 regardless of which L2E
  fires — these weights never move again (verified directly).

Nothing else changes: L2I still physically integrates charge and crosses
its own `check_threshold()`/`fire()` (verified directly, Part 6); L2I→L2E
inhibition is still scheduled via the identical `l2_inhibition_delay`
causal path (verified); delivery is still uniform across the whole L2E
pool; no winner/pattern/owner/index/cross-neuron state is read anywhere in
either new code path (verified by AST-adjacent source inspection); L2E
self-spike learning, loser depression, distance/geometry, L1I, adaptive
threshold, leak, and Phase 15 protection are all untouched (verified
directly — the flag interacts with none of them).

## 4. Baseline-equivalence evidence

- Unit level: `CorticalColumn`-level weights/learning_rate identical,
  explicit-off vs. omitted.
- Engine level: a full 200-step run is byte-identical, explicit-off vs.
  omitted, for every L2E and L2I weight.
- Full backend suite: **299 passed, 5 failed** — the same pre-existing
  flow-rate failures documented since before Phase 6, unchanged; **19
  passed, 0 failed** in the new `test_pretrained_l2i_recruitment.py`
  (exceeds the 17 required proofs — two were split into paired
  unit+engine-level variants for precision).

## 5. Multi-seed results (5 weight seeds × 3 topology seeds × 3 schedules)

`phase17_controlled_comparison.py`: **A** (learned recruitment) vs. **B**
(pre-trained recruitment), identical `DASHBOARD_PRESET`/seeds throughout.

### Recruitment breadth (mean over 15 combinations)

| Schedule | Config | active | quiet | never-fired |
|---|---|---|---|---|
| short_hold_switch (20+20) | A | 4.80 | 0.00 | 3.20 |
| short_hold_switch | B | 1.40 | 0.00 | **6.60** |
| long_hold_switch (600+200) | A | 1.40 | 1.60 | 5.00 |
| long_hold_switch | B | 1.00 | 0.00 | **7.00** |
| equal_interleaving (40 rot.) | A | 3.60 | 1.80 | 2.60 |
| equal_interleaving | B | 2.00 | 0.60 | **5.40** |

**Pre-trained recruitment recruits measurably FEWER neurons in every single
schedule.** This is the central, seed-robust negative finding.

### Tyrant share (mean)

| Schedule | A | B |
|---|---|---|
| short_hold_switch | 0.331 | **0.840** |
| long_hold_switch | 0.465 | **1.000** |
| equal_interleaving | 0.538 | **0.689** |

**Under B, the long-hold schedule reaches literal, total, single-neuron
monopoly (tyrant_share = 1.000) in every one of the 15 seed/topology
combinations tested.** This is exactly the caution named in this phase's
own instructions: **"Fixed WTA may make the first random tyrant stronger."**
Confirmed directly, not hypothetically.

### Distinct ownership, collisions, forgetting, ambiguity (equal_interleaving)

| Config | distinct_owners | collisions | forgetting | ambiguity | later responses | latency to 2nd |
|---|---|---|---|---|---|---|
| A | 3.60 | 0.40 | 1.00 | 0.0312 | 7.04 | 2.14 |
| B | **2.00** | **1.00** | 0.00 | **0.0050** | 5.72 | 2.64 |

Distinct ownership is worse under B; collisions are worse; ambiguity is
lower (mechanistically explained below); forgetting is lower under B but
this tracks trivially from there being fewer distinct owners to lose in the
first place, not genuine stability.

### One-hot / no-response / simultaneous-firer rates

| Schedule | Config | one-hot | no-response | multi-firer |
|---|---|---|---|---|
| long_hold_switch | A | 0.2985 | 0.5285 | 0.1730 |
| long_hold_switch | B | 0.4835 | 0.5165 | **0.0000** |
| equal_interleaving | A | 0.3807 | 0.6086 | 0.0107 |
| equal_interleaving | B | 0.3356 | 0.6642 | 0.0002 |

**One-hot firing is NOT the same as different patterns having different
owners** (the explicit caution in this phase's instructions) — B's
one-hot rate is comparable to or higher than A's, purely because instant,
reliable single-spike L2I recruitment eliminates same-step multi-firer
events almost entirely (any single crossing now reliably triggers L2I
before a rival can also cross), **while distinct ownership across patterns
is simultaneously worse.** Clean firing hygiene and genuine one-to-one
representation are different axes; B improves the former while degrading
the latter.

### L2I activity

| Schedule | Config | L2I firing rate | delivery count |
|---|---|---|---|
| short_hold_switch | A | 0.075 | 3.0 |
| short_hold_switch | B | 0.130 | 4.8 |
| long_hold_switch | A | 0.302 | 241.2 |
| long_hold_switch | B | 0.484 | 386.6 |
| equal_interleaving | A | 0.230 | 735.6 |
| equal_interleaving | B | 0.336 | 1,074.2 |

L2I fires and delivers substantially more often under B in every schedule
— expected and mechanical, since single-spike recruitment makes it trivial
to trigger.

## 6. Frequency analysis, including half-frequency false positives

See §2 items 8–10. The central point, restated: **half-frequency was
observed in this codebase (a sustained `row 1` hold converges L1E to
exactly 0.5) purely from synchronized global suppression with zero
selective prediction.** This phase does not implement any
frequency-based learning-stop rule (deferred, §10; verified by a dedicated
test that no weight-mutating code path reads any neuron's firing
frequency) — but the measurement itself is the concrete demonstration of
why such a rule, if built later, must be checked against this exact
false-positive before being trusted.

## 7. One-hot vs. one-to-one distinction

Restated concretely from §5's data: **B achieves BETTER one-hot discipline
(fewer simultaneous firers) while achieving WORSE one-to-one ownership
(fewer distinct owners, more collisions, near-total tyranny in long-hold).**
These are the two things this phase's cautions explicitly warn not to
conflate, and the multi-seed data shows them moving in opposite directions
under this specific mechanism.

## 8. Spare-capacity challenge results

Protocol exactly as specified: train the original four equally (the
equal-interleaving run) → freeze/record → introduce `row 0` (existing
held-out probe) with plasticity live, fixed identical schedule (10
exposures) for A and B → identify responder + prior status → freeze again
→ re-evaluate all five patterns.

| Config | novel captured (n/15) | from never-fired | from active | tyrant captured novel | mean retention | mean novel consistency |
|---|---|---|---|---|---|---|
| A | 15/15 | 0 | 15 | 12/15 | 0.750 | 0.86 |
| B | 15/15 | **6** | 9 | **9/15** | **0.950** | **0.98** |

**A genuinely surprising, counter-to-the-headline-trend result:** in the
spare-capacity challenge specifically, B shows a HIGHER genuine
spare-capacity recruitment rate (6/15 vs. 0/15 seeds where the novel
pattern's eventual owner had never fired before), LOWER tyrant capture of
the novel pattern (9/15 vs. 12/15), and BETTER retention/consistency of the
original four's ownership after novel exposure (0.950 vs. 0.750; 0.98 vs.
0.86). The mechanism is straightforward: because B's own training already
leaves more neurons genuinely untouched (§5's higher never-fired counts),
there is simply a larger genuinely-spare pool available when a novel input
arrives, and because the surviving specialist(s) under B are so
overwhelmingly dominant already, introducing one more pattern is *less*
likely to destabilize their existing ownership. **This is a real secondary
benefit riding on top of the primary failure mode (excessive tyranny during
training), not an independent success** — worth flagging for narrower
follow-up, not as grounds for promotion on its own.

## 9. Negative results and failure modes

1. **Fewer active neurons, more never-fired neurons, in every schedule
   tested** — the central, most seed-robust finding.
2. **Total, literal single-neuron monopoly (tyrant_share=1.000) in every
   seed under the long-hold schedule** — confirms the phase's own explicit
   caution about strengthening the first random tyrant.
3. **Worse distinct ownership, more collisions**, in the equal-interleaving
   schedule.
4. One-hot firing improves, but this is explicitly warned NOT to be
   conflated with one-to-one ownership, which gets worse.

## Per the explicit promotion bar (§ instructions)

> "The pre-trained condition is only promising if it improves or preserves
> distinct pattern ownership, consistency, spare recruitment, retention;
> without increasing tyrant capture across patterns, forgetting, dead
> neurons, ambiguous same-step responses."

| Criterion | Result under B | Bar met? |
|---|---|---|
| Distinct pattern ownership | Worse (2.00 vs 3.60) | **No** |
| Consistency | Mixed (novel-pattern consistency better; original-pattern per-pattern consistency not improved) | Mixed |
| Spare recruitment | Better in the specific challenge (6/15 vs 0/15) | Yes |
| Retention | Better in the specific challenge (0.950 vs 0.750) | Yes |
| Tyrant capture (training-time) | Much worse (up to 1.000 share) | **No** |
| Dead (never-fired) neurons | Worse in every schedule | **No** |
| Ambiguous same-step responses | Better (lower) | Yes |

**Fails the bar on the two criteria the instructions weight most heavily
for the core hypothesis (dead neurons, tyrant capture) despite passing on
three others.**

## 10. Explicitly deferred Lecture 14 work (not designed, not implemented)

- The excitatory prediction/decoder population.
- Any encoder/decoder reconstruction equation.
- Frequency-based free energy.
- Synapse-level free energy / maturity.
- Any additional explicit temporal-dynamics equation.

None of these were silently designed or partially sketched anywhere in
this phase's code or scripts.

## Recommendation

**Pre-trained L2I recruitment should remain default off.** It fails the
promotion bar's two most consequential criteria (dead-neuron count,
tyrant-capture/monopoly), confirming this phase's own stated caution in a
concrete, seed-robust, 15-combination result (most starkly: total monopoly
in every long-hold seed). The genuinely positive secondary finding (better
spare-capacity recruitment and retention specifically within the novel-
pattern challenge) is real and reproducible but is a downstream consequence
of the primary failure (more neurons left untouched to begin with), not an
independent success — it is flagged as a candidate for narrower, separate
follow-up (e.g., "why does the surviving specialist retain ownership
better when it's already overwhelmingly dominant" is itself an interesting
question) rather than grounds to test further as currently scoped. Not
rejected outright (the mechanism itself works exactly as designed,
mechanically, and the AST/unit-level guarantees hold perfectly), but there
is no basis to promote it, and the negative recruitment/tyranny result is
strong enough that further testing of THIS specific mechanism in THIS
form is not recommended either.

## Working-tree / branch notes

A remote push (`3a5f158`, uploading the two Lecture 14 text files) had
diverged from this local branch's own prior work (`030fffe`). Reconciled
with a conflict-free local merge (`055b30f`) before starting this phase;
not pushed. `july14` base untouched throughout.
