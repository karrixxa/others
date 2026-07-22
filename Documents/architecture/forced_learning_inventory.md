# Forced Learning / Forced-Win Inventory

Living catalog of levers that assign winners, binders, or plasticity by **code policy** rather than authentic model dynamics. Cross-links: [`tenant_compliance_no_forced_win_research.md`](tenant_compliance_no_forced_win_research.md), [`tenant_compliance_remediation_plan.md`](tenant_compliance_remediation_plan.md) Stage 9.

**Status:** Production force exclusivity cascade restored (2026-07-21). Soft race + graded + Stage 14 autonomy are labeled control outside `hybrid_cortical_biological`. Under bio+coincidence, winners emerge from full-pop race + graded E/I + **plastic per-assembly I→E gates** (turnover, subthreshold ceiling) + continuous RF–sensory mismatch attenuation + dendritic latch eligibility with **honest apical**. Primary column ownership is receiver-owned `EmergentOwnershipEvidence`; `bind_pattern` is an optional revisable readout latch. AbhiCIPP argmax WTA remains **forbidden**.

## Disposition key

| Tag | Meaning |
|-----|---------|
| **keep-as-labeled-control** | Reachable outside bio; forbidden under bio |
| **replace-with-biology** | Retire under bio/lab when coincidence + graded I pass gates |
| **retire** | Delete or diagnostic-only (no mutation authority) |
| **audit-only** | Observe / log; never decides \(\Delta w\) or winners |

## Profile tags

| Tag | Meaning |
|-----|---------|
| **production** | Force exclusivity cascade (`exclusivity` ON, `descending_mode=force`, autonomy OFF) |
| **hybrid** | Legacy `hybrid_cortical` forced-win chain |
| **bio** | `hybrid_cortical_biological` |
| **lab** | Explicit lab flags |

---

## A. Hybrid cortical-column chain (legacy)

| # | Symbol | Forces | Profile | Severity | Disposition |
|---|--------|--------|---------|----------|-------------|
| 1 | `HybridCorticalColumn._process_pattern_legacy` | Sensory from `line_id` | hybrid | hard | keep-as-labeled-control |
| 2 | `Layer4Adapter.line_indices` | Catalog template indices | hybrid | hard | keep-as-labeled-control |
| 3 | `Layer4Adapter.process` (`allow_l4_input_fallback`) | Fabricate relay from input | hybrid | hard | keep-as-labeled-control (forbidden bio) |
| 4 | `ContextAssembly` preassigned `line_id` | Catalog-bound assemblies | hybrid | hard | keep-as-labeled-control |
| 5–7 | `_compete_legacy` | max Vm + catalog tie; winner below θ; `Vm×0.5` | hybrid | hard | keep-as-labeled-control |
| 8 | Legacy `integrate` + `ContextTransitionMap.observe` | Learn without authentic unique spike | hybrid | hard | keep-as-labeled-control |
| 9 | `SequenceTransitionMemory.best_successor` | Symbolic max-count prediction | hybrid | soft | keep-as-labeled-control |
| 10 | `NextLinePredictor._unknown_prediction` placeholder | Catalog placeholder @ conf 0 | hybrid | hard | keep-as-labeled-control (forbidden bio) |
| 11 | `FeedbackGainController` 2.0/0.5 | Symbolic L6 boost | hybrid | hard | keep-as-labeled-control |
| 12–13 | `prior_active_bias` | Sticky prior drive | hybrid | soft | replace-with-biology (retired bio Stage 8) |

## B. Production nucleus force / wipe

| # | Symbol | Forces | Profile | Severity | Disposition |
|---|--------|--------|---------|----------|-------------|
| 15–17 | `PretrainedInhibitorExclusivityPolicy.force_central_fire` / `wipe_loser_membranes`; `WtaCoordinator` exclusivity | Force NI; wipe E; stop multi-spike | production | hard | keep-as-labeled-control (forbidden bio) |
| 18 | Exclusivity attempt-order reorder | Prefer non-mismatch | production | soft | replace-with-biology |
| 19–21 | Nucleus re-wipe; PE-LTD×3; Site-B unbound skip | Policy after exclusivity | production | soft | replace-with-biology |
| 22–25 | `DescendingInhibition._force_pair_inhibition`; defaults force+exclusivity | Force L1 I / E wipe | production | hard | keep-as-labeled-control |
| 26 | Soft channel×scale NI (exclusivity OFF) | Legitimate graded I | lab | soft (ok) | keep (biological path) |

## C. Soft eligibility / plasticity gates

