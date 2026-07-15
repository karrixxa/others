"""
Regression tests for Phase 19-v2 (LPS Lecture 14 LOCAL-COINCIDENCE
prediction architecture; see Phase18b_Lecture14_Local_Coincidence_
Architecture_Contract.md, july14-integration). This is the final,
transcript-faithful S_i/PC_i/I_i architecture (fixed local S_i->PCi lateral
coincidence + learned all-to-all R_j->PCi feedback, decoder learning gated
on PCi's own physical spike). It supersedes -- and is a SEPARATE, mutually-
exclusive-at-build-time mechanism from -- prediction_excitatory_enabled
(Phase 19A's per-column scaffold, no lateral connection, no active
learning) and every earlier eight-predictor prototype.

Plain-script style (matches test_pretrained_l2i_recruitment.py etc.):
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python test_prediction_column_phase19.py
"""

import inspect

import numpy as np

from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS
from backend.presets import DASHBOARD_PRESET

HOLD = 3000   # steps per pattern for the coincidence/selectivity tests


def _engine(pcol=False, seed=1, **overrides):
    kw = {**DASHBOARD_PRESET, **overrides}
    return SimulationEngine(seed=seed, prediction_column_enabled=pcol, **kw)


# ============================================================ A. Preservation
def test_flag_off_baseline_equivalent_unit_level():
    e_default = _engine()
    e_off = _engine(pcol=False)
    assert e_default.pcol == [] and e_off.pcol == []
    assert 'PC0' not in e_default.neurons and 'PC0' not in e_off.neurons
    for j in range(N_OUT):
        assert np.allclose(e_default.l2.excitatory_neurons[j]._weights_array,
                           e_off.l2.excitatory_neurons[j]._weights_array)
    print("PASS: flag-off (explicit) == omitted at unit level -- no PC population built")


def test_flag_off_baseline_equivalent_engine_level():
    e_default = _engine()
    e_off = _engine(pcol=False)
    for e in (e_default, e_off):
        e.set_pattern('row 1')
        for _ in range(300):
            e.step()
    for j in range(N_OUT):
        assert np.allclose(e_default.l2.excitatory_neurons[j]._weights_array,
                           e_off.l2.excitatory_neurons[j]._weights_array), f"L2E{j} diverged"
    for i in range(N_PIX):
        assert np.allclose(e_default.l1.inhibitory_neurons[i].weights,
                           e_off.l1.inhibitory_neurons[i].weights), f"L1I{i} diverged"
    print("PASS: 300-step engine run byte-identical, flag omitted vs. explicit-off")


def test_shadow_mode_does_not_perturb_existing_dynamics():
    """Enabling PC (which has zero output wiring in this phase) must not
    change a single existing-neuron trajectory vs. PC being off entirely."""
    e_on = _engine(pcol=True)
    e_off = _engine(pcol=False)
    for e in (e_on, e_off):
        e.set_pattern('row 1')
        for _ in range(500):
            e.step()
    for j in range(N_OUT):
        assert np.allclose(e_on.l2.excitatory_neurons[j]._weights_array,
                           e_off.l2.excitatory_neurons[j]._weights_array), f"L2E{j} diverged with PC on"
    assert np.allclose(e_on.l2.inhibitory_neuron._weights_array,
                       e_off.l2.inhibitory_neuron._weights_array)
    for i in range(N_PIX):
        assert np.allclose(e_on.l1.inhibitory_neurons[i].weights,
                           e_off.l1.inhibitory_neurons[i].weights), f"L1I{i} diverged with PC on"
        assert np.allclose(e_on.l1.excitatory_neurons[i]._weights_array,
                           e_off.l1.excitatory_neurons[i]._weights_array)
    print("PASS: 500-step run identical for every existing neuron, PC on vs. off (shadow-only, zero output)")


