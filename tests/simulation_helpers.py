from dataclasses import replace

from cognative_paradigm.lines import LINE_IDS, get_line, pattern_from_indices
from cognative_paradigm.simulation.engine import BrainSimulator, SimulationResult
from cognative_paradigm.simulation.learning_dynamics import (
    DEFAULT_LEARNING_DYNAMICS,
    LearningDynamics,
)

PATTERN_LEARN_MAX_STEPS = 300

# Catalog soft-ecology helpers (labeled control under force production).
# Soft NI + graded descending + Stage 14 autonomy; gradual E′ climb (gain < θ).
SOFT_CATALOG_COMPETITION = {
    "pretrained_inhibitor_exclusivity_enabled": False,
    "descending_mode": "graded",
    "emergent_autonomy_enabled": True,
    "l2_to_l1_i_gain": 0.18,
    "central_pool_gain": 0.50,
    "central_competition_ni_discharge_fraction": 0.70,
}


def force_cascade_dynamics(**overrides) -> LearningDynamics:
    """Production force exclusivity path (NI wipe + same-tick L1I)."""
    base = {
        "membrane_noise_std": 0.0,
        "wta_fair_ties": False,
        "wta_rng_seed": 0,
        "pretrained_inhibitor_exclusivity_enabled": True,
        "descending_mode": "force",
        "emergent_autonomy_enabled": False,
        "l2_to_l1_i_gain": 0.26,
    }
    base.update(overrides)
    return replace(DEFAULT_LEARNING_DYNAMICS, **base)


def deterministic_dynamics(**overrides) -> LearningDynamics:
    """Disable biological WTA noise/fair-ties for identity-sensitive tests."""
    base = {
        "membrane_noise_std": 0.0,
        "wta_fair_ties": False,
        "wta_rng_seed": 0,
        "membrane_tau": 10.0,
        "nucleus_relay_weight": 0.075,
        "nucleus_threshold": 1.05,
        "ring_feedback_gain": 1.15,
        "e_learning_rate": 0.015,
        "eligibility_alpha": 0.5,
        "eligibility_threshold": 0.75,
        "eligibility_decay": 0.06,
        "consolidation_weight_threshold": 0.15,
        # Soft independent race needs temporal + exc flow for catalog learning.
        "temporal_integration_enabled": True,
        "excitatory_flow_rate_enabled": True,
        "inhibitory_turnover_enabled": False,
        "assembly_flow_credit_enabled": False,
        "inhibitory_flow_rate_enabled": False,
        # Match SOFT_CATALOG_COMPETITION (labeled soft ecology control).
        **dict(SOFT_CATALOG_COMPETITION),
    }
    base.update(overrides)
    # Force/exclusivity control cannot coexist with Stage 14 autonomy.
    if base.get("pretrained_inhibitor_exclusivity_enabled") or base.get(
        "descending_mode"
    ) == "force":
        base["emergent_autonomy_enabled"] = False
    return replace(DEFAULT_LEARNING_DYNAMICS, **base)


def unguided_ecological_dynamics(**overrides) -> LearningDynamics:
    """Self-paced defaults: ecological rotation + full robustness stack."""
    soft = dict(SOFT_CATALOG_COMPETITION)
    soft.update(overrides)
    return robustness_dynamics(
        ecological_stimulus_mode="rotation",
        **soft,
    )


def biology_dynamics(**overrides) -> LearningDynamics:
    """Default biological learning dynamics for tests."""
    return deterministic_dynamics(**overrides)


def robustness_dynamics(**overrides) -> LearningDynamics:
    """Full Phases 1–5 temporal + flow robustness stack for stress tests."""
    base = {
        "temporal_integration_enabled": True,
        "sim_dt_ms": 1.0,
        "stim_duration_ms": 40.0,
        "auto_stim_interval_ms": 1000,
        "excitatory_flow_rate_enabled": True,
        "exc_trace_decay": 0.8,
        "exc_trace_normalized": True,
        "inhibitory_turnover_enabled": True,
        "assembly_flow_credit_enabled": True,
        "inhibitory_flow_rate_enabled": True,
        "inh_trace_decay": 0.8,
        "inh_trace_normalized": True,
        "relay_weight_init_spread": 0.0,
    }
    base.update(overrides)
    return deterministic_dynamics(**base)


