# Phase 19A — Corrected Prediction Scaffold Checkpoint

This checkpoint implements the **corrected per-input-column prediction
scaffold** described by
`Phase18b_Lecture14_Prediction_Architecture_Contract_Corrected.md`.

It does **not** implement active decoder plasticity. It does **not** promote
the earlier "one predictor per L2E, broadcast to all 9 L1E" topology as the
main Lecture 14 path.

## Implemented topology

- Existing `L1E0..L1E8`, `L1I0..L1I8`, `L2E0..L2E7`, `L2I` unchanged as
  populations.
- New prediction population: exactly `P0..P8`.
- Interpretation: `Pi` means "predict / reconstruct input pixel i", not
  "representation neuron i".
- Stored decoder matrix: `L2Ej -> Pi`, serialized as `decoder{j}->{i}`.
- Fixed replay path: `Pi -> L1Ei`, serialized as `pred{i}->{i}`.
- No `P -> L1I`.
- No `P -> P`.
- No `P -> all L1E` broadcast.

## Implemented timing

- `t`: sensory evidence drives existing L1/L2 dynamics and an `L2E` may spike.
- `t+1`: queued decoder events from that physical `L2E` spike arrive at `P`.
- `t+2`: queued replay from a physical `P` spike arrives only at the matching
  `L1E`.

No same-step `L2E -> P -> L1E` shortcut exists in `step()`.

## Controls and observability

Prediction remains default-off. When enabled, the backend reports:

- the nine `P` neuron ids and pixel mapping;
- stored and effective decoder matrices;
- local replay mapping and weight;
- control mode: `normal`, `disabled`, or `shuffled`;
- queued / arrived / integrated / delivered prediction events;
- prediction neuron voltage, threshold, refractory state, spikes, and firing
  frequency through the standard neuron state serializer.

## Deliberately not implemented here

No active `L2E -> P` plasticity rule runs in this checkpoint.

The unresolved local-learning requirement is:

- a future decoder rule must decide whether **pixel i** was truly present when
  a causal `L2E` event arrived at `Pi`;
- that teaching signal must be local to the `Pi` column / incoming synapse;
- it must not use pattern names, owner assignments, argmax routing, hidden
  winners, or global reconstruction error.

This checkpoint therefore only scaffolds storage, delivery, controls, and
evaluation hooks for the corrected topology.

## Focused verification

`test_prediction_phase19.py` verifies:

- feature-off baseline equivalence;
- exactly nine `P` neurons;
- full `8 x 9` `L2E -> P` connectivity;
- strict one-to-one `P -> L1E` replay;
- no `P -> L1I`;
- no same-step `L2E -> P`;
- no same-step `P -> L1E`;
- replay reaches only the matching `L1E` column;
- frozen replay does not mutate weights, confidence, or specialization state;
- disabled/shuffled controls do not mutate the stored decoder matrix;
- existing `L1I` / `L2I` causal behavior is unchanged when prediction is inert.
