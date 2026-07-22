"""Quick API smoke test: reset, auto-stim to 4/4, probe, per-neuron sensory state."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def req(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read())


def main() -> int:
    print("=== Smoke test: local per-neuron learning ===")

    try:
        status, health = req("GET", "/api/health")
    except urllib.error.URLError as exc:
        print(f"FAIL: backend not reachable at {BASE} ({exc})")
        return 1

    if status != 200 or not health.get("ok"):
        print(f"FAIL: health {health}")
        return 1
    print("OK health")

    status, _ = req("POST", "/api/reset")
    if status != 200:
        print("FAIL: reset")
        return 1
    print("OK reset")

    status, pulse = req("POST", "/api/stimulate", {})
    binds = [e for e in pulse.get("step_events", []) if e.get("type") == "PATTERN_BOUND"]
    if binds or pulse["training"]["progress"] != "0/4":
        print(f"FAIL: instant bind or wrong progress: {pulse['training']}")
        return 1
    print("OK no instant bind")

    locked: str | None = None
    learned: list[str] = []
    for step in range(2000):
        status, body = req("POST", "/api/stimulate", {})
        if status != 200:
            print(f"FAIL: stimulate status {status}")
            return 1

        line = body.get("line_id")
        learned = body["training"].get("learned_line_ids", [])

        if line:
            if locked is None:
                locked = line
            elif line != locked and line not in learned and locked not in learned:
                print(f"FAIL: line switched before bind: {locked} -> {line} at step {step}")
                return 1
            if line not in learned:
                locked = line

        if body["training"].get("equilibrium"):
            progress = body["training"]["progress"]
            print(f"OK equilibrium at step {step + 1}: {progress} learned={learned}")
            break
    else:
        print("FAIL: no 4/4 equilibrium in 800 steps")
        return 1

    status, state = req("GET", "/api/state")
    grids = state.get("conductance_weights", {}).get("grid_by_neuron", {})
    if len(grids) != 4:
        print(f"FAIL: expected 4 per-neuron grids, got {len(grids)}")
        return 1

    ring = state["nucleus"]["ring"]
    centers = {
        neuron["id"]: neuron.get("sensory_conductances", {}).get("input_r1_c1")
        for neuron in ring
    }
    if not all(value is not None for value in centers.values()):
        print(f"FAIL: missing sensory_conductances: {centers}")
        return 1
    rounded = {key: round(value, 4) for key, value in centers.items()}
    print(f"OK per-neuron center sensory weights: {rounded}")

    status, probe = req("POST", "/api/probe", {"active_indices": [3, 4, 5]})
    symbol = (probe.get("neural") or {}).get("symbol")
    verdict = probe.get("verdict")
    if status != 200 or verdict != "recognized" or not symbol:
        print(f"FAIL: probe H1 {probe}")
        return 1
    print(f"OK probe H1 recognized: {symbol} (verdict={verdict})")

    print("=== ALL API SMOKE CHECKS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
