# Adapter audit

The frozen conformance adapter was imported without modification and its
`production_case` maturity trace was compared with a new direct trace using
`Neuron`, `CoincidencePyramidalCell`, and the production
`SimulationEngine._apply_prediction_column_learning` method.

Both paths use:

- initial decoder weight 4;
- eta 1;
- decoder maximum 11;
- production coincidence threshold 5, mapped from oracle maturity;
- soma threshold 7, mapped from the oracle soma threshold;
- basal weight 0 with a positive basal signal, preserving physical basal
  eligibility without adding charge;
- one positive apical signal per coincidence.

Their stored weights after the two updates are exactly equal as Python floats:
4.404958677685951 and 4.764417934239916. Both produce zero spikes. Therefore
adapter routing, state persistence, and response projection do not cause the
maturity mismatch.

The oracle and production equations differ. The accepted oracle applies
`eta * apical_magnitude`, giving delta 1 and `4 -> 5`. Production applies
`eta * (1 - d/d_max)^2`, giving raw delta 0.4049586776859504 and stored delta
0.4049586776859506. The tiny raw/stored difference is ordinary floating-point
subtraction rounding and is far too small to explain the threshold outcome.

The adapter maps the oracle maturity value to the production coincidence
threshold because production exposes no separate decoder-maturity parameter.
That mapping is not responsible for the divergence: direct production and the
adapter agree, and both compare pre-update dendritic charge against 5 before
learning. Somatic response is never reached in the reduced trace because total
dendritic charge remains below 5.

The queue mismatch is also below the projection layer. The adapter's direct-cell
golden cannot model an engine presentation switch, so the audit manipulates the
real production engine queues and calls the real `_start_presentation`. Both
deques are replaced with zero-filled deques. This is a genuine engine state
transition, not an adapter interpretation.