def catalog_soft_dynamics(**overrides) -> LearningDynamics:
    """Deterministic stack with soft NI for multi-pattern catalog learning."""
    soft = dict(SOFT_CATALOG_COMPETITION)
    soft.update(overrides)
    return deterministic_dynamics(**soft)


def interleaved_learn_all(
    sim: BrainSimulator,
    *,
    line_ids: tuple[str, ...] | None = None,
    max_rounds: int = 300,
) -> int:
    """
    Rotate catalog presentations until every line owns a ring neuron.

    Returns the number of stimulate steps executed.
    """
    catalog = line_ids or LINE_IDS

    def all_learned() -> bool:
        return all(
            sim.nucleus.pattern_ownership.owner_for_pattern(get_line(line_id).edge_ids)
            for line_id in catalog
        )

    steps = 0
    for round_index in range(max_rounds):
        if all_learned():
            return steps
        line_id = catalog[round_index % len(catalog)]
        sim.stimulate_pattern(get_line(line_id))
        steps += 1

    if not all_learned():
        missing = [
            line_id
            for line_id in catalog
            if not sim.nucleus.pattern_ownership.owner_for_pattern(
                get_line(line_id).edge_ids
            )
        ]
        raise AssertionError(
            f"interleaved rotation did not bind all patterns within {max_rounds} "
            f"steps; missing {missing}"
        )
    return steps


def interleaved_learn_all_with_offline_replay(
    sim: BrainSimulator,
    *,
    line_ids: tuple[str, ...] | None = None,
    max_rounds: int = 300,
    replay_interval: int = 4,
    offline_steps: int = 2,
) -> int:
    """Rotate catalog presentations with periodic offline consolidation."""
    catalog = line_ids or LINE_IDS

    def all_learned() -> bool:
        return all(
            sim.nucleus.pattern_ownership.owner_for_pattern(get_line(line_id).edge_ids)
            for line_id in catalog
        )

    steps = 0
    for round_index in range(max_rounds):
        if all_learned():
            return steps
        line_id = catalog[round_index % len(catalog)]
        pattern = get_line(line_id)
        sim.stimulate_pattern(pattern, line_id=line_id)
        steps += 1
        if replay_interval > 0 and steps % replay_interval == 0:
            sim.offline_consolidation_steps(offline_steps)

    if not all_learned():
        missing = [
            line_id
            for line_id in catalog
            if not sim.nucleus.pattern_ownership.owner_for_pattern(
                get_line(line_id).edge_ids
            )
        ]
        raise AssertionError(
            f"interleaved rotation with replay did not bind all patterns within "
            f"{max_rounds} steps; missing {missing}"
        )
    return steps


def ownership_owner_ids(sim: BrainSimulator) -> dict[str, str]:
    """Map pattern ownership key → ring neuron id."""
    return dict(sim.nucleus.pattern_ownership.as_dict())


def assert_injective_ownership(sim: BrainSimulator, *, line_ids: tuple[str, ...] | None = None) -> None:
    """Each catalog line maps to a distinct ring neuron."""
    catalog = line_ids or LINE_IDS
    owners: list[str] = []
    for line_id in catalog:
        pattern = get_line(line_id)
        owner = sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids)
        if owner is None:
            raise AssertionError(f"{line_id} has no owner")
        owners.append(owner)
    assert_unique_owners(sim, owners=owners)


def assert_unique_owners(
    sim: BrainSimulator,
    *,
    owners: list[str] | None = None,
) -> None:
    """Bound patterns map to distinct ring neurons (no ownership collisions)."""
    active = owners if owners is not None else list(ownership_owner_ids(sim).values())
    if len(active) != len(set(active)):
        raise AssertionError(f"duplicate owners in map: {active}")


