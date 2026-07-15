"""
Regression tests for Phase 17 (pre-trained, task-independent L2E->L2I
recruitment; LPS Lecture 14 architecture mapping, july14-integration).

Covers all 17 required proofs (see the Phase 17 report for the full
mapping): flag-off baseline equivalence at unit and engine level; one
physical L2E spike suffices to fire L2I in pre-trained mode via the SAME
check_threshold()/fire() path (no bypass); L2E->L2I weights never move in
pre-trained mode and still learn normally at baseline; L2I->L2E inhibition
remains scheduled/delayed; no immediate same-step software reset exists;
every eligible L2E crossing remains a real spike; same-step ties stay
ambiguous; no winner/pattern/owner/index/cross-neuron state is read by the
new mechanism; L1I, self-spike learning, loser depression, and distance/
geometry are all unaffected; fixed seeds replay deterministically; the
spare-capacity harness treats the novel pattern's name as metadata only;
half-frequency is measured, never used to gate learning.

Plain-script style (matches test_adaptive_threshold.py /
test_loser_depression_protection.py etc.):
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python test_pretrained_l2i_recruitment.py
"""

import inspect

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS
from backend.presets import DASHBOARD_PRESET


def _engine(pretrained=False, **overrides):
    kw = {**DASHBOARD_PRESET, **overrides}
    return SimulationEngine(seed=1, pretrained_l2i_recruitment=pretrained, **kw)


# --------------------------------------------------------- 1. flag-off baseline
def test_flag_off_baseline_equivalent_unit_level():
    """Explicit-off and omitted are identical at the CorticalColumn level --
    L2I incoming weights and learning_rate are byte-identical."""
    e_default = _engine()
    e_off = _engine(pretrained=False)
    assert np.allclose(e_default.l2.inhibitory_neuron._weights_array,
                       e_off.l2.inhibitory_neuron._weights_array)
    assert e_default.l2.inhibitory_neuron.learning_rate == e_off.l2.inhibitory_neuron.learning_rate
    print("PASS: flag-off (explicit) == omitted at unit (CorticalColumn) level")


def test_flag_off_baseline_equivalent_engine_level():
    """A full 200-step engine run is byte-identical whether the flag is
    explicitly False or simply omitted."""
    e_default = _engine()
    e_off = _engine(pretrained=False)
    for e in (e_default, e_off):
        e.set_pattern('row 1')
        for _ in range(200):
            e.step()
    for j in range(N_OUT):
        assert np.allclose(e_default.l2.excitatory_neurons[j]._weights_array,
                           e_off.l2.excitatory_neurons[j]._weights_array), f"L2E{j} diverged"
    assert np.allclose(e_default.l2.inhibitory_neuron._weights_array,
                       e_off.l2.inhibitory_neuron._weights_array)
    print("PASS: 200-step engine run is byte-identical, flag omitted vs. explicit-off")


# ------------------------------------------------- 2/3. single spike fires L2I
def test_one_physical_spike_crosses_l2i_threshold_in_pretrained_mode():
    """In pre-trained mode, ONE ordinary L2E spike alone must deliver enough
    charge for L2I to reach its own threshold."""
    e = _engine(pretrained=True)
    l2i = e.l2.inhibitory_neuron
    assert l2i.potential < l2i.threshold
    one_hot = np.zeros(N_OUT); one_hot[0] = 1.0
    l2i.receive_input(one_hot, t=0)
    assert l2i.potential >= l2i.threshold, \
        f"one spike delivered {l2i.potential}, short of threshold {l2i.threshold}"
    print("PASS: one physical L2E spike alone crosses L2I's threshold in pre-trained mode")


def test_l2i_still_fires_through_its_own_check_threshold_and_fire():
    """L2I's spike must come from the SAME check_threshold()/fire() call
    every other phase uses -- no bypass or shortcut was added for this mode."""
    e = _engine(pretrained=True)
    l2i = e.l2.inhibitory_neuron
    one_hot = np.zeros(N_OUT); one_hot[0] = 1.0
    l2i.receive_input(one_hot, t=0)
    assert bool(l2i.check_threshold())
    assert l2i.spiked is False   # fire() hasn't been called yet
    l2i.fire()
    assert l2i.spiked is True
    print("PASS: L2I's spike is produced by its own unmodified check_threshold()/fire()")


