"""
Phase 23 -- frequency measurement only (NO gating; measurement only, no new
flags, no learning-stop rule implemented in this phase).

Measures L1E's own firing frequency under several conditions, and asks:
does frequency near 0.5 predict genuine prediction/reconstruction accuracy,
or does it remain a false positive (per Phase 17's established finding: a
sustained single-pattern hold converges L1E frequency to EXACTLY 0.5 via
mere synchronized global L1I suppression, with ZERO selective prediction
involved at all)?

Conditions:
  1. external-input-only:        plain baseline, no PC, no pretrained L2I.
  2. global-synchronized-suppression: baseline L1I feedback topology
                                  (Phase 17's established false-positive
                                  regime -- included here as the reference
                                  case the other conditions are compared
                                  against).
  3. selective-predictive-inhibition: Phase 21's condition C (PCi->Ii,
                                  learned).
  4. correct-learned-prediction:  condition C, but ALSO score whether the
                                  active pixel's own PCi is the one doing
                                  the suppressing (genuine, not incidental).
  5. incorrect-prediction:        force the WRONG PCi (a column not part of
                                  the pattern) to drive L1I -- a manufactured
                                  negative control no legitimate mechanism
                                  would produce, to see whether frequency
                                  alone can tell this apart from (3)/(4).
  6. reconstruction-with-input-removed: Phase 20's frozen-reconstruction
                                  setup (external input removed, one L2E
                                  cued) -- measures PCi's own frequency
                                  (there is no external L1E drive to measure
                                  in this condition at all).
"""

import json

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS
from backend.presets import DASHBOARD_PRESET

HOLD = 2000
ACTIVE = (3, 4, 5)


def _freq(engine, population, indices, steps=HOLD, pre_steps=0):
    for _ in range(pre_steps):
        engine.step()
    counts = np.zeros(len(indices))
    for _ in range(steps):
        engine.step()
        for k, i in enumerate(indices):
            if engine.spiked.get(f'{population}{i}'):
                counts[k] += 1
    return counts / steps


def condition_1_external_input_only():
    e = SimulationEngine(seed=1, **DASHBOARD_PRESET)
    e.set_pattern('row 1')
    return _freq(e, 'L1E', range(N_PIX), pre_steps=200)


def condition_2_global_synchronized_suppression():
    # Same as condition 1 -- the baseline global L1I topology IS the
    # established false-positive regime from Phase 17; kept as its own
    # named condition for direct side-by-side comparison in the report.
    return condition_1_external_input_only()


def condition_3_selective_predictive_inhibition():
    e = SimulationEngine(seed=1, prediction_column_enabled=True,
                         prediction_column_to_i_enabled=True, **DASHBOARD_PRESET)
    e.set_pattern('row 1')
    return _freq(e, 'L1E', range(N_PIX), pre_steps=200)


def condition_4_correct_learned_prediction():
    """Same engine/run as condition 3 -- additionally scores whether the
    active pixels' OWN PCi is doing the suppressing (reads PC firing
    alongside L1E firing in the SAME run, never a separate claim)."""
    e = SimulationEngine(seed=1, prediction_column_enabled=True,
                         prediction_column_to_i_enabled=True, **DASHBOARD_PRESET)
    e.set_pattern('row 1')
    for _ in range(200):
        e.step()
    l1e_counts = np.zeros(N_PIX)
    pc_counts = np.zeros(N_PIX)
    for _ in range(HOLD):
        e.step()
        for i in range(N_PIX):
            if e.spiked.get(f'L1E{i}'):
                l1e_counts[i] += 1
            if e.spiked.get(f'PC{i}'):
                pc_counts[i] += 1
    return l1e_counts / HOLD, pc_counts / HOLD