def force_sole_binder(
    sim: BrainSimulator,
    pattern,
    keep_id: str | None = None,
    *,
    silence_others: bool = True,
) -> str:
    """Unbind hitchhikers so Rule 7.2 sole-owner freeze tests are meaningful.

    One-shape deterministic replay can consolidate multiple ring neurons onto the
    same edge set; SG-2 freezes LTP+LTD only for the sole binder. When
    ``silence_others`` is True, floor other neurons' relay/sensory maps so they
    cannot re-bind during rematch pulses.
    """
    binders = sim.nucleus.pattern_ownership.binders_for_pattern(pattern.edge_ids)
    if not binders:
        raise AssertionError("pattern has no binders to force sole ownership")
    keep = keep_id or binders[0]
    for competitor in sim.nucleus.ring:
        if competitor.neuron.id == keep:
            continue
        memory = competitor.neuron.memory
        if (
            memory.is_bound()
            and memory.bound_pattern is not None
            and memory.bound_pattern.edge_ids == pattern.edge_ids
        ):
            memory.unbind()
            competitor.neuron.prediction.clear()
            competitor.neuron.bound_symbol_id = None
            sim.symbols.release_neuron(competitor.neuron.id)
            competitor.eligibility_trace.reset()
        if silence_others:
            competitor.relay_conductances.replace_weights(
                {key: 0.01 for key in competitor.relay_conductances.as_dict()}
            )
            competitor.sensory_conductances.replace_weights(
                {key: 0.01 for key in competitor.sensory_conductances.as_dict()}
            )
    remaining = sim.nucleus.pattern_ownership.binders_for_pattern(pattern.edge_ids)
    if remaining != [keep]:
        raise AssertionError(f"expected sole binder {keep}, got {remaining}")
    return keep


def stimulate_until_pattern_bound(
    sim: BrainSimulator,
    active_indices: list[int],
    *,
    max_steps: int = PATTERN_LEARN_MAX_STEPS,
) -> None:
    pattern = pattern_from_indices(active_indices)
    for _ in range(max_steps):
        sim.stimulate_pattern(pattern)
        if sim.nucleus.pattern_ownership.owner_for_pattern(pattern.edge_ids):
            return
    raise AssertionError(
        f"pattern {active_indices} did not bind within {max_steps} steps"
    )


def stimulate_until_recognized(
    sim: BrainSimulator,
    active_indices: list[int],
    *,
    max_steps: int = 80,
) -> SimulationResult:
    pattern = pattern_from_indices(active_indices)
    last: SimulationResult | None = None
    for _ in range(max_steps):
        last = sim.stimulate_pattern(pattern)
        if last.output_symbol:
            return last
    raise AssertionError(
        f"pattern {active_indices} not recognized within {max_steps} steps"
    )


def learn_pattern(
    sim: BrainSimulator,
    active_indices: list[int],
    *,
    max_steps: int = PATTERN_LEARN_MAX_STEPS,
) -> SimulationResult:
    stimulate_until_pattern_bound(sim, active_indices, max_steps=max_steps)
    return stimulate_until_recognized(sim, active_indices)


def learn_catalog_line(
    sim: BrainSimulator,
    line_id: str,
    *,
    max_steps: int = PATTERN_LEARN_MAX_STEPS,
) -> SimulationResult:
    from cognative_paradigm.lines import LINE_INDICES

    return learn_pattern(sim, LINE_INDICES[line_id], max_steps=max_steps)


def learn_all_catalog_lines(
    sim: BrainSimulator,
    *,
    max_steps_per_pattern: int = PATTERN_LEARN_MAX_STEPS,
) -> dict:
    """Bind every catalog line.

    Soft independent race cannot reliably sequential-hold after the first bind
    (mismatch owners still charge and trip NI). Use interleaved rotation unless
    the labeled exclusivity wipe cascade is explicitly enabled.
    """
    if not sim.dynamics.pretrained_inhibitor_exclusivity_enabled:
        rounds = max(250, max_steps_per_pattern)
        interleaved_learn_all(sim, max_rounds=rounds)
        return sim.get_state()["training"]
    for line_id in LINE_IDS:
        learn_catalog_line(sim, line_id, max_steps=max_steps_per_pattern)
    return sim.get_state()["training"]
