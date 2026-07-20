"""Shared helpers for the Phase 35 mature-mechanism efficacy experiment.
Measurement-only: imports and uses the production SimulationEngine exactly
as committed at db30ceadbe18cf90e01f6d54dee0203f342b24a8. Nothing here
modifies backend/simulation.py or snn/dendrite.py.
"""
import copy
import sys

PROJ = "/tmp/claude-275450548/-home-cxiong-others-cipp-learning-AbhiCIPP/55d19a97-a1ec-436c-ada9-dbb060f69996/scratchpad/phase35-mature-efficacy-clone/cipp-learning-AbhiCIPP"
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

import numpy as np
from backend.simulation import SimulationEngine, N_OUT, N_PIX, PATTERNS

MATURITY = 350.0  # emergent boundary: prediction_threshold(500) - prediction_lateral_weight(150)
MAX_STAGE1_HORIZON = 20000  # documented, calibration-derived (see calibration_log.txt):
                             # 3 pilot seeds all matured between 5000-10000 steps; this is
                             # 2-4x that with margin, while staying well under a minute of
                             # wall-clock at ~750 steps/sec.

STAGE1_KW = dict(
    prediction_column_enabled=True,          # Phase 35 decoder/coincidence learning ON
    prediction_column_to_i_enabled=False,    # physical PC-to-local-I suppression OFF
    prediction_leak_diagnostic_disable=True, # passive (PCi soma) decay OFF
    loser_depression=False,                  # loser depression OFF
    l2e_budget=False,                        # global (sum-renormalization) normalization OFF
)


def active_pixels(pattern_name):
    return sorted(i for i, v in enumerate(PATTERNS[pattern_name]) if v)


def decoder_totals(e, active):
    return np.array([sum(e.pcol[i].decoder_weights[j] for i in active) for j in range(N_OUT)])


def find_leader(e, active):
    totals = decoder_totals(e, active)
    order = np.argsort(-totals)
    top, second = totals[order[0]], totals[order[1]]
    tied = bool(np.isclose(top, second, atol=1e-6))
    return int(order[0]), tied, totals


def full_decoder_snapshot(e):
    """decoder_weights for every PC, every source -- used to confirm
    inactive (pixel, source) pairs never change."""
    return np.array([[pc.decoder_weights[j] for j in range(N_OUT)] for pc in e.pcol])


def run_stage1(seed, pattern="row 1", max_horizon=MAX_STAGE1_HORIZON):
    """Run one held-pattern presentation, tracking natural maturation, checked
    every engine step (cheap: this is a 9x8 float compare, not a full sim
    step). Returns a results dict; if matured, result['engine'] holds the
    live engine at the qualifying checkpoint step."""
    active = active_pixels(pattern)
    inactive = [i for i in range(N_PIX) if i not in active]
    e = SimulationEngine(seed=seed, **STAGE1_KW)
    e.set_pattern(pattern)

    initial_snapshot = full_decoder_snapshot(e)
    responder_history = []
    matured_step = None
    per_pixel_maturity_step = {i: None for i in active}
    first_pc_spike_after_maturity = None
    leader = None
    update_events = {i: 0 for i in active}
    prev_weights = {i: e.pcol[i].decoder_weights[:] for i in active}
    stale_classes = {}

    step = 0
    for step in range(1, max_horizon + 1):
        e.step()
        cur_leader, tied, totals = find_leader(e, active)
        if leader != cur_leader:
            responder_history.append((step, cur_leader, tied))
            leader = cur_leader
        # count qualifying decoder-update events for the CURRENT leader at
        # each active pixel (any increase this step counts as one event)
        for i in active:
            w_now = e.pcol[i].decoder_weights
            for j in range(N_OUT):
                if w_now[j] > prev_weights[i][j] + 1e-12:
                    update_events[i] += 1 if j == cur_leader else 0
            prev_weights[i] = w_now[:]
        # track origin_class telemetry (should be current-correct throughout
        # Stage 1 -- no pattern switch has happened yet)
        for rec in e.dynamic_state()['prediction_column'].get('last_deliveries', []):
            stale_classes[rec['origin_class']] = stale_classes.get(rec['origin_class'], 0) + 1
        per_pixel = [e.pcol[i].decoder_weights[cur_leader] for i in active]
        for i, w in zip(active, per_pixel):
            if w >= MATURITY and per_pixel_maturity_step[i] is None:
                per_pixel_maturity_step[i] = step
        if all(v is not None for v in per_pixel_maturity_step.values()) and matured_step is None:
            matured_step = step
        if matured_step is not None and first_pc_spike_after_maturity is None:
            for i in active:
                if e.spiked.get(f'PC{i}'):
                    first_pc_spike_after_maturity = (step, i)
                    break
        if matured_step is not None and first_pc_spike_after_maturity is not None:
            break

    reached = matured_step is not None
    final_snapshot = full_decoder_snapshot(e)
    inactive_unchanged = True
    inactive_diffs = []
    if reached:
        for i in inactive:
            for j in range(N_OUT):
                if abs(final_snapshot[i, j] - initial_snapshot[i, j]) > 1e-9:
                    inactive_unchanged = False
                    inactive_diffs.append((i, j, float(initial_snapshot[i, j]), float(final_snapshot[i, j])))

    result = dict(
        seed=seed, pattern=pattern, active_pixels=active, inactive_pixels=inactive,
        reached_maturity=reached,
        matured_step=matured_step,
        per_pixel_maturity_step=per_pixel_maturity_step,
        responder_history=responder_history,
        final_leader=leader,
        final_tied=find_leader(e, active)[1],
        final_totals=decoder_totals(e, active).tolist(),
        decoder_update_events=update_events,
        stale_classification_counts=stale_classes,
        inactive_pixels_unchanged=inactive_unchanged,
        inactive_pixel_diffs=inactive_diffs,
        first_pc_spike_after_maturity=first_pc_spike_after_maturity,
        steps_run=step,
    )
    return result, (e if reached else None)


