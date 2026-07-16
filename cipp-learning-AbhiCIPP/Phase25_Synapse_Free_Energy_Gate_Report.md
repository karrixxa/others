# Phase 25 — Synapse-Level Free-Energy Experiment: GATED OFF

**Status: gate assessed, implementation NOT started. No new flag, no
free-energy rule, no code change of any kind in this phase.**

## The gate

Phase 25 was explicitly scoped as: **"PROCEED ONLY AFTER a prediction
signal is demonstrably meaningful."** It must not reuse the existing
neuron-wide structural free-energy value and call it synaptic; it should
test whether correct synapses stabilize independently while incorrect
peripheral synapses remain plastic, and treat the universal center pixel 4
separately from pattern-distinguishing pixels.

## Assessment: the prediction signal is meaningful in DIRECTION but not in MAGNITUDE/GROWTH

This is a genuinely mixed picture, reported honestly rather than forced
into a clean pass or fail:

**What IS meaningful** (established across Phases 19–22): the *qualitative*
decoder signal — which `R_j → PCi` synapse gets credited — is real and
correct. Precision is exactly 1.0 across every pattern, every seed, every
combination tested with `pretrained_l2i_recruitment` (Phase 22). Only
synapses that causally, physically contributed to a genuine coincidence
event ever move at all (Phase 19's locality tests). Center pixel 4 is
correctly distinguished from peripheral pixels throughout (never conflated
with failure). This is not a noisy or arbitrary signal — the *direction* of
what it learns is exactly right.

**What is NOT meaningful yet**: the *growth dynamics* a synapse-level
free-energy rule would need to modulate. Phase 20's 50,000-step trajectory
showed decoder weights plateau completely by step 10,000 and never move
again — not because the synapses have "reached equilibrium" in any
free-energy sense, but because `PCi` itself simply stops physically firing
once upstream `L2` competition settles into a fixed rhythm (Phase 19's
switch-boundary finding: coincidence firing is front-loaded and phase-
sensitive). A free-energy gate modulates *how much a synapse learns when
its neuron fires* — but here the bottleneck is *whether the neuron fires at
all*, which free-energy has no mechanism to address. Building a synapse-
level stabilization rule on top of a signal whose growth is already
externally throttled by an unrelated upstream dynamic would not test the
free-energy hypothesis at all — it would just measure "how much of nothing
can a rule stabilize," and any apparent stabilization would be a trivial
artifact of `PCi` no longer firing, not evidence the rule is doing
anything.

## Decision

**Do not implement a synapse-level free-energy rule in this phase.** The
gate does not cleanly pass: there is a real, correct qualitative signal to
work with, but the specific growth dynamics this phase would need to test
against (sustained, ongoing per-synapse learning that a free-energy gate
could meaningfully modulate) are not currently present under realistic
training. Revisiting this would first require addressing Phase 19's
front-loaded/phase-sensitive firing issue (a genuine open problem, not
resolved by any phase so far) so that `PCi` continues to fire — and
therefore continues to generate learning events — well past the initial
transient. Only then would there be a live, ongoing per-synapse learning
process for a free-energy gate to act on.

## Commit

This report only. No production code, no new tests.
