"""Full Stage 1 + Stage 2 pipeline for one seed. Measurement-only."""
import copy
import json
import sys
import time

sys.path.insert(0, "/tmp/claude-275450548/-home-cxiong-others-cipp-learning-AbhiCIPP/55d19a97-a1ec-436c-ada9-dbb060f69996/scratchpad/mature_efficacy_scripts")
import lib
from backend.simulation import N_OUT, N_PIX, PATTERNS

HELD_PATTERN = "row 1"
SECOND_PATTERN = "col 1"  # overlaps HELD_PATTERN at pixel 4 only (the shared center pixel)
FOUR_PATTERNS = ["row 1", "col 1", "diag \\", "diag /"]

STAGE2_WINDOW = 1000          # steps per single-pattern test
INTERLEAVE_BLOCK = 100        # steps per pattern within the interleaved schedule
INTERLEAVE_ROUNDS = 2         # full cycles through all 4 patterns


def to_jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if hasattr(obj, "item"):
        return obj.item()
    return obj


def run_condition(engine, active_expected, novel_pixels, label):
    """Run all 3 Stage-2 tests on one live engine (already at the matured
    checkpoint), in sequence, returning a dict of per-test metrics."""
    out = {}

    # Test 1: continued held-pattern presentation
    out["continued_held"] = lib.collect_metrics(engine, active_expected, novel_pixels, STAGE2_WINDOW)

    # Test 2: switch to one overlapping second pattern
    engine.set_pattern(SECOND_PATTERN)
    second_active = lib.active_pixels(SECOND_PATTERN)
    second_novel = [i for i in lib.active_pixels(HELD_PATTERN) if i not in second_active]
    out["pattern_switch"] = lib.collect_metrics(engine, second_active, second_novel, STAGE2_WINDOW)

    # Validity check for test 3: decoder locality must still hold after the
    # switch (no inactive-pixel decoder entry may have moved).
    before = out["pattern_switch"]["decoder_snapshot_before"]
    after = out["pattern_switch"]["decoder_snapshot_after"]
    locality_ok = True
    for i in range(N_PIX):
        if i in second_active:
            continue
        for j in range(N_OUT):
            if abs(before[i][j] - after[i][j]) > 1e-9:
                locality_ok = False
    valid_for_test3 = locality_ok

    # Test 3: short equal-interleaved four-pattern schedule, only if test 2 was valid
    if valid_for_test3:
        interleaved_metrics = []
        for rnd in range(INTERLEAVE_ROUNDS):
            for pat in FOUR_PATTERNS:
                engine.set_pattern(pat)
                pat_active = lib.active_pixels(pat)
                pat_novel = [i for i in range(N_PIX) if i not in pat_active]
                block = lib.collect_metrics(engine, pat_active, pat_novel, INTERLEAVE_BLOCK)
                interleaved_metrics.append(dict(round=rnd, pattern=pat, metrics=block))
        out["interleaved_four_pattern"] = interleaved_metrics
    else:
        out["interleaved_four_pattern"] = None
    out["test3_ran"] = valid_for_test3
    return out


def main(seed):
    t0 = time.time()
    stage1_result, checkpoint_engine = lib.run_stage1(seed, pattern=HELD_PATTERN)
    stage1_result["wall_seconds"] = round(time.time() - t0, 2)

    if checkpoint_engine is None:
        result = dict(seed=seed, stage1=stage1_result, verdict="NATURAL_THREE_PIXEL_MATURITY_NOT_REACHED")
        return result

    # independence check
    ok, detail = lib.verify_engine_independence(checkpoint_engine)
    independence = dict(ok=ok, detail=detail)

    b, c, l1i_reshape_log = lib.make_bc(checkpoint_engine)
    active_expected = lib.active_pixels(HELD_PATTERN)
    novel_pixels = [i for i in range(N_PIX) if i not in active_expected]

    t1 = time.time()
    b_out = run_condition(b, active_expected, novel_pixels, "B_shadow")
    c_out = run_condition(c, active_expected, novel_pixels, "C_active")
    wall_stage2 = round(time.time() - t1, 2)

    result = dict(
        seed=seed,
        stage1=stage1_result,
        independence_check=independence,
        l1i_reshape_log=l1i_reshape_log,
        stage2=dict(B_shadow=b_out, C_active=c_out, wall_seconds=wall_stage2),
        total_wall_seconds=round(time.time() - t0, 2),
    )
    return result


if __name__ == "__main__":
    seed = int(sys.argv[1])
    out_path = sys.argv[2]
    result = main(seed)
    with open(out_path, "w") as f:
        json.dump(to_jsonable(result), f, indent=2)
    print(f"seed={seed} done, wrote {out_path}")