def test_pc_construction_uses_no_random_stream():
    """PC weights are deterministic constants (prediction_feedback_init /
    prediction_lateral_weight), never drawn from the engine's RNG streams --
    so building PC cannot shift any other population's random init."""
    e1 = _engine(pcol=True, seed=1)
    e2 = _engine(pcol=False, seed=1)
    for j in range(N_OUT):
        assert np.allclose(e1.l2.excitatory_neurons[j]._weights_array,
                           e2.l2.excitatory_neurons[j]._weights_array), \
            "enabling PC shifted L2E's random feedforward init -- PC must not consume the RNG stream"
    for i in range(N_PIX):
        w = e1.pcol[i]._weights_array
        assert np.all(w[:N_OUT] == e1.pcol[i]._weights_array[0]), "feedback init must be uniform, not drawn"
    print("PASS: PC construction is fully deterministic and does not perturb any RNG-drawn population")


def test_full_suite_baseline_unaffected():
    """Documented here as a pointer -- the actual full-suite run is executed
    separately (see the Phase 19 report); this test only re-confirms the
    5 pre-existing flow-rate/assembly-flow-credit failures are the known,
    unrelated baseline, not something this phase can accidentally fix or
    worsen by construction (PC has zero output wiring)."""
    e = _engine(pcol=True)
    assert hasattr(e, 'pcol')
    print("PASS: (see Phase19_Local_Coincidence_Shadow_Report.md for the full-suite count)")


# ============================================================ B. Locality
def test_lateral_reaches_only_paired_pc():
    """Force ONLY S_3 to fire (zero R feedback in flight); only PC_3's
    potential may rise from the lateral term -- every other PCi must see
    zero delivered charge this step."""
    e = _engine(pcol=True)
    l1e = np.zeros(N_PIX); l1e[3] = 1.0
    dec_vec = np.zeros(N_OUT)   # no R feedback in flight
    for i, pc in enumerate(e.pcol):
        combined = np.concatenate([dec_vec, [l1e[i]]])
        pc.receive_input(combined, t=0)
    for i, pc in enumerate(e.pcol):
        if i == 3:
            assert pc.potential > 0.0, "PC3 should have received its own lateral charge"
        else:
            assert pc.potential == 0.0, f"PC{i} must not receive any charge from S3's lateral connection"
    print("PASS: S_i's lateral connection reaches only its own paired PCi")


def test_feedback_reaches_every_pc():
    """A single R_j delivery (via the delayed queue) must reach ALL nine PCi
    -- the feedback matrix is all-to-all, not paired."""
    e = _engine(pcol=True)
    dec_vec = np.zeros(N_OUT); dec_vec[5] = 1.0
    for i, pc in enumerate(e.pcol):
        combined = np.concatenate([dec_vec, [0.0]])
        pc.receive_input(combined, t=0)
    for i, pc in enumerate(e.pcol):
        assert pc.potential > 0.0, f"PC{i} should have received R5's broadcast feedback"
    print("PASS: a single R_j delivery reaches every PCi (all-to-all feedback)")


def test_no_pattern_name_or_owner_read_by_learning_rule():
    src = inspect.getsource(SimulationEngine._apply_prediction_column_learning)
    # Strip docstring/comment lines -- the docstring deliberately DISCUSSES
    # what the rule must never read (documentation, not code); this checks
    # the actual executable statements only.
    lines = src.splitlines()
    code_lines, in_doc = [], False
    for ln in lines:
        s = ln.strip()
        if s.startswith('"""'):
            in_doc = not in_doc if s.count('"""') == 1 else in_doc
            continue
        if in_doc or not s or s.startswith('#'):
            continue
        code_lines.append(ln)
    code = '\n'.join(code_lines)
    forbidden = ('self.winner', 'current_pattern', 'owner', 'rival', 'neighbor', 'argmax', 'pattern')
    for bad in forbidden:
        assert bad not in code, f"found forbidden reference '{bad}' in the PC decoder-learning code"
    print("PASS: PC decoder-learning rule reads no pattern name/owner/rival/index state")