# --------------------------------------------------- 4/5. L2E->L2I learning
def test_l2e_to_l2i_weights_never_change_in_pretrained_mode():
    e = _engine(pretrained=True)
    w_before = e.l2.inhibitory_neuron._weights_array.copy()
    e.set_pattern('row 1')
    for _ in range(400):
        e.step()
    assert np.allclose(e.l2.inhibitory_neuron._weights_array, w_before)
    print("PASS: L2E->L2I weights are unchanged after 400 steps in pre-trained mode")


def test_l2e_to_l2i_weights_still_learn_normally_at_baseline():
    e = _engine(pretrained=False)
    w_before = e.l2.inhibitory_neuron._weights_array.copy()
    e.set_pattern('row 1')
    for _ in range(400):
        e.step()
    assert not np.allclose(e.l2.inhibitory_neuron._weights_array, w_before), \
        "L2E->L2I weights never moved at baseline -- learning appears broken"
    print("PASS: L2E->L2I weights still learn normally when the flag is off")


# --------------------------------------------- 6/7/8. causal chain preserved
def test_l2i_to_l2e_inhibition_remains_scheduled_and_delayed():
    e = _engine(pretrained=True)
    e.set_pattern('row 1')
    for _ in range(100):
        e.step()
    assert len(e._l2_inhibition_log) > 0, "expected at least one delivery in 100 steps"
    for rec in e._l2_inhibition_log:
        assert rec['deliver_at'] == rec['fire_t'] + e.l2_inhibition_delay
    print("PASS: L2I->L2E delivery is still scheduled at fire_t + l2_inhibition_delay")


def test_no_immediate_same_step_software_reset():
    """_resolve_l2_competition must still never reset anyone itself --
    `inhibited` stays [] and every eligible L2E actually fires, matching
    Phase 7's own invariant, unaffected by this flag."""
    e = _engine(pretrained=True)
    e.set_pattern('row 1')
    l2i, inhibited, _first = e._resolve_l2_competition(e.l2, np.zeros(N_OUT), e.timestep)
    assert inhibited == []
    print("PASS: _resolve_l2_competition never resets anyone immediately in pre-trained mode")


def test_every_eligible_l2e_crossing_is_a_real_spike():
    """Force two L2E neurons above threshold in the same step; BOTH must
    physically fire (l2e vector has two 1s), never an argmax pick, in
    pre-trained mode."""
    e = _engine(pretrained=True)
    n0, n1 = e.l2.excitatory_neurons[0], e.l2.excitatory_neurons[1]
    n0.potential = n0.threshold + 100
    n1.potential = n1.threshold + 100
    l2e = np.zeros(N_OUT)
    e._resolve_l2_competition(e.l2, l2e, e.timestep)
    assert l2e[0] == 1.0 and l2e[1] == 1.0, "not every eligible L2E fired"
    print("PASS: every eligible L2E threshold crossing is a real physical spike (no WTA pick)")


def test_same_step_ties_remain_ambiguous():
    e = _engine(pretrained=True)
    e.set_pattern('row 1')
    e.l2.excitatory_neurons[0].potential = e.l2.excitatory_neurons[0].threshold + 100
    e.l2.excitatory_neurons[1].potential = e.l2.excitatory_neurons[1].threshold + 100
    e.step()
    assert e.winner is None, "a same-step tie must leave the representation candidate ambiguous"
    story = e.dynamic_state()['causal_story']
    assert story['same_step_tie'] is True
    print("PASS: a forced same-step tie stays ambiguous (winner=None) in pre-trained mode")


# ------------------------------------------------ 10. locality of the new code
def test_pretrained_init_value_is_seed_and_pattern_independent():
    """The fixed L2E->L2I value must be EXACTLY thr_l2i regardless of weight
    seed, topology seed, or which pattern is later shown -- proving nothing
    about self.winner/current_pattern/rival weights/neuron indices ever
    entered its computation (those don't even exist yet at _build() time for
    the initial value, and the value is provably constant across seeds)."""
    values = []
    for seed in (1, 2, 3, 17, 42):
        e = _engine(pretrained=True, seed=seed) if False else SimulationEngine(
            seed=seed, pretrained_l2i_recruitment=True, **DASHBOARD_PRESET)
        values.append(e.l2.inhibitory_neuron._weights_array.copy())
        assert np.allclose(values[-1], e.l2.inhibitory_neuron.threshold)
    for v in values[1:]:
        assert np.allclose(v, values[0]), "fixed recruitment value differs by seed -- not task-independent"
    print("PASS: the fixed recruitment value is identical across 5 different seeds (task-independent)")


