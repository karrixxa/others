# 5. Current State and Open Questions

## 5.1 Status matrix

| Component | Status | Evidence-based interpretation |
| --- | --- | --- |
| Four center-crossing 3×3 inputs | Implemented | Present in the simulator and tests. |
| Event-driven spiking and delays | Implemented | Multiple engine paths and timing tests exist. |
| Local bounded feedforward adaptation | Implemented | Present in neuron/engine code and weight experiments. |
| L2 competition | Implemented in several forms | Deterministic WTA, conductance-based inhibition, and event-resolved hard reset have all been explored. |
| Analytic sub-boundary ordering | Implemented | Used by `rg_coincidence`; tested for causal event order. |
| Pattern specialization | Experimentally observed under bounded conditions | Stronger than random response, but not robustly solved for all four patterns across all schedules. |
| Row→column→row turnover | Experimentally observed in tuned `rg_coincidence` protocol | Eight-seed artifact exists; depends on selected initialization and hard-reset architecture. |
| Predictive inhibitory connectivity | Implemented | Several topologies contain learnable prediction pathways. |
| Selective prediction effect | Partial | Some isolated mechanics and suppression are measured; later intended local mechanism remains incompletely validated. |
| Basal/apical coincidence | Implemented in root `rg_coincidence`; later morphology work reported | Exact relationship between root preset and later Phase 35–39 lineage must not be conflated. |
| Residual/error sheet | Implemented in `rg_residual` | Physical effect requires configuration-specific validation. |
| Local delayed mismatch/SwitchI | Reported | Later Phase 38.1 design is described in notes but not fully represented in this branch code. |
| Robust four-pattern ownership | Open | Reported later audits continued to find collisions and incomplete coverage. |
| Preservation without forgetting | Partial/open | Row recovery exists in a bounded protocol; general continual stability is not established. |
| Symbol binding and composition | Open | Composition probes expose limitations; no complete symbol network exists. |
| Scale invariance and what/where | Open | Conceptual future architecture only. |
| Hardware efficiency | Open | No branch-local neuromorphic hardware measurements. |

## 5.2 What can be claimed now

The project can credibly claim that it:

- translated several CIPP principles into executable, inspectable spiking mechanisms;
- created a controlled overlapping-pattern environment for falsifying those mechanisms;
- demonstrated local learning and pattern-dependent specialization under some configurations;
- showed that event timing and inhibitory causality materially change ownership;
- implemented explicit prediction, residual, and coincidence pathways;
- demonstrated a tuned row→column→row turnover result in the event-resolved root preset;
- identified multiple mechanisms that looked successful visually but failed stronger causal or robustness tests;
- developed a reproducible research workflow combining specifications, code, tests, experiments, visualization, and audits.

## 5.3 What should not be claimed

The current evidence does not support saying that:

- the full CIPP architecture is complete;
- the network robustly learns all four patterns under arbitrary schedules and seeds;
- prediction is proven to improve ownership;
- coincidence counters alone demonstrate predictive suppression;
- one neuron per pattern is a settled biological claim;
- the simulator establishes brain-level symbolic reasoning;
- the model is already more energy efficient than conventional hardware;
- every Phase 35–39 result is present and reproducible from this branch;
- Pong, DnD, or Pi performance claims are verified by this repository.

## 5.4 Immediate scientific questions

### 1. Which code lineage is the next baseline?

The repository should choose explicitly between:

- the root graph/event-resolved `rg_coincidence` architecture;
- the July 14 flexible lineage;
- the later Phase 35–39 local prediction lineage described in notes.

Combining their strongest ideas without first defining one executable baseline will reproduce the current ambiguity.

### 2. Can four-pattern ownership be measured without tuning to one schedule?

A decisive protocol should use:

- equal-interleaved and phased schedules;
- standard and shifted pixel-index permutations;
- preregistered seeds;
- frozen-learning post-training probes;
- stable-owner, confusion, latency, and unused-neuron metrics;
- no hidden owner locks, labels, argmax assignments, or pattern-boundary resets.

### 3. Does prediction selectively change lower-level dynamics?

Run an iso-seeded, iso-topological shadow-versus-active comparison where the sole difference is physical delivery of paired local prediction inhibition. Measure explained and novel pixels separately.

### 4. Does local mismatch change the appropriate L2 candidate?

Trace the entire chain: residual creation → eligibility update → request → queue → paired delivery → candidate membrane/firing → re-competition. A nonzero request is not enough.

### 5. How should zero weights behave?

Decide whether zero means reversible silence or structural pruning. If reversible, use a positive floor or a local recovery path and test it directly.

### 6. What biological detail is necessary?

Leak, refractory recovery, conductance, dendritic compartments, and ion-channel-inspired state should be added only when each resolves a defined causal ambiguity. Biological detail without a falsifiable role can make the simulator harder to interpret.

## 5.5 Recommended paper framing

The paper should be a CIPP-centered technical retrospective:

1. why CIPP matters;
2. the pathway from sparse events to symbols;
3. the controlled four-pattern model;
4. local unlabeled learning and competition;
5. prediction, residual, and basal/apical coincidence;
6. what the simulator experiments taught;
7. current evidence and open mechanisms;
8. AI agents as supporting research instruments;
9. broader importance for alternative computing.

The strongest contribution is not a claim that the final network is solved. It is the conversion of CIPP ideas into causal mechanisms that can be implemented, measured, contradicted, and refined.

## 5.6 Repository cleanup recommended before the next experiment

- Declare one canonical runnable directory in the root README.
- Add a `CURRENT_BASELINE.md` with exact commit, preset, flags, and run commands.
- Link every headline result to an immutable JSON/report artifact.
- Move superseded proposals into a clearly labeled historical directory.
- Preserve phase reports but label whether their implementation is present in the branch.
- Make the selected preset visible in every exported result and screenshot.
- Keep documentation-only, UI-only, measurement-only, and dynamics commits separate.

These are not cosmetic changes. They reduce the chance that a future agent or researcher tests a different system than the one intended.