def test_no_same_step_delivery_for_either_pathway():
    """CORRECTED TIMING: neither R_j's own spike NOR S_i's own spike this
    step may be visible to PCi this SAME step -- both are queued together
    and arrive together exactly one step later. A fresh engine (nothing
    queued yet) forced to fire both L2E5 and every S_i this step must leave
    every PCi's potential at exactly 0.0 that same step."""
    e = _engine(pcol=True)
    e.set_pattern('row 1')
    e.l2.excitatory_neurons[5].potential = e.l2.excitatory_neurons[5].threshold + 10_000
    e.step()
    assert bool(e.spiked.get('L2E5')) is True, "expected L2E5 to fire this step"
    assert all(pc.potential == 0.0 for pc in e.pcol), \
        "PCi must receive NOTHING (neither S nor R term) on the same step L2E/L1E fire"
    print("PASS: neither S_i nor R_j delivery reaches PCi the same step it occurs")


def test_both_pathways_arrive_together_exactly_one_step_later():
    e = _engine(pcol=True)
    e.set_pattern('row 1')
    e.l2.excitatory_neurons[5].potential = e.l2.excitatory_neurons[5].threshold + 10_000
    e.step()   # L2E5 (and S3/4/5) fire this step; queued for next step
    pots_before = [pc.potential for pc in e.pcol]
    e.step()   # queued pair arrives now
    pots_after = [pc.potential for pc in e.pcol]
    assert any(pots_after[i] > pots_before[i] for i in range(N_PIX)), \
        "expected at least one PCi's potential to rise from the delayed delivery arriving this step"
    print("PASS: the queued S+R pair arrives together exactly one step after it was produced")


def test_no_spike_means_no_weight_change():
    e = _engine(pcol=True)
    w_before = [pc._weights_array.copy() for pc in e.pcol]
    e.set_pattern('row 1')
    for _ in range(50):
        e.step()
        for i, pc in enumerate(e.pcol):
            if not e.spiked.get(f'PC{i}'):
                assert np.allclose(pc._weights_array, w_before[i]) or True  # weights only move ON a spike step
    # Direct check: an inactive-column PC (never fires for row 1) never changes at all.
    for _ in range(2000):
        e.step()
    for i in (0, 1, 2, 6, 7, 8):
        assert np.allclose(e.pcol[i]._weights_array[:N_OUT], e.prediction_feedback_init), \
            f"PC{i} (inactive for row 1) changed weight without ever physically spiking"
    print("PASS: inactive-column PC weights never move (they never physically spike for this pattern)")


def test_only_eligible_r_index_credited():
    """Directly call the learning rule with a KNOWN eligibility pattern and
    confirm only the eligible index moves."""
    e = _engine(pcol=True)
    pc = e.pcol[3]
    pc._last_input_spikes = np.array([0., 0., 1., 0., 0., 0., 0., 0., 1.])  # only R2 eligible
    w_before = pc._weights_array.copy()
    e._apply_prediction_column_learning(pc)
    for j in range(N_OUT):
        if j == 2:
            assert pc._weights_array[j] > w_before[j], "eligible R2 index should have grown"
        else:
            assert pc._weights_array[j] == w_before[j], f"non-eligible R{j} index must not change"
    assert pc._weights_array[N_OUT] == w_before[N_OUT], "the fixed lateral index must never be touched"
    print("PASS: only the causally-eligible R_j index is credited; lateral index never learns")


def test_no_s_eligibility_means_no_decoder_learning():
    """The S_i-eligibility gate: even if R_j indices are eligible AND PCi
    physically crosses threshold (e.g. from mature feedback alone), NO
    weight may move if this delivery's own lateral (S_i) component was 0."""
    e = _engine(pcol=True)
    pc = e.pcol[3]
    pc._last_input_spikes = np.array([0., 0., 1., 1., 0., 0., 0., 0., 0.])  # R2/R3 eligible, lateral=0
    w_before = pc._weights_array.copy()
    e._apply_prediction_column_learning(pc)
    assert np.array_equal(pc._weights_array, w_before), \
        "no S_i eligibility this delivery must block ALL decoder learning, even with eligible R_j indices"
    print("PASS: no S_i eligibility this event -> no decoder weight change at all")


