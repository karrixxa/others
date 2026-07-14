# Geometric Influence / Temporal Winner — Phase 1 Audit

Branch: `july14-integration`. Read-only audit per
`July_14_Geometric_Influence_Temporal_Winner_Brief.txt` §14 (required audit)
and §20 (most important immediate questions). No source files were modified
to produce this report; no mechanisms were changed. Scope: `backend/*.py`,
`neuron_flexible.py`, `layers.py`, `snn/rules/*.py`, `frontend/*.js`, plus the
tests and diagnostics that already exist in the repo.

## Headline findings (read this first)

1. **CONFLICT — the exposed "winner" is defined as the LATEST spiker, not the
   first responder.** `SimulationEngine._resolve_episode`
   (`backend/simulation.py:1616-1638`) picks `winner` by
   `latest_t = max(ts for ts, _ in episode_l2_spikes)`, tiebroken by most
   spikes — the literal opposite of brief §8/§9's "the first-spike identity
   carries the primary representation." This `self.winner` field is the only
   winner concept serialized to the frontend (`backend/simulation.py:1742,
   1750, 1775`) and is what `receptive.js`, `renderer.js`, and `charts.js`
   render as the assembly/pattern owner. Every dashboard-visible "ownership"
   signal in this codebase currently measures last-spiker, not first-spiker.
   The raw per-step WTA (`_resolve_l2_competition`,
   `backend/simulation.py:1285-1319`) *does* fire the first neuron to cross
   threshold immediately, and `episode_l2_spikes` retains the full ordered
   spike list — the first-responder data exists in memory — but nothing
   persists or reports it as `self.winner` does for latest-spike.
2. **CONFLICT — L2E placement is a mathematically perfect ring, exactly what
   brief §6 prohibits.** `L2_HOMES` (`backend/simulation.py:68-75`) places
   all 8 L2E neurons at identical radius `_R=3.2` and equal 45° angular
   spacing. Verified numerically (see below): every even-indexed L2E has an
   **identical** sorted set of 9 distances-to-pixel values, and every
   odd-indexed L2E has the other identical set — i.e. 8 neurons carry only a
   2-way geometric signature, not 8 distinct ones. No jitter, no
   minimum-separation rule, no randomness anywhere in position generation
   (confirmed: grep for `min_sep`/`separation`/`collision`/`overlap` in
   `backend/simulation.py`, `neuron_flexible.py`, `layers.py` — NOT FOUND).
