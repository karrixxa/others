"""
Phase 21 -- selective local predictive inhibition (2x2 factorial).

Wires the deferred PCi->Ii->Si path (Phase18b_Lecture14_Local_Coincidence_
Architecture_Contract.md), the first phase where PCi's own output affects
any other neuron (Phases 19-20 were shadow-only). Two independent
factorial variables:

  Input topology:    A/C = existing global L2E->all-L1I feedback (baseline)
                     B/D = selective PCi->Ii (this column's own PC only)
  L1I regulation:    A/B = learned (existing default)
                     C/D = fixed/pretrained (prediction_column_to_i_enabled's
                           counterpart pretrained_l1i_regulation)

Measures, per condition, over a long single-pattern ('row 1') hold:
  - all-nine sync rate: fraction of steps where every L1Ii fires together
    (expected near-total under global/A/C; a real test of whether selective
    input breaks this).
  - per-pixel selectivity: L1Ii firing rate for i in the pattern's active
    set (3,4,5) vs the inactive set (0,1,2,6,7,8).
  - center suppression: L1I4's own firing rate reported separately (pixel 4
    is legitimately active in every pattern).
  - L1E rhythm: L1E's own mean firing rate (duty cycle) -- a real E/silent/E
    rhythm requires regular L1I-driven suppression; weaker/rarer L1I firing
    should show up as a HIGHER L1E duty cycle (less suppression).
  - unwanted global silence: whether L1E's duty cycle ever collapses to (near)
    zero for an extended run (over-suppression failure mode).
"""

import json

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX
from backend.presets import DASHBOARD_PRESET

HOLD_STEPS = 3000
ACTIVE = (3, 4, 5)
INACTIVE = (0, 1, 2, 6, 7, 8)


def _make(condition, seed=1):
    selective = condition in ('B', 'D')
    fixed = condition in ('C', 'D')
    kw = dict(seed=seed, pretrained_l1i_regulation=fixed, **DASHBOARD_PRESET)
    if selective:
        kw['prediction_column_enabled'] = True
        kw['prediction_column_to_i_enabled'] = True
    return SimulationEngine(**kw)


def run(condition, seed=1):
    e = _make(condition, seed)
    e.set_pattern('row 1')
    l1i_counts = np.zeros(N_PIX)
    l1e_counts = np.zeros(N_PIX)
    all_nine_sync_steps = 0
    for _ in range(HOLD_STEPS):
        e.step()
        l1i_spiked = np.array([1.0 if e.spiked.get(f'L1I{i}') else 0.0 for i in range(N_PIX)])
        l1e_spiked = np.array([1.0 if e.spiked.get(f'L1E{i}') else 0.0 for i in range(N_PIX)])
        l1i_counts += l1i_spiked
        l1e_counts += l1e_spiked
        if l1i_spiked.all():
            all_nine_sync_steps += 1
    l1i_rate = l1i_counts / HOLD_STEPS
    l1e_rate = l1e_counts / HOLD_STEPS
    return dict(
        l1i_rate_active=round(float(l1i_rate[list(ACTIVE)].mean()), 4),
        l1i_rate_inactive=round(float(l1i_rate[list(INACTIVE)].mean()), 4),
        l1i_rate_center=round(float(l1i_rate[4]), 4),
        l1e_duty_cycle=round(float(l1e_rate.mean()), 4),
        l1e_min_rate=round(float(l1e_rate.min()), 4),
        all_nine_sync_rate=round(all_nine_sync_steps / HOLD_STEPS, 4),
        l1i_rate_per_pixel=[round(float(x), 4) for x in l1i_rate],
    )


def main():
    results = {}
    for condition in ('A', 'B', 'C', 'D'):
        results[condition] = run(condition)
        print(f"\n=== condition {condition} ===")
        print(json.dumps(results[condition], indent=2))

    with open('phase21_selective_inhibition_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nWritten to phase21_selective_inhibition_results.json")


if __name__ == "__main__":
    main()