| # | Symbol | Forces | Profile | Severity | Disposition |
|---|--------|--------|---------|----------|-------------|
| 27–32 | `BoundMatchRecallPolicy.spike_eligible` / hitchhiker freeze; `_plasticity_eligible` | Who may spike / LTP | production | soft | **replace-with-biology** via opt-in `nucleus_dendritic_coincidence_enabled` (not auto under bio — mastery 4/4) |
| 33–36 | Consolidator thresholds; neuromod floor; readiness; offline replay | Local evidence schedules | all/lab | soft | keep as local evidence (no cross-neuron veto) |
| 37–38 | Synthetic Δt / post-time fallbacks | Fabricated timing | lab | soft | replace-with-biology (refuse without real times) |

## D. Ownership / routing

| # | Symbol | Forces | Profile | Severity | Disposition |
|---|--------|--------|---------|----------|-------------|
| 39–40 | `FeatureCodeOwnership` / `AbstractCodeOwnership` | Global claim APIs | orphaned | stub | **retire** — `claim`/`can_bind`/`release` raise; read-only diagnostics remain |
| 41 | `PatternOwnership` | Former consolidator exclusivity | removed | — | do not reintroduce |
| 42–43 | `PatternMemorySnapshot` / `BindingOwnershipIndex` | Read-only binder index | all | audit | audit-only |
| 44 | `ContextAssemblyNetwork._eligible_drive_targets` owner filter | Owned → drive owner only | bio | soft | **retired under bio+coincidence** — full population drive; legacy/coincidence-OFF keeps owner-only / unbound recruit |
| 45 | `OWNERSHIP_COLLISION` audit | Logs dual bind | all | audit | audit-only |
| 46 | `SymbolRegistry.create` | 1:1 neuron↔symbol raise | production | soft | keep local; no global learning authority |

## E. Stage 7 / Stage 9 dendritic path

| # | Symbol | Role | Disposition |
|---|--------|------|-------------|
| 48 | `LocalGainScaler` | Unity stub | **replace-with-biology** → `DendriticCoincidenceGate` |
| — | `DendriticCoincidenceGate` | Basal×apical coincidence eligibility (somatic amp OFF) | Stage 9 ship; Stage 11 A+D threshold 0.05 |
| — | `ApicalContextDrivePolicy` | Honest apical: self-prior + unique prediction / L6 excess; ambient=0 | Stage 11 A+D ship |
| — | `dendritic_coincidence_enabled` | Column bio / lab flag | ON under bio factory |
| — | `nucleus_dendritic_coincidence_enabled` | Nucleus lab; bypasses BoundMatch soft gates | default OFF; requires soft exclusivity + graded |

### Nucleus afferent mapping (Phase 2)

| Afferent | Compartment |
|----------|-------------|
| L2 sensory / relay feedforward | **BASAL** |
| Descending / L1-context / recurrent collateral context | **APICAL** |

## G. Stage 10 — Soft routing retirement (bio column)

| # | Symbol | Role | Disposition |
|---|--------|------|-------------|
| 44′ | Full-pop `_eligible_drive_targets` | Shapes drive all assemblies under bio+coincidence | **shipped** |
| — | Bound mismatch basal ×0.12 | Local PE-like attenuation when binder ≠ sensory | **shipped** (replaces unbound-only soft filter that protected specialization) |
| — | `ContextInhibitoryNetwork.for_biological` | Stronger graded I (`inhibition_strength=0.90`, `e_collateral=0.70`) + Stage 13 plastic I→E gates | **shipped** |
| — | Wider sensory init spread | Assist race differentiation | **shipped** |
| — | Owner∪unbound / novel→unbound-only | Soft registry filters | **retired** under bio+coincidence; kept for legacy/coincidence-OFF |
| — | Bio requires `dendritic_coincidence_enabled=True` | Validator lock (Stage 10 security) | **shipped** — cannot PATCH coincidence OFF under bio |

## H. Stage 11 — Honest apical + eligibility selectivity (A+D staged)

| # | Symbol | Role | Disposition |
|---|--------|------|-------------|
| — | Ambient 0.35/0.55 blanket | Fake apical for all assemblies | **retired** under bio |
| — | `ApicalContextDrivePolicy` combination apical | Self-prior + prediction-match / pending-gain excess | **shipped** |
| — | Coincidence may block unique-winner bind | Bind evidence requires `allows_eligibility` | **shipped** (Stage 9; selectivity meaningful after ambient retire) |
| — | Somatic amp / Option C | `basal * last_amplification` in column drive | **forbidden** this stage |
| — | Option B plasticity scale | Lab off-by-default | **deferred** |

## I. Stage 12 — Hybrid C emergent ownership (RF / spike evidence)

