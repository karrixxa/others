# L2 pre-inhibition race and paired-inhibition failure audit

Verdict: **EXISTING_PAIRED_PATH_UNAVAILABLE**

## Verified lineage

- Requested/repaired commit:
  `db30ceadbe18cf90e01f6d54dee0203f342b24a8`
- Checkout:
  `/home/cxiong/codex-runs/codex1-phase35-paired-failure-audit/repo/`
- State: detached HEAD, clean.
- Phase 35 prediction was never enabled and no simulation engine was
  constructed for measurement.

## Finding

The repaired lineage has the production global/shared delayed L2I fanout in
`backend/simulation.py`. It does not have a paired L2 inhibitory population,
paired/defer-once delivery mode, native configuration flag, or native experiment
harness. A Git-history search for `defer_once_enabled` returned no commit, and
the bundle exposes no alternate branch containing such a path.

The existing paired/defer-once experiment is located at:

`/home/cxiong/codex-runs/l2-refractory-aware-inhibition-review/run_refractory_aware_inhibition_experiment.py`

It is an external measurement harness pinned to Phase 29:

- `PROJECT_DIR` points to
  `/home/cxiong/codex-runs/l2-local-inhibition-review/repo/cipp-learning-AbhiCIPP`;
- `REQUESTED_COMMIT` is
  `4764f1758a7399439df2242dfa60819501fc2333`;
- `install_paired()` constructs eight local inhibitory neurons and replaces
  `_resolve_l2_competition` and `_deliver_scheduled_l2_inhibition` at runtime
  using `MethodType`;
- `defer_once_enabled` is attached dynamically by that external script, not
  read from a production engine flag.

Therefore the historical paired path cannot be invoked natively from the
requested repaired lineage. Changing its pinned project path, copying its
monkeypatch into this audit, or reconstructing it against `db30cea` would be the
port/reimplementation explicitly prohibited by the request.

## Execution decision

The required G/P iso-seeded comparison, smoke seed, and five equal-interleaved
seeds were not run. Running global alone would not answer the paired comparison,
and using the external Phase 29 monkeypatch would violate both exact-lineage and
native-path requirements.

## Verification performed

- Exact commit and clean checkout verification.
- Repository-wide source/document inventory.
- Reachable Git-history string search.
- Read-only inspection of the earlier external harness and report.
- Process check.

Runtime was under one minute. No source or model file was edited, no parameters
were changed, no production dynamics were changed, nothing was committed or
pushed, and no audit processes remain.
