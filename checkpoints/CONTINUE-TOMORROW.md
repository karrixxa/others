# CONTINUE TOMORROW — morning resume

**Paused:** 2026-07-21 evening  
**Branch:** `Paul_Model` (tracks `origin/Paul_Model` / `faraday` — `git@faraday.lps.umd.edu:cipp/cipp-learning.git`)  
**HEAD:** `026616c27363387ef76c1562d38759e371afa5e1`  
**Sim checkpoint:** optional — export fresh via `GET /api/checkpoint` if continuing a live brain session  

## Resume from

1. Branch: `Paul_Model`
2. UI: http://127.0.0.1:5173 · API: http://127.0.0.1:8000 · Rasters: http://127.0.0.1:5174
3. Conda: `paradigm_env`
4. Triad: full-pipeline + Thulle (`.cursor/triad.json` locked)
5. Read `CHECKPOINT.md` (gitignored local handoff) + this file

### Restart backend

```bash
cd /home/prodrig/Documents/Paradigm_New/backend
conda run -n paradigm_env --no-capture-output \
  uvicorn cognative_paradigm.api.main:app --reload --port 8000 --host 127.0.0.1
```

### Restart frontend

```bash
cd /home/prodrig/Documents/Paradigm_New/frontend
npm run dev
# rasters: npm run dev:rasters
```

---

## DONE (locked) — 2026-07-21

| Item | Status |
|------|--------|
| **Production force inhibitor cascade** | **DONE** — exclusivity ON, `descending_mode=force`, autonomy OFF |
| One-shot L1I (`l2_to_l1_i_gain=0.26` ≥ E′ θ) | **DONE** — same-tick E′→L1I on active shape |
| L2E → force NI → wipe other L2E | **DONE** — `ProductionForceCascadeDefaults` |
| Soft/graded/Stage 14 autonomy | **Labeled control** (not production) |
| Raster fidelity: hot fraction 0.88, NI raw membrane, L1 E′ rows, full history scroll | **DONE** |
| Stages 9–13 hybrid bio lab stack | **DONE** (prior; lab path) |

**Doctrine:** Production = force cascade. Soft race / graded / emergent autonomy only via labeled control. No Abhi argmax WTA under bio. Do not reopen without ask.

---

## OPEN next morning

1. **Live smoke** — confirm rasters: each L2E shows NI + shape L1 I same column; losers depleted on energy plot.
2. **Soft FULL lab residual** — if ecology under labeled soft path still open (see prior CHECKPOINT notes).
3. **Optional logging polish** — early-descending path historically omitted `event_log` for E′; force same-tick path logs; verify graded/soft labeled path if used.
4. **UI drift** — frontend consolidation threshold 0.25 vs backend 0.28 (Suggestion).

### Residual (carry-forward)

- Playwright E2E: install Chromium if `npm run test:e2e` fails on missing browser.
- Promote lab biology to production only after metrics beat locked production **and** explicit ask (force cascade is production now).

---

## Quick validation

```bash
cd backend && PYTHONPATH=. conda run -n paradigm_env python -m pytest \
  tests/test_production_defaults_lock.py \
  tests/test_pretrained_inhibitor_exclusivity.py \
  tests/test_emergent_autonomy.py \
  tests/test_secondary_l1e_descending.py -q

cd frontend && node --test src/app/charts/rasterCharts.test.js
```

---

## Checkpoint artifacts

| Artifact | Path | Notes |
|----------|------|-------|
| Resume doc | `checkpoints/CONTINUE-TOMORROW.md` | this file (tracked) |
| Local handoff | `CHECKPOINT.md` | gitignored; mirror of session state |
| Older sim JSON | `checkpoints/paul_model_2026-07-20_stage13.json` | Stage 13 era; re-export if needed |
