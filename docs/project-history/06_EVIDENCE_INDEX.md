# 6. Evidence Index

## 6.1 Branch snapshot

| Item | Value |
| --- | --- |
| Repository | `karrixxa/others` |
| Branch | `endofjuly21` |
| Snapshot before this archive | `6ec6a29f8fbcc3160c9f2d253dca8d1dfbaca4c9` |
| Root simulator upload | `2a3093db52e9cb2b1bdb345d9c7ae520c6b0cdb1` |
| Root reports/README upload | `5cee7efb2514d640298f80092dd6a672bf032cdf` |
| Lecture-note upload | `6ec6a29f8fbcc3160c9f2d253dca8d1dfbaca4c9` |
| Older main baseline | `556bb74` |
| Four-pattern conversion | `ec3ece8` |
| July 14 measured integration | `4e24e26` |

## 6.2 Architecture evidence

| Claim | Status | Primary evidence |
| --- | --- | --- |
| Network is graph/spec driven | Implemented | `backend/network_spec.py`, `backend/simulation.py` |
| Five built-in root presets exist | Implemented | `backend/network_spec.py`, `README.md` |
| Root coincidence preset has explicit basal/apical edge kinds | Implemented | `backend/network_spec.py`, `snn/neurons.py`, `tests/test_coincidence_cell.py`, `tests/test_coincidence_spec.py` |
| Analytic sub-boundary events are used | Implemented | `backend/simulation.py`, `tests/test_event_scheduler.py`, `tests/test_causal_step.py` |
| Residual/ErrorE and SwitchI topology exists | Implemented | `backend/network_spec.py`, `tests/test_residual_topology.py`, `docs/residual_error_pathway_flowchart.md` |
| Older flexible lineage remains in tree | Implemented | `cipp-learning-AbhiCIPP/` |

## 6.3 Experimental evidence

| Claim | Status | Primary evidence |
| --- | --- | --- |
| Tuned row→column→row coincidence sweep was run | Experimentally observed | `experiments/coincidence_turnover_results.json`, `experiments/coincidence_turnover_sweep.py`, `docs/COINCIDENCE_TURNOVER_TUNING.md` |
| Coincidence mechanics were separately tested | Experimentally observed | `experiments/coincidence_results.json`, `experiments/coincidence_experiment.py`, `tests/test_coincidence_experiment.py` |
| Predictive inhibition was compared over overlap schedule | Experimentally observed | `experiments/predictive_inhibition_results.json`, `experiments/predictive_inhibition/FINAL_REPORT.md` |
| RG timing/symmetry was measured | Experimentally observed | `experiments/rg_timing_results.json`, `experiments/rg_timing_symmetry.py` |
| Linear weight variants were ablated | Experimentally observed | `docs/LINEAR_WEIGHT_ABLATION_REPORT.md`, `experiments/linear_ablation/` |
| Composition depends partly on carried membrane state | Experimentally observed/interpretation | `experiments/linear_ablation/phase4_composition.json` |

## 6.4 Conceptual and lecture evidence

| Topic | Primary evidence |
| --- | --- |
| CIPP motivation, free energy, prediction, and residual | `notes2/june26.txt`, `notes2/june29.txt`, `notes2/july1.txt` |
| Four-pattern and simulation behavior discussions | `notes2/july6.txt` through `notes2/july14.txt` |
| Two-E/one-I column, weight compression, prediction locality, leak | `notes2/july15.txt`, `notes2/july17.txt` |
| Basal/apical active-dendrite decision | `notes2/july20.txt` |
| Latest lecture interpretation and Phase 35 direction | `notes2/july21.txt` |

Lecture notes establish intended architecture and reported experiment history. They do not by themselves prove that a mechanism exists in this branch or produces the intended behavior.

## 6.5 Agent-workflow evidence

| Claim | Status | Evidence |
| --- | --- | --- |
| Workflow evolved from architect/implementer split | Reported with repository documentation | `docs/agent_workflow_evolution.md` |
| Specifications were used as handoff artifacts | Implemented/documented | top-level `Claude_*.md` files and `docs/claude_switchi_investigation_prompt.md` |
| Separate structural, execution, metric, scientific, and regression audits became necessary | Documented | `docs/agent_workflow_evolution.md`, audit prompts, tests, experiment reports |
| UI activity once differed from intended SwitchI charge behavior | Reported | `docs/agent_workflow_evolution.md` |

## 6.6 Later phase claims not fully branch-local

The following identifiers appear in notes or prior reports but their complete code/result chain is not contained in `endofjuly21` as reconstructed:

- Phase 27–29 ownership and centered-encoder audits;
- Phase 30–33 paired inhibition, defer-once, and microstep studies;
- Phase 34 commit `d8ce099`;
- Phase 35 base `db30cead...` and later prediction audits;
- Phase 36 checkpoint `621f2cf`;
- Phase 37 candidate `92e1ff89`;
- Phase 38.1 `7f7c383` and later `ac4179b` report;
- Phase 39 `cff4b80`;
- Phase 39.2 `a812734`.

These should be recovered from their original worktrees/remotes before exact quantitative claims are promoted into the main README or a paper.

## 6.7 External/earlier projects

| Project | Branch-local artifact status | Allowed statement |
| --- | --- | --- |
| Pong | Not found | Reported bounded RL/software experiment; details require artifact recovery. |
| DnD | Not found | Reported exploratory state/rules work; completion status unresolved. |
| Pi/HPC | Not found | Reported performance-engineering project; exact benchmark unverified here. |

## 6.8 Evidence rules for future updates

For each new headline result, retain:

1. exact commit SHA and branch;
2. clean/dirty worktree state;
3. complete parameter and feature-flag snapshot;
4. schedule, seeds, and stopping rule;
5. raw machine-readable results;
6. script used to generate them;
7. relevant test output;
8. interpretation separated from observation;
9. whether the dashboard used the same preset;
10. whether the result was independently reproduced.

A useful result record should answer: **what code ran, what physical mechanism differed, what was measured, and how strongly does that measurement support the claim?**