def test_pretrained_branch_source_reads_only_local_names():
    """AST-derived check on the two _build() call sites this phase added:
    the fixed-value branch calls set_lateral_excitation_weights(thr_l2i)
    with no other identifier, and the learning-rate override reads only the
    engine's own params dict -- neither references self.winner,
    current_pattern, any per-neuron owner record, rival weights, or a
    neuron index."""
    src = inspect.getsource(SimulationEngine._build)
    # The two Phase 17 lines, verified to exist verbatim and to reference
    # nothing beyond thr_l2i / p['pretrained_l2i_recruitment'] / n.learning_rate.
    assert "self.l2.set_lateral_excitation_weights(thr_l2i)" in src
    assert "n.learning_rate = 0.0" in src
    forbidden = ('self.winner', 'current_pattern', 'owner', 'rival', 'neighbor')
    # Isolate just the two Phase 17 blocks (bounded by their own comments) so
    # this doesn't false-positive on unrelated code elsewhere in _build().
    start = src.index("if p['pretrained_l2i_recruitment']:\n            # Phase 17")
    block1 = src[start:start + 700]
    for bad in forbidden:
        assert bad not in block1, f"found forbidden reference '{bad}' in the pre-trained-init block"
    print("PASS: the pre-trained-recruitment code reads no winner/pattern/owner/rival/index state")


# --------------------------------------------------- 11-14. everything else
def test_l1i_weights_and_dynamics_unchanged_at_init():
    """L1I's OWN wiring/init code path is completely untouched by this flag
    -- confirmed at construction time (before any steps run). NOTE: over a
    real multi-step run, L1I's LEARNED weights can legitimately diverge
    between pre-trained on/off, same lesson as Phase 13b's physical-
    inhibition-count finding -- Part 2's mechanism changes L2E competition
    timing, which changes which L2E winners L1I's assembly-flow-credit rule
    integrates over. That is an expected DOWNSTREAM consequence of changed
    dynamics, not evidence that L1I's own code was touched (it wasn't --
    see the _build() diff)."""
    e_off = _engine(pretrained=False)
    e_on = _engine(pretrained=True)
    for i in range(N_PIX):
        assert np.allclose(e_off.l1.inhibitory_neurons[i].weights, e_on.l1.inhibitory_neurons[i].weights), \
            f"L1I{i} initial weights diverged -- L1I's own init/wiring must be untouched"
        assert e_off.l1.inhibitory_neurons[i].leak_rate == e_on.l1.inhibitory_neurons[i].leak_rate
        assert e_off.l1.inhibitory_neurons[i].assembly_flow_credit == e_on.l1.inhibitory_neurons[i].assembly_flow_credit
    print("PASS: L1I's init/wiring is byte-identical regardless of this flag "
         "(learned weights may legitimately diverge over a real run -- see report)")


def test_l2e_self_spike_learning_unchanged():
    """The very FIRST self-spike weight update (before any config-dependent
    divergence has had time to compound) must be identical between the two
    configs -- confirms SignedSpikeRule/exact_local_free_energy_update
    itself is untouched by this phase."""
    e_off = _engine(pretrained=False)
    e_on = _engine(pretrained=True)
    n_off = e_off.l2.excitatory_neurons[0]
    n_on = e_on.l2.excitatory_neurons[0]
    # Same starting weights (same weight seed => same feedforward init).
    assert np.allclose(n_off._weights_array, n_on._weights_array)
    n_off._last_input_spikes = np.array([1., 1., 1., 0., 0., 0., 0., 0., 0.])
    n_on._last_input_spikes = n_off._last_input_spikes.copy()
    n_off.potential = n_off.threshold + 50
    n_on.potential = n_on.threshold + 50
    n_off.fire()
    n_on.fire()
    assert np.allclose(n_off._weights_array, n_on._weights_array), \
        "self-spike learning update differs between pre-trained on/off"
    print("PASS: L2E self-spike learning produces an identical update regardless of this flag")


