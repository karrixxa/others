#!/usr/bin/env python3
from dataclasses import replace

from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS as D
from scripts.experimental.tune_catalog_benchmark import benchmark_curriculum

profiles = {
    "gradual_c": dict(
        membrane_tau=9.0,
        nucleus_relay_weight=0.060,
        nucleus_threshold=1.25,
        eligibility_alpha=0.34,
        consolidation_weight_threshold=0.20,
        e_learning_rate=0.021,
        sensory_baseline_weight=0.45,
    ),
    "gradual_d": dict(
        membrane_tau=8.5,
        nucleus_relay_weight=0.058,
        nucleus_threshold=1.27,
        eligibility_alpha=0.33,
        consolidation_weight_threshold=0.21,
        e_learning_rate=0.020,
    ),
    "gradual_e": dict(
        membrane_tau=8.0,
        nucleus_relay_weight=0.057,
        nucleus_threshold=1.28,
        eligibility_alpha=0.32,
        consolidation_weight_threshold=0.22,
        e_learning_rate=0.019,
    ),
}

for name, kw in profiles.items():
    dyn = replace(D, **kw)
    reports = [benchmark_curriculum(dyn, seed=s) for s in range(8)]
    steps = [r["total_steps"] for r in reports]
    viol = sum(r["invariant_violations"] + r["integrity_violations"] for r in reports)
    avg = sum(steps) / len(steps)
    print(f"{name}: avg={avg:.0f} per_shape={avg/4:.1f} viol={viol} sample={reports[0]['line_steps']}")
