# PHASE35_SELECTIVE_SWITCH_TIMING_CONTRACT

Read-only architectural design and timing analysis, at
`db30ceadbe18cf90e01f6d54dee0203f342b24a8`. No production file edited, no
experiment run, no Codex artifact touched. This is a design document, not
an implementation -- nothing here is committed or executable. Codex 2's
separate residual-signal-in-seed-3 experiment was not duplicated: this
analysis derives everything from code reading and the already-established
`step()` ordering, not from running the engine.

## Verdict

**`LOCAL_SELECTIVE_SWITCH_TIMING_VALID`**

A minimal local pathway satisfying every stated constraint is buildable
from primitives that already exist in this codebase (coincidence-gated
dendritic compartments, per-connection traces, delayed inhibitory delivery
registers). Exact earliest timesteps resolve cleanly with no circularity.
The mechanism can act within an ordinary held presentation -- it does not
structurally require waiting for the next pattern -- subject to the
documented failure-mode safeguards below, which are necessary design
requirements, not open unknowns.

## Grounding: the two existing facts this design leans on

1. **Step ordering** (established in the prior causal-reach audit,
   `backend/simulation.py` `step()`, re-verified here): the PC
   coincidence-resolution block (`~2646-2669`) executes *before* the L2
   feedforward/competition block (`~2671+`) within the same step. This is
   structurally different from the legacy L1I pathway, whose own fire
   happens *after* L2 competition that step, forcing a genuine one-step
   delay before it can matter to L2 at all.
2. **L2 eligibility is a pure per-neuron potential check**
   (`_resolve_l2_competition`, line 2429: `eligible = [j for j, e in
   enumerate(l2.excitatory_neurons) if e.check_threshold()]`). Nothing
   about this is a global argmax -- it is N independent local threshold
   checks. A targeted inhibitory delivery to one L2Ej's own potential,
   applied before this line runs that step, removes exactly that one
   neuron from `eligible` and nothing else -- the same mechanism already
   used for L1I->L1E (`apply_inhibition`), just re-targeted.

Causal-reach audit finding this design must explicitly not repeat: the
existing PCi->Ii->Ei pathway suppresses the *shared* L1E layer every
competing L2E depends on equally, which is exactly why it can reach L2 with
100% reliability and still never change ownership (confirmed empirically,
including under a genuine tie). The new pathway targets L2Ej's *own*
excitability instead, precisely to avoid this.

## The minimal pathway

### Cells and synapses (per pixel i, per L2 source j)