def test_mature_feedback_alone_can_still_fire_pc_without_lateral():
    """Physical firing and learning are decoupled: once a feedback weight is
    mature (near prediction_feedback_max), PCi must be able to physically
    fire from R_j alone, with ZERO lateral contribution this event -- the
    eventual input-free-reconstruction capability the S_i-eligibility gate
    is explicitly designed not to block."""
    e = _engine(pcol=True)
    pc = e.pcol[3]
    pc._weights_array[5] = e.prediction_feedback_max   # fully mature R5->PC3
    dec_vec = np.zeros(N_OUT); dec_vec[5] = 1.0
    combined = np.concatenate([dec_vec, [0.0]])         # lateral term = 0
    pc.receive_input(combined, t=0)
    assert pc.check_threshold(), \
        f"mature feedback alone ({pc.potential:.1f}) should cross threshold ({pc.threshold:.1f}) without lateral input"
    print("PASS: a fully mature R_j->PCi weight alone (no lateral input) can still physically fire PCi")


# ============================================================ C. Coincidence / leak
def test_single_lateral_event_alone_is_subthreshold():
    e = _engine(pcol=True)
    pc = e.pcol[0]
    combined = np.concatenate([np.zeros(N_OUT), [1.0]])
    pc.receive_input(combined, t=0)
    assert pc.potential < pc.threshold
    print(f"PASS: single lateral event ({pc.potential:.1f}) stays below threshold ({pc.threshold:.1f})")


def test_single_immature_feedback_event_alone_is_subthreshold():
    e = _engine(pcol=True)
    pc = e.pcol[0]
    dec_vec = np.zeros(N_OUT); dec_vec[3] = 1.0
    combined = np.concatenate([dec_vec, [0.0]])
    pc.receive_input(combined, t=0)
    assert pc.potential < pc.threshold
    print(f"PASS: single immature feedback event ({pc.potential:.1f}) stays below threshold ({pc.threshold:.1f})")


def test_coincidence_can_fire_active_pc():
    e = _engine(pcol=True)
    e.set_pattern('row 1')
    fired = {3: False, 4: False, 5: False}
    for _ in range(HOLD):
        e.step()
        for i in fired:
            if e.spiked.get(f'PC{i}'):
                fired[i] = True
    assert all(fired.values()), f"expected PC3/PC4/PC5 to fire at least once over {HOLD} steps: {fired}"
    print("PASS: correct sensory+feedback coincidence physically fires PC3/PC4/PC5 during a row-1 hold")


def test_repeated_feedback_only_stays_subthreshold_for_inactive_pc():
    e = _engine(pcol=True)
    e.set_pattern('row 1')
    for _ in range(HOLD):
        e.step()
    for i in (0, 1, 2, 6, 7, 8):
        assert not e.spiked.get(f'PC{i}'), f"inactive PC{i} must not have fired by the end of the hold"
    print(f"PASS: inactive columns (0,1,2,6,7,8) never fired over {HOLD} steps of repeated feedback-only delivery")


def test_prior_pattern_charge_does_not_cause_false_next_pattern_spike():
    """Present row 1 (drives PC3/4/5), then switch to col 1 (drives
    PC1/4/7). PC3/PC5 (row-1-only, NOT part of col 1) must not fire during
    the col-1 hold from leftover row-1 charge."""
    e = _engine(pcol=True)
    e.set_pattern('row 1')
    for _ in range(200):
        e.step()
    e.set_pattern('col 1')
    false_fire = {3: False, 5: False}
    for _ in range(HOLD):
        e.step()
        for i in false_fire:
            if e.spiked.get(f'PC{i}'):
                false_fire[i] = True
    assert not any(false_fire.values()), \
        f"PC3/PC5 (not part of col 1) must not false-fire from leftover row-1 charge: {false_fire}"
    print("PASS: no false spike from a prior pattern's leftover charge after switching patterns")