3. **CONFLICT — L1I is not spatially selective; synchrony is by construction,
   not a bug.** `backend/simulation.py:693-707`: a single feedback-weight
   vector is drawn once and `.copy()`-assigned to all 9 L1I units
   (identical weights), all given the identical threshold
   (`inh.threshold = thr_l1i`), and all fed the identical scalar signal
   (whether any L2E won this step) rather than anything pixel-specific. This
   is explicit and commented ("Give the bank one task-independent feedback
   vector... independent random vectors create arbitrary phase groups with
   no pixel-local signal that could correct them" — line 693-696). All 9
   units are genuinely separate `Neuron` objects that each independently
   `fire()` (no event duplication/broadcast in the serializer — verified),
   but they are functionally clones, so they cross threshold on the same
   step by mathematical necessity, not because of any serializer or UI
   artifact.
4. **CONFIRMED — distance-based influence is live in production, not a dead
   flag.** `distance_weighting` defaults to `False` in the engine
   (`backend/simulation.py:459`), but `backend/api.py:98-101` (the actual
   dashboard entry point) explicitly sets
   `distance_weighting=True, distance_power=2.0, distance_ref=7.472,
   distance_min=1.0`. Given finding #2, this means the live system already
   applies a distance-shaped factor whose geometric input is a perfect ring
   — so the feature is real and active, but its symmetry-breaking effect is
   structurally capped at a 2-way split by finding #2. `distance_ref=7.472`
   (the ring's farthest L2E↔pixel distance) is chosen so every factor is
   `>= 1` — documented as a deliberate deviation from a literal `1/d²`
   attenuation, because a literal version "silences L2E entirely" (comment,
   `backend/api.py:90-97`). This is a considered engineering choice, not an
   oversight, but it means the deployed influence law is not the brief's
   literal `g_ij = 1/max(d,d_min)^2`.
5. **No confirmed double-application of influence in weight learning for the
   winner.** The winner's plasticity path uses the raw stored weight and
   (under the live `structural_free_energy=True` config) a gate based only on
   the neuron's own summed positive weights vs. threshold — no membrane
   potential, no distance term, enters that gate. However, for **losers**,
   `apply_competitive_reset` derives its depression magnitude `p_loss` from
   `v_pre` (`neuron_flexible.py:623-624`), and `v_pre` was already
   distance-attenuated at delivery — so distance shapes both "how much charge
   this loser had" and, through that same charge, "how hard it gets
   depressed." This is not a literal `factor²` bug, but it is a two-stage
   reuse of one distance-derived quantity in one computation path, which is
   exactly the class of thing brief §7 ("avoid applying influence twice")
   asks to be surfaced rather than silently accepted.
6. **No fake/synthesized raster spikes and no UI-side simulation found.**
   Both the L1I "9 rows" and the general raster are backed by 9 (or N)
   genuinely independent per-neuron `fire()` calls and `spiked` flags, traced
   end-to-end through `serializer.py` → `websocket.py` → `raster.js`/`charge.js`
   with no inference, duplication, or client-side membrane math found. See
   the frontend section below for the one real caveat (a client-computed
   "dead neuron" label in `receptive.js`).

## Geometry / coordinates (brief §14.1-2, §20.1-2)

- **Coordinates are engine state**, not renderer-invented. They live in three
  places: the module constant `L2_HOMES` (`backend/simulation.py:68-75`), the
  per-neuron `meta[nid]['pos']` dict built in `_register_neurons`
  (`backend/simulation.py:1007-1024`), and a per-afferent `n.distance` array
  cached on each L2E `Neuron` (`neuron_flexible.py:922-933`, populated by
  `_apply_l2e_distances`, `backend/simulation.py:1045-1066`). `renderer.js`
  reads `m.pos` off the `topology` message only (`renderer.js:85-89`) — no
  ring/circle/grid math exists client-side. **No coordinate-ownership
  conflict.**
- **L1E/L1I placement**: fixed 3×3 grid, `pos=[(c-1)*GRID, (1-r)*GRID, z]`,
  `GRID=2.2`, `z=0.0` (L1E) / `z=-2.0` (L1I) — no jitter. The brief treats a
  perfect L1 grid as acceptable-but-not-ideal (jitter recommended, not
  required); still a gap versus the brief's "seeded random position inside
  its assigned cell" recommendation.
- **L2E placement**: perfect ring (finding #2). **L2I**: single fixed point
  `[0, 0, 6.0]` — brief explicitly allows this ("does not need mathematical
  perfection... central placement reduces extreme unfairness").
- **Positions on reset/reseed**: `reset()` and `reseed()` both call
  `_build()`, which recomputes `L2_HOMES`/grid positions from the same
  deterministic (non-random) formulas every time — byte-identical across
  rebuilds. Only weights/seed change on reseed. So positions don't drift, but
  only because there is no randomness in their generation at all yet — the
  brief's "use a recorded random seed so the same geometry can be recreated"
  doesn't currently apply because geometry isn't seeded/random.
- **Minimum separation**: NOT FOUND anywhere.
- **Distance computation**: real Euclidean distance, computed once per
  `_build()` in `_apply_l2e_distances` and cached on the neuron — not
  recomputed per step. Verified numerically (`d_min=1.0` doesn't bind; real
  distances range ~4.0–7.47 given the current ring/grid geometry).
- **Distance distribution** (computed directly from the live constants):
  pairwise L2E–L2E distances collapse to 6 distinct values (ring symmetry);
  per-L2E sorted distance-to-pixel profiles are one of exactly two patterns
  (even vs. odd ring index): `[4.123, 4.673, 4.673, 5.122, 5.575, 5.575,
  6.72, 7.071, 7.071]` or `[4.001, 4.596, 4.596, 5.122, 5.993, 5.993, 6.406,
  6.406, 7.472]`. Influence (`1/max(d,1)^2`) ranges ~0.018–0.062 under a
  literal `d_ref=1` convention; under the live `d_ref=7.472` convention every
  factor is instead in `[1.0, ~3.5]`.

## Influence / distance application (brief §14.6-8, §20.3-4)

- Mechanism: `effective_weights()` (`snn/rules/delivery.py:19-26`) computes
  `factor = (distance_ref/max(d_i, distance_min))**distance_power` and
  returns `w * factor` as `w_eff`, used only inside `InstantaneousDelivery`/
  `FlowRateDelivery.deliver` (`delivery.py:38-45, 53-67`) to build the
  membrane deposit. Stored weights (`n._weights_array`) are never mutated by
  this factor.
- Learning uses the raw binary participation mask
  (`n._last_input_spikes`, set unscaled in `delivery.py:45,67`) and the raw
  stored weight (`snn/rules/excitatory.py:65-85`) — distance does not
  re-enter the winner's own potentiation term under the live
  `structural_free_energy=True` config. See finding #5 for the loser-path
  caveat.
- Live config confirms distance-weighting is genuinely on
  (`backend/api.py:98-101`), contradicting an initial assumption that it's an
  inert default — it is a real, active, but geometry-starved feature (finding
  #4).
- `L2E_INIT_JITTER=0.05` (`backend/simulation.py:239`) is unrelated — it
  jitters initial *feedforward weight* draws, not geometry. No code confuses
  the two, but the name is easy to mis-scan for "geometric jitter."

## Learning equation (brief §14, §7)

Active rule (confirmed via `signed_spike_learning=True` in both the engine
default, `backend/simulation.py:520`, and the live `api.py:73`):
`SignedSpikeRule.on_fire` (`snn/rules/excitatory.py:65-85`) computes a signed
±1 participation signal and calls the shared kernel `bounded_signed_update`
(`snn/rules/excitatory.py:30-57`). That kernel does **not** use the brief's
literal symmetric `(1 - w/w_cap)^2` on both directions — it normalizes
`q = clamp((w-w_min)/(w_cap-w_min))` and uses `H_up(q) = 1-q²` for
potentiation but `H_down(q) = 1-(1-q)²` (reflected) for depression, with the
kernel's own docstring explaining why: a literal negative `1-(w/w_cap)^2`
"becomes zero at w_cap and would make a capped losing weight impossible to
depress" (`excitatory.py:36-39`). This is a **documented, deliberate**
departure from the brief's example formula, not an accidental substitution
of `w^2` — but it is a departure the brief's own text says not to make
("Do not replace it with w², 1-w²/w_max, or another superficially similar
equation") without it being flagged, so it needs an explicit decision, not
silent inheritance. The plain quadratic `dw = eta*p*(1-(w²/w_max))` does
still exist as `ChargeBasedRule` (`excitatory.py:129-133`) but is inactive
under the live config (`signed_spike_learning=True` takes precedence).

## Probe plasticity (brief mention)

**No "probe" plasticity mechanism exists.** The only hits for "probe" in the
codebase are `_refractory_probe()` in `sustained_dominance.py` (a test/diagnostic
helper) and an old-pattern-retention re-probe described in
`metrics_consolidation.py:63-94` — both are measurement scripts, not an
engine-level plasticity rule. There is no `apply_probe`/`probe_plasticity` in
`neuron_flexible.py`, `layers.py`, or `backend/simulation.py`.

## Threshold-crossing, argmax, hard-reset (brief §14.14-16, §20.6-8)

Three distinct "winner" concepts coexist at different levels — conflating
them would misread the system:

1. **Physical WTA** (`_resolve_l2_competition`,
   `backend/simulation.py:1285-1319`): among neurons crossing threshold
   *this step*, `max(eligible, key=potential)` fires; ties break by Python's
   `max` (lowest index), not an explicit documented rule. This is the one
   that actually fires, drives L2I, and triggers resets — and it is,
   in effect, first-in-time already, since competition resolves every step.
2. **Episode-reporting winner** (`_resolve_episode`,
   `backend/simulation.py:1616-1638`): latest-spike-wins (finding #1) — this
   is a pure reporting field (`self.winner`), never touches weights, WTA, or
   membrane state, but it is the only thing the UI/dashboard/metrics see as
   "the winner."
3. **Auto-cycle streak winner** (`_auto_cycle_tick`,
   `backend/simulation.py:1189-1224`): `argmax` over spike **counts**
   accumulated across a `visit_steps` window — used only to decide when a
   pattern counts as "trained" for the auto-cycle scheduler, not the
   moment-to-moment WTA.

`apply_competitive_reset` (`neuron_flexible.py:599-660`) is confirmed **not**
a permanent lock: it clears membrane/current traces unconditionally but sets
no persistent disabled flag, and it does not touch the refractory timer — a
reset loser remains eligible to fire again on a later step. No `argmax` over
hidden/opaque membrane state is used to *declare an owner*; the closest thing
is the auto-cycle streak counter, which only gates scheduling, not learning
or the winner label used elsewhere.

**None of the brief §9 diagnostic fields are currently recorded**:
`physicalFirstSpiker`, `physicalFirstSpikeStep`, `earliestResponseSet`,
`sameStepTie`, `L2I threshold source`, `L2I delivery step`, and
"which L2E event gets credit for L2I's threshold crossing" are all absent as
named/persisted fields. The raw data to reconstruct most of them exists
transiently in `episode_l2_spikes` (an ordered list of `(t, neuron_id)`) but
is discarded after `_resolve_episode` keeps only the latest-spike label.
L2I's causal source can only be inferred post hoc by correlating same-step
`True` entries in `self.spiked`, never explicitly linked.

## L2E→L2I / L2I→L2E (brief §14.11, §20.7)

- **Accumulation**: L2I is driven only by the current step's single WTA
  winner (`l2e[winner]=1.0`, then `l2.inhibitory_neuron.receive_input(l2e,
  t=t)` — `backend/simulation.py:1303-1306`), through that winner's own
  learned E→I weight — not a broadcast of every L2E spike (only one L2E can
  spike per step anyway under WTA). L2I also decays via its own leak when
  `l2i_leak_enabled` (off in the live config: `leak_enabled=False`,
  `l2i_leak_enabled=False`, `backend/api.py:68-69`).
- **Delivery**: when L2I crosses threshold, **every** non-winner L2E
  (`backend/simulation.py:1311-1318`) gets an unconditional
  `apply_competitive_reset()` — unweighted hard reset to rest plus structural
  depression of participating positive weights, explicitly not a learned
  `L2I->L2E` gate magnitude (removed; see
  `L2_Hard_Reset_Competitive_Depression_Spec.md`). This physically delays
  competitors (finding relevant to brief §20.7: yes, L2I's firing does
  physically suppress rivals for at least one step via the hard reset), but
  there is **no per-neuron delay/conductance-style ramp** — it's an
  instantaneous, all-or-nothing reset the step L2I fires, not the brief's
  "delayed conductance-like inhibitory event" model.
- **Audited exemption**: distance-weighting is applied only on the L2E↔pixel
  feedforward path (`_apply_l2e_distances` only touches
  `l2.excitatory_neurons[j].distance`); the L2E→L2I and L2I→L2E paths carry
  **no distance-based influence at all** currently. This is not a
  "documented and tested" exception per brief §6's requirement — it's simply
  unimplemented. **CONFLICT / gap**, not yet resolved either way.

## Why all nine L1I units fire together (brief §14.12, §20.5)

See finding #3. Structural, not a serializer artifact: identical weights
(one vector `.copy()`-assigned to all 9, `backend/simulation.py:697-705`),
identical threshold, identical scalar input (does the current step have *any*
L2E winner — not which pixel it represents). Each unit is a real, distinct
`Neuron` that independently calls `fire()`
(`backend/simulation.py:1489-1491`); the serializer/websocket path was
traced end-to-end and confirmed not to duplicate or synthesize this (or any)
event (`backend/serializer.py`, `backend/websocket.py`, `raster.js:63-73`,
`charge.js:63-78`).

## Scheduler (brief §14.18, §20.9)

**Interleaved round-robin, not train-to-saturation.** `_auto_cycle_tick`
(`backend/simulation.py:1189-1224`) advances to the next pattern in
`_cycle_order` after a fixed `visit_steps` dwell regardless of whether the
current pattern is "trained," stopping the whole cycle only once every
pattern has met its streak threshold. `ablation_harness.py` and
`stage_learning_harness.py` implement the same fixed-dwell round robin for
their own diagnostics.

## Preset parity (brief §14.19)

`PATTERNS`/`N_OUT` are single-sourced from `backend/simulation.py` in every
harness checked (no duplicate constant copies). However, **behavioral**
config differs substantially: the live dashboard (`backend/api.py:66-176`)
enables `distance_weighting`, `structural_free_energy`, `loser_depression`,
`l2i_hard_reset_losers`, `hard_reset_clear_traces`; `ablation_harness.py`'s
`BASELINE` and `stage_learning_harness.py`'s `MINIMAL` presets leave most of
these at the engine's own (different) constructor defaults. Diagnostic-script
results are **not directly comparable** to live-dashboard behavior unless the
same overrides are applied — this is a real gap versus brief §13's "dashboard
and command-line diagnostics must use the same shared preset."

## Frontend (brief §14, UI-artifact check)

No coordinate-ownership conflict, no fake/inferred spikes, no client-side
membrane simulation, no locally-invented simulation parameters (config comes
from `/api/config`, patterns from `topology.patterns`). Two items worth
tracking, both low-severity relative to the engine-level conflicts above:

- `frontend/receptive.js:148,167-168` computes its own "dead neuron" label
  (sum of top-3 `w/threshold` ratios `< 1.0`) independently of the backend's
  own confidence/consolidation notion of a stalled unit
  (`backend/simulation.py:344,346`) — these two "dead" concepts could
  diverge and should not both be trusted as equivalent.
- "Hide silent lanes" (brief §10/§20.10's concern about mistaking hidden
  lanes for specialization) **does not exist in the current frontend at
  all** (`raster.js` only has a manual L1-layer show/hide toggle) — so this
  specific risk is not live yet, but there's also no safeguard/label
  prepared for when it's built.
- `inspector.js` exposes only weight + confidence per synapse; distance,
  influence, and effective-transmission are **not serialized to the client
  at all** (`backend/simulation.py:1714-1718`'s synapse payload has no
  distance/influence fields) — brief §11/§7's required per-connection
  inspector fields are absent end-to-end, not hidden by the frontend.

## Baseline tests and diagnostics (unchanged, no edits)

Ran on `july14-integration` HEAD (`b02cd9e`) with no source changes, using a
throwaway venv (`numpy`, `pytest`, `fastapi`, `uvicorn`, `websockets` per
`requirements.txt`; venv lives outside the repo and was not committed):

- **`pytest -q`: 117 passed, 5 failed** — all 5 failures are pre-existing and
  unrelated to this audit (no code was touched): `test_assembly_flow_credit.py
  ::test_integration_four_pattern_regime_is_active_and_bounded`, and 4 in
  `test_flow_rate.py` (`test_flow_off_is_baseline`,
  `test_flow_builds_charge_smoothly`,
  `test_flow_can_cross_threshold_without_new_input`,
  `test_flow_forces_single_chunk`) — all appear to be exercising
  `excitatory_flow_rate`, which `backend/api.py:153` and its own comment
  (`api.py:149-152`) say the engine now pins OFF unconditionally in `_build`,
  making these tests' assumption (that turning the flag on changes behavior)
  stale versus current engine behavior. This is a pre-existing test/engine
  drift, not something introduced here — flagged for whoever owns the next
  phase, not fixed in this audit.
- **`sustained_dominance.py`** (unmodified, run as-is): baseline
  (`subtractive_reset` OFF) mean over 4 seeds: `distinct=2.00/4,
  sustained_dominance=0.497, dead=5.00` — consistent with
  `AGENT_HANDOFF.md`'s documented current state (no true 1-to-1 ownership).
- **`ablation_harness.py --seeds 1 2 --epochs 3`** (unmodified, small run for
  baseline capture): `dom=0.39±0.015, distinct=2/4, collisions=2, dead=5,
  rf_cos 0.915->0.904`. Consistent with the sustained-dominance run above.

No diagnostic output files were committed (per `CLAUDE.md`: never commit
generated diagnostic outputs) — the numbers above are transcribed directly
into this document instead.

## Classification summary

- **Confirmed engine behavior** (not UI, not hypothesis): perfect L2E ring
  geometry; identical L1I weights/thresholds/input causing lockstep firing;
  `distance_weighting=True` live in `api.py` with `d_ref` chosen to keep
  factors `>=1`; episode winner = latest-spike-wins; three distinct
  "winner" concepts (physical WTA / episode report / auto-cycle streak);
  `apply_competitive_reset` is not a permanent lock; interleaved round-robin
  scheduler (no train-to-saturation); no minimum-separation rule; no probe
  plasticity mechanism; distance applied once (not literally squared) for
  the winner's own learning, but reused across two dependent computations
  for losers.
- **UI artifacts / frontend-only concerns**: `receptive.js`'s independently
  computed "dead" label; hardcoded `N_PIX=9` assumption baked into 3
  frontend files instead of read from topology (would silently mismatch if
  backend `N_PIX` ever changed); "hide silent lanes" doesn't exist yet, so
  no live risk but no prepared safeguard either.
- **Conflicts with the brief that need a decision, not just an implementation
  task**: (1) latest-spike winner vs. brief's first-spike-identity
  requirement — this likely explains much of the "ownership instability"
  documented in `AGENT_HANDOFF.md`; (2) perfect-ring L2E geometry with only a
  2-way distinguishing signature, actively feeding a live distance-weighting
  feature that therefore can't deliver its intended symmetry-breaking; (3)
  L1I has zero pixel-selectivity, contradicting the brief's "learned/predicted
  spatial pattern" expectation; (4) L2E→L2I / L2I→L2E paths carry no
  distance influence at all (undocumented exemption, not a tested one); (5)
  the active depression kernel's asymmetric `H_up`/`H_down` split versus the
  brief's literal symmetric `(1-w/w_cap)²` on both directions; (6) dashboard
  vs. CLI-diagnostic presets diverge on several behavioral flags.
- **Unknowns / not yet determined**: whether same-step ties can occur under
  any non-default engine configuration (`lasting_inhibition` branch also
  reduces to a single `max`-selected winner, but this wasn't exhaustively
  checked against every flag combination); whether the "dead" label
  divergence between `receptive.js` and the backend's confidence/consolidation
  state has ever produced a visibly wrong dashboard label in practice (not
  reproduced here, only shown to be possible by construction).

No mechanisms were changed to produce this report. Nothing has been merged
from `four-pattern`. Nothing was pushed.
