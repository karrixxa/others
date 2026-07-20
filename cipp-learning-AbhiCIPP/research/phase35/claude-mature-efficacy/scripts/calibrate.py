"""Calibration pilot: measure natural coincidence/maturation rate under the
Stage 1 config, to pick a documented, evidence-based max horizon before
committing to the full run. Read-only measurement, no production code
touched."""
import sys
import time

sys.path.insert(0, "/tmp/claude-275450548/-home-cxiong-others-cipp-learning-AbhiCIPP/55d19a97-a1ec-436c-ada9-dbb060f69996/scratchpad/phase35-mature-efficacy-clone/cipp-learning-AbhiCIPP")

import numpy as np
from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS

STAGE1_KW = dict(
    prediction_column_enabled=True,        # Phase 35 decoder/coincidence learning ON
    prediction_column_to_i_enabled=False,  # physical PC-to-local-I suppression OFF
    prediction_leak_diagnostic_disable=True,  # passive (PCi soma) decay OFF
    loser_depression=False,                # loser depression OFF
    l2e_budget=False,                      # global (sum-renorm) normalization OFF; matches default
)


def held_pattern_pixels(name):
    return set(i for i, v in enumerate(PATTERNS[name]) if v)


def main():
    seed = 1
    pattern = "row 1"
    active = held_pattern_pixels(pattern)
    print(f"pattern={pattern} active_pixels={sorted(active)}")

    e = SimulationEngine(seed=seed, **STAGE1_KW)
    e.set_pattern(pattern)

    t0 = time.time()
    N = 3200
    coincidence_events = 0
    for step in range(N):
        e.step()
        for pc in e.pcol:
            if pc.last_coincidence_step == e.timestep - 1:
                pass
    dt = time.time() - t0
    print(f"{N} steps took {dt:.2f}s ({N/dt:.1f} steps/sec)")

    # Identify the natural responder: which L2Ej has the largest total decoder
    # mass across the 3 active-pixel PCs (the pixels this pattern actually
    # drives) after the calibration run.
    totals = np.zeros(N_OUT)
    for j in range(N_OUT):
        totals[j] = sum(e.pcol[i].decoder_weights[j] for i in active)
    responder = int(np.argmax(totals))
    print(f"apparent natural responder: L2E{responder}, total decoder mass across active pixels: {totals}")
    per_pixel = [e.pcol[i].decoder_weights[responder] for i in active]
    print(f"L2E{responder}'s decoder weight at each active pixel after {N} steps: {dict(zip(sorted(active), per_pixel))}")
    print(f"max any decoder weight reached: {max(pc.decoder_weights[j] for pc in e.pcol for j in range(N_OUT)):.4f}")

    # Count total decoder UPDATE events accumulated for the responder at one
    # active pixel by inverting the saturating recurrence from init to current value.
    from backend.simulation import SimulationEngine as _SE
    w_init = 50.0
    eta = 0.15
    w_max = 1200.0
    for i in sorted(active):
        w = e.pcol[i].decoder_weights[responder]
        wv = w_init
        n = 0
        while wv < w and n < 200000:
            wv += eta * (1 - wv / w_max) ** 2
            n += 1
        print(f"  pixel {i}: current weight {w:.4f} implies ~{n} qualifying coincidence events so far")


if __name__ == "__main__":
    main()
