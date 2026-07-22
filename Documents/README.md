# Documents — layout index

Normative specifications, architecture notes, biology alignment, and archived plans for the Cognative Paradigm workspace.

---

## Directory map

| Path | Contents |
|------|----------|
| **`tenants.txt`** | Constitutional authority (Tenant rules) |
| **`paradigm_spec.md`** | Paradigm specification |
| **`model_equations.md`** | Formal model equations |
| **`biological_fidelity_spec.md`** | Biological v1 fidelity contract |
| **`architecture/`** | System design documents |
| **`biology/`** | Biology alignment audits, roadmaps, lab promotion (reserved) |
| **`archive/`** | Superseded or complete plans; historical prompts |
| **`research/`** | *(repo root)* `research/papers/raw/` — PDF sources |

### `architecture/`

| File | Purpose |
|------|---------|
| `cortical_column_design.md` | Hybrid cortical-column plan (Phases 0–8) |
| [`tenant_compliance_no_forced_win_research.md`](architecture/tenant_compliance_no_forced_win_research.md) | Strict causal tenant audit, remediation options, and no-forced-win benchmark baseline |
| [`tenant_compliance_remediation_plan.md`](architecture/tenant_compliance_remediation_plan.md) | Staged remediation plan (review-authorized; runtime implementation not authorized until Thulle/user says implement) |

### `biology/`

| File | Purpose |
|------|---------|
| [`multiplicative_computation_research.md`](biology/multiplicative_computation_research.md) | Biological multiplicative/gain mechanisms, evidence, equations, and optional-lab verdict |

### `archive/`

| File | Purpose |
|------|---------|
| `cortical_column_implementation_prompt.txt` | Original column implementation prompt |
| `v02_implementation_plan.md` | Superseded v0.2 bind-gate era plan |
| `self_paced_learning_plan.md` | Complete unguided-learning plan (2026-07-13) |
| `Technical_Specification_v0.8.md` | Historical technical specification |

### Biology docs (root — deferred move)

These remain at `Documents/` root to avoid link churn across README, specs, and CI references. A future pass may relocate them under `biology/` with a link-repair sweep:

- `biological_learning_roadmap.md`
- `biological_alignment_plan.md`
- `biological_alignment_audit.md`
- `biological_training_foundations.md`
- `biological_lab_promotion_checklist.md`
- `grid_and_layers_research.md`

### Other active docs (root)

- `system_overview.md`
- `workspace_metrics_graphs.md`
- `three_way_repo_comparison.md`
- `cipp_comparison_strengths_weaknesses.md`

---

## Related repo paths

| Path | Purpose |
|------|---------|
| `research/papers/raw/` | Research PDFs (moved from `Research Reports/`) |
| `assets/images/map.webp` | Cortical column layer diagram |
| `assets/images/originals/` | Original image assets |
| `backend/scripts/experimental/` | Tuning / probe scripts (non-production) |
| `backend/cognative_paradigm/cortical_column/` | Column domain contracts (Phase 1+) |

---

## Link repair notes (Phase 0)

After archiving `self_paced_learning_plan.md`, references in `biological_fidelity_spec.md` and `biological_learning_roadmap.md` now point to `Documents/archive/self_paced_learning_plan.md`.

Root `README.md` normative links (`tenants.txt`, `paradigm_spec.md`, etc.) are unchanged — those files stayed in place.
