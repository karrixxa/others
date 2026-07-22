#!/usr/bin/env python3
"""
Side-by-side outcome comparison: Abhi CIPP (AbhiCIPP) vs Cognative Paradigm.

Runs comparable scenarios on the four center-crossing catalog shapes shared by both
repos (H1/V1/D0/D1 ↔ row 1 / col 1 / diag \\ / diag /).

Usage:
  PYTHONPATH=backend:. python backend/scripts/compare_abhi_paradigm.py
  ABHI_ROOT=/path/to/cipp-learning python backend/scripts/compare_abhi_paradigm.py
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from dataclasses import dataclass

# Paradigm
PARADIGM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PARADIGM_ROOT, "backend"))

from cognative_paradigm.domain.event_log import EventType
from cognative_paradigm.lines import LINE_IDS, get_line
from cognative_paradigm.simulation.engine import BrainSimulator
from cognative_paradigm.simulation.learning_dynamics import DEFAULT_LEARNING_DYNAMICS
from cognative_paradigm.simulation.stimulus_stream import RotatingStimulusStream
from cognative_paradigm.diagnostics.learning_integrity import LearningIntegrityAuditor
from cognative_paradigm.lines import LINE_INDICES

ABHI_ROOT = os.environ.get("ABHI_ROOT", "/tmp/cipp-learning-abhi")
sys.path.insert(0, ABHI_ROOT)

from backend.simulation import SimulationEngine, N_OUT  # noqa: E402

# Shared four center-cell patterns (Paradigm id → Abhi pattern name)
SHARED_PATTERNS: list[tuple[str, str]] = [
    ("H1", "row 1"),
    ("V1", "col 1"),
    ("D0", "diag \\"),
    ("D1", "diag /"),
]


@dataclass
class HeldPatternResult:
    first_winner_step: int | None
    bind_or_trained_step: int | None
    modal_winner: str | None
    distinct_winners: int
    weight_delta_active: float | None


@dataclass
class InterleavedResult:
    steps: int
    distinct_modal_winners: int
    bound_or_trained: int
    pattern_to_owner: dict[str, str]


def _abhi_ff_weights(engine, neuron_index: int, active_pixels: list[int]) -> tuple[float, float]:
    """Mean FF weight on active vs inactive pixels for one L2E."""
    neuron = engine.l2.excitatory_neurons[neuron_index]
    weights = neuron._weights_array[1:]  # skip inhibitory gate index 0
    active = [weights[p] for p in active_pixels]
    inactive = [weights[p] for p in range(9) if p not in active_pixels]
    return (sum(active) / len(active), sum(inactive) / len(inactive))


def _paradigm_active_indices(line_id: str) -> list[int]:
    from cognative_paradigm.lines import LINE_INDICES

    return LINE_INDICES[line_id]


def _abhi_visit_winner(engine, visit_steps: int) -> int | None:
    """Run one visit window; return modal L2E index (argmax spike counts)."""
    counts = [0] * N_OUT
    for _ in range(visit_steps):
        engine.step()
        for j in range(N_OUT):
            if engine.spiked[f"L2E{j}"]:
                counts[j] += 1
    if sum(counts) == 0:
        return None
    return int(max(range(N_OUT), key=lambda j: counts[j]))


def run_abhi_held(pattern_name: str, *, max_visits: int = 200, seed: int = 0) -> HeldPatternResult:
    engine = SimulationEngine(seed=seed)
    engine.set_pattern(pattern_name)
    visit_steps = engine.visit_steps
    winners: list[int | None] = []
    bind_step = None
    streak = 0
    prev: int | None = None
    active_pixels = [i for i, v in enumerate(engine.input_vec) if v > 0]

    for visit in range(1, max_visits + 1):
        winner_idx = _abhi_visit_winner(engine, visit_steps)
        winners.append(winner_idx)
        if winner_idx is not None and winner_idx == prev:
            streak += 1
        else:
            streak = 1 if winner_idx is not None else 0
        prev = winner_idx
        if bind_step is None and streak >= engine.trained_streak:
            bind_step = visit

    modal = Counter(w for w in winners if w is not None)
    modal_winner = f"L2E{modal.most_common(1)[0][0]}" if modal else None
    weight_delta = None
    if modal:
        idx = modal.most_common(1)[0][0]
        act, inact = _abhi_ff_weights(engine, idx, active_pixels)
        weight_delta = act - inact

    first_winner = next((i + 1 for i, w in enumerate(winners) if w is not None), None)
    return HeldPatternResult(
        first_winner_step=first_winner,
        bind_or_trained_step=bind_step,
        modal_winner=modal_winner,
        distinct_winners=len(set(w for w in winners if w is not None)),
        weight_delta_active=weight_delta,
    )


def run_paradigm_held(line_id: str, *, max_steps: int = 200) -> HeldPatternResult:
    sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
    pattern = get_line(line_id)
    active = pattern.edge_ids
    from cognative_paradigm.learning.weight_consolidation import pattern_weight_score

    winners: list[str | None] = []
    bind_step = None
    winner_competitor = None

    for step in range(1, max_steps + 1):
        result = sim.stimulate_pattern(pattern)
        w = sim.nucleus.last_winner
        winners.append(w.neuron.id if w else None)
        if any(e.get("type") == EventType.PATTERN_BOUND.name for e in result.step_events):
            bind_step = step
        if w and winner_competitor is None:
            winner_competitor = w

    modal = Counter(w for w in winners if w is not None)
    modal_winner = modal.most_common(1)[0][0] if modal else None
    weight_delta = None
    if winner_competitor:
        score = pattern_weight_score(
            winner_competitor.sensory_conductances,
            active,
            e_max_weight=DEFAULT_LEARNING_DYNAMICS.e_max_weight,
        )
        weight_delta = score

    first_winner = next((i + 1 for i, w in enumerate(winners) if w is not None), None)
    return HeldPatternResult(
        first_winner_step=first_winner,
        bind_or_trained_step=bind_step,
        modal_winner=modal_winner,
        distinct_winners=len(set(w for w in winners if w is not None)),
        weight_delta_active=weight_delta,
    )


def run_abhi_interleaved(*, max_rounds: int = 120, seed: int = 0) -> InterleavedResult:
    engine = SimulationEngine(seed=seed)
    visit_steps = engine.visit_steps
    pattern_winners: dict[str, Counter] = {name: Counter() for _, name in SHARED_PATTERNS}
    trained: set[str] = set()
    streaks: dict[str, int] = {name: 0 for _, name in SHARED_PATTERNS}
    prev: dict[str, int | None] = {name: None for _, name in SHARED_PATTERNS}

    for _round in range(max_rounds):
        for _, abhi_name in SHARED_PATTERNS:
            engine.set_pattern(abhi_name)
            winner_idx = _abhi_visit_winner(engine, visit_steps)
            if winner_idx is not None:
                pattern_winners[abhi_name][winner_idx] += 1
                if winner_idx == prev[abhi_name]:
                    streaks[abhi_name] += 1
                else:
                    streaks[abhi_name] = 1
                prev[abhi_name] = winner_idx
                if streaks[abhi_name] >= engine.trained_streak:
                    trained.add(abhi_name)

    owners = {
        abhi: (f"L2E{c.most_common(1)[0][0]}" if c else None)
        for abhi, c in pattern_winners.items()
    }
    distinct = len({v for v in owners.values() if v is not None})
    return InterleavedResult(
        steps=max_rounds * len(SHARED_PATTERNS),
        distinct_modal_winners=distinct,
        bound_or_trained=len(trained),
        pattern_to_owner={k: v or "—" for k, v in owners.items()},
    )


def run_paradigm_interleaved(*, max_rounds: int = 120) -> InterleavedResult:
    sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
    stream = RotatingStimulusStream(
        hold_steps=DEFAULT_LEARNING_DYNAMICS.ecological_stimulus_hold_steps
    )
    pattern_winners: dict[str, Counter] = {lid: Counter() for lid, _ in SHARED_PATTERNS}
    bound: set[str] = set()

    for pulse in range(max_rounds * len(SHARED_PATTERNS)):
        line_id = stream.next_line_id(pulse)
        result = sim.stimulate_pattern(get_line(line_id))
        if sim.nucleus.last_winner:
            pattern_winners[line_id][sim.nucleus.last_winner.neuron.id] += 1
        if any(e.get("type") == EventType.PATTERN_BOUND.name for e in result.step_events):
            bound.add(line_id)

    owners = {
        lid: (c.most_common(1)[0][0] if c else None)
        for lid, c in pattern_winners.items()
    }
    distinct = len({v for v in owners.values() if v is not None})
    return InterleavedResult(
        steps=pulse + 1,
        distinct_modal_winners=distinct,
        bound_or_trained=len(bound),
        pattern_to_owner={k: v or "—" for k, v in owners.items()},
    )


def run_abhi_sustained_dominance(pattern_name: str, *, seed: int = 0, hold_cycles: int = 40) -> float:
    """Fraction of held cycles won by modal specialist after interleaved train."""
    engine = SimulationEngine(seed=seed)
    steps = engine.params["cycle_period"]
    names = [name for _, name in SHARED_PATTERNS]
    for _ in range(60):
        for name in names:
            engine.set_pattern(name)
            for _ in range(steps):
                engine.step()
    engine.set_pattern(pattern_name)
    winners: list[int] = []
    for _ in range(steps * hold_cycles):
        engine.step()
        for j in range(N_OUT):
            if engine.spiked[f"L2E{j}"]:
                winners.append(j)
                break
    if not winners:
        return 0.0
    top_n = Counter(winners).most_common(1)[0][1]
    return top_n / len(winners)


def run_paradigm_integrity_gate() -> dict:
    """Phase 8 audit summary for production dynamics."""
    sim = BrainSimulator(dynamics=DEFAULT_LEARNING_DYNAMICS)
    stream = RotatingStimulusStream(
        hold_steps=DEFAULT_LEARNING_DYNAMICS.ecological_stimulus_hold_steps
    )
    learned: set[str] = set()
    for pulse in range(500):
        line_id = stream.next_line_id(pulse)
        sim.stimulate_pattern(get_line(line_id), line_id=line_id)
        for catalog_id in LINE_IDS:
            if sim.nucleus.pattern_ownership.owner_for_pattern(
                get_line(catalog_id).edge_ids
            ):
                learned.add(catalog_id)
        if len(learned) == len(LINE_IDS):
            break

    collisions = sum(
        1
        for event in sim.event_log.entries
        if event.get("type") == EventType.OWNERSHIP_COLLISION.name
    )
    integrity = LearningIntegrityAuditor(dynamics=DEFAULT_LEARNING_DYNAMICS).run(
        [LINE_INDICES[line_id] for line_id in LINE_IDS],
        max_steps_per_pattern=120,
    )
    return {
        "learned_count": len(learned),
        "ownership_collisions": collisions,
        "integrity_violations": integrity.violation_count,
        "integrity_binds": len(integrity.binds),
    }


def main() -> None:
    print("=" * 72)
    print("Abhi CIPP vs Cognative Paradigm — outcome comparison")
    print(f"Abhi root: {ABHI_ROOT}")
    print(f"Paradigm:  {PARADIGM_ROOT}")
    print("Shared patterns: H1↔row1, V1↔col1, D0↔diag\\, D1↔diag/")
    print("=" * 72)

    print("\n## 1. Single held pattern (H1 / row 1)")
    abhi_h1 = run_abhi_held("row 1")
    par_h1 = run_paradigm_held("H1")
    print(f"  {'Metric':<28} {'Abhi':<22} {'Paradigm':<22}")
    print(f"  {'First winner step':<28} {abhi_h1.first_winner_step!s:<22} {par_h1.first_winner_step!s:<22}")
    print(f"  {'Bind/trained step':<28} {abhi_h1.bind_or_trained_step!s:<22} {par_h1.bind_or_trained_step!s:<22}")
    print(f"  {'Modal winner':<28} {abhi_h1.modal_winner!s:<22} {par_h1.modal_winner!s:<22}")
    print(f"  {'Distinct winners':<28} {abhi_h1.distinct_winners!s:<22} {par_h1.distinct_winners!s:<22}")
    print(f"  {'Weight evidence':<28} {abhi_h1.weight_delta_active!s:<22} {par_h1.weight_delta_active!s:<22}")

    print("\n## 2. Interleaved rotation (4 shared shapes, 120 rounds)")
    abhi_int = run_abhi_interleaved()
    par_int = run_paradigm_interleaved()
    print(f"  {'Metric':<28} {'Abhi':<22} {'Paradigm':<22}")
    print(f"  {'Total steps':<28} {abhi_int.steps!s:<22} {par_int.steps!s:<22}")
    print(f"  {'Distinct modal winners':<28} {abhi_int.distinct_modal_winners}/4{'':<17} {par_int.distinct_modal_winners}/4")
    print(f"  {'Trained/bound count':<28} {abhi_int.bound_or_trained}/4{'':<17} {par_int.bound_or_trained}/4")
    print("  Pattern → owner (modal winner):")
    for (lid, abhi_name), _ in zip(SHARED_PATTERNS, SHARED_PATTERNS):
        print(
            f"    {lid:4} / {abhi_name:8}  "
            f"Abhi: {abhi_int.pattern_to_owner[abhi_name]:<14} "
            f"Paradigm: {par_int.pattern_to_owner[lid]}"
        )

    print("\n## 3. Sustained dominance after interleaved train (Abhi metric)")
    print("  Fraction of held cycles won by modal specialist (40 cycles each):")
    for lid, abhi_name in SHARED_PATTERNS:
        dom = run_abhi_sustained_dominance(abhi_name, seed=0)
        print(f"    {abhi_name:8} ({lid}): {dom:.2f}")

    print("\n## 4. Abhi full 8-pattern interleaved (reference)")
    engine = SimulationEngine(seed=0)
    visit_steps = engine.visit_steps
    from backend.simulation import PATTERNS

    winners_by_pattern: dict[str, Counter] = {n: Counter() for n in PATTERNS}
    for _ in range(30):
        for name in PATTERNS:
            engine.set_pattern(name)
            winner_idx = _abhi_visit_winner(engine, visit_steps)
            if winner_idx is not None:
                winners_by_pattern[name][winner_idx] += 1
    distinct_8 = len({c.most_common(1)[0][0] for c in winners_by_pattern.values() if c})
    print(f"  Distinct modal winners across 8 patterns (30 epochs): {distinct_8}/8")

    print("\n## 5. Paradigm Phase 8 integrity gate (production)")
    gate = run_paradigm_integrity_gate()
    print(f"  Rotation learned: {gate['learned_count']}/4")
    print(f"  OWNERSHIP_COLLISION events: {gate['ownership_collisions']}")
    print(
        f"  Integrity probe: binds={gate['integrity_binds']} "
        f"violations={gate['integrity_violations']}"
    )

    print("\n" + "=" * 72)
    print("Key architectural differences affecting outcomes:")
    print("  • Abhi: 8 L2E + shared L2I, signed-spike FF plasticity, no ownership map")
    print("  • Paradigm: 4 ring E + central I, eligibility bind, PatternMemorySnapshot")
    print("  • Abhi 'trained' = 3 consecutive same-winner rounds per pattern")
    print("  • Paradigm 'bound' = PATTERN_BOUND event (eligibility + weight gate)")
    print("=" * 72)


if __name__ == "__main__":
    main()
