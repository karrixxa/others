# 3. Mechanisms, Failures, and Lessons

## 3.1 Local feedforward learning

The intended feedforward rule strengthens only synapses involved in a locally observed causal event. A typical bounded potentiation uses presynaptic activity, postsynaptic participation, a learning rate, and a saturation factor. This gives an owner stability without an external target label.

The core tension is plasticity versus preservation:

- rapid growth helps a representative become responsive;
- saturation prevents divergence;
- excessive compression makes candidates too similar;
- depression can free capacity but can also destroy useful or recoverable inputs;
- maturity can stabilize old knowledge but can prevent correction.

The experiments therefore moved from asking “do weights change?” to asking whether the final weights support distinct, recoverable behavior under frozen-learning probes.

## 3.2 Winner-take-all and causal credit

The desired causal sequence is:

1. several L2 neurons integrate the same volley;
2. one physically crosses threshold first;
3. its spike recruits inhibition;
4. rivals are prevented from claiming the same event;
5. only causally justified synapses receive winner credit.

A synchronous simulator can violate this sequence by marking all same-step crossers as simultaneous. A deterministic tie-break may make the output reproducible but still insert a hidden winner policy. Analytic sub-boundary timing was introduced to recover a physical order from the membrane trajectories.

### Failure modes

| Failure | Observable symptom | Scientific problem |
| --- | --- | --- |
| Late inhibition | Several L2 neurons fire for one input. | Duplicate ownership and ambiguous learning credit. |
| Hard immediate reset | Earliest cell wins nearly every presentation. | First-responder tyranny; unused cells cannot recruit. |
| Global feedback inhibition | All lower-level features are suppressed. | Winner identity and prediction selectivity are erased. |
| Weak local inhibition | Duplicate specialists survive. | Sparse representation is not established. |
| Persistent conductance | Rivals remain suppressed into a new pattern. | Switching is impaired. |
| Reset followed by fresh accumulation | Rivals rebound tens of steps later. | A one-time pulse does not create stable competition. |

The central lesson is that inhibition is part of the computation, not a cleanup operation.

## 3.3 Pattern overlap and the center pixel

Because all four patterns share pixel 4, a simple positive Hebbian rule repeatedly reinforces the center for every pattern. An early center advantage can become self-amplifying:

1. a neuron is slightly better aligned to the center;
2. it crosses first more often;
3. its center weight strengthens;
4. it becomes competitive for every pattern;
5. other neurons lose opportunities to specialize.

Centered/covariance-style encoding attempts to represent deviation from common activity rather than raw positive co-activation. Reported experiments reduced the center/peripheral imbalance but did not eliminate the dynamical competition problem. This showed that representation and competition must be repaired separately.

## 3.4 Weight saturation, compression, and exact zeros

The saturating term \((1-w/w_{max})^2\) is useful because it makes growth diminish near a bound. Yet several interacting processes can still compress a population:

- repeated winners approach a common ceiling;
- losing cells can be driven toward the same lower bound;
- global normalization can couple otherwise local synapses;
- exact clipping at zero removes current from an afferent;
- recovery may require a postsynaptic spike that the weakened afferent can no longer help produce.

Later reported probes found that exact zero was not mathematically absorbing in every case, but was functionally absorbing in most measured completed states. This motivates an explicit positive floor or a recovery mechanism if zero is not intended to mean permanent pruning.

## 3.5 Prediction: from broadcast to local explanation

The early global architecture allowed a higher-level winner to recruit all lower-level inhibition. That can reduce activity but cannot show that the correct features were predicted.

The refined contract is:

1. an L2 representation sends structured feedback;
2. feedback reaches candidate local prediction columns;
3. only columns with concurrent sensory evidence create a valid match;
4. matched activity recruits paired local inhibition;
5. unmatched sensory activity remains as residual;
6. persistent residual may trigger updating or a switch.

### Required measurements

- source L2 spike time;
- apical delivery time and target;
- basal sensory event time and target;
- coincidence decision;
- prediction-cell membrane and spike;
- paired inhibitory delivery mass;
- target L1 membrane/firing difference versus shadow;
- response of unrelated novel columns;
- later ownership/switching, measured separately.

