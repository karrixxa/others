# Phase 35 production-to-oracle conformance report

## Verdict

`MIXED`

Production conforms on timestep-local physical gating, state clearing,
default-off behavior, exactly-once observation, and source/target-sparse
learning. It does not conform on pattern-switch queue carryover or on the
accepted oracle's threshold-crossing learning sequence.

## Integrity and isolation

- Bundle SHA-256 observed:
  `656b3a63522ddcb5f9960765769f90e167c660fb9ea5f7bbdbb4feaa6e727685`
- Production commit checked out: `4e712a4b7dea033b9191680a4b4e3577d93ca304`
- Base commit checked out: `4764f1758a7399439df2242dfa60819501fc2333`
- The bundle reports complete history and passed `git bundle verify`.
- Production and oracle files were read/imported but not modified.

## Golden cases

All 19 accepted golden inputs were executed through both implementations.
Eleven match the complete comparison projection exactly. Eight differ in the
decoder association key: the accepted oracle records the basal source
(`input->target`, or `inN->target`), while production's decoder is physically
the apical feedback connection (`feedback->target`). Physical coincidence,
delivery counts, and end-state clearing agree in all 19 direct-cell runs.

The threshold-crossing golden has an additional behavioral difference. Starting
at `d=4` with maturity 5, the oracle's update reaches 5 and the next coincidence
spikes. Production's saturating update reaches 4.404958677685951 and then
4.764417934239916, so neither coincidence spikes.

## Physical timing and clearing

Neither input, single-branch inputs, offsets, schedule/delivery permutations,
wrong target, wrong feedback source, repeated single-branch events, shadow
delivery, and timestep clearing all match the oracle's physical gate.

Pattern-switch carryover does not. A queued nonzero basal/apical pair was placed
in the production engine's two delay queues. Calling `_start_presentation`
replaced both with zero vectors. The accepted contract requires already queued
physical events to survive a switch. This is a `PHYSICAL_TIMING_MISMATCH` within
the overall mixed verdict.

The one-time deferral golden records each event exactly once. The direct
production adapter delivers the deferred event once, and the engine delay queue
uses one `popleft` per step; no duplicate was observed. The switch reset is a
separate silent-loss path.

## Maturity and learning order

At `d_before` values 4, 5, and 6 around maturity 5, oracle and production spike
decisions agree: false, true, true. Production resolves coincidence before
calling its learning method. Therefore `d_before_learning` determines the
current event, and a learning update cannot retroactively fire that event.

The subsequent-coincidence threshold-crossing sequence nevertheless differs
because the update equations do not produce the same post-event weight. The
allowed verdict vocabulary has no distinct learning-equation verdict; this
difference is represented under `LEARNING_ORDER_MISMATCH` in `results.json`,
with the explicit qualification that ordering itself passed.

## Locality and sparse learning

With feedback delivered to nine apical targets and basal input at targets 1, 4,
and 7, production updates exactly `feedback->t1`, `feedback->t4`, and
`feedback->t7`. The other six floating-point weights remain byte-identical.

A separate two-source test delivers only `feedback1`; only its connection
changes, while `feedback0` remains byte-identical. Production therefore passes
source and target locality. The association-name disagreement with the oracle is
reported as a conformance difference, not as a production locality failure.

## Default-off comparison

Separate subprocesses loaded production and base commits, constructed default
engines with seed 7, ran five steps, and hashed timestep, spike-map, and complete
weight snapshots after each step. Hashes are identical:

`1b864ebc809a5c45022a88d5c9cbbdc8eb2202b00466fb1311100b4406170959`

Result: no `DEFAULT_OFF_MISMATCH` observed in this bounded comparison.

## Bounded exhaustive comparison

The production comparison enumerated 9,216 ordered two-event records from a
96-event domain:

- branch: basal, apical
- source: input, feedback, other
- target: t0, t1
- scheduled timestep: 0, 1
- delivered timestep: 0, 1
- magnitude: 1
- provenance: current-correct only
- delivery role: active, shadow

The exhaustive projection covers coincidence count/targets, delivery counts,
and clearing. It intentionally excludes decoder association naming and spike
calibration, which have dedicated tests above. Counterexamples in this bounded
physical projection: 0.

The accepted oracle's original 589,824-record enumeration remains unchanged;
this production comparison is a smaller feasible causal subset and reports its
domain exactly.

## Scope and process status

No Gate C, integrated suppression, four-pattern ownership, or parameter tuning
was run. No production files were patched. No conformance processes remain
running at report completion.