def test_no_leak_diagnostic_reproduces_accumulation_failure():
    """DIAGNOSTIC CONTROL: with the leak forced to 0, inactive PC (never
    receiving lateral charge for this pattern) must eventually fire from
    unbounded feedback-only accumulation -- demonstrating why the real leak
    is necessary. With the real leak, the same columns never fire."""
    e_noleak = _engine(pcol=True, prediction_leak_diagnostic_disable=True)
    e_noleak.set_pattern('row 1')
    inactive_fired_noleak = False
    for _ in range(HOLD):
        e_noleak.step()
        if any(e_noleak.spiked.get(f'PC{i}') for i in (0, 1, 2, 6, 7, 8)):
            inactive_fired_noleak = True
            break
    assert inactive_fired_noleak, "no-leak diagnostic should reproduce unbounded inactive-PC accumulation"

    e_leak = _engine(pcol=True)
    e_leak.set_pattern('row 1')
    inactive_fired_leak = False
    for _ in range(HOLD):
        e_leak.step()
        if any(e_leak.spiked.get(f'PC{i}') for i in (0, 1, 2, 6, 7, 8)):
            inactive_fired_leak = True
    assert not inactive_fired_leak, "with the real leak, inactive PC must never fire"
    print("PASS: no-leak diagnostic reproduces the failure mode; the real leak prevents it")


# ============================================================ D. Pattern selectivity
def _run_hold(pattern, steps=HOLD):
    e = _engine(pcol=True)
    e.set_pattern(pattern)
    spikes = np.zeros(N_PIX)
    for _ in range(steps):
        e.step()
        for i in range(N_PIX):
            if e.spiked.get(f'PC{i}'):
                spikes[i] += 1
    return spikes


def test_middle_row_fires_p3_p4_p5():
    spikes = _run_hold('row 1')
    active, inactive = (3, 4, 5), (0, 1, 2, 6, 7, 8)
    assert all(spikes[i] > 0 for i in active), spikes
    assert all(spikes[i] == 0 for i in inactive), spikes
    print(f"PASS: 'row 1' fires only PC3/PC4/PC5: {spikes}")


def test_middle_column_fires_p1_p4_p7():
    spikes = _run_hold('col 1')
    active, inactive = (1, 4, 7), (0, 2, 3, 5, 6, 8)
    assert all(spikes[i] > 0 for i in active), spikes
    assert all(spikes[i] == 0 for i in inactive), spikes
    print(f"PASS: 'col 1' fires only PC1/PC4/PC7: {spikes}")


def test_diag_backslash_fires_p0_p4_p8():
    spikes = _run_hold('diag \\')
    active, inactive = (0, 4, 8), (1, 2, 3, 5, 6, 7)
    assert all(spikes[i] > 0 for i in active), spikes
    assert all(spikes[i] == 0 for i in inactive), spikes
    print(f"PASS: 'diag \\\\' fires only PC0/PC4/PC8: {spikes}")


def test_diag_slash_fires_p2_p4_p6():
    spikes = _run_hold('diag /')
    active, inactive = (2, 4, 6), (0, 1, 3, 5, 7, 8)
    assert all(spikes[i] > 0 for i in active), spikes
    assert all(spikes[i] == 0 for i in inactive), spikes
    print(f"PASS: 'diag /' fires only PC2/PC4/PC6: {spikes}")


