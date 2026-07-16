"""
Regression/sanity tests for Phase 23 (frequency measurement only; no
gating, no new flags, no learning-stop rule implemented). See
Phase23_Frequency_Measurement_Report.md.

Plain-script style:
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python test_phase23_frequency_measurement.py
"""

import numpy as np

import phase23_frequency_measurement as p23
from backend.simulation import N_PIX

ACTIVE = (3, 4, 5)


def test_condition_1_runs_and_returns_plausible_frequency():
    f = p23.condition_1_external_input_only()
    assert f.shape == (N_PIX,)
    assert 0.0 <= f.min() and f.max() <= 1.0
    print(f"PASS: condition 1 (external-input-only) active-pixel mean freq = {f[list(ACTIVE)].mean():.3f}")


def test_condition_3_selective_inhibition_runs():
    f = p23.condition_3_selective_predictive_inhibition()
    assert f.shape == (N_PIX,)
    print(f"PASS: condition 3 (selective) active-pixel mean freq = {f[list(ACTIVE)].mean():.3f}")


def test_baseline_frequency_is_near_the_known_false_positive_value():
    """Phase 17's established finding: a sustained hold under the baseline
    global-suppression topology converges L1E frequency near 0.5, with ZERO
    selective prediction involved. This must still hold (it is the
    reference case Phase 23's whole analysis depends on)."""
    f = p23.condition_1_external_input_only()
    active_mean = f[list(ACTIVE)].mean()
    assert 0.35 < active_mean < 0.65, (
        f"expected the known false-positive baseline to sit near 0.5, got {active_mean:.3f} "
        f"-- if this has moved, Phase 23's frequency-vs-accuracy analysis needs revisiting")
    print(f"PASS: baseline active-pixel frequency ({active_mean:.3f}) reproduces the known "
         f"near-0.5 false-positive regime")


def test_frequency_cannot_distinguish_correct_from_incorrect_prediction():
    """The core Phase 23 finding: forcing an INCORRECT (wrong-pixel)
    predictive suppression produces an L1E frequency statistically
    indistinguishable from genuinely CORRECT selective suppression --
    frequency alone is not a valid signal for gating learning."""
    f_correct = p23.condition_3_selective_predictive_inhibition()
    f_incorrect = p23.condition_5_incorrect_prediction()
    correct_active = f_correct[list(ACTIVE)].mean()
    incorrect_active = f_incorrect[list(ACTIVE)].mean()
    assert abs(correct_active - incorrect_active) < 0.15, (
        f"expected correct ({correct_active:.3f}) and incorrect ({incorrect_active:.3f}) "
        f"prediction to produce SIMILAR frequency (the whole point of this finding) -- "
        f"if they now differ substantially, frequency may have become a usable signal; "
        f"update Phase24's gate decision")
    print(f"PASS (documents the core finding): correct ({correct_active:.3f}) and incorrect "
         f"({incorrect_active:.3f}) prediction produce statistically similar L1E frequency")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