def _clone_pc(pc, memo):
    """CoincidencePyramidalCell.__getattr__ delegates any unknown attribute
    to self.soma (snn/dendrite.py ~line 157-158). copy.deepcopy's default
    reduce/reconstruct protocol probes a partially-built, attribute-less
    instance with hasattr(y, '__setstate__') before any attribute is set;
    that probe falls into __getattr__, which itself tries self.soma (also
    unset), which falls into __getattr__ again -- infinite recursion
    (confirmed empirically: RecursionError, ~986 frames, when this instance
    is passed through plain copy.deepcopy). This is a genuine property of
    the reviewed class, not a mistake in this harness -- documented in
    report.md. Worked around here, without touching snn/dendrite.py, by
    cloning via __dict__ directly (object.__new__ + per-field deepcopy),
    which never triggers attribute lookup on an incomplete instance."""
    if id(pc) in memo:
        return memo[id(pc)]
    new = object.__new__(type(pc))
    memo[id(pc)] = new
    for k, v in vars(pc).items():
        new.__dict__[k] = copy.deepcopy(v, memo)
    return new


def clone_engine(engine):
    """Full independent deep copy of a SimulationEngine, correct in the
    presence of CoincidencePyramidalCell's __getattr__ trap. self.pcol and
    self.neurons both hold references to the SAME PC objects (backend/
    simulation.py line 1814: self.neurons[nid] = self.pcol[i]) -- clone
    pcol's cells first and seed a shared memo so every other path to the
    same object (self.neurons, telemetry closures, etc.) resolves to the
    identical clone rather than a divergent duplicate."""
    memo = {}
    if getattr(engine, "prediction_column_enabled", False):
        for pc in engine.pcol:
            _clone_pc(pc, memo)
    new = object.__new__(type(engine))
    memo[id(engine)] = new
    for k, v in vars(engine).items():
        new.__dict__[k] = copy.deepcopy(v, memo)
    return new


def verify_engine_independence(engine):
    """Prove B/C clones share no mutable state before trusting their
    divergence to the flag difference. Returns (ok, detail)."""
    b = clone_engine(engine)
    c = clone_engine(engine)
    b_before = summarize_engine(b)
    c_before = summarize_engine(c)
    b.step()
    b_after = summarize_engine(b)
    c_after = summarize_engine(c)
    ok = (c_before == c_after) and (b_before != b_after)
    detail = dict(c_unchanged=(c_before == c_after), b_changed=(b_before != b_after))
    return ok, detail