The active and shadow circuits must be iso-topological. If the active condition also removes a global inhibitory pathway, the comparison cannot attribute the result to local prediction alone.

## 3.6 Why additive coincidence failed conceptually

An additive neuron receives sensory charge (b) and feedback charge (a). If (a+b\geq\theta), coincidence can fire—but repeated (a) alone may also accumulate past threshold unless decay and timing are exact. Raising decoder weights enough for one-volley response can make feedback alone sufficient. Lowering them can create a cold start in which the cell never spikes and therefore never learns.

The explicit dendritic abstraction resolves the logical ambiguity:

\[
g(t)=\mathbf{1}[B(t)>0] \cdot \mathbf{1}[A(t)>0],
\]

where (B(t)) is a physically delivered basal event and (A(t)) is a physically delivered apical event in the allowed window. Only if (g(t)=1) does the coincidence mechanism deliver somatic charge or enable its local update.

This is AND-like, but it remains a dynamical event mechanism rather than a conventional clocked logic gate.

## 3.7 Learning and firing must be separate

The decoder has a cold-start problem if potentiation requires a mature prediction-cell spike. The lecture-derived solution was to permit local subthreshold coincidence to update eligibility or decoder weight while requiring a real somatic spike before physical inhibition occurs.

This creates two thresholds of evidence:

- **learning eligibility:** bottom-up and top-down events met locally;
- **physical explanatory action:** the prediction/coincidence cell actually fired and delivered inhibition.

A weight-crossing event should not retroactively make the current event mature. The pre-update value determines the current physical response; the new value affects a later coincidence.

## 3.8 Residual and mismatch switching

Residual activity is not simply “high total activity.” It is local sensory evidence that was not explained by the current top-down prediction.

The later reported delayed-local proposal used:

\[
R_i(t)=\mathbf{1}[\text{basal evidence at }i],\mathbf{1}[\text{PC}_i\text{ did not fire}],
\]

and a local eligibility matrix (e_{j,i}) updated only when prediction cell (i) fired in connection with apical input from L2 candidate (j). A candidate-specific mismatch request was then

\[
q_j(t)=\sum_i e_{j,i}(t)R_i(t),
\]

queued for delayed delivery to the paired candidate. The attraction of this rule is locality: it requires no pattern label or global owner oracle. Its weakness is that a plausible formula is not enough; the queued delivery must be shown to alter the appropriate L2 dynamics.

## 3.9 Carryover, switching, and boundary hygiene

Events already in a delay queue at a pattern switch are physically part of the prior causal history. Deleting them makes evaluation cleaner but changes the model. The project therefore treated queue carryover as something to measure and classify.

Similarly, manually zeroing membranes can isolate synaptic structure in a controlled probe, but that result must not be confused with normal continuous operation. Both carried-state and controlled-state probes are useful when labeled correctly.

## 3.10 Visualization as an instrument

The dashboard evolved to expose:

- spike rasters;
- membrane charge buildup;
- weights and receptive fields;
- inhibitory delivery;
- causal stories and source/target events;
- pattern phases and stepping;
- topology and preset selection.

These views helped reveal bugs and unexpected dependencies. They also created a new hazard: a panel may display a queued or counted event without proving that it changed the physical model. The interface is an instrument, not the evidence itself.

## 3.11 Experimental discipline learned

The project converged on a stronger validation hierarchy:

1. **Specification:** state the intended local mechanism and prohibited shortcuts.
2. **Structure:** verify the expected neurons, edges, and compartments exist.
3. **Mechanics:** verify event timing, delivery, state clearing, and learning locality.
4. **Isolation:** compare active and shadow conditions differing in one physical action.
5. **Behavior:** measure selective suppression, ownership, recovery, and switching.
6. **Robustness:** repeat across seeds, schedules, and index permutations.
7. **Interpretation:** claim only what the experiment directly supports.

This hierarchy is one of the most important outcomes of the work.