def condition_5_incorrect_prediction():
    """Force a WRONG PCi (not part of the pattern) to drive its paired L1Ii
    every step -- a manufactured negative control matching no legitimate
    learning outcome, to test whether frequency alone can distinguish this
    from genuine (3)/(4)."""
    e = SimulationEngine(seed=1, prediction_column_enabled=True,
                         prediction_column_to_i_enabled=True, **DASHBOARD_PRESET)
    e.set_pattern('row 1')
    wrong_i = 0   # pixel 0 is not part of 'row 1' (active = 3,4,5)
    l1e_counts = np.zeros(N_PIX)
    for _ in range(HOLD):
        e.l1.inhibitory_neurons[wrong_i].potential = (
            e.l1.inhibitory_neurons[wrong_i].threshold + 10_000)
        e.step()
        for i in range(N_PIX):
            if e.spiked.get(f'L1E{i}'):
                l1e_counts[i] += 1
    return l1e_counts / HOLD


def condition_6_reconstruction_with_input_removed():
    """Phase 20's frozen-reconstruction setup: measures PCi's own frequency
    (there is no external L1E drive in this condition -- input is zeroed)."""
    e = SimulationEngine(seed=1, prediction_column_enabled=True, **DASHBOARD_PRESET)
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
    active = [i for i, v in enumerate(PATTERNS['row 1']) if v]
    for i in active:
        e.pcol[i]._weights_array[4] = e.prediction_feedback_max
    e._set_plasticity_frozen(True)
    e.input_vec = np.zeros(N_PIX)
    pc_counts = np.zeros(N_PIX)
    steps = 200
    for step_i in range(steps):
        if step_i < 5:
            e.l2.excitatory_neurons[4].potential = e.l2.excitatory_neurons[4].threshold + 10_000
        e.step()
        for i in range(N_PIX):
            if e.spiked.get(f'PC{i}'):
                pc_counts[i] += 1
    return pc_counts / steps


def main():
    results = {}
    f1 = condition_1_external_input_only()
    results['1_external_input_only'] = dict(mean=round(float(f1.mean()), 4),
                                            active_mean=round(float(f1[list(ACTIVE)].mean()), 4),
                                            per_pixel=f1.round(4).tolist())
    f2 = condition_2_global_synchronized_suppression()
    results['2_global_synchronized_suppression'] = dict(
        mean=round(float(f2.mean()), 4), active_mean=round(float(f2[list(ACTIVE)].mean()), 4),
        per_pixel=f2.round(4).tolist(),
        note="identical run to condition 1 -- the baseline topology IS the false-positive regime")

    f3 = condition_3_selective_predictive_inhibition()
    results['3_selective_predictive_inhibition'] = dict(
        mean=round(float(f3.mean()), 4), active_mean=round(float(f3[list(ACTIVE)].mean()), 4),
        per_pixel=f3.round(4).tolist())

    l1e4, pc4 = condition_4_correct_learned_prediction()
    results['4_correct_learned_prediction'] = dict(
        l1e_active_mean=round(float(l1e4[list(ACTIVE)].mean()), 4),
        pc_active_mean=round(float(pc4[list(ACTIVE)].mean()), 4),
        l1e_per_pixel=l1e4.round(4).tolist(), pc_per_pixel=pc4.round(4).tolist())

    f5 = condition_5_incorrect_prediction()
    results['5_incorrect_prediction'] = dict(
        mean=round(float(f5.mean()), 4), active_mean=round(float(f5[list(ACTIVE)].mean()), 4),
        pixel0_rate=round(float(f5[0]), 4), per_pixel=f5.round(4).tolist())

    f6 = condition_6_reconstruction_with_input_removed()
    results['6_reconstruction_with_input_removed'] = dict(
        pc_active_mean=round(float(f6[list(ACTIVE)].mean()), 4), pc_per_pixel=f6.round(4).tolist())

    print(json.dumps(results, indent=2))
    with open('phase23_frequency_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nWritten to phase23_frequency_results.json")


if __name__ == "__main__":
    main()