def summarize_engine(e):
    parts = []
    parts.append(tuple(sorted(e._all_weights().items())))
    parts.append(e.timestep)
    parts.append(tuple(sorted(e.spiked.items())) if hasattr(e, 'spiked') else None)
    if e.prediction_column_enabled:
        parts.append(tuple(tuple(pc.decoder_weights) for pc in e.pcol))
        parts.append(tuple(pc.basal_connection.weight for pc in e.pcol))
    return tuple(parts)


def make_bc(checkpoint_engine):
    """Build B (shadow: PC spikes occur, PC->I delivery disabled) and
    C (active: PC->I delivery enabled) as independent deep copies of the
    naturally-matured checkpoint.

    Structural note (documented, not a code change): prediction_column_to_i_
    enabled controls L1I's incoming-weight-vector SHAPE at build time
    (l1i_n_feedback = 1 if enabled else N_OUT -- backend/simulation.py
    ~line 1134). The checkpoint was built with the flag off (Stage 1 never
    touches it), so every L1I neuron's weight vector is N_OUT-dimensional.
    B keeps that shape (the flag stays off). For C, flipping the flag post-
    clone would leave a 1-element delivery (`np.array([pcol_spiked[i]])`)
    hitting an N_OUT-dimensional weight vector -- a real shape mismatch, not
    a semantic choice. There is no way to recover "the value the engine
    would have drawn at construction" after the fact (that draw consumes a
    different number of RNG samples for a differently-shaped array), so
    rather than inventing a new random value, C's L1I weight is collapsed to
    the MEAN of the checkpoint's own existing N_OUT-dimensional vector for
    each L1I neuron -- the one summary statistic that uses only real,
    already-determined values from this specific run, applied identically
    and mechanically to all 9 L1I neurons and to every seed. Nothing else
    about L1I (its own learning_rate, threshold, leak) is touched; L1I
    keeps learning normally from this point on. This is the only deviation
    from a pure attribute flip in this experiment.
    """
    b = clone_engine(checkpoint_engine)
    c = clone_engine(checkpoint_engine)
    b.prediction_column_to_i_enabled = False
    c.prediction_column_to_i_enabled = True
    l1i_reshape_log = []
    for i, inh in enumerate(c.l1.inhibitory_neurons):
        old = inh.weights.copy()
        new_val = float(np.mean(old))
        inh.weights = np.array([new_val])
        l1i_reshape_log.append(dict(l1i_index=i, old_shape=list(old.shape),
                                    old_values=old.tolist(), new_value=new_val))
    return b, c, l1i_reshape_log


def collect_metrics(e, active_expected, novel_pixels, window_steps):
    """Roll a metrics accumulator forward `window_steps` engine steps on a
    live engine, recording everything the task's metric list asks for."""
    m = dict(
        pc_spikes={f'PC{i}': 0 for i in range(N_PIX)},
        l1i_events=0,
        l1e_expected_fires=0, l1e_expected_opportunities=0,
        l1e_novel_fires=0, l1e_novel_opportunities=0,
        l2e_fires={f'L2E{j}': 0 for j in range(N_OUT)},
        multi_winner_steps=0,
        stale_counts={},
        decoder_snapshot_before=full_decoder_snapshot(e).tolist(),
    )
    for _ in range(window_steps):
        e.step()
        for i in range(N_PIX):
            if e.spiked.get(f'PC{i}'):
                m['pc_spikes'][f'PC{i}'] += 1
        if e.prediction_column_to_i_enabled:
            m['l1i_events'] += sum(1 for i in range(N_PIX) if e.spiked.get(f'PC{i}'))
        winners_this_step = [j for j in range(N_OUT) if e.spiked.get(f'L2E{j}')]
        for j in winners_this_step:
            m['l2e_fires'][f'L2E{j}'] += 1
        if len(winners_this_step) > 1:
            m['multi_winner_steps'] += 1
        for i in range(N_PIX):
            fired = bool(e.spiked.get(f'L1E{i}'))
            if i in active_expected:
                m['l1e_expected_opportunities'] += 1
                m['l1e_expected_fires'] += int(fired)
            elif i in novel_pixels:
                m['l1e_novel_opportunities'] += 1
                m['l1e_novel_fires'] += int(fired)
        for rec in e.dynamic_state()['prediction_column'].get('last_deliveries', []):
            m['stale_counts'][rec['origin_class']] = m['stale_counts'].get(rec['origin_class'], 0) + 1
    m['decoder_snapshot_after'] = full_decoder_snapshot(e).tolist()
    return m