| # | Symbol | Role | Disposition |
|---|--------|------|-------------|
| — | `EmergentOwnershipEvidence` | Receiver-owned RF concentration + unique-spike consistency; no global claim | **shipped** |
| — | Continuous RF–sensory mismatch ×~0.12 | PE prefers local RF evidence over latch-only | **shipped** |
| — | Sensory drive RF top-k mask | Specialize unbound via weights; mask from evidence not bind-only | **shipped** |
| — | `bind_pattern` readout latch | Optional UI/checkpoint/NeuronMemory sync after evidence + coincidence; **revisable** on sustained mismatch | **shipped** (demoted from ownership authority) |
| — | Mastery advance | Emergent column evidence **or** latch **or** nucleus bind (prefer evidence) | **shipped** |
| — | AbhiCIPP argmax WTA | Forced sole winner every step | **forbidden** — keep plural→abstain |
| — | Soft owner-only drive under bio+coincidence | Registry recruitment filter | **remain retired** |
| — | `PatternOwnership.can_bind/claim` | Global claim API | **do not reintroduce** |
| — | Somatic amp / nucleus dendritic auto-ON | — | **remain forbidden** |

## J. Stage 13 — Option A plastic column I→E gates

| # | Symbol | Role | Disposition |
|---|--------|------|-------------|
| — | `ColumnIeGatePlasticity` | Per-target I→E gate book; reuses `InhibitoryTurnoverPlasticity` (u=w/G) | **shipped** (bio only) |
| — | `ContextInhibitoryNetwork.for_biological` | Enables plastic gates; ceiling `i_max=0.48` **subthreshold** vs E θ≈0.55 | **shipped** |
| — | Gate plasticity event | Authentic I discharge / Stage 6 suppress; Δu from V_pre/θ | **shipped** |
| — | Drive-race collateral | Reads per-target gate when plastic (no argmax) | **shipped** |
| — | Legacy `ContextInhibitoryNetwork()` | Fixed coupling scalars; plastic OFF | **keep** |
| — | AbhiCIPP `_resolve_l2_competition` argmax | Forced unique among crossers | **forbidden** |
| — | Learning without unique under bio | Plural/silence → no sensory plasticity | **remain locked** |
| — | Option B loser FF depression | — | **not this stage** |
| — | Option C shared L2I pool | — | **not this stage** |

**Remediation note:** Stage 13 Option A borrows AbhiCIPP *gate turnover* only. Sole winners must still emerge from authentic spike count after drive race + graded E→I→E. Plural and silence remain first-class abstentions. Gate ceiling stays below E threshold so saturated I→E cannot act as lockout identity.

## K. Stage 14 — Emergent autonomy (labeled soft/graded control)

| # | Symbol | Role | Disposition |
|---|--------|------|-------------|
| — | `emergent_autonomy_enabled` (default **False** on production force) | Retires BoundMatch soft gates when ON (soft/graded labs) | **shipped** |
| — | Soft-gate null via `PredictionErrorModulator.soft_gates_active` | No rematch freeze / hitchhiker spike block / 0.7 attenuation when autonomy ON | **shipped** |
| — | Unique-spike eligibility credit | Bind eligibility only when `len(spikers)==1` under autonomy | **shipped** (evidence schedule) |
| — | First-commit consolidator | Skip second `PATTERN_BOUND` for a pattern while LTP stays open | **shipped** (evidence schedule; not spike routing) |
| — | BoundMatch freeze / hitchhiker spike gate | Production default when `emergent_autonomy_enabled=False` | **production** |
| — | Force exclusivity + `descending_mode=force` | Hard cascade (L2E → NI wipe → L1I) | **production** (forbidden with autonomy) |
| — | Soft race + graded descending | Labeled lab/ecology control | **keep-as-labeled-control** |
| — | Bio column `hybrid_biological_dynamics` | Autonomy ON; mastery prefers emergent evidence | **shipped** |
| — | AbhiCIPP argmax WTA | Forced sole winner | **forbidden** |

## F. Already removed (do not reintroduce)

Force-assist modules (`latency_wta_arbiter`, `recall_drive_integrator`, `stimulus_completion_schedule`, `substep_lateral_suppression`), `PatternOwnership.can_bind/claim`, consolidator collision blocker, hottest-spare, capture gain, primary-only LTP — see `test_biological_sparseness.py` / `model_equations.md`.

## Promotion gates (soft-force retirement)

Stage 10 column soft-routing gates (met):

1. Stage 8 causal regression lock stays green.
2. Mastery probe: 4/4 binds, distinct winners, no plural-unknown storm.
3. Abstention honesty preserved (plural L2 → no unique winner).
4. No consolidator / ownership claim API reintroduced.
5. L5 END after D1 requires episodic training (no wrap STDP across ends).

Still open (post–force production restore): soft race + Stage 14 autonomy remain labeled control for labs; rematch freeze is production default. Nucleus dendritic coincidence stays opt-in (separate from autonomy).
