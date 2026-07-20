# Phase 35 oracle v2 and repaired-production conformance

## Verdict

`REPAIRED_PRODUCTION_CONFORMS_TO_ORACLE_V2`

The corrected independent oracle and repaired production commit
`db30ceadbe18cf90e01f6d54dee0203f342b24a8` agree on every tested semantic
projection. The repair bundle SHA-256 is
`1b330b7402913a5ed92402fba41f1105d687ca1ed080985bef470903f8c3587e`,
matching the supplied checksum.

## Oracle v2 corrections

Decoder associations are keyed by feedback source and target: `d[j,i]`.
Learning applies once per distinct locally delivered positive feedback source:

`eta * 1 * (1 - d_before/d_max)^2`

The local factor is binary. Positive event magnitude opens eligibility but does
not multiply the learning delta. Magnitude does scale physical charge: basal
charge is magnitude times fixed basal weight, and apical charge is magnitude
times `d_before[j,i]`. Multiple same-source events can add charge but cause only
one source-target update in a timestep.

Same-step, same-target basal and configured apical delivery opens the dendritic
gate. Pre-learning weighted charge then determines whether the ordinary soma
reaches threshold. Learning is local to the open gate and does not require a
soma spike. This resolves the earlier gating-structure question without copying
production behavior: the written biological contract supports separate
coincidence and somatic-response stages, and production uses that structure. No
`GATING_CONTRACT_MISMATCH` was found.

## Golden and semantic enumeration

Twenty corrected goldens were run. They retain the prior 19 scenario families
and add an explicit magnitude-charge-versus-learning-factor case. Oracle v2 and
production match all 20 on coincidence targets, spikes, source-target update
keys, delivery counts, and end-of-timestep clearing.

The bounded semantic enumeration covers 9,216 ordered two-event records from 96
single events:

- branch: basal, apical
- source: input, feedback, other
- target: t0, t1
- scheduled timestep: 0, 1
- delivered timestep: 0, 1
- magnitude: 1
- role: active, shadow
- provenance: current-correct

It checks gate equivalence, no effect without an open gate, clearing, and
exactly-once delivery. Counterexamples: 0. This is a bounded enumeration, not a
rerun of the original 589,824-record space.

## Maturity behavior

The isolated maturity trace uses basal weight 0, soma threshold 5, `d_init=4`,
eta 1, and `d_max=11`. Pre-learning apical charge and post-learning weights are:

| Coincidence | `d_before` | Current fire | `d_after` |
|---:|---:|:---:|---:|
| 0 | 4.0 | no | 4.404958677685951 |
| 1 | 4.404958677685951 | no | 4.764417934239916 |
| 2 | 4.764417934239916 | no | 5.085760774726105 |
| 3 | 5.085760774726105 | yes | 5.374837019467993 |

The third update crosses the effective threshold but does not fire its current
event. The fourth valid coincidence fires. Boundary controls at pre-learning
weights 4, 5, and 6 produce false, true, and true respectively.

## Queue carryover repair

A deterministic pair scheduled before a switch—`L2E0 -> PC4.apical` and
`L1E4 -> PC4.basal`—remains in the parallel delay queues after switching from
`row 1` to `col 1`. It arrives once, produces the expected PC4 response, and is
classified `stale-same-pixel`. On the following step PC4 does not repeat and the
last-delivery record is empty. Normal compartment state still clears through the
cell update path.

## Sparse learning and default-off behavior

With one feedback source reaching nine targets and basal input at targets 1, 4,
and 7, both systems update exactly:

- `feedback->t1`
- `feedback->t4`
- `feedback->t7`

Weights at t0, t2, t3, t5, t6, and t8 remain byte-identical.

Default-off engines at base `4764f1758a7399439df2242dfa60819501fc2333` and
repaired production were run for five seeded steps. Their spike-map and complete
weight-state hashes are identical:

`1b864ebc809a5c45022a88d5c9cbbdc8eb2202b00466fb1311100b4406170959`

## Scope

No production files were edited. The original oracle and all prior artifacts
were left unchanged. Gate C, integrated suppression, ownership, and parameter
tuning were not run. `mismatch_traces_v2.json` contains zero mismatches. No
processes remain running.