- **`R_i` (Residual cell)**, one per pixel, alongside the existing `PC_i`.
  Two inputs, same physical sources `PC_i` already has:
  - *Excitatory*: the same delayed basal signal `PC_i` already receives
    from `s_to_pcol_queue` (L1E_i's state from step t, arriving at t+1).
  - *Inhibitory (shunting veto)*: `PC_i`'s own spike this step. If `PC_i`
    fires (the coincidence gate opened -- this pixel's current apical
    source explained it), `R_i` is vetoed. If `PC_i` does *not* fire while
    the basal input is present, `R_i` fires.
  - This is `Residual_i(t+1) = basal_i(t) AND NOT PC_i(t+1)` -- an AND-NOT
    motif built from signals `PC_i` already has, no new sensory tap, no
    comparison across pixels, no label.
  - Per the false-switching failure mode below, `R_i` should integrate
    (require >=2 accumulated unexplained-basal events, mirroring L1I's own
    accumulation requirement) rather than fire from one instance --
    detailed in Failure modes.

- **`elig[j,i]`**, one scalar trace per existing apical connection (i.e.
  living on the same `DendriticConnection` object that already carries
  `d[j,i]`, not a new data structure). Set (bumped toward a ceiling) at the
  moment L2Ej's apical event is *delivered* to pixel i's apical compartment
  -- the same delivery event `PC_i`'s own coincidence gate observes, not a
  new tap. Decays on a *fast* timescale, much faster than `d[j,i]`'s own
  permanent, monotonic growth (see Trace semantics below).

- **`SwitchI_j`**, one per L2 source (mirrors `L1I_i`'s one-per-pixel
  structure). Two inputs:
  - *Excitatory*: `R_i`'s spike, routed through the same connection object
    that carries `elig[j,i]` -- i.e. `SwitchI_j` only ever hears about
    residual at pixel i *through* the (j,i) connection, which is what
    makes the routing local rather than a lookup table.
  - *Gate*: `elig[j,i]` above a fixed threshold. Both conditions must hold
    for `SwitchI_j` to fire -- residual alone or trace alone is
    structurally insufficient (see below).
  - Output: one inhibitory event, delivered *only* to `L2Ej`'s own
    potential, via the same `apply_inhibition`-style mechanism already used
    for `L1I->L1E`. Never a broadcast to the pool.

No new population beyond `R_i` (9 cells) and `SwitchI_j` (`N_OUT` cells,
i.e. 8 by the current pool size) is required. No new synapse type is
required beyond the existing decoder connection plus one new scalar trace
riding on it.

### Signs

- `R_i`: excitatory input from basal L1E (delayed), inhibitory (shunting)
  input from `PC_i`'s own spike.
- `elig[j,i]`: not a signal, a local state variable; set by an excitatory
  event (apical delivery), decays passively.
- `SwitchI_j`: excitatory input from `R_i` (gated by `elig[j,i]`); output is
  strictly inhibitory, targeted at `L2Ej`.
- Everything downstream of `SwitchI_j` at `L2Ej` is the existing inhibitory
  delivery mechanism (`apply_inhibition`), unchanged.

### Queue / delay behavior and exact earliest timesteps

Let `t` be the step L2Ej wins and its apical event is scheduled
(`arrival_step = t + prediction_feedback_delay`, i.e. `t+1` under the
committed default delay of 1 -- same queue `PC_i` already uses, no new
queue class needed, `elig[j,i]` is written at the same delivery event
`PC_i`'s apical compartment already observes):

| Quantity | Earliest step | Why |
|---|---|---|
| `elig[j,i]` can be set | **t+1** | same step the apical event is physically delivered (delivery, not scheduling, per the repaired queue-carryover contract) |
| `Residual_i` can exist | **t+1** | same step `PC_i` resolves its own coincidence (or fails to) using this same delivered data |
| `SwitchI_j` can fire | **t+1** | both its inputs (`R_i`, `elig[j,i]`) are available same-step, since the PC block runs before the L2 competition block within `t+1` |
| Incumbent inhibition can *arrive* at `L2Ej` | **t+2** | deliberately deferred one further step via a new delay register (see below), *not* applied same-step |
| A rival can physically cross | **t+2** | earliest step `L2Ej` is actually excluded from `eligible`, per `_resolve_l2_competition`'s per-neuron threshold check |

**Why the inhibition is deferred to t+2 rather than applied same-step at
t+1, even though the code order would structurally allow same-step
delivery:** every other inhibitory pathway in this codebase (`L1I->L1E`,
`L2I->L2E`) is queue/register-based, never a same-step intervention reached
into the middle of an in-progress competition block. Reaching into
`_resolve_l2_competition` mid-step would be a genuinely new kind of
causal path with no existing precedent, more fragile (order-of-operations
sensitive, interacts unpredictably with `l2_charge_chunks`), and,
critically, is exactly what closes the circularity question below cleanly
by construction rather than by argument. A one-step register
(`switch_inhibition_delay[j]`, set at the end of t+1 from `SwitchI_j`'s
fire, read at the start of t+2's L2 competition, mirroring
`l1i_feedback_delay` exactly) is the minimal, consistent, already-precedented
choice.

**Whether action must occur on the next pattern presentation: no.** Given
`prediction_feedback_delay=1`, the full chain from "L2Ej wins with an
unexplained residual at t" to "a rival gets a fair shot at t+2" is two
steps. Ordinary held presentations in this codebase run hundreds to
thousands of steps (1000+ in the mature-efficacy and causal-reach audits),
so t+2 is essentially always *within* the same presentation. The only edge
case is a residual detected in the last step or two before a scheduled
pattern/probe switch, in which case the consequence (t+2) spills into the
next presentation -- this is a normal, expected queue-carryover case, not a
special one, and should be handled exactly like the already-repaired
PC queue-carryover: not reset or dropped at the boundary, classified via
the same `current-correct`/`stale-*`/`mixed` telemetry convention already
built for `PC_i`, reusing `_prediction_column_origin_class`'s pattern
rather than inventing a second one.

### Circularity check

The task's concern: `PC_i`'s firing depends on L2 feedback, while the
switch changes *later* L2 ownership -- could this become circular (using
information from a decision that hasn't happened yet)?

It cannot, and the reason is the same discipline the existing architecture
already enforces for decoder learning: every input to this pathway is
*delayed, already-physically-delivered* data.

- L2Ej's spike at `t` is generated from `t`'s own feedforward drive,
  computed independently of `PC_i`/`R_i`/`SwitchI_j` entirely (L2
  competition is causally upstream of and blind to this whole pathway).
- That spike is *queued*, not used instantaneously -- it only becomes
  visible to `PC_i`/`elig[j,i]` on delivery at `t+1`, by which point it is
  strictly past information.
- `Residual_i(t+1)` and `elig[j,i](t+1)` are therefore both judgments about
  `t`, computed at `t+1` -- never about `t+1` itself, let alone anything
  later.
- `SwitchI_j`'s own effect is *further* deferred via its own register to
  `t+2` -- it can only ever influence L2 decisions from `t+2` onward, never
  retroactively touch the `t` or `t+1` decisions that produced the
  information it acted on.

This is an ordinary closed-loop control structure with a fixed minimum
latency (2 steps here) -- a thermostat reacting to a past temperature
reading, not an oracle reading a future one. It is the exact same causal
discipline already verified for `d_before_learning` ordering and the
PC delivery queues; this design adds no new class of risk, only reuses the
existing one correctly.

### Trace creation, decay, and reset semantics

`elig[j,i]` must be **structurally distinct from `d[j,i]`** -- this is the
single most important modeling choice, and worth stating explicitly since
conflating them would violate "no weight decay" (the task's own
constraint) by turning the permanent, monotonic decoder into something that
decays:

- **Creation**: bumped (not simply set to a ceiling, to avoid a hidden
  binary/labeling flavor) by a fixed increment on every apical delivery
  event to (j,i), regardless of whether `PC_i` ends up firing that step --
  eligibility reflects "j recently tried to explain pixel i," not "j
  succeeded."
- **Decay**: a fast passive leak, on the order of a handful of steps'
  time constant -- much faster than `d[j,i]`'s permanent growth, and
  faster than a typical presentation's length, so eligibility reflects
  *recent* activity only, never stale history from an earlier presentation
  or an earlier, now-irrelevant pattern.
- **Reset**: cleared at the same presentation-switch boundary the PC
  compartments themselves are (or rather, is *not* force-cleared any more
  than PC's own physical queue is, per the repaired queue-carryover
  contract -- it decays naturally on its own fast timescale rather than
  being wiped). This keeps the new mechanism consistent with the existing,
  already-repaired "do not reset physical/eligibility state at switches"
  principle.
- **No decay on `d[j,i]` itself, ever** -- the switch pathway reads `d[j,i]`
  nowhere; it only reads the separate, fast `elig[j,i]` trace and the
  physical apical-delivery event. The decoder's existing monotonic,
  saturating, never-depressed contract is completely untouched.

### Conditions preventing residual-only or trace-only switching

Structural, not incidental: `SwitchI_j`'s firing condition is an explicit
two-input AND (`R_i` AND `elig[j,i] > threshold`), built the same way
`PC_i`'s own basal-AND-apical coincidence gate is built. Residual alone
(e.g. genuinely novel sensory input right after a pattern switch, before
any L2E has tried to explain it yet -- `elig` is near zero for everyone)
cannot fire `SwitchI_j` for any j, because no j's gate is open. Trace alone
(recent delivery, but no residual because everything is in fact explained)
cannot fire it either, because `R_i` is silent. There is no path to firing
`SwitchI_j` that bypasses either input -- this is a hard-wired AND, not a
soft/weighted combination that could be satisfied by one strong input
alone.

### How the mechanism avoids over-broadly suppressing rivals

`SwitchI_j`'s output is delivered *only* to `L2Ej`'s own potential -- never
to L1E (unlike the legacy pathway), never broadcast to the L2 pool (unlike
`L2I`'s own uniform delivery). Any L2Ek with k != j and no recent apical
delivery to pixel i has `elig[k,i] ~ 0` and is never targeted, regardless
of how much residual exists -- its own feedforward drive from L1E is
completely untouched, exactly satisfying "preserve the sensory drive
available to rival/spare L2 cells."

**Honest limitation on tied competitors, stated rather than hidden**: if
two L2E's are genuinely tied and *both* deliver apical feedback to pixel i
in the same step (a documented, common occurrence in this codebase -- see
the causal-reach audit's seed 2), `elig[j,i]` and `elig[k,i]` are *both*
set together, and if residual persists despite both of them explaining
part of the pattern, `SwitchI_j` and `SwitchI_k` both fire and both
incumbents are inhibited together. This is not a bug to be engineered away
under the "no global argmax" constraint (there is no local, label-free way
to pick a winner between two exactly-equal local traces without a global
comparison) -- and arguably it is the *correct* behavior: a persistent tie
that still leaves residual is precisely the pathology this mechanism exists
to disturb, and suppressing both co-incumbents together (rather than
neither) is what actually opens the door for a genuine third, previously
silent rival to get a look. What the mechanism reliably avoids is
suppressing an *uninvolved* rival that had nothing to do with the residual
-- it does not, and structurally cannot, promise to protect one member of
an actively-tied pair from the other's fate.

### How legacy global L1I activity is kept out of the switch decision

By construction, not by a guard flag: `R_i`, `elig[j,i]`, and `SwitchI_j`
are wired exclusively from (a) the existing delayed basal/apical queues
`PC_i` already uses and (b) `PC_i`'s own spike outcome. `L1I_i` -- whether
running in legacy global-broadcast mode or the existing Phase 21 selective
mode -- never appears anywhere in this wiring. There is no code path by
which `L1I`'s state could influence `R_i`/`elig`/`SwitchI_j`, so the
pathway's behavior is provably identical regardless of
`prediction_column_to_i_enabled`'s setting. This should be directly
testable the same way `test_default_off_equivalence` already is: construct
two engines differing only in the legacy L1I flag, confirm `R_i`/`elig`/
`SwitchI_j` state is byte-identical between them.

### Default-off equivalence requirements

A new flag, e.g. `switch_inhibition_enabled: bool = False`, gating the
entire pathway, following the exact precedent of `prediction_column_enabled`
and `prediction_column_to_i_enabled`:

- Off: no `R_i`/`SwitchI_j` cells built, no `elig[j,i]` trace allocated or
  updated, no new register, zero code executed beyond a boolean check.
  Must be byte-identical to the current committed engine on the same
  deterministic-run/hash-comparison test already used for the two existing
  flags (mature-efficacy audit's 120-step SHA-256 comparison is a direct
  template).
- On: must not alter `d[j,i]`'s own trajectory, the existing PCi/L1I
  pathway's behavior, or L2's ordinary competition when no `SwitchI_j` ever
  fires (i.e. a run with zero residual events must also be byte-identical
  to the flag-off case) -- this is the natural, stronger sibling test to
  flag-off equivalence.

## Failure modes

- **Oscillation.** Incumbent A suppressed at t+2 -> rival B wins instead
  -> if B's own decoder for this pixel is still immature, B also fails to
  explain it -> residual persists -> B's own freshly-set `elig[j=B,i]`
  combined with the still-present residual could fire `SwitchI_B` next,
  ping-ponging between A and B forever. **Required safeguard**: `SwitchI_j`
  needs its own per-target refractory period (mirroring
  `L1I_FEEDBACK_REFRACTORY`) -- once j has been inhibited, it cannot be
  re-targeted for a minimum dwell window, giving whichever L2E currently
  holds the pixel a fair, protected interval to actually mature its
  decoder there before being judged again. Without this safeguard the
  mechanism is not viable; with it, oscillation is bounded by construction.
- **Permanent incumbent suppression.** The inhibitory delivery to `L2Ej`
  must be a bounded, temporary event (a fixed-magnitude discharge with the
  same recover-via-leak/refractory semantics every other inhibitory event
  in this codebase already has), never a permanent weight change or lesion
  -- matches the task's own word "temporarily," and keeps this pathway
  categorically different from anything resembling weight decay.
- **Union predictors producing no residual.** If some L2Ej's decoder has
  matured broadly enough (or a blended/ambiguous representation happens to
  satisfy the coincidence gate) that `PC_i` fires reliably across all the
  relevant pixels, `Residual_i` never appears, and this pathway has no way
  to detect or correct that -- it only reacts to *absence* of explanation,
  not to whether an explanation that technically fires is semantically
  correct or too general. This is a real, honestly-stated blind spot:
  representational over-generality is a different failure mode from
  under-explanation, and this specific mechanism cannot address it.
- **False switching on familiar, correctly-explained patterns.** A single
  missed coincidence (ordinary refractory/timing noise on an otherwise
  correct, mature incumbent) must not trigger a switch. **Required
  safeguard**: `R_i` should require accumulated evidence (>=2 unexplained-
  basal events, mirroring `L1I`'s own 2-event accumulation before it can
  fire) rather than firing from a single instance -- consistent with the
  rest of this codebase's design philosophy that nothing fires from one
  ambiguous event.

## Why the other four verdicts do not apply

- `VALID_ONLY_ON_LATER_PRESENTATION`: would require the earliest possible
  effect to fall structurally outside the current presentation. t+2 sits
  well inside an ordinary presentation's length; only a boundary edge case
  spills over, and that is handled as ordinary queue carryover, not as a
  structural requirement.
- `REQUIRES_NONLOCAL_INFORMATION`: every signal used (delayed basal,
  delayed apical, `PC_i`'s own spike, a per-connection trace) is already
  local to the existing architecture; nothing here compares across pixels,
  uses a label, or computes a global argmax.
- `TIMING_CYCLE_UNRESOLVED`: exact earliest steps are given for every
  requested quantity, and the circularity question is closed by
  construction (queue-delayed inputs, register-delayed output), not left
  open.
- `ARCHITECTURE_NOT_VIABLE`: every component maps onto a primitive that
  already exists and is already tested elsewhere in this codebase
  (coincidence-gated AND dendrite, per-connection scalar state, delayed
  inhibitory register, targeted `apply_inhibition`-style delivery) -- there
  is no unbuildable requirement.

## Scope discipline

No production file was edited. No experiment was run -- everything above
is derived from reading `backend/simulation.py` (the already-established
`step()` ordering and `_resolve_l2_competition`, re-verified at lines
2429-2489 for this analysis) and `snn/dendrite.py`'s existing compartment
pattern, not from executing the engine. This does not duplicate Codex 2's
residual-signal-in-seed-3 experiment -- that is an empirical measurement of
whether residual actually occurs given real trained weights; this is a
structural design/timing analysis of a mechanism that does not yet exist,
independent of any particular seed's outcome. No Codex 1 or Codex 2
artifact was read or touched. No process was started. Nothing pushed.
