"""Gate B rerun with its obsolete queue-deletion assertion superseded."""

import importlib.util
from pathlib import Path


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load("phase35_gate_b_original", Path(
    "/home/cxiong/codex-runs/codex1-phase35-implementation/test_phase35_gate_b.py"))
queue = load("phase35_queue_repair", Path(__file__).with_name("test_queue_carryover.py"))

TESTS = [
    gate.test_d_before_learning_and_next_coincidence_fire,
    gate.test_fanout_selective_learning_and_locality,
    gate.test_no_duplicate_or_deferred_delivery,
    gate.test_paired_output_route,
    queue.test_scheduled_pair_survives_pattern_switch_and_delivers_once,
    queue.test_origin_classification_is_passive_and_complete,
]

if __name__ == "__main__":
    for test in TESTS:
        test()
        print("PASS", test.__name__)
    print(f"GATE_B_REPAIRED_PASS {len(TESTS)}")