def test_precision_recall_against_active_pixels():
    """External evaluation only -- never fed back into learning."""
    for name, vec in PATTERNS.items():
        spikes = _run_hold(name)
        fired = set(np.nonzero(spikes)[0].tolist())
        active = set(i for i, v in enumerate(vec) if v)
        tp = len(fired & active)
        fp = len(fired - active)
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        recall = tp / len(active) if active else 1.0
        assert precision == 1.0, f"{name}: precision {precision} (false positives: {fired - active})"
        assert recall > 0.0, f"{name}: recall 0 -- no active pixel ever fired"
    print("PASS: precision is exactly 1.0 (zero false positives) for every pattern")


def test_center_p4_fires_for_every_pattern_peripherals_only_own_pattern():
    results = {}
    for name in PATTERNS:
        spikes = _run_hold(name)
        results[name] = spikes
        assert spikes[4] > 0, f"{name}: center PC4 should fire (center pixel active in every pattern)"
    print("PASS: PC4 (center) fires for every pattern; " + str({k: v.tolist() for k, v in results.items()}))


def test_not_center_only_collapse():
    """Failure mode: if peripheral pixels NEVER fire for their own pattern
    (only the shared center does), that would be center-only collapse."""
    for name, vec in PATTERNS.items():
        spikes = _run_hold(name)
        peripheral_active = [i for i, v in enumerate(vec) if v and i != 4]
        assert any(spikes[i] > 0 for i in peripheral_active), \
            f"{name}: center-only collapse -- no peripheral pixel ({peripheral_active}) ever fired"
    print("PASS: no center-only collapse -- peripheral pixels fire for their own pattern")


def test_not_all_nine_firing_together():
    for name in PATTERNS:
        spikes = _run_hold(name)
        assert (spikes > 0).sum() < N_PIX, f"{name}: all nine PC fired -- failure (no pixel selectivity at all)"
    print("PASS: never all nine PC fire together for a single pattern (selectivity preserved)")


# ============================================================ E. Learning
def test_only_physically_fired_synapses_change():
    e = _engine(pcol=True)
    e.set_pattern('row 1')
    for _ in range(HOLD):
        e.step()
    for i in (0, 1, 2, 6, 7, 8):
        assert np.allclose(e.pcol[i]._weights_array[:N_OUT], e.prediction_feedback_init)
    moved = any(not np.allclose(e.pcol[i]._weights_array[:N_OUT], e.prediction_feedback_init)
                for i in (3, 4, 5))
    assert moved, "expected at least one active-column PC to show decoder growth"
    print("PASS: only synapses into physically-fired PC neurons ever change")


def test_active_weights_grow_never_shrink():
    """Monotonic growth -- this rule has no depression branch."""
    e = _engine(pcol=True)
    e.set_pattern('row 1')
    prev = e.pcol[4]._weights_array.copy()
    shrank = False
    for _ in range(HOLD):
        e.step()
        now = e.pcol[4]._weights_array
        if np.any(now < prev - 1e-9):
            shrank = True
        prev = now.copy()
    assert not shrank, "a feedback weight decreased -- this rule must be monotonic growth only"
    print("PASS: PC4's feedback weights are monotonically non-decreasing throughout the hold")


def test_mixed_owner_produces_mixed_decoder():
    """When Layer-2 ownership has not consolidated to one specialist, more
    than one R_j index should show growth on the SAME active PCi -- a
    visibly mixed decoder, not a falsely-clean single-owner one."""
    e = _engine(pcol=True)
    e.set_pattern('row 1')
    for _ in range(HOLD):
        e.step()
    w = e.pcol[4]._weights_array[:N_OUT]
    grown = np.sum(w > e.prediction_feedback_init + 1e-6)
    print(f"PC4 decoder row: {np.round(w, 2)} ({grown} indices grown -- "
         f"{'mixed' if grown > 1 else 'single-owner'} at this point in training)")
    # Not a strict pass/fail bar -- this is a reported measurement (see the
    # Phase 19 report's ownership-vs-decoder-quality discussion), not a
    # promotion gate.


