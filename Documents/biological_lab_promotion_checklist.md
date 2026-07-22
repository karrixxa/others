# Biological Lab Promotion Checklist

**Status:** Dry-run only — no production promotion authorized  
**Policy:** `DEFAULT_LEARNING_DYNAMICS` remains phenomenological, mastery
scheduled, force-exclusive, and mature-I frozen until a separate explicit
promotion order.

## Required evidence

- [ ] `tests/test_production_defaults_lock.py` passes before and after the run.
- [ ] Production `pytest -m biological` gate passes unchanged.
- [ ] Lab tests run under the separate `biological_lab` marker.
- [ ] Rotation learns 4/4 within 300 pulses for seeds 0, 7, and 42.
- [ ] Ownership collisions are zero and integrity ratio is 1.0.
- [ ] Excitatory spike rate remains in the declared 0.05–0.35 band.
- [ ] Rotation/mastery guide-dependence ratio is at least 0.95.
- [ ] Full triplet frequency-dependence and recorded-time tests pass.
- [ ] Dual eligibility preserves PE-LTD without wiping unrelated memories.
- [ ] Vogels iSTDP soft-NI ecology reaches at least 3/4 without force wipe.
- [ ] Graded descending plus soft NI reaches the declared ecology target.
- [ ] Scaling remains stable on the soft stack.
- [ ] Offline replay shows paired pulse savings without ownership reads.
- [ ] Security Validator reports PASS.
- [ ] General Tyborc reports holistic PASS.

## Column causal-safety (metric pack)

Normative exact-zero gates for `hybrid_cortical_biological` only. Legacy
`hybrid_cortical` chain accuracy remains a separate path
(`ColumnMetricPack.evaluate_column`) and is **not** promotion evidence by itself.

- [ ] `false_winner_count == 0`
- [ ] `l4_fabrication_count == 0`
- [ ] `learning_without_provenance_count == 0`
- [ ] `refractory_violation_count == 0`
- [ ] `register_event_mismatch_count == 0`
- [ ] `binding_collision_count == 0`
- [ ] `CausalSafetyMetricSnapshot.passes_exact_zero()` is true after prescribed
      episodes + empty-Pattern abstention stimulus
- [ ] Non-biological columns are rejected by `evaluate_causal_safety`

```bash
cd backend
python -m pytest tests/test_column_metric_pack.py -q
```

## Dry-run command set

```bash
cd backend
python -m pytest tests/test_production_defaults_lock.py -q
python -m pytest -m biological -q
python -m pytest -m biological_lab -q
python scripts/baseline_ecology_benchmark.py --max-pulses 300 --seeds 0,7,42
python -m pytest tests/test_column_metric_pack.py -q
```

Running these commands collects evidence only. It must not modify
`DEFAULT_LEARNING_DYNAMICS`, API defaults, or production exclusivity.

## Promotion decision

- [ ] A separate user order explicitly authorizes production changes.
- [ ] Exact proposed default diff is reviewed before editing.
- [ ] Rollback values are recorded.
- [ ] Documentation and API compatibility impacts are approved.

Current decision: **NO PROMOTION — DRY-RUN ONLY**.
