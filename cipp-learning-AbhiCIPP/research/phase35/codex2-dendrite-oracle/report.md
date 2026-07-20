# Phase 35 dendritic coincidence oracle report

## Verdict

`SEMANTIC_CONTRACT_CONSISTENT`

The standalone model produced 19 golden scenarios spanning all requested cases and found no
counterexample in its bounded exhaustive search.

## Artifacts

- `reference_oracle.py` contains the parameterized model, golden-case builder,
  and exhaustive checker. It imports no production code.
- `golden_cases.json` records complete inputs and expected summaries.
- `results.json` records parameter sets, the exact search space, verdict, and
  counterexamples.
- `semantic_contract.md` states causal rules and the explicit shadow-delivery
  interpretation.

## Golden coverage

The 19 cases cover neither input; basal only; apical alone at maximum decoder
weight; same-step coincidence; offsets -1 and +1; equal scheduling with unequal
delivery; unequal scheduling with equal delivery; wrong target; wrong feedback
source; repeated single-branch events; timestep clearing; decoder threshold
crossing; three active targets out of nine; queue carryover with stale-same-pixel
and stale-wrong-pixel provenance; a mixed-origin carryover; one-time refractory
deferral; and active versus shadow delivery.

## Exhaustive search

The checker enumerates ordered records containing exactly two distinct event IDs.
Each event ranges over:

- branch: 2 values (`basal`, `apical`)
- source: 3 values (`input`, `feedback`, `other`)
- target: 2 values (`t0`, `t1`)
- scheduled timestep: 2 values (0, 1)
- delivered timestep: 2 values (0, 1)
- magnitude: 2 values (1, 2)
- origin pattern: 2 values (`A`, `B`)
- current pattern: 1 value (`B`)
- origin pixel: 2 values (`p0`, `p1`)
- current pixel: 1 value (`p0`)
- delivery role: 2 values (`active`, `shadow`)

This is 768 possible events and 768² = 589,824 ordered two-event records. Three
additional runs check weights immediately below, at, and immediately above the
maturity threshold, for 589,827 simulations total.

For every two-event record the checker verifies exact equivalence between the
physical gate and the conjunction of active role, opposite branches, configured
feedback source, equal target, and equal delivered timestep. It also checks no
spike/update without coincidence, update target locality, exactly-once delivery,
and end-of-timestep clearing. The boundary runs verify pre-update maturity.

Counterexamples: 0.

## Limits

The exhaustive claim is bounded to the documented domains and two-event records.
Multi-event behavior is represented by goldens, notably the nine-target case,
but is not exhaustively enumerated. Queue ownership and refractory mechanics are
outside the cell model: the oracle accepts the final delivered timestep and
checks exactly-once observation. Residual traces are intentionally non-causal and
therefore are not a state dimension. The result makes no claim about production
implementation, four-pattern ownership, or integrated network suppression.