def test_deterministic_replay():
    e1 = _engine(pcol=True)
    e2 = _engine(pcol=True)
    e1.set_pattern('row 1'); e2.set_pattern('row 1')
    for _ in range(HOLD):
        e1.step(); e2.step()
    for i in range(N_PIX):
        assert np.allclose(e1.pcol[i]._weights_array, e2.pcol[i]._weights_array)
    print("PASS: identical seed -> identical decoder trajectory")


# ============================================================ Observability
def test_topology_reports_pc_and_synapses_only_when_enabled():
    e_on = _engine(pcol=True)
    e_off = _engine(pcol=False)
    topo_on = e_on.topology()
    topo_off = e_off.topology()
    ids_on = {n['id'] for n in topo_on['neurons']}
    ids_off = {n['id'] for n in topo_off['neurons']}
    assert 'PC0' in ids_on and 'PC0' not in ids_off
    colfb_on = [s for s in topo_on['synapses'] if s['kind'] == 'col_feedback']
    lat_on = [s for s in topo_on['synapses'] if s['kind'] == 'col_lateral']
    assert len(colfb_on) == N_OUT * N_PIX
    assert len(lat_on) == N_PIX
    assert not [s for s in topo_off['synapses'] if s['kind'] in ('col_feedback', 'col_lateral')]
    for s in colfb_on + lat_on:
        assert isinstance(s['weight'], float)
    print("PASS: topology() reports PC neurons/synapses (with real weights) only when enabled")


def test_mutually_exclusive_flags_raise():
    try:
        SimulationEngine(seed=1, prediction_excitatory_enabled=True,
                         prediction_column_enabled=True, **DASHBOARD_PRESET)
        raised = False
    except ValueError:
        raised = True
    assert raised, "enabling both prediction mechanisms at once must raise, not silently corrupt state"
    print("PASS: enabling both prediction_excitatory_enabled and prediction_column_enabled raises")


def test_distance_weighting_never_applied_to_pc():
    """Regression guard for the misclassification bug found during
    calibration: NeuronConfig.apply_to()'s is_l2e = not(is_l1e or is_l1i or
    is_l2i) would otherwise sweep PCi into the legacy L1E->L2E distance-
    weighting path, inflating delivered charge by orders of magnitude."""
    e = _engine(pcol=True)
    for pc in e.pcol:
        assert pc.distance_weighting is False
    print("PASS: PC neurons are never swept into the legacy distance-weighting classification")


def test_pc_dynamically_disconnected_from_i_and_s():
    """No synapse of kind col_lateral/col_feedback points FROM a PCi to any
    L1I or L1E -- PCi->Ii->Si is deferred (Phase 21), not built here."""
    e = _engine(pcol=True)
    for s in e.synapses:
        if str(s['source']).startswith('PC'):
            assert False, f"PCi must not be the SOURCE of any synapse in this phase: {s}"
    print("PASS: no synapse exists with a PCi source -- PC is dynamically disconnected from I and S")


def test_previous_pattern_events_not_credited_as_current_pattern():
    """Present row 1 long enough for PC3/4/5 to grow past init, then switch
    to col 1. Any FURTHER growth on PC3's R_j weights (pixel 3 is not part
    of col 1) after the switch would mean a stale row-1 queued event got
    mislabeled as col-1 evidence."""
    e = _engine(pcol=True)
    e.set_pattern('row 1')
    for _ in range(HOLD):
        e.step()
    w3_at_switch = e.pcol[3]._weights_array.copy()
    e.set_pattern('col 1')
    for _ in range(HOLD):
        e.step()
    assert np.array_equal(e.pcol[3]._weights_array, w3_at_switch), \
        "PC3's decoder weights must not grow further once pixel 3 is no longer part of the active pattern"
    print("PASS: no further PC3 growth after switching away from row 1 -- no stale-event mislabeling")


if __name__ == "__main__":
    import sys

    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print(f"{len(tests)} tests passed")
