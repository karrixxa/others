"""Phase 34 Gate C -- exploratory two-pattern integration (measurement
only). NOT a claim that prediction solves four-pattern ownership -- a
narrow question: once ONE pattern's row-associated decoder synapse has
ORGANICALLY matured under real, unforced training (Gate A/B already
established the immature->mature transition and the causal PCi->Ii->Ei
chain in isolation; Gate A Part 2 additionally measured that natural
maturation for a real pattern's own causal responder takes on the order of
a few thousand real steps at the corrected eta=0.15 -- not the "orders of
magnitude longer" this gate originally assumed before that correction),
does presenting a SECOND, partially-overlapping pattern show the EXPLAINED
(row) pixels suppressed while the NOVEL (column-only) pixels remain as
residual, un-suppressed activity?

Method (revised after the Codex preflight correction -- no decoder weight
is assigned directly anywhere in this script):

  1. Identify pattern 'row 1's actual causal first-responder L2Ej by
     presenting 'row 1' alone under REAL competitive dynamics (no
     assignment, no oracle -- read off the engine's own physical spike
     history).
  2. Continue presenting 'row 1' alone, with prediction_active_dendrite_
     enabled on from the start, for ROW1_TRAIN_STEPS real steps -- long
     enough (per Gate A Part 2's measured natural coincidence rate, with
     margin) for the decoder to organically mature past prediction_active_
     dendrite_coincidence_weight. Maturity is VERIFIED (not assumed) before
     proceeding; if it fails to mature within budget, this gate reports
     that honestly rather than forcing the weight.
  3. Resume the SAME, now organically-trained engine under an interleaved
     row/column presentation schedule and MEASURE L1E activity per pixel,
     per pattern. A separate "off" condition (prediction_active_dendrite_
     enabled=False throughout) runs the identical schedule from a freshly
     built engine for comparison. 3 fixed seeds.

Config: centered_encoder_enabled=True (Phase 29/30), l2_charge_chunks=1
(the plain K=1 control -- Phase 33's causal microstep race post-dates this
branch and is not used here), prediction_column_enabled + prediction_
active_dendrite_enabled + prediction_column_to_i_enabled + pretrained_
l1i_regulation (Gate B's validated wiring)."""

from __future__ import annotations

import json

import numpy as np

from backend.simulation import N_OUT, N_PIX, SimulationEngine
from backend.presets import DASHBOARD_PRESET

SEEDS = (1, 2, 3)
ROW_PIXELS = (3, 4, 5)     # 'row 1'
COL_PIXELS = (1, 4, 7)     # 'col 1'
ROW_ONLY = tuple(p for p in ROW_PIXELS if p not in COL_PIXELS)   # 3, 5
COL_ONLY = tuple(p for p in COL_PIXELS if p not in ROW_PIXELS)   # 1, 7
CENTER = 4

ROW1_TRAIN_STEPS = 9_000   # Gate A Part 2 measured natural maturation at ~4,239-5,831 steps; generous margin
MEASURE_PRESENTATIONS = 40
MEASURE_STEPS_PER_PRESENTATION = 20


def _engine(seed, prediction_active_dendrite_enabled):
    overrides = dict(
        l2_charge_chunks=1,
        centered_encoder_enabled=True,
        prediction_column_enabled=True,
        prediction_active_dendrite_enabled=prediction_active_dendrite_enabled,
        prediction_column_to_i_enabled=prediction_active_dendrite_enabled,
        pretrained_l1i_regulation=prediction_active_dendrite_enabled,
    )
    return SimulationEngine(seed=seed, topology_seed=seed, **{**DASHBOARD_PRESET, **overrides})


def _train_row1_organically(seed):
    """Real, unforced training: presents 'row 1' alone with active-dendrite
    on, reads off the actual causal first-responder L2Ej from the engine's
    own spike history, and verifies (never assumes) organic decoder
    maturation. Returns the trained engine so measurement can continue from
    its real, earned state."""
    e = _engine(seed, prediction_active_dendrite_enabled=True)
    e.set_pattern('row 1')
    for _ in range(ROW1_TRAIN_STEPS):
        e.step()
    counts = np.array([e._neuron_total_spikes.get(f'L2E{j}', 0) for j in range(N_OUT)])
    responder_j = int(np.argmax(counts))
    matured_pixels = [i for i in ROW_PIXELS
                      if e.pcol[i]._weights_array[responder_j] >= e.prediction_active_dendrite_coincidence_weight]
    return e, responder_j, counts.tolist(), matured_pixels


