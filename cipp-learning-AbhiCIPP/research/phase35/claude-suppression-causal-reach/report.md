# Phase 35 predictive-suppression causal-reach audit

Measurement-only, building directly on
`/home/cxiong/codex-runs/claude-phase35-mature-efficacy/`. Same checkpoint
(`db30ceadbe18cf90e01f6d54dee0203f342b24a8`), same Stage 1 natural-
maturation code, same `clone_engine`/`make_bc` B-vs-C construction, reused
unchanged. No production file edited, no neural parameter changed, nothing
pushed.

## Verdict

**`SUPPRESSION_CHANGES_LATER_ACTIVITY_ONLY`**

Traced 12,600 PC-spike-derived events across 7 seeds (6 with a single clean
natural leader, 1 with a genuine, persistent two-way tie). Every single
delivered suppression event blocks sensory firing and **all** L2 spiking
completely, at the very next step, with 100% reliability. It never once
changes which L2E ends up owning the pattern -- in either the clean or the
tied seed. The reason is structural, not a matter of timing or magnitude:
suppression acts on the sensory input layer every competing L2E shares, so
it removes the whole race for a step rather than tilting it.

## Step ordering, established by reading the code before writing any tracer

This whole audit hinges on getting `backend/simulation.py`'s `step()`
ordering exactly right, so I read it start to finish (lines ~2538-2923)
before writing a line of tracing code, rather than assuming the task's
proposed chain was literally same-step throughout. The actual ordering:

1. **t**: PC_i resolves its coincidence using data queued
   `prediction_feedback_delay` steps ago. If it fires, `pcol_spiked[i]=1`
   this step.
2. **t**: if `prediction_column_to_i_enabled`, L1I_i receives
   `pcol_spiked[i]` this same step (line ~2826).
3. **t**: L1I_i may or may not cross its own threshold this step, depending
   on accumulated charge (see below).
4. **t, end of step**: `self.l1i_feedback_delay = l1i.copy()` (line 2909) --
   L1I's fire outcome *this* step is stored in a register.
5. **t+1, start of next step**: L1E_i's `receive_input` reads
   `l1i_feedback_delay[i]` as *this* step's inhibitory event (line 2584) --
   **one step later** than the L1I fire that caused it. This is a real,
   built-in delay in the existing L1E inhibition mechanism, not something
   introduced by Phase 35.
6. **t+1, same step**: L1E_i's resulting firing state directly builds
   `ff_vec`, delivered to every L2E as feedforward drive **in the same
   step** (lines 2694-2696, 2744-2748) -- no additional delay between L1E's
   decision and L2's use of it.

So a PC_i spike at step t can, at the earliest, affect the L2 decision at
step t+1 -- not t. Whether that L2 decision has "already happened" by the
time suppression could apply is exactly the empirical question this audit
answers: no, it hasn't -- L1E's state at t+1 and L2's feedforward drive at
t+1 are computed in the same step, so there is no window where L2 could
have already moved past L1E's influence for that step.

**Why suppression isn't delivered every time PC spikes**: L1I's own weight
(after the topology-reshape adaptation documented in the mature-efficacy
report) sits below its own threshold (`thr_l1i=8000`; reshaped weight
~4,600-5,000 depending on seed) -- one PC-driven delivery alone can't fire
it. With `L1I_FEEDBACK_REFRACTORY=2` and no leak (`l1i_leak_enabled=False`,
untouched default), charge accumulates undecayed across deliveries until a
second one crosses threshold, then L1I fires and resets. Empirically this
produces a clean, exact alternation -- every PC spike event either delivers
(L1I crosses threshold) or doesn't, split almost exactly 50/50 in every
seed traced.

## Two analyses, kept explicitly separate

**Analysis 1 (primary): within-C matched comparison.** C's own natural
delivered/undelivered alternation is a built-in treatment/no-treatment
split *inside one consistent engine* -- it isolates PC's specific causal
contribution without needing engine B at all, and without any risk of
conflating it with anything else.

**Analysis 2 (secondary, explicitly caveated): B vs C.** While building
this, I found something worth flagging clearly: **B's L1I is not silent.**
It still receives the pre-existing legacy global L2E-winner broadcast every
step (`inh.receive_input(l2e, t=t)`) -- a completely different, and
empirically *more frequent*, trigger than C's PC-driven path (B fired L1I
2,250 times across the 3 active pixels over 1,500 steps; C fired it 900
times). B and C can therefore diverge for reasons that have nothing to do
with any specific PC event. This means a naive B-vs-C step-by-step
comparison is confounded for the fine-grained causal-reach question --
it answers "does the whole selective-vs-global regime differ", not "does
this PC event reach L2." Analysis 1 was built specifically to avoid this
confound; Analysis 2 is reported separately and only for what it can
legitimately answer (whole-regime ownership comparison, which matches how
it was already used in the mature-efficacy experiment).

**A correction to the prior report, surfaced by this finding:** the
mature-efficacy report's `B_l1i_events=0` metric measured only *selective*
delivery events (necessarily zero when the flag is off) -- it should not be
read as "B's L1I never fires." B's L1I fires constantly, via the
pre-existing legacy pathway; that experiment's actual conclusions (about
sensory/PC-layer activity and ownership) are unaffected by this, but the
specific number needs this caveat attached, and now has it, here and in
`results.json`.