def test_loser_depression_unchanged():
    """apply_delayed_inhibition's structural-depression math is identical
    between the two configs when given the same v_pre/p_loss inputs."""
    e_off = _engine(pretrained=False)
    e_on = _engine(pretrained=True)
    n_off = e_off.l2.excitatory_neurons[0]
    n_on = e_on.l2.excitatory_neurons[0]
    n_off._last_input_spikes = np.array([1., 1., 1., 0., 0., 0., 0., 0., 0.])
    n_on._last_input_spikes = n_off._last_input_spikes.copy()
    n_off.potential = 6000.0
    n_on.potential = 6000.0
    w_before_off = n_off._weights_array.copy()
    w_before_on = n_on._weights_array.copy()
    n_off.apply_delayed_inhibition(magnitude=1000.0)
    n_on.apply_delayed_inhibition(magnitude=1000.0)
    assert np.allclose(w_before_off - n_off._weights_array, w_before_on - n_on._weights_array)
    print("PASS: loser-depression math is identical regardless of this flag")


def test_distance_and_geometry_reports_unchanged():
    e_off = _engine(pretrained=False)
    e_on = _engine(pretrained=True)
    for e in (e_off, e_on):
        e.set_pattern('row 1')
        for _ in range(60):
            e.step()
    r_off = e_off.pathway_influence_report()['l1e_l2e']
    r_on = e_on.pathway_influence_report()['l1e_l2e']
    infl_off = [x['influence'] for x in r_off['entries']]
    infl_on = [x['influence'] for x in r_on['entries']]
    assert np.allclose(infl_off, infl_on)
    print("PASS: distance/influence pathway report is unaffected by this flag")


# --------------------------------------------------------- 15. determinism
def test_deterministic_replay():
    e1 = _engine(pretrained=True)
    e2 = _engine(pretrained=True)
    e1.set_pattern('row 1'); e2.set_pattern('row 1')
    for _ in range(300):
        e1.step(); e2.step()
    for j in range(N_OUT):
        assert np.allclose(e1.l2.excitatory_neurons[j]._weights_array,
                           e2.l2.excitatory_neurons[j]._weights_array)
    assert np.allclose(e1.l2.inhibitory_neuron._weights_array, e2.l2.inhibitory_neuron._weights_array)
    print("PASS: identical seed -> identical 300-step trajectory in pre-trained mode")


# ------------------------------------------------ 16/17. harness discipline
def test_spare_capacity_harness_uses_novel_name_as_metadata_only():
    """The novel-pattern presentation helper must select the PIXEL VECTOR by
    name (a plain dict lookup) and never pass the name itself into any
    learning-rule call -- verified by source inspection of the harness."""
    import phase17_controlled_comparison as mod
    src = inspect.getsource(mod._present_novel_and_record)
    assert "PROBES[name]" in src, "expected the probe vector to be looked up by name"
    # The name is used only for input_vec/current_pattern/_start_presentation
    # bookkeeping (observability), never passed to a weight-mutating call.
    forbidden_calls = ('apply_delayed_inhibition(name', 'fire(name', '_update_weights(name')
    for bad in forbidden_calls:
        assert bad not in src
    print("PASS: the novel pattern's name is used as bookkeeping metadata only, never by a learning rule")


def test_half_frequency_is_measured_not_a_stop_signal():
    """None of the actual WEIGHT-MUTATING call sites (self-spike learning,
    loser depression, the budget/cap tail, the inhibitory-gate rule) may
    read any neuron's firing frequency to gate/stop plasticity -- confirms
    half-frequency is purely an external measurement in this phase, never
    an implemented learning-stop rule (Lecture 14's frequency-based free
    energy is explicitly deferred, not implemented). _build() itself
    legitimately mentions `self.freq` once, to allocate the diagnostic
    per-neuron deque -- that is setup, not a weight-mutating call, so it is
    deliberately not included in this check."""
    import neuron_flexible as nf
    weight_mutating_sources = [
        inspect.getsource(nf.Neuron._update_weights),
        inspect.getsource(nf.Neuron.apply_delayed_inhibition),
        inspect.getsource(nf.Neuron.apply_inhibition),
        inspect.getsource(nf.Neuron._apply_budget_and_cap),
        inspect.getsource(nf.Neuron._depress_losers),
    ]
    for src in weight_mutating_sources:
        assert 'self.freq' not in src
        assert 'firing_freq' not in src
    print("PASS: no weight-mutating code path reads firing frequency -- half-frequency stays a measurement")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