def _measure(e, presentations=MEASURE_PRESENTATIONS, steps_per=MEASURE_STEPS_PER_PRESENTATION):
    """Per-presentation FIRING RATE (fraction of steps within the window a
    pixel spikes), not a binary "did it ever fire" indicator -- L1I
    suppression is a transient membrane subtraction, not an absolute block,
    so a continuously-held pixel would trivially saturate a binary measure
    to 1.0 regardless of any real suppression."""
    activity = {p: {'row 1': [], 'col 1': []} for p in range(N_PIX)}
    schedule = ['row 1', 'col 1'] * (presentations // 2)
    for pattern in schedule:
        e.set_pattern(pattern)
        pixel_fire_count = np.zeros(N_PIX)
        for _ in range(steps_per):
            e.step()
            for p in range(N_PIX):
                if e.spiked.get(f'L1E{p}'):
                    pixel_fire_count[p] += 1.0
        for p in range(N_PIX):
            activity[p][pattern].append(float(pixel_fire_count[p]) / steps_per)
    return {p: {pat: float(np.mean(vals)) if vals else 0.0 for pat, vals in d.items()}
            for p, d in activity.items()}


def main():
    per_seed = []
    for seed in SEEDS:
        e_on, responder_j, pilot_counts, matured_pixels = _train_row1_organically(seed)
        on = _measure(e_on)

        e_off = _engine(seed, prediction_active_dendrite_enabled=False)
        e_off.set_pattern('row 1')
        for _ in range(ROW1_TRAIN_STEPS):
            e_off.step()   # identical real training exposure, no prediction mechanism
        off = _measure(e_off)

        per_seed.append(dict(seed=seed, responder_j=responder_j, pilot_counts=pilot_counts,
                              matured_pixels=matured_pixels,
                              decoder_organically_matured=bool(matured_pixels),
                              off=off, on=on))

    def _avg(cond_key, pixel_set, pattern):
        vals = [row[cond_key][p][pattern] for row in per_seed for p in pixel_set]
        return float(np.mean(vals)) if vals else 0.0

    all_matured = all(row['decoder_organically_matured'] for row in per_seed)

    summary = dict(
        row_only_pixels=list(ROW_ONLY), col_only_pixels=list(COL_ONLY), center=CENTER,
        all_seeds_organically_matured=all_matured,
        # Explained (row-only) pixel activity during 'row 1' presentations --
        # expected to drop under prediction-on if suppression is real.
        row_only_activity_during_row1_off=_avg('off', ROW_ONLY, 'row 1'),
        row_only_activity_during_row1_on=_avg('on', ROW_ONLY, 'row 1'),
        # Novel (column-only) pixel activity during 'col 1' presentations --
        # expected to remain as residual, largely UNsuppressed (the decoder
        # was only ever taught row 1's responder, never col 1's).
        col_only_activity_during_col1_off=_avg('off', COL_ONLY, 'col 1'),
        col_only_activity_during_col1_on=_avg('on', COL_ONLY, 'col 1'),
    )
    row_suppressed = summary['row_only_activity_during_row1_on'] < summary['row_only_activity_during_row1_off']
    col_preserved = abs(summary['col_only_activity_during_col1_on'] - summary['col_only_activity_during_col1_off']) < 0.15

    results = dict(per_seed=per_seed, summary=summary,
                   observation=dict(
                       row_pixels_show_suppression_trend=row_suppressed,
                       col_pixels_remain_largely_unaffected=col_preserved),
                   note=("EXPLORATORY measurement only -- not a claim that prediction solves "
                         "four-pattern ownership. Decoder maturity for row 1's responder was "
                         "trained ORGANICALLY (real, unforced coincidences over "
                         f"{ROW1_TRAIN_STEPS} real steps), not assigned directly."))

    with open('phase34_gate_c_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("Gate C (exploratory) summary:")
    print(json.dumps(summary, indent=2))
    print("all_seeds_organically_matured:", all_matured)
    print("row_pixels_show_suppression_trend:", row_suppressed)
    print("col_pixels_remain_largely_unaffected:", col_preserved)
    for row in per_seed:
        print(f"  seed {row['seed']}: responder_j={row['responder_j']} matured_pixels={row['matured_pixels']}")
    return results


if __name__ == '__main__':
    main()
