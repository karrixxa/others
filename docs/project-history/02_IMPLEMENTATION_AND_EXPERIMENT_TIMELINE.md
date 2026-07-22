# 2. Implementation and Experiment Timeline

This timeline distinguishes branch-local evidence from later phase reports preserved in `notes2/`.

## 2.1 Early flexible simulator lineage

The directory `cipp-learning-AbhiCIPP/` contains the earlier from-scratch implementation and its transition toward the four-pattern problem.

Major components include:

- flexible neuron and cortical-column classes;
- local excitatory and inhibitory learning experiments;
- stage-learning, lockout, dominance, and ablation harnesses;
- a FastAPI/WebSocket dashboard;
- receptive-field, weight, raster, charge, and inspection views;
- reports diagnosing L2I integration, ownership instability, initialization, and consolidation.

The branch history shows the following locally verifiable milestones:

| Date | Commit | Evidence-backed change |
| --- | --- | --- |
| July 13 | `ec3ece8` | Converted the active recognition task to four center-crossing patterns. |
| July 13 | `3791b6a` | Aligned active tests with the four-pattern task. |
| July 13 | `9e17e0e` | Added a readable raster and one-pattern diagnostics. |
| July 13 | `5519036` | Integrated charge buildup with the raster and selection. |
| July 13 | `c1f4dbc` | Added hover, stepping, pixel legend, input weights, and causal-story UI. |
| July 13 | `a21bca6` | Added measurement/configuration infrastructure without intended neural-rule changes. |
| July 13 | `dbf648b` | Added a measurement-only sequential four-pattern diagnostic. |
| July 14 | `92d9858` | Added an L2I extinction tracer. |
| July 14 | `b342b58` | Corrected a false DEAD badge and added Fit View. |
| July 14 | `fcc8db5` | Integrated July 14 probe and causal diagnostics. |
| July 14 | `88ed801` | Added July 14 measurement and raster work. |
| July 14 | `4e24e26` | Measured symmetry and ownership across seeds. |

These commits establish the actual progression from a visually inspectable simulator to increasingly measurement-driven diagnosis.

## 2.2 Root graph-based rebuild

On July 21, commit `2a3093d` uploaded the root graph-based simulator and its complete artifact set. Commit `5cee7ef` added its top-level specifications, reports, and README; commit `6ec6a29` added the class notes through July 21.

The graph model introduced:

- `NetworkSpec` typed nodes and typed edges;
- a generic simulation engine driven by the graph;
- five built-in experimental presets;
- topology serialization and a browser editor;
- golden topology snapshots and regression tests;
- saved multi-seed experiments;
- a distinct event-resolved coincidence preset.

### Preset progression

| Preset | Scientific purpose | Important limitation |
| --- | --- | --- |
| `old` | Dense winner-gated L1 inhibition plus shared L2 competition. | Winner identity is erased by dense feedback. |
| `pi` | Pattern-specific predictive interneurons learn local inhibitory outputs. | Early predictive inhibition did not reliably produce the intended turnover. |
| `rg` | Inserts explicit retinal-ganglion-like event sources and a plastic RG→L1 path. | Keeps dense old feedback, so it does not isolate contextual explaining-away. |
| `rg_residual` | Preserves an evidence path, creates a residual sheet, and tests charged SwitchI coincidence. | More complex; behavior must be separated from display activity and routing bugs. |
| `rg_coincidence` | Explicit basal/apical coincidence plus analytic sub-boundary ordering. | Its hard reset and tuned initialization solve a bounded turnover protocol, not the general four-pattern problem. |

## 2.3 Predictive-inhibition study

The saved predictive-inhibition artifacts compare baseline and prediction-enabled conditions over row→column→row schedules. The final report explicitly separates architecture from outcome.

The main lesson was negative but useful: adding a locally plastic predictive-inhibition pathway did not automatically produce robust incumbent replacement. Depending on configuration, the incumbent could remain dominant, new competition could be poorly recruited, or an apparent change could reflect altered topology rather than selective prediction.

This led to three methodological requirements:

1. compare active and shadow mechanisms with identical topology and state;
2. measure the physically delivered inhibitory effect, not just learned weights;
3. measure explained and novel pixels separately rather than using total activity alone.

## 2.4 RG and residual/error studies

The RG work separated exogenous evidence from cortical inhibition. An active input pixel repeatedly causes an RG event; L1 receives it through a learned afferent rather than through direct external injection. This exposed timing and initialization effects that were hidden when the sensory cell itself was the source.

