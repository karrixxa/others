import sys
import time

sys.path.insert(0, "/tmp/claude-275450548/-home-cxiong-others-cipp-learning-AbhiCIPP/55d19a97-a1ec-436c-ada9-dbb060f69996/scratchpad/phase35-mature-efficacy-clone/cipp-learning-AbhiCIPP")

import numpy as np
from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS

STAGE1_KW = dict(
    prediction_column_enabled=True,
    prediction_column_to_i_enabled=False,
    prediction_leak_diagnostic_disable=True,
    loser_depression=False,
    l2e_budget=False,
)


def held_pattern_pixels(name):
    return set(i for i, v in enumerate(PATTERNS[name]) if v)


def main():
    for seed in (1, 2, 3):
        pattern = "row 1"
        active = sorted(held_pattern_pixels(pattern))
        e = SimulationEngine(seed=seed, **STAGE1_KW)
        e.set_pattern(pattern)
        MAX = 60000
        CHECK = 5000
        t0 = time.time()
        matured_at = None
        for step in range(1, MAX + 1):
            e.step()
            if step % CHECK == 0:
                totals = np.array([sum(e.pcol[i].decoder_weights[j] for i in active) for j in range(N_OUT)])
                leader = int(np.argmax(totals))
                per_pixel = [e.pcol[i].decoder_weights[leader] for i in active]
                print(f"seed={seed} step={step} leader=L2E{leader} totals={np.round(totals,1)} "
                      f"leader_per_pixel={[round(v,1) for v in per_pixel]}")
                if all(v >= 350.0 for v in per_pixel) and matured_at is None:
                    matured_at = step
                    print(f"  ** seed={seed}: all 3 pixels >= 350 for L2E{leader} at step {step} **")
                    break
        dt = time.time() - t0
        print(f"seed={seed}: {dt:.1f}s wall for {step} steps, matured_at={matured_at}")
        print()


if __name__ == "__main__":
    main()