## Results

**Within-C matched comparison, aggregated across the 6 clean-leader seeds**
(1, 3, 10, 14, 17, 22 -- identical numbers in every single one):

| | delivered (n=5,400) | undelivered (n=5,400) |
|---|---|---|
| L1E_i fires at t+1 | **0.0** | 1.0 |
| Natural leader L2E fires at t+1 | **0.0** | 1.0 |
| *Any* L2E fires at t+1 | **0.0** | 1.0 |

Not one partial or marginal case anywhere in 10,800 events. The underlying
dynamics are fully deterministic given fixed config/topology (no
stochasticity in neuron integration or firing), so the reach is exactly
100% or exactly 0%, never in between.

**Tied seed (2)**, added specifically for this audit because it produces a
persistent, exact tie between L2E0 and L2E3 (see the mature-efficacy
calibration log) -- the 6 clean seeds alone can't distinguish "suppression
can't redirect ownership because there's no real competitor to redirect it
toward" from "suppression can't redirect ownership even with real
competition." Result: identical pattern, and critically, `any_l2e_fire_rate
_given_delivered = 0.0` means **both** tied competitors are blocked
*together* on delivered steps, not selectively. This is the direct,
mechanistic reason a real tie is not broken: suppression removes the shared
feedforward drive both compete for, rather than favoring one over the
other.

**Requested aggregate fractions** (see `results.json` for full detail):

- fraction of PC events that alter sensory firing: **0.5**
- fraction that alter future L2 input: **0.5**
- fraction that alter L2 membrane but not firing: **0.0**
- fraction that alter an L2 spike: **0.5**
- fraction that alter ownership: **0.0**

The 0.5's are not partial effect sizes -- they're exactly the delivery rate
(does L1I cross threshold this event or not); conditional on delivery the
effect is deterministically complete. The membrane-but-not-firing fraction
is exactly 0.0 because a delivered event drives `ff_vec` to zero for all 3
active pixels together (they suppress in lockstep, sharing timing), so L2E
receives *no* new feedforward charge that step at all -- there's no
intermediate case where charge moves but stays sub-threshold.

## Why does 20% sensory reduction produce zero ownership effect?

**`SUPPRESSION_CHANGES_LATER_ACTIVITY_ONLY`**, not any of the other four
specific-failure verdicts, and not a genuine mix of them:

- **Not "reaches L2 too late"** -- reach is same-step (t+1's suppressed L1E
  state feeds t+1's L2 feedforward drive in the identical step), not
  delayed relative to the decision it needs to influence.
- **Not "reaches L2 but insufficient for threshold"** -- there is no
  threshold-marginal case anywhere in the data; a delivered event removes
  *all* feedforward charge, not a partial amount, so this isn't about
  crossing a threshold at all.
- **Not "structurally decoupled from the first race"** -- decoupled would
  mean the mechanism doesn't reliably reach the race's raw material. It
  does, every single time it fires, with perfect fidelity.
- **The real mechanism**: suppression acts on L1E, the *shared* sensory
  input layer every competing L2E depends on equally. When it fires, it
  removes the entire feedforward drive for that step for every competitor
  at once (directly confirmed in the tied seed -- both rivals blocked
  together). A mechanism that cannot differentially favor one competitor
  over another cannot, by construction, redirect which one wins. It can
  only modulate how often the race happens at all -- which is exactly what
  the mature-efficacy experiment measured as a real, reproducible 20%
  reduction in activity, correctly, without that reduction ever being able
  to touch ownership.

In the 6 clean-leader seeds there's a second, additive reason (no real
competitor is present for suppression to redirect ownership toward even in
principle -- the leader wins ~100% of its undelivered opportunities against
negligible rivalry), but the tied seed shows the first mechanism is
sufficient on its own: even with two genuine, exactly-tied competitors
present, suppression still can't break the tie, because it removes both
competitors' drive together rather than one relative to the other.

## Checkout status and scope discipline

Reused the existing standalone scratch clone from the mature-efficacy
experiment (`/tmp/.../phase35-mature-efficacy-clone/`) -- same checkout,
no new clone needed, still fully separate from Codex 1/2's directories and
the production repo. No commits made. Nothing pushed. No production source
file modified; all instrumentation lives in the external harness
(`scripts/causal_trace.py`, reusing `scripts/lib.py` unchanged from the
prior experiment) and reads engine state through existing public
attributes only -- no monkey-patching, no internal method overrides.

## Artifacts

- `report.md` (this file), `results.json` -- this directory.
- `per_seed/seed_{1,3,10,14,17,22}.json` and `per_seed/seed_2_tied.json` --
  full per-seed trace output (within-C matched comparison, B-vs-C
  comparison, and 40 sample raw PC events each).
- `scripts/causal_trace.py`, `scripts/lib.py` -- the exact runnable code
  used to produce every number in this report.

## Runtime and process status

~16.5s per seed, ~116s total across 7 seeds. No processes from this audit
remain running -- every `causal_trace.py` invocation completed and exited
before this report was written; confirmed via `ps -u cxiong` immediately
before finalizing.