The residual topology preserved a complete evidence path and copied activity into an ErrorE sheet. Predictive inhibition targeted the residual sheet. SwitchI was intended to combine residual charge with a local incumbent trace so that only a charged coincidence could challenge the incumbent before normal WTA recomputed the winner.

The agent-workflow record notes an implementation audit in which SwitchI edges appeared active in the interface but the neuron was still acting like a Boolean relay rather than accumulating the intended charge. Correcting that bug illustrates why an illuminated edge is not evidence of the intended dynamics.

## 2.5 Event-resolved coincidence study

The `rg_coincidence` preset changed the numerical model more fundamentally. Instead of resolving all threshold crossings only at integer step boundaries, it computes analytic crossing times within a boundary. Immediate reset events can then be ordered by physical crossing time.

The saved turnover sweep tested row→column→row across eight seeds and multiple initialization fractions and coincidence learning rates. Its selection record identifies `L2 init total = 0.95θ` and `C eta = 0.001` as the selected setting, with order-invariant behavior in the paired-order check. The README also reports success for the tuned turnover protocol with zero L2 tie events.

This is a real bounded result. It does **not** demonstrate equal-interleaved ownership for all four patterns, nor does it show that zero-latency hard reset is the final biologically preferred mechanism.

## 2.6 Linear-weight ablation

The linear ablation artifacts tested whether removing the saturating weight update improved ownership or composition. The experiments separated isolated weight behavior, factorial conditions, confirmation seeds, and a composition probe.

The stored composition result shows why a seemingly learned pair of row/column owners does not guarantee immediate composition: with membrane carryover removed and learning frozen, neither owner necessarily crosses threshold on the first plus-pattern boundary. Some apparent crossings in the carried condition depend on pre-existing membrane state. This reinforced the need to separate learned synaptic structure from dynamical state.

## 2.7 Later Phase 27–39 work preserved as reports

The class notes describe a later experimental program whose complete code/commit chain is not contained in this branch snapshot.

### Phase 27: causal ownership audit — reported

Persistent collisions were associated with an early advantage on the universally shared center input. Both winner potentiation and loser depression contributed; neither alone explained every failure.

### Phase 28A: common-input activity gate — reported

A proposed gate attempted to prevent the shared center feature from dominating learning. It did not provide a complete ownership solution.

### Phase 29: centered/covariance encoder — reported

Centering reduced the center/peripheral imbalance substantially and modestly improved distinct ownership, but did not produce robust four-owner success by itself.

### Phases 30–33: paired inhibition and timing alternatives — reported

Experiments explored local inhibition, accumulation, defer-once strategies, and microstep timing. Fast repeated inhibition prevented rebound but produced first-responder tyranny. A K=20 microstep candidate failed its ownership gate; K=1 was retained for subsequent small tests.

### Phase 34: active-dendrite feasibility — reported

An explicit same-step coincidence rule passed isolated feasibility gates and decoder weights matured organically. The integrated active condition did not show the intended selective suppression and may have confounded local prediction with a routing/topology change. It was treated as partial, not promoted.

### Phase 35: decoder/coincidence maturity — reported

Longer natural exposure produced decoder maturation in many but not all seeds. The notes distinguish shadow prediction from physical local suppression and warn that prediction and ownership are separate questions.

### Phases 36–38.1: local predictive output and delayed mismatch — reported

The proposed path evolved from a same-step product toward a local delayed pipeline:

- a residual exists when basal L1 evidence is present but the corresponding coincidence cell does not fire;
- a local eligibility trace links an L2 candidate to a prediction column only through actual decoder/coincidence events;
- eligibility times residual produces a request;
- the request is queued and delivered later to the paired L2 candidate;
- there is no global argmax, label, ownership oracle, or same-step hard reset in this path.

The reports also record instrumentation bugs caused by renamed queue fields and an expected signal field that was absent. These were software defects, not scientific verdicts.

### Phase 39/39.2: preset and dashboard parity — reported

The work exposed a usability/scientific reproducibility problem: backend mechanisms could exist while the dashboard still opened in a baseline preset. A final-candidate preset and prediction/coincidence panel were added in the reported lineage. Frontend/API parity was checked separately from neural dynamics.

## 2.8 Why the timeline matters

The development was not a monotonic march toward one solved model. Each apparent success narrowed the real question:

- WTA required causal ordering, not just a selected index.
- local prediction required selective physical delivery, not a feedback edge.
- coincidence required compartment semantics, not enough additive charge.
- stable ownership required post-training probes, not training dominance.
- a working backend required preset/UI parity to be observable and reproducible.

The resulting history is valuable because it documents both mechanisms and the reasons several attractive shortcuts were rejected.
