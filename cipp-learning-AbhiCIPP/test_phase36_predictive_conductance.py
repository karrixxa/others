"""Deterministic causal tests for Phase 36 predictive-output conductance."""

from collections import deque

import numpy as np

from backend.simulation import N_OUT, N_PIX, PATTERNS, SimulationEngine
from backend.presets import DASHBOARD_PRESET


PC_IDX = 3
ACTIVE_ROW = "row 1"


def _engine(persistent=False):
    kw = dict(
        DASHBOARD_PRESET,
        seed=1,
        prediction_column_enabled=True,
        prediction_column_to_i_enabled=True,
        prediction_column_persistent_conductance_enabled=persistent,
        pretrained_l1i_regulation=True,
        prediction_feedback_init=400.0,
        prediction_feedback_max=400.0,
        prediction_lateral_weight=400.0,
        prediction_threshold=700.0,
        prediction_learning_rate=0.0,
        prediction_feedback_delay=1,
        refractory=0,
    )
    engine = SimulationEngine(**kw)
    engine._set_plasticity_frozen(True)
    engine.set_pattern(ACTIVE_ROW)
    return engine


def _prime_single_pc_event(engine, pc_idx=PC_IDX):
    apical = np.zeros(N_OUT)
    apical[0] = 1.0
    basal = np.zeros(N_PIX)
    basal[pc_idx] = 1.0
    engine.l2e_to_pcol_queue = deque([apical])
    engine.s_to_pcol_queue = deque([basal])
    engine.pcol_delivery_metadata_queue = deque([[
        dict(source="L2E0", target=f"PC{pc_idx}", target_compartment="apical",
             scheduled_step=-1, arrival_step=0, origin_pattern=ACTIVE_ROW),
        dict(source=f"L1E{pc_idx}", target=f"PC{pc_idx}", target_compartment="basal",
             scheduled_step=-1, arrival_step=0, origin_pattern=ACTIVE_ROW),
    ]])


def _clear_future_pc_events(engine):
    engine.l2e_to_pcol_queue = deque(np.zeros(N_OUT) for _ in range(engine.prediction_feedback_delay))
    engine.s_to_pcol_queue = deque(np.zeros(N_PIX) for _ in range(engine.prediction_feedback_delay))
    engine.pcol_delivery_metadata_queue = deque([] for _ in range(engine.prediction_feedback_delay))


def test_persistent_predictive_conductance_requires_selective_topology():
    try:
        SimulationEngine(
            seed=1,
            prediction_column_enabled=True,
            prediction_column_persistent_conductance_enabled=True,
            **DASHBOARD_PRESET,
        )
        raised = False
    except ValueError:
        raised = True
    assert raised, (
        "prediction_column_persistent_conductance_enabled must require the paired "
        "selective PC_i -> L1I_i -> L1E_i topology"
    )


def test_default_off_predictive_path_stays_instantaneous_only():
    engine = _engine(persistent=False)
    _prime_single_pc_event(engine)

    engine.step()
    _clear_future_pc_events(engine)

    assert engine.spiked["PC3"], "the primed basal+apical pair must physically fire PC3"
    assert engine.spiked["L1I3"], "PC3's spike must reach only its paired L1I3 this step"
    assert engine.spiked["L1E3"], "paired L1E3 must still spike on the priming step (one-step delay preserved)"
    assert [i for i in range(N_PIX) if engine.spiked[f"L1I{i}"]] == [PC_IDX]

    engine.step()
    l1e3 = engine.l1.excitatory_neurons[PC_IDX]
    inhibited = [nid for nid, _ev in engine._inh_events]
    assert not engine.spiked["L1E3"], "the paired L1I3 discharge must suppress L1E3 one step later"
    assert inhibited == ["L1E3"], f"only the paired target may receive the predictive discharge, got {inhibited}"
    assert l1e3.inh_trace == 0.0
    assert l1e3.inh_trace_pending == 0.0

    engine.step()
    assert engine.spiked["L1E3"], "without Phase 36 enabled, no persistent tail may remain after the one-step hit"


def test_predictive_conductance_is_paired_delayed_persistent_and_decays():
    engine = _engine(persistent=True)
    _prime_single_pc_event(engine)

    engine.step()
    _clear_future_pc_events(engine)

    assert engine.spiked["PC3"]
    assert engine.spiked["L1I3"]
    assert engine.spiked["L1E3"], "the original one-step delay must remain intact on the priming step"
    assert [i for i in range(N_PIX) if engine.spiked[f"L1I{i}"]] == [PC_IDX]

    engine.step()
    l1e3 = engine.l1.excitatory_neurons[PC_IDX]
    l1e4 = engine.l1.excitatory_neurons[4]
    l1e5 = engine.l1.excitatory_neurons[5]
    expected_tail = (-l1e3.weights[0]) * (1.0 - l1e3.inh_trace_decay)
    inhibited = [nid for nid, _ev in engine._inh_events]
    assert not engine.spiked["L1E3"], "the paired discharge must still land one step later"
    assert engine.spiked["L1E4"] and engine.spiked["L1E5"], "nonpaired active row-1 pixels must remain unsuppressed"
    assert inhibited == ["L1E3"], f"the conductance path must stay strictly paired, got {inhibited}"
    assert np.isclose(l1e3.inh_trace, expected_tail)
    assert l1e3.inh_trace_pending == 0.0
    assert l1e4.inh_trace == 0.0 and l1e5.inh_trace == 0.0

    engine.step()
    assert not engine.spiked["L1E3"], "the seeded tail must suppress the paired pixel on the following step"
    assert np.isclose(l1e3.inh_trace, expected_tail * l1e3.inh_trace_decay)
    retained = PATTERNS[ACTIVE_ROW][PC_IDX] * engine.params["threshold"] - expected_tail
    assert np.isclose(l1e3.potential, retained * (1.0 - l1e3.leak_rate))
    assert l1e4.inh_trace == 0.0 and l1e5.inh_trace == 0.0

    engine.input_vec[:] = 0.0
    engine.current_pattern = "phase36-silent"
    engine.step()
    assert np.isclose(l1e3.inh_trace, expected_tail * (l1e3.inh_trace_decay ** 2))
    assert l1e3.inh_trace_pending == 0.0
    assert l1e4.inh_trace == 0.0 and l1e5.inh_trace == 0.0


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, name) for name in dir(mod) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"OK: {test.__name__}")
    print(f"{len(tests)} tests passed")
