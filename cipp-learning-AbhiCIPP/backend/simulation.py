"""
SimulationEngine -- steppable wrapper around the spiking network.

Spikes are delivered immediately except for L1I feedback, which is held in a
one-step register so a spike at t suppresses its paired L1E at t+1. Every neuron
has a 3D position for display; the L2 positions in L2_HOMES remain so the layout
is meaningful in the viewport, but they do not imply a conduction delay.

Learning architecture:
  - L1E neurons are treated as pre-trained pixel encoders: weights are fixed
    at [-1.0, 1.0] and learning_rate = 0.  They fire whenever the external
    pixel is active and they are not suppressed by their paired L1I neuron.
  - L2E neurons use signed input-spike learning by default. Active pixel gates
    potentiate, inactive pixel gates depress, and there is no positive weight
    budget on this path.
  - L1I / L2I incoming excitatory weights have no budget. Each gate is capped at
    its inhibitory neuron's own threshold, and both inhibitory thresholds share
    the L2I scale by default.
  - L1I is a trainable accumulator by default. Every L1I observes the same L2E
    winner stream, so the bank starts from copies of one random, task-independent
    feedback vector. Independent vectors create arbitrary pixel phase classes
    without any pixel-local signal that can repair them.
  - L1I credits every L2E contributor in its accumulation window, not only the
    final threshold-crossing winner. Its effective one-step refractory interval
    prevents consecutive feedback pulses. With constant input this converges to
    a synchronized fire/suppress rhythm that halves active L1E frequency.

L2I supplies learned lateral inhibition to the competing L2E pool. L1I supplies
paired feedback inhibition to L1E through the delayed register. Membrane leak is
independently configurable for L2E, L2I, and L1I and is off for all three by
default.
"""

from __future__ import annotations

import os
import sys
from collections import deque, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from layers import InputLayer                       # noqa: E402
from cortical_column_flexible import CorticalColumn  # noqa: E402
from neuron_flexible import UNIT, LEAK_SCALE, Neuron  # noqa: E402  fixed-point convention
from snn import CoincidencePyramidalCell, NeuronConfig  # noqa: E402
from snn.rules.delivery import effective_weights  # noqa: E402


PATTERNS = {
    'row 1':    [0, 0, 0, 1, 1, 1, 0, 0, 0],
    'col 1':    [0, 1, 0, 0, 1, 0, 0, 1, 0],
    'diag \\':  [1, 0, 0, 0, 1, 0, 0, 0, 1],
    'diag /':   [0, 0, 1, 0, 1, 0, 1, 0, 0],
}

# Held-out PROBES (observability only): the four non-center-crossing row/column
# lines. These are NEVER trained -- auto-cycle's _cycle_order is built from
# PATTERNS.keys() only (see _build), so a probe can never enter the training
# rotation. present_probe() shows one for a presentation-scoped, plasticity-
# FROZEN window (see Neuron.plasticity_frozen) so the network's real physical
# response to an unseen line is observable without teaching it anything.
# PATTERNS and PROBES share the same one-hot 3x3 encoding; a name is a key into
# exactly one of the two dicts, never a neuron index.
PROBES = {
    'row 0': [1, 1, 1, 0, 0, 0, 0, 0, 0],
    'row 2': [0, 0, 0, 0, 0, 0, 1, 1, 1],
    'col 0': [1, 0, 0, 1, 0, 0, 1, 0, 0],
    'col 2': [0, 0, 1, 0, 0, 1, 0, 0, 1],
}

# Shared pattern metadata: single source of truth for "is this name trained or
# held-out", used by the engine, the API layer, and the frontend (via
# topology()'s pattern_roles) so no caller re-derives or hardcodes the split.
PATTERN_ROLE = {**{name: 'train' for name in PATTERNS}, **{name: 'probe' for name in PROBES}}

# How long a neuron's spike history keeps it counted as "active" for the
# evidence-based receptive-field status (see _l2e_status) -- a few presentation
# windows' worth, not a single step.
STATUS_RECENT_WINDOW = 200

# Four center-crossing input primitives, but the L2E pool is DECOUPLED from the
# pattern count: N_OUT L2E neurons compete over len(PATTERNS) inputs. With N_OUT=8
# and 4 patterns that is 2x overcapacity -- multiple neurons vie for each pattern, so
# competition/recruitment dynamics (who wins, who differentiates, who dies) are
# visible. N_OUT sizes the L2E layer and everything downstream (ring, feedback fan-in,
# L1I afferents); PATTERNS is cycled by NAME and never indexes a neuron, so the two
# are independent.
N_PIX = 9
N_OUT = 8
PRED_CONTROL_NORMAL = 'normal'
PRED_CONTROL_DISABLED = 'disabled'
PRED_CONTROL_SHUFFLED = 'shuffled'
PREDICTION_CONTROL_MODES = (
    PRED_CONTROL_NORMAL,
    PRED_CONTROL_DISABLED,
    PRED_CONTROL_SHUFFLED,
)

# 3D layout for the L2 output neurons -- evenly spaced ring in the XY plane.
import math as _math
_R, _Z = 3.2, 4.0
L2_HOMES = [
    (round(_R * _math.cos(k * 2 * _math.pi / N_OUT), 4),
     round(_R * _math.sin(k * 2 * _math.pi / N_OUT), 4),
     _Z)
    for k in range(N_OUT)
]

GRID = 2.2

# ---- Phase 3: seeded, engine-owned geometry (jittered/irregular placement) ----
# Brief SS6: a perfect L2E grid/circle gives near-identical geometric influence
# to every neuron and defeats distance-based symmetry breaking; L1 neurons
# should be jittered within their assigned spatial cells rather than sitting at
# exact grid points. This adds a SEEDED alternative to the deterministic
# ring/grid above, selectable via `symmetric_geometry` (default True: EVERY
# existing caller/test that doesn't pass it gets the exact legacy positions,
# byte-identical). `L2_HOMES` and the legacy pixel-grid formula are kept
# exactly as they were -- they remain both the `symmetric_geometry=True`
# position source AND the fixed reference geometry `legacy_distance_compat`
# uses (see _apply_l2e_distances).
#
# TEMPORARY COMPATIBILITY SHIM (Phase 3 only, always on by default): even when
# `symmetric_geometry=False` (irregular geometry is what's placed/rendered),
# `legacy_distance_compat=True` makes the DELIVERY distances that feed
# distance_weighting keep coming from the LEGACY ring/grid reference geometry,
# not the real new positions -- so today's distance_weighting=True dynamics
# stay numerically identical regardless of which geometry is on screen. This
# is a deliberate, explicitly labeled placeholder: topology()'s `geometry`
# block reports it so nothing presents these pinned numbers as if they were
# computed from the visible (possibly jittered) coordinates. Phase 4 removes
# this shim and lets distance/influence follow the real new geometry.
L1_JITTER_FRAC = 0.30         # max L1E offset from its cell center, as a fraction of GRID
L1I_PAIR_JITTER_FRAC = 0.12   # small additional L1I offset from its paired L1E's (x,y)
L2E_PLACEMENT_RADIUS = 3.6    # bounding disk radius for irregular L2E placement (z fixed at _Z)
L2E_MIN_SEPARATION = 1.3      # minimum enforced pairwise Euclidean distance between L2E homes
L2E_PLACEMENT_MAX_TRIES = 20000     # rejection-sampling attempts per restart
L2E_PLACEMENT_MAX_RESTARTS = 50     # full-restart budget (placement is generous; should never exhaust)


def _legacy_l1_xy():
    """Deterministic legacy L1E/pixel-grid (x,y) positions -- no jitter. This
    is both the `symmetric_geometry=True` position source and the fixed
    reference geometry `legacy_distance_compat` uses, regardless of which
    placement mode is actually active. Returns an (N_PIX,2) array."""
    pos = np.zeros((N_PIX, 2))
    for i in range(N_PIX):
        r, c = divmod(i, 3)
        pos[i] = ((c - 1) * GRID, (1 - r) * GRID)
    return pos


def _jittered_l1e_xy(rng):
    """Seeded jitter for the 9 L1E positions, each confined to its OWN 3x3
    spatial cell (brief SS6: a neuron must not cross into another sensory
    region, or it would change which spatial pattern it represents). Offset
    magnitude (L1_JITTER_FRAC * GRID = 0.66) stays well inside the half-GRID
    (1.1) cell boundary. Returns an (N_PIX,2) array."""
    base = _legacy_l1_xy()
    max_off = L1_JITTER_FRAC * GRID
    return base + rng.uniform(-max_off, max_off, size=base.shape)


def _paired_l1i_xy(rng, l1e_xy):
    """Each L1I sits NEAR its paired L1E (same pixel index) with a small
    independent offset (brief SS6: 'near the paired L1E unit ... with a small
    offset', not a literal coincident overlap). The added offset
    (L1I_PAIR_JITTER_FRAC * GRID = 0.264) keeps L1I within the same cell as
    its L1E even at L1E's maximum jitter (0.66 + 0.264 = 0.924 < 1.1)."""
    max_off = L1I_PAIR_JITTER_FRAC * GRID
    return l1e_xy + rng.uniform(-max_off, max_off, size=l1e_xy.shape)


def _irregular_l2e_xy(rng):
    """Seeded rejection-sampling placement of the N_OUT L2E homes inside a
    bounded disk (brief SS6: 'randomly placed within a bounded cortical-column
    region', 'enforce minimum separation', 'do not place them ... at equal
    angles or equal radii'). Returns an (N_OUT,2) array; raises if the
    constants can't be satisfied (a build-time configuration error, not a
    runtime/per-step concern)."""
    for _restart in range(L2E_PLACEMENT_MAX_RESTARTS):
        pts: list[np.ndarray] = []
        tries = 0
        while len(pts) < N_OUT and tries < L2E_PLACEMENT_MAX_TRIES:
            tries += 1
            r = L2E_PLACEMENT_RADIUS * np.sqrt(rng.uniform(0.0, 1.0))
            theta = rng.uniform(0.0, 2 * np.pi)
            cand = np.array([r * np.cos(theta), r * np.sin(theta)])
            if all(np.linalg.norm(cand - p) >= L2E_MIN_SEPARATION for p in pts):
                pts.append(cand)
        if len(pts) == N_OUT:
            return np.array(pts)
    raise RuntimeError(
        f"could not place {N_OUT} L2E neurons with min separation "
        f"{L2E_MIN_SEPARATION} inside radius {L2E_PLACEMENT_RADIUS} after "
        f"{L2E_PLACEMENT_MAX_RESTARTS} restarts -- loosen the placement constants")


# ---- Phase 4: per-connection distance/influence, audited separately per pathway ----
# Brief SS7: influence must be exposed per-connection (source, target, distance,
# influence, raw weight, effective transmission) and applied EXACTLY ONCE --
# never once in delivery and again in learning. This adds FOUR NEW, fully
# independent experimental pathways -- L2E->L2I, L2I->L2E, L2E->L1I, L1I->L1E
# -- each with its OWN ablation flag, ALL DEFAULT OFF, sharing ONE configurable
# power law that is DELIBERATELY SEPARATE from the legacy L1E->L2E pathway
# (distance_weighting/distance_power/distance_ref/distance_min/
# legacy_distance_compat -- Phase 2/3, left completely UNCHANGED by this
# section; that remains the "legacy-distance baseline"). "Do not enable every
# pathway together": DASHBOARD_PRESET leaves all four new flags OFF -- this is
# deliberately isolated, one-pathway-at-a-time experimental infrastructure, not
# a new default behavior. The "geometry-off" baseline (distance_weighting=False
# and every infl_* flag False) and the "legacy-distance" baseline
# (distance_weighting=True, legacy_distance_compat=True) are both fully
# preserved -- nothing in this section touches either one.
INFLUENCE_SAFE_MAX = 4.0   # reporting/safety ceiling; the DEFAULT law (ref==min)
                          # never approaches this (max influence == 1.0 exactly)


def _power_law_influence(d, ref, d_min, power):
    """influence = (ref / max(d, d_min)) ** power. With the DEFAULT ref==d_min,
    this is a pure ATTENUATION law: influence <= 1.0 for every d >= d_min,
    never amplifying -- "avoid extreme amplification" as a structural default,
    not merely a clip. Vectorized (accepts a scalar or an ndarray)."""
    dd = np.asarray(d, dtype=float)
    return (float(ref) / np.maximum(dd, float(d_min))) ** float(power)


def _summarize_pathway(entries: list[dict]) -> dict:
    """min/median/max influence + a `safe` flag (brief: "avoid extreme
    amplification") for one pathway's per-connection entries."""
    infl = [e['influence'] for e in entries]
    return dict(entries=entries,
               influence_min=round(min(infl), 4) if infl else None,
               influence_median=round(float(np.median(infl)), 4) if infl else None,
               influence_max=round(max(infl), 4) if infl else None,
               safe=(max(infl) <= INFLUENCE_SAFE_MAX) if infl else True)


# Active L2E fan-in: exactly N_PIX pixel afferents. There is NO index-0 local-I
# placeholder and no negative L2I->L2E gate -- L2 competition is a causal,
# delayed L2E->L2I->L2E event (Phase 7) plus local competitive depression (see
# Neuron.apply_delayed_inhibition and L2_Hard_Reset_Competitive_Depression_Spec.md).
L2E_FANIN = N_PIX
FREQ_WINDOW = 40
WEIGHT_EPS = 1e-6
LOG_MAX = 400

# ---- Phase 6: representation candidate == first physical L2E threshold
# crossing (brief SS8-9). RETIRED (was here through Phase 5): the "episode"
# window (EPISODE_QUIET_K/EPISODE_MAX_LEN, _update_episode/_resolve_episode)
# that resolved self.winner via LATEST-spike-wins from grouped spike history.
# That was the Phase 1 audit's headline conflict with the brief ("the
# dashboard's exposed winner is latest-spike-wins, not first-spike-wins").
# self.winner is now set directly in _track_presentation() the moment the
# presentation's first physical L2E spike occurs (never re-derived by argmax/
# index/charge/geometry/UI logic), and stays None for the rest of that
# presentation if that first response was a same-step tie (earliestResponseSet
# has >1 member) -- an ambiguous same-step set gets no winner-specific credit.
# Nothing else depended on the episode fields (confirmed: not read by any
# test, script, or frontend file), so they were removed rather than left
# as unused dead code alongside the new mechanism.

# L2 lateral inhibition ("adaptive gate") parameters. Competition in L2 is
# produced by the shared inhibitory neuron L2I suppressing near-winners through
# the L2I->L2E synapse, NOT by a procedural hard reset. Each L2E owns one gate
# from L2I whose strength is learned by the inhibitory-plasticity rule
# (Neuron.apply_inhibition): it grows when it suppresses a neuron that was close
# to firing and saturates at L2_GATE_WMAX. These values were chosen by a
# parameter sweep (see the competition investigation) as the point giving the
# broadest participation with the most per-pattern differentiation; crucially
# L2_GATE_WMAX < thr_l2 so a saturated gate can't fully reset the membrane.
#
# FIXED-POINT SCALE (see neuron_flexible.py): the model runs at the
# UNIT-scaled fixed-point scale, so thresholds are the integers 1000 / 8000 and
# all charge-like magnitudes are scaled by UNIT. Scaling rules by role:
#   - LINEAR magnitudes (gate init, potentials, weights, clips) scale by UNIT.
#   - the learning rate eta scales by UNIT (dw must scale with w).
#   - the QUADRATIC saturation denominator w_max in dw = eta*p*(1 - w^2/w_max)
#     scales by UNIT**2, because w^2 scales by UNIT**2. The gate MAGNITUDE still
#     settles at its natural equilibrium sqrt(w_max) = UNIT*sqrt(1.5) ~= 1225,
#     which is still well below thr_l2 = 8000 -- the "< threshold, partial
#     discharge" property is preserved; only the numeric denominator is large.
L2_GATE_INIT = -500          # initial gate magnitude 500 == 0.5 * UNIT (linear)
L2_GATE_WMAX = 1500 * UNIT   # quadratic w_max == 1.5 * UNIT**2; equilibrium sqrt ~= 1225 (< thr_l2)
L2_GATE_ETA = 100            # inhibitory-plasticity eta == 0.1 * UNIT (scales with charge)

# L2E->L2I "assembly evidence" synapses.
#
# Two regimes, by design, not by accident:
#   EARLY in training, no single L2E->L2I synapse is anywhere near enough on
#   its own (see L2_EI_WEIGHT_INIT_LOW/_HIGH_FRAC: the random init range is
#   well below threshold_l2), so L2I only fires once several distinct L2E neurons
#   have spiked within its short retention window (L2I_LEAK_RATE). This is
#   what produces the initial "round robin": no one source is trusted yet, so
#   competition is decided by population consensus, not a single vote.
#   OVER TRAINING, the L2E->L2I weights are NOT budgeted (weight_budget=None,
#   homeostasis off for L2I) and each synapse's cap is the neuron's OWN
#   threshold_l2 (not a fixed sub-threshold ceiling) -- so as the existing,
#   unmodified Hebbian rule repeatedly credits the synapse from whichever L2E
#   habitually wins (and therefore habitually co-occurs with L2I's discharge
#   cycle: L2E fires -> L2I fires -> that L2E gets inhibited, repeat), that
#   one synapse can grow all the way up to threshold_l2 and become
#   sufficient on its own: once it has, a single spike from that specific,
#   now-trusted source fires L2I immediately, matching L2E's own transition
#   from many-volley LIF accumulation to single-volley pattern-integrator
#   firing (see the module docstring). The temporal-integration REQUIREMENT
#   (multiple contributors) is therefore a property of an undertrained
#   synapse, not a permanent structural ceiling -- see L2I_Temporal_Integration.md
#   for the original (now superseded) design that made it permanent.
# L2I_LEAK_RATE is still much faster than leak_l2 (L2E's slow, many-volley
# accumulator): L2I needs a SHORT retention window so that only spikes from
# roughly the same "burst" of population activity sum together while the
# synapses are still weak, while isolated single-neuron spikes decay away
# before a second volley's worth of unrelated evidence could pad them out.
#
# The init range is expressed as a FRACTION of threshold_l2, not an absolute
# constant, because the achievable ceiling of the round-robin phase depends on
# both together: with volley-spaced contributions decaying by r=(1-leak)^4
# per gap, n same-size contributions sum to at most w/(1-r) as n -> infinity
# (a geometric series). With L2I_LEAK_RATE=0.07, r=(0.93)^4~=0.748, so that
# ceiling is w/0.252 ~= 3.97*w -- population consensus can only ever ratchet
# threshold_l2 to just under 4*(the init weight), REGARDLESS of how many
# volleys pass. The mean init weight must therefore scale with threshold_l2
# (not stay fixed) or raising the threshold alone can make the ceiling fall
# below threshold_l2, at which point L2I could never fire at all via the
# round-robin route -- and since L2I's own E->I weights only update on ITS
# OWN fire, it would then never learn either (a silently dead network, not
# merely a slow one). [0.25, 0.5] * threshold_l2 keeps the same relative
# dynamics validated in L2I_Temporal_Integration.md (a single contribution at
# ~37.5% of threshold; 4 volley-spaced contributions needed to cross) at
# whatever threshold_l2 is actually configured to.
# Init fractions as integer rationals (1/4, 1/2) per the fixed-point convention.
L2_EI_WEIGHT_INIT_LOW_FRAC = 1 / 4   # low end of the random E->I init range,
L2_EI_WEIGHT_INIT_HIGH_FRAC = 1 / 2  # high end -- both as a fraction of threshold_l2.
                                     # The LEARNING ceiling is threshold_l2 itself
                                     # (see the per-neuron cap assignment below),
                                     # not this range -- this is an INITIAL value only.
L2I_LEAK_RATE = 70 / LEAK_SCALE      # L2I's own membrane/trace leak (>> leak_l2); 70/1000 == 0.07

# L2E->L1I feedback weights (the "quiet the inputs" loop). Governed by
# EXACTLY the same two-regime "assembly evidence" policy as L2E->L2I above,
# scaled to L1I's own threshold on the L2I scale -- L1I was
# previously an instant integrator from t=0 (every synapse initialized
# at-or-above its own threshold, so a single L2E spike always fired it
# immediately, with no round-robin phase and nothing left for the existing
# Hebbian rule to actually move). Now: synapses start randomly in
# [0.25, 0.5] * thr_l1i (L1_EI_WEIGHT_INIT_LOW/_HIGH_FRAC -- same fractions as
# L2I, so the same relative dynamics apply: ~37.5% of threshold from one
# spike, 4 volley-spaced spikes needed to cross), are NOT weight-budgeted,
# and are individually capped at thr_l1i itself, so a habitually-participating
# source can learn its way up to full self-sufficiency exactly like L2I does.
# L1I_LEAK_RATE (== L2I_LEAK_RATE numerically, kept as its own named constant
# since it governs a different neuron) gives the same ~1.49x reachable-ceiling
# headroom above threshold that L2I_LEAK_RATE gives L2I -- see the
# L2_EI_WEIGHT_INIT_LOW_FRAC note above for the derivation (it is scale-free:
# depends only on the weight/threshold fraction and the leak rate, not the
# absolute threshold value, so the identical fractions and leak rate carry
# over unchanged at any shared L2I/L1I threshold scale).
L1_EI_WEIGHT_INIT_LOW_FRAC = 1 / 4   # low end of the random L2E->L1I init range,
L1_EI_WEIGHT_INIT_HIGH_FRAC = 1 / 2  # high end -- both as a fraction of thr_l1i.
                                      # Learning ceiling is thr_l1i itself (see the
                                      # per-neuron cap assignment below), not this.
L1I_LEAK_RATE = 70 / LEAK_SCALE      # L1I's own membrane/trace leak (>> leak_l1); 70/1000 == 0.07
# fire() is followed by update() in the same outer step, so a timer of 2 counts
# down to 1 immediately and blocks exactly the following step. This prevents
# consecutive feedback pulses and sets the trained constant-drive rhythm to 2:1.
L1I_FEEDBACK_REFRACTORY = 2

# Learning rate for the charge-based excitatory rule (Neuron._update_weights),
# used by every positive-weight population: L1I's incoming weights, L2I's
# incoming weights, and L2E's feedforward weights. Expressed as a FRACTION of
# each neuron's OWN weight_cap (learning_rate = ETA_FRAC * weight_cap), not a
# shared absolute constant -- with an absolute constant, L1I (cap=thr_l1=1)
# and L2I (cap=threshold_l2=8) would take a wildly different NUMBER OF EVENTS
# to reach self-sufficiency even though they're meant to behave with the same
# relative pace (this was the actual cause of L1I "training too fast" /
# L2I's weights climbing too high: same absolute dw per event, an 8x smaller
# target). Scaling eta by weight_cap makes the FRACTIONAL growth per event
# (dw/w_max) independent of the neuron's absolute scale.
#
# ETA_FRAC=0.01 was chosen by simulating the saturating recursion
# f_{n+1} = f_n + ETA_FRAC*p*(1-f_n^2) (f = w/w_max) from the init-range
# midpoint (f=0.375) with a representative p~=0.6: it takes ~180 events for a
# habitually-participating synapse to reach 90% of its own cap -- a genuinely
# long "gatling gun" round-robin phase, not a handful of volleys. See
# Weight_Update_Unification.md for the full derivation and validation.
ETA_FRAC = 0.01

# Floor for L2E's feedforward (positive) weights after budget renormalization
# (see min_positive_weight in Neuron._apply_budget_and_cap). An order
# of magnitude below the feedforward init range (ff_weights ~ uniform[0.05,
# 0.20] below) so a pattern the neuron hasn't seen in a while still delivers
# some nonzero charge instead of literally none.
L2E_MIN_WEIGHT_FLOOR = 10   # fixed-point weight floor; 10 == 0.01 * UNIT (linear)

# L2E feedforward weight budget as a multiple of threshold_l2. The old 1x forced
# every neuron to the SAME total weight, flattening winner-vs-rival margins and
# causing pattern collisions (7/8 distinct). Loosening to 2x lets specialists
# separate -> a clean 8/8 distinct map with 0 dead units, at no dominance cost.
# See memory note one-to-one-and-lasting-inhibition for the frontier this sits on.
L2E_BUDGET_MULT = 2

# Mean L2E feedforward weight at init (fixed-point). 125 == the mean of the legacy
# Uniform(50,200) init, preserved by the balanced mode so the LIF-accumulation scale
# is unchanged -- only the balance/bias of the init differs, not its magnitude.
L2E_INIT_MEAN = 125.0
EDGE_DETECTOR_CANDIDATE_MEAN = 250.0
L2E_INIT_JITTER = 0.05   # default jitter eps for the balanced init (Uniform(1-eps,1+eps))


def _sinkhorn_balance(Z, col_target, max_iters=1000, tol=1e-12):
    """Doubly-balance a POSITIVE matrix by alternating row/column normalization
    (Sinkhorn-Knopp). Returns a matrix with every row summing to 1 and every column
    summing to `col_target`. For an (m x n) matrix the consistent choice is
    col_target = m/n (total mass = m along both axes). Convergence is geometric for a
    strictly positive matrix (Sinkhorn's theorem); the loop stops early once both the
    row- and column-sum errors fall below `tol`. Permutation-EQUIVARIANT: permuting
    rows or columns of the input permutes the output identically (it uses only per-row
    and per-column sums, never a position)."""
    Z = np.array(Z, dtype=float)
    for _ in range(max_iters):
        Z *= 1.0 / Z.sum(axis=1, keepdims=True)           # rows -> sum 1
        Z *= col_target / Z.sum(axis=0, keepdims=True)     # cols -> sum col_target
        row_err = np.abs(Z.sum(axis=1) - 1.0).max()
        col_err = np.abs(Z.sum(axis=0) - col_target).max()
        if max(row_err, col_err) < tol:
            break
    return Z


def balanced_feedforward_init(rng, n_out, n_pix, jitter=L2E_INIT_JITTER,
                              target_mean=L2E_INIT_MEAN, max_iters=1000, tol=1e-12):
    """Task-INDEPENDENT, doubly-balanced L2E feedforward init (Sinkhorn-Knopp).

    1. Sample a narrow positive matrix Z[j,i] ~ Uniform(1-jitter, 1+jitter).
    2. Alternately normalize rows and columns until every L2E has equal total incoming
       weight AND every input pixel has equal total outgoing weight across L2E.
    3. Scale the balanced matrix so its overall MEAN entry == target_mean.

    Depends only on (rng, n_out, n_pix, jitter) -- it never inspects PATTERNS, never
    privileges the center pixel, and encodes no line templates. jitter=0 yields an
    exactly uniform matrix (every entry == target_mean, perfectly symmetric); jitter>0
    injects small UNBIASED differences for the learning/competition rules to amplify.
    Result: each L2E's incoming sum == target_mean*n_pix, each pixel's outgoing sum ==
    target_mean*n_out, so no neuron or pixel is privileged at t=0."""
    Z = rng.uniform(1.0 - jitter, 1.0 + jitter, size=(n_out, n_pix))
    B = _sinkhorn_balance(Z, n_out / n_pix, max_iters=max_iters, tol=tol)
    return B * (target_mean / B.mean())


def legacy_wide_feedforward_init(rng, n_out, n_pix):
    """ABLATION: the original wide-uniform init, Uniform(50, 200) (mean 125). Kept so
    the balanced init can be A/B'd against the historical unbalanced starting point."""
    return rng.uniform(50, 200, size=(n_out, n_pix))


def scaled_legacy_wide_feedforward_init(rng, n_out, n_pix, target_mean):
    """Generate the legacy-wide matrix once, then rescale that SAME draw to a new
    mean while preserving every relative random difference.

    This is measurement-only developmental scaling, not a new balancing rule:
    no redraw, no Sinkhorn normalization, no pattern-aware structure. A base
    legacy-wide matrix with mean m is multiplied by target_mean / m.
    """
    base = legacy_wide_feedforward_init(rng, n_out, n_pix)
    mean = float(base.mean()) or 1.0
    return base * (float(target_mean) / mean)


class SimulationEngine:
    def __init__(self, seed: int = 1,
                 # Fixed-point scale (see neuron_flexible.py): the model
                 # runs at the UNIT-scaled scale, so thresholds are INTEGERS and
                 # every charge-like magnitude (potentials, weights, gate, clips)
                 # is scaled by UNIT. Leak rates stay dimensionless ratios stored
                 # as integer numerators over LEAK_SCALE.
                 threshold: int = 1 * UNIT,           # 1000
                 threshold_l2: int = 8 * UNIT,        # 8000
                 leak_l1: float = 100 / LEAK_SCALE,   # 0.10
                 leak_l2: float = 10 / LEAK_SCALE,    # 0.01
                 # Membrane leak is opt-in for every trainable population.
                 # L2E, L2I, and L1I remain independently controllable.
                 leak_enabled: bool = False,
                 l2i_leak_enabled: bool = False,
                 # L1I is a pure accumulator by default when immediate relay is
                 # disabled. Its former fast evidence-window leak remains available
                 # as an explicit ablation rather than being imposed unconditionally.
                 l1i_leak_enabled: bool = False,
                 learning_rate: float = 0.05,
                 weight_cap: int = 1 * UNIT,          # 1000
                 refractory: int = 2,
                 volley_period: int = 4,
                 input_period: int | None = None,
                 cycle_period: int | None = None,
                 homeostasis: bool = False,
                 ca_rate: float = 0.01,
                 ca_target: float = 0.012,   # between a specialist's rate (~0.01) and a
                                             # tyrant's (~0.02): below it a unit is grown,
                                             # above it a unit is shrunk (see sweep in memory)
                 homeo_up: float = 0.01,
                 homeo_down: float = 0.01,
                 l2e_lr_frac: float | None = None,
                 l2i_lr_frac: float | None = None,
                 l1i_lr_frac: float | None = None,
                 l2_gate_eta: float | None = None,
                 l2i_threshold_frac: float = 1,   # unit multiplier (1 == unchanged)
                 # L1I threshold as a fraction of L2I's resolved threshold.
                 # 1.0 makes the two inhibitory populations match exactly.
                 l1i_threshold_frac: float = 1,
                 ei_sat_mult: float = 1,          # unit multiplier (1 == unchanged)
                 l1i_ei_init_frac: float | None = None,
                 # Confidence-gated consolidation (see Claude_Confidence_Consolidation_Plan.md
                 # and neuron_flexible.Neuron). Enabled on L2E by default: a local, label-free
                 # consolidation rule that protects mature specialists, depresses
                 # losing near-winners, and keeps stale neurons reusable. All the
                 # numeric knobs below are DIMENSIONLESS (scale-invariant) except
                 # conf_cap, which is a weight and scales with thr_l2 via conf_cap_frac.
                 confidence_consolidation: bool = True,
                 loser_depression: bool = True,
                 conf_cap_frac: float = 1 / 3,   # effective mature gate value = frac * thr_l2
                 conf_beta: float = 0.05,        # confidence EMA rate toward maturity
                 eta_min: float = 0.05,          # plasticity floor fraction for mature gates
                 eta_loss: float = 0.01,         # loser-depression rate (dimensionless)
                 loss_gamma: float = 2,          # protect-small / punish-large exponent
                 conf_rho_active: float = 1e-5,  # confidence decay while recently active
                 conf_rho_dead: float = 1e-3,    # confidence decay once dead past grace
                 conf_ca_dead: float = 0.002,    # ca below this counts the neuron inactive
                 conf_grace: int = 5000,         # inactive steps before dead-decay engages
                 # Signed-spike depression ("4a"): OFF pixels deliver no charge but
                 # their positive gates are depressed on fire. L2E only; default off
                 # so the baseline is untouched. eta_off is the depression rate.
                 # ON by default: sharpens receptive-field margins, which is what
                 # keeps the 8 specialists distinct AND lifts sustained-presentation
                 # dominance (0.23->0.36) with no measured cost. eta_off is the rate.
                 signed_depression: bool = True,
                 eta_off: float = 0.20,          # OFF-gate depression rate (dimensionless)
                 # L2E feedforward weight budget (sum-renormalization competition).
                 # DEFAULT OFF: the project moved to the signed-spike rule below,
                 # whose -1 signal on inactive inputs supplies the downward pressure
                 # the budget used to impose (see signed_spike_learning). Under the
                 # signed rule this flag is inert anyway (_update_weights returns
                 # before _apply_budget_and_cap); it is kept as a knob so the older
                 # budget/charge regime can still be reconstructed for comparison.
                 l2e_budget: bool = False,
                 # Event-driven firing: resolve L2 competition EVERY step -- every
                 # threshold-crosser fires (Phase 7: no argmax pick), and L2I
                 # accumulates their events toward its own threshold. DEFAULT ON:
                 # this per-step flow is the canonical L2 procedure. Turn OFF to
                 # fall back to the cycle-quantized regime (resolve the same
                 # competition only on the intrinsic cycle boundary, once per
                 # cycle_period steps), which decouples winner timing from the
                 # input rate -- kept as a knob so that rate-decoupling regime can
                 # still be reconstructed for A/B.
                 event_driven: bool = True,
                 # L2 feedforward charge granularity: deliver this step's L1->L2E
                 # drive in K equal chunks (weight_ji/K per active synapse) WITHIN a
                 # frozen outer timestep, re-attempting resolution after each chunk
                 # and stopping at the first chunk that produces a threshold-crosser
                 # (consolidation-first: the earliest strong responder(s) fire before
                 # rivals pile up charge). The clock does not advance and no
                 # leak/update runs between chunks. K=1 (default) delivers the full
                 # drive in one chunk and reproduces the un-chunked behavior exactly.
                 l2_charge_chunks: int = 1,
                 # L1I feedback firing mode. DEFAULT OFF: L1I is a trainable
                 # threshold accumulator. When enabled it acts as an IMMEDIATE
                 # DETERMINISTIC RELAY: any L1I that receives a nonzero L2E
                 # feedback signal fires in that same step, with NO membrane
                 # accumulation, NO learned-threshold crossing, and NO dependence on
                 # L1I feedback-weight training (the learned integrator introduced a
                 # phase shift and was not useful). With the flag off, L1I fires only
                 # when accumulated feedback crosses its own threshold. Either way L1I output stays binary
                 # and the L1I->L1E inhibition delivery path is unchanged.
                 l1i_immediate_relay: bool = False,
                 # Sparse excitatory FLOW-RATE accumulation (opt-in; see Neuron and
                 # step(), and the flow-rate section of the methodology doc). DEFAULT
                 # OFF -> instantaneous V += dot(weights, spikes). When ON, an input
                 # spike opens a decaying excitatory current trace that integrates
                 # into V over time (weight = current amplitude, not a charge packet)
                 # for the positive-charge integrators L2E / L2I / L1I (NOT L1E, the
                 # abstract sensory source; NOT L1I in immediate-relay mode). Flow
                 # mode is the finer temporal model, so it FORCES effective
                 # l2_charge_chunks = 1 (chunking is ignored while it is on).
                 excitatory_flow_rate: bool = True,
                 exc_trace_decay: float = 0.8,        # per-timestep current decay d
                 exc_trace_normalized: bool = True,   # inject drive*(1-d) so total ~= drive
                 # Per-L2I override of excitatory flow. None (default) = L2I follows
                 # excitatory_flow_rate like L2E. Set False to give the shared L2I
                 # INSTANT charge delivery (V += weight in one step) while L2E keeps
                 # flow: under flow, a single L2E->L2I spike is spread over decaying
                 # steps while L2I leaks, so its peak reaches only ~0.6x the weight --
                 # and since the weight is capped AT L2I's threshold, NO single spike
                 # can ever fire L2I (no one-shot single-source relay is possible).
                 # Instant delivery makes a trained (weight==theta) synapse fire L2I
                 # from one spike, the "now-trusted source relays L2I" mechanism.
                 l2i_excitatory_flow_rate: bool | None = None,
                 # Flow-proportional assembly credit for the E->I integrators (L2I/L1I).
                 # On the inhibitory neuron's OWN fire, credit every incoming positive
                 # synapse in proportion to the flow it delivered over the retention
                 # window (per-synapse leaky trace), normalized so the dominant driver
                 # gets the full learning rate; non-contributors decay toward the floor.
                 # Breaks the L2I firing deadlock (a habitual winner's E->I synapse
                 # climbs to self-sufficiency instead of only the threshold-crossing
                 # spike taking credit). Default OFF -> legacy last-volley E->I credit.
                 assembly_flow_credit: bool = False,
                 assembly_decay_frac: float = 0.5,    # down-pressure on non-contributing gates
                 # Inhibitory FLOW (opt-in; symmetric to the excitatory flow). When on,
                 # a real L2I->L2E discharge injects the gate into a decaying inhibitory
                 # CURRENT that drains the target's charge out over ~1/(1-decay) steps
                 # (sustained suppression) instead of a one-shot subtraction. Applies
                 # to the same neurons as the excitatory flow (L2E/L2I/L1I, not L1E).
                 inhibitory_flow_rate: bool = False,
                 inh_trace_decay: float = 0.8,
                 inh_trace_normalized: bool = True,
                 # Inhibitory-gate plasticity rule (see Neuron.apply_inhibition).
                 # inhibitory_delta_rule False = legacy saturating rule (every L2I->L2E
                 # gate converges to the same ceiling sqrt(w_max) -> uniform). True
                 # (DEFAULT) = a differentiating local rule selected by
                 # inhibitory_rule_mode:
                 #   "turnover" (DEFAULT): on each discharge the NORMALIZED gate
                 #     u = w/G updates as du = eta_up*p_t*(1-u) - eta_down*u, with
                 #     p_t = clamp(v_pre/theta, 0, p_max). Purely event-local (no target
                 #     voltage, no averages): high-charge rivals accumulate stronger
                 #     gates while weak/dead targets drift down via size-proportional
                 #     turnover.
                 #   "margin": diagnostic; relax toward s = clamp(v_pre-margin*theta,0,G).
                 inhibitory_delta_rule: bool = True,
                 inhibitory_rule_mode: str = "turnover",
                 inhibitory_eta_up: float = 0.02,       # turnover strengthening rate
                 inhibitory_eta_down: float = 0.005,    # turnover size-proportional decay
                 inhibitory_p_max: float = 1.0,         # turnover cap on p_t = v_pre/theta
                 inhibitory_margin_frac: float = 0.5,   # margin mode: target_post = frac*theta
                 inhibitory_delta_eta: float = 0.05,    # margin mode: EMA rate
                 # Distance attenuation of DELIVERED excitatory drive (opt-in; see
                 # Neuron.receive_input and the methodology doc). When on, each
                 # afferent's delivered amplitude is multiplied by
                 # (distance_ref/max(d_i, distance_min))^distance_power -- weight =
                 # learned gate, distance = delivery attenuation, trace = temporal
                 # flow. It does NOT change stored weights or the trace math, and is
                 # not entangled with chunking. OFF by default (per-synapse distances
                 # default to 1.0 = no attenuation until real functional distances
                 # are provided). Applies in both flow-rate and instantaneous modes.
                 distance_weighting: bool = False,
                 distance_power: float = 2.0,
                 distance_ref: float = 1.0,
                 distance_min: float = 1.0,
                 # Lasting inhibition: replace the one-shot lateral discharge with a
                 # LEAKY decaying inhibitory field. L2I (a leaky integrator) pumps a
                 # shared field when it fires; the field hyperpolarizes the whole L2E
                 # pool every step and decays with inh_decay. A pattern's specialist
                 # keeps the field pumped (rivals stay suppressed for a finite window
                 # = sustained ownership); when the pattern changes the field decays
                 # and the new specialist takes over. inh_boost_frac scales the per-
                 # fire field increment as a fraction of threshold_l2.
                 lasting_inhibition: bool = False,
                 inh_decay: float = 0.15,
                 inh_boost_frac: float = 1.0,
                 # ---- Phase 7: causal L2E->L2I->L2E competition (replaces the
                 # legacy immediate-reset tiebreak; see July_14_Geometric_
                 # Influence_Temporal_Winner_Brief.txt SS9). L2I accumulates
                 # actual arriving L2E spike events and fires on its OWN
                 # threshold crossing exactly as before; what changes is what
                 # happens next -- instead of instantly clamping every non-
                 # winner in the same timestep, L2I schedules a delayed,
                 # uniform inhibitory conductance delivered l2_inhibition_delay
                 # steps later (see _deliver_scheduled_l2_inhibition), sized as
                 # l2_inhibition_frac * threshold_l2 (a FIXED, configurable
                 # magnitude -- there is still no learned L2I->L2E gate; a
                 # learned/adaptive gate is out of scope for this phase). The
                 # delivery floors at rest (never forces a specific value) and
                 # is skipped entirely for a target still in its OWN post-spike
                 # refractory window. default frac=1.0 means a target that
                 # never crossed threshold (charge < threshold_l2) is still
                 # fully floored, reproducing the net discharge magnitude of
                 # the retired immediate clamp -- only the CAUSALITY (delayed,
                 # accumulate-then-cross-threshold, self-normal-reset-on-own-
                 # spike, no ID-based exemption) actually changes.
                 l2_inhibition_delay: int = 1,
                 l2_inhibition_frac: float = 1.0,
                 # Reset-by-subtraction on L2E fire: on spike, potential -= threshold
                 # (floored at rest) instead of a full reset to rest. Standard LIF;
                 # leaves the winner its residual overshoot like partially-inhibited
                 # losers keep theirs, directly attacking the discharge asymmetry
                 # that drives the round-robin (see AGENT_HANDOFF.md sec 5-6). L2E
                 # only; default off so the baseline is untouched.
                 subtractive_reset: bool = False,
                 # Hard-reset inhibition on losing L2E (see neuron_flexible.Neuron
                 # and Hard_Reset_Inhibition_Plan.md). When on, a real L2I->L2E
                 # discharge clamps the non-winner's membrane back to rest AFTER the
                 # inhibitory plasticity rule has read its pre-reset charge, so loser
                 # charge carryover (the round-robin's engine) drops to zero. L2E
                 # only; default off keeps the small subtractive/flow gate.
                 l2i_hard_reset_losers: bool = False,
                 # Clear the excitatory/inhibitory current traces on a hard reset so
                 # no residual flow refills the membrane after it is clamped to rest.
                 hard_reset_clear_traces: bool = True,
                 # Membrane saturation ceiling for L2E, as a multiple of thr_l2
                 # (None = unbounded, the baseline). Bounds accumulated charge so
                 # the membrane can't ratchet to ~2-3x threshold between cycles;
                 # this keeps the (small, capped) L2I->L2E gate in a range where
                 # it can actually regulate firing frequency -- inhibition, not a
                 # pile-up, sets who fires. Local finite driving force; L2E only.
                 v_sat_frac: float | None = None,
                 # Learnable L2I->L2E gate equilibrium, as a fraction of thr_l2
                 # (None = module default, ~0.15*thr). The gate grows by the
                 # inhibitory rule and settles at sqrt(w_max); this sets that
                 # target. Raising it toward/above 1.0 lets a fired owner's L2I
                 # discharge FLOOR its rivals to rest (they lose all their charge
                 # and cannot fire) -- the inhibitory winner-take-all lockout that
                 # makes ongoing plasticity safe (only the owner fires, so only
                 # the owner learns). Pair with v_sat so a rival's bounded charge
                 # is within reach of the gate. L2E only.
                 l2_gate_eq_frac: float | None = None,
                 # Minimal SIGNED-SPIKE feedforward learning (see
                 # Claude_Minimal_Signed_Spike_Learning_Prompt.md). Replaces the
                 # potentiation + OFF-depression + confidence + budget stack with a
                 # single local signed rule: on fire, active inputs (+1) potentiate
                 # and inactive inputs (-1) depress, dw = eta*p*(1-(w/w_cap)^2)*sig,
                 # bounded to [min_positive_weight, weight_cap], NO budget. Intended
                 # to be run with the compensating mechanisms off and refractory=0
                 # (the "minimal experiment"). L2E only. DEFAULT ON: this is now the
                 # project's canonical L2E learning rule. When on it takes over
                 # _update_weights entirely (returns early), so l2e_budget,
                 # confidence_consolidation, loser_depression and signed_depression
                 # are all bypassed for L2E regardless of their own defaults.
                 signed_spike_learning: bool = True,
                 # Structural free-energy plasticity gate (see Neuron and the
                 # methodology doc). EXCITATORY postsynaptic neurons only (L2E
                 # feedforward). When on, the signed-spike learning rate is scaled by
                 # gate = max(eta_floor, 1 - clamp(sum_positive_afferents/theta, 0, 1))
                 # -- a structural, input/voltage-independent consolidation brake
                 # that REPLACES the voltage term p in the signed rule. Under-built
                 # L2E stay plastic; mature specialists slow down and resist being
                 # reshaped on a later pattern. Default OFF -> signed rule uses p.
                 structural_free_energy: bool = False,
                 structural_fe_eta_floor: float = 0.02,
                 # ---- Phase 10 (corrected Phases 6-12 prompt file):
                 # adaptive-threshold ablation. A SEPARATE experiment from
                 # geometry and from the existing synaptic-scaling homeostasis
                 # feature (`homeostasis` above) -- NOT a rename/reuse of it.
                 # For each L2E neuron: effective_threshold = threshold + a_i;
                 # on that neuron's own spike, a_i += delta_threshold_frac*thr_l2;
                 # every step, a_i decays exponentially toward zero with time
                 # constant tau_threshold (steps). Default OFF reproduces
                 # baseline exactly (see Neuron.check_threshold). Defaults below
                 # are reasonable, documented starting points -- NOT swept or
                 # tuned to make any particular seed succeed: delta_threshold_frac
                 # 0.05 is a small, noticeable-but-not-immediately-disabling
                 # per-spike step; tau_threshold 25 steps is the same order of
                 # magnitude as the presentation windows used throughout this
                 # repo's own tests/diagnostics (20-60 steps), so the effect is
                 # visible within one presentation without one spike silencing
                 # the neuron for many presentations afterward.
                 adaptive_threshold: bool = False,
                 delta_threshold_frac: float = 0.05,
                 tau_threshold: float = 25.0,
                 # Phase 15: local developmental protection from L2I loser
                 # depression (see Neuron.apply_delayed_inhibition/
                 # _loser_depression_maturity). SEPARATE from adaptive_threshold,
                 # structural_free_energy, and homeostasis above -- not a rename
                 # or silent reuse of any of them. Uses ONLY each L2E's own
                 # self.ca (the slow EMA of its own physical spiking, already
                 # computed unconditionally every step regardless of the
                 # homeostasis flag -- see Neuron.update); a neuron with little/
                 # no firing history has its structural WEIGHT-DEPRESSION gain
                 # scaled down by a smooth maturity = clamp(ca/ca_ref, 0, 1), but
                 # the physical inhibitory membrane transient is UNCHANGED
                 # regardless. Default OFF reproduces every prior phase's
                 # apply_delayed_inhibition gain exactly (gate multiplies by
                 # exactly 1.0 when off). loser_depression_protection_ca_ref
                 # 0.02 is a single, reasonable, NOT-swept-per-seed default: with
                 # ca_rate's own default 0.01 and this repo's typical 20-100 step
                 # presentation windows, a neuron firing roughly once every ~50
                 # steps reaches this reference (order-of-magnitude "established,
                 # repeatedly-firing competitor"), not a per-experiment tuned value.
                 loser_depression_protection: bool = False,
                 loser_depression_protection_ca_ref: float = 0.02,
                 # Phase 17 (LPS Lecture 14 mapping): pre-trained, task-independent
                 # L2E->L2I recruitment. Default OFF reproduces the current learned-
                 # recruitment baseline byte-identically. When True: every L2E->L2I
                 # synapse is initialized to one identical fixed value (the resolved
                 # L2I threshold itself -- see _build, no unit conversion needed since
                 # infl_l2e_l2i, the only thing that would attenuate this delivery,
                 # stays off and untouched), and L2I's OWN incoming-excitatory
                 # learning_rate is pinned to 0 so those weights never move again.
                 # Nothing else changes: L2I still physically integrates charge and
                 # crosses its own threshold (Neuron.check_threshold/fire, untouched),
                 # L2I->L2E inhibition is still scheduled and causally delayed by
                 # l2_inhibition_delay (untouched), delivery is still uniform across
                 # the whole L2E pool (untouched). This flag touches ONLY the initial
                 # value and the learning rate of L2I's own incoming weights -- it
                 # does not add a prediction-excitatory population, a frequency/
                 # synapse-level free-energy rule, or any explicit time equation
                 # (those Lecture 14 proposals are explicitly deferred, not
                 # implemented here).
                 pretrained_l2i_recruitment: bool = False,
                 # Phase 19A (LPS Lecture 14 corrected prediction scaffold;
                 # see Phase18b_Lecture14_Prediction_Architecture_Contract_
                 # Corrected.md). Default OFF reproduces the exact baseline
                 # topology and step() behavior. When True: builds nine
                 # prediction excitatory neurons P0..P8, one per input column,
                 # stores an 8x9 positive-bounded L2Ej->Pi decoder matrix, and
                 # enables a fixed local Pi->L1Ei replay path. Physical timing
                 # stays causal and delayed only: L2Ej at t can affect Pi no
                 # earlier than t+1, and Pi at t can affect its paired L1Ei no
                 # earlier than t+1 (so a sensory L2E spike at t replays no
                 # earlier than t+2). This checkpoint is a SCAFFOLD ONLY:
                 # decoder learning is deliberately NOT implemented here.
                 prediction_excitatory_enabled: bool = False,
                 # Reserved for a future explicitly-justified local L2E->P
                 # decoder-learning equation. Phase 19A does not use it.
                 eta_pred: float = 0.05,
                 # Phase 19-v2 (LPS Lecture 14 LOCAL-COINCIDENCE prediction
                 # architecture; see Phase18b_Lecture14_Local_Coincidence_
                 # Architecture_Contract.md). A SEPARATE, ADDITIVELY-COEXISTING
                 # mechanism from prediction_excitatory_enabled above (mutually
                 # exclusive at _build() time -- enabling both raises, see
                 # _build_prediction_column_population). Default OFF preserves
                 # the exact baseline topology/step() behavior. When True:
                 # builds nine "PC0".."PC8" prediction-column neurons, one per
                 # input column i, each with nine total afferents:
                 # eight LEARNED R_j->PCi feedback weights (index 0..7, one per
                 # L2Ej) plus one FIXED S_i->PCi lateral-coincidence weight
                 # (index 8, never learned). R_j->PCi delivery is queued and
                 # arrives exactly one step later (t+1); S_i->PCi delivery is
                 # SAME-STEP (a direct local physical connection, no delay --
                 # this is the "lime" connection in the annotated diagram).
                 # Decoder learning (the R_j->PCi feedback weights) updates
                 # ONLY on PCi's own physical spike, crediting ONLY the R_j
                 # sources that actually, causally contributed to that specific
                 # spike (this step's delayed-register eligibility, read off
                 # PCi's own _last_input_spikes -- no separate bookkeeping).
                 # PCi's output (P_i->I_i->S_i in the full architecture) is NOT
                 # wired in this phase -- shadow mode: a PC spike has zero
                 # effect on any other neuron.
                 prediction_column_enabled: bool = False,
                 # Fixed S_i->PCi lateral weight (index 8, never learned).
                 # EXPERIMENTAL CANDIDATE value -- see the Phase 19 report for
                 # the calibration reasoning (must satisfy: a single lateral
                 # event alone stays subthreshold, i.e. < prediction_threshold).
                 prediction_lateral_weight: float = 150.0,
                 # Initial value for every R_j->PCi feedback weight (index
                 # 0..7). Deliberately small and NONZERO (not exactly 0) so the
                 # "no-leak" diagnostic control can demonstrate unbounded
                 # accumulation from repeated feedback-only delivery -- with a
                 # true zero init, zero delivered repeatedly is still zero, and
                 # the diagnostic could not show the failure mode it exists to
                 # demonstrate.
                 prediction_feedback_init: float = 50.0,
                 # Saturating ceiling for R_j->PCi feedback weight growth (w_max
                 # in the delta rule below). Deliberately set slightly ABOVE
                 # prediction_threshold so a FULLY mature feedback weight can
                 # eventually fire PCi alone, without any lateral coincidence --
                 # this is the intended Part 7 "prediction without input"
                 # end-state, reached only by synapses that have genuinely,
                 # repeatedly, causally contributed to a real PCi spike.
                 prediction_feedback_max: float = 1200.0,
                 # eta_prediction: the R_j->PCi feedback learning rate (delta_w
                 # = eta * spike(PCi) * eligibility(Rj) * (1 - w/w_max)^2, see
                 # _apply_prediction_column_learning). Separately named, never
                 # aliased to learning_rate/eta_pred/l2e_lr_frac.
                 prediction_learning_rate: float = 0.15,
                 # PCi's own firing threshold. Separately named from
                 # threshold/threshold_l2 -- this population's coincidence
                 # detection is calibrated against ITS OWN scale, not L1/L2's.
                 # EMPIRICALLY CALIBRATED (see the Phase 19 report's
                 # feasibility measurement): with the defaults above and this
                 # preset's actual S_i duty cycle (~90%, refractory=0) and
                 # R_j duty cycle (~50%), a bare lateral-alone steady state
                 # settles around ~420-500 and a bare feedback-alone steady
                 # state (inactive columns) around ~200-210. 500 sits just
                 # above the lateral-alone ceiling (so PURE sensory-only
                 # input, without any representation feedback, cannot fire
                 # PCi on its own) while still reachable when a genuine
                 # causal R_j coincidence briefly lifts the retained lateral
                 # charge over the line. At threshold=300 lateral-alone COULD
                 # eventually cross it (false "coincidence" from sensory
                 # alone); at threshold=600+ no combination reliably crosses
                 # it. This window is narrow and the resulting PCi firing
                 # rate is low and front-loaded (see the report) -- reported
                 # honestly, not smoothed over.
                 prediction_threshold: float = 500.0,
                 # PCi's own membrane leak fraction per step (fixed-point,
                 # same convention as leak_l1/leak_l2 -- see neuron_flexible.
                 # Membrane.leak_rate). Deliberately a NEW, separately-tunable
                 # value -- see the Phase 19 report's feasibility calibration
                 # for why this needs to be substantially larger than leak_l1
                 # (0.1): S_i's own duty cycle in this preset is very high
                 # (frequently >90% of steps, refractory=0), so a weak leak
                 # would let repeated LATERAL-ALONE delivery alone ratchet PCi
                 # to threshold with no representation feedback at all --
                 # exactly the false-positive failure this phase must rule
                 # out (Part 5's coincidence/leak requirements).
                 prediction_leak: float = 0.3,
                 # R_j->PCi feedback delivery delay in steps (t -> t+arrival).
                 # Fixed at 1 (never same-step) per the architecture's causal
                 # requirement; exposed as a named constant for clarity/tests,
                 # not intended to be swept in this phase.
                 prediction_feedback_delay: int = 1,
                 # DIAGNOSTIC CONTROL ONLY (Part 5's explicit "no-leak
                 # diagnostic" requirement) -- forces prediction_leak to 0.0
                 # regardless of the value above, to reproduce and demonstrate
                 # the unbounded-accumulation failure mode that motivates the
                 # real leak. Never used outside that one diagnostic test/run.
                 prediction_leak_diagnostic_disable: bool = False,
                 # Phase 21 (LPS Lecture 14 selective local predictive
                 # inhibition; see Phase18b_Lecture14_Local_Coincidence_
                 # Architecture_Contract.md's deferred "PCi->Ii->Si" path,
                 # wired for the first time in this phase). Requires
                 # prediction_column_enabled (raises otherwise -- selective
                 # input needs an actual PC population to draw from). Default
                 # OFF reproduces the exact baseline L1I input topology
                 # (all-nine-identical global L2E broadcast, n_feedback_inputs
                 # = N_OUT). When True: L1Ii's incoming array is replaced
                 # (not appended to) with a SINGLE input from its own paired
                 # PCi only (n_feedback_inputs = 1) -- "route each PCi's
                 # pixel-specific prediction to L1Ii INSTEAD OF all-nine-
                 # identical global L2E evidence", delivered same-step
                 # (immediate), matching the existing L2E->L1I feedback's own
                 # same-step delivery convention (see step()'s "2d. Deliver
                 # L2E winner spike immediately to all L1I neurons").
                 prediction_column_to_i_enabled: bool = False,
                 # Phase 36.1: keep Phase 21's paired PC_i -> L1I_i topology
                 # and decoder-learning path intact, but gate ONLY the real
                 # physical output delivery into L1I. Default OFF makes "shadow"
                 # and "active-topology" conditions use identical PC/L1I
                 # construction, weights, RNG, and routing dimensions while the
                 # paired output remains physically silent.
                 prediction_column_to_i_delivery_enabled: bool = False,
                 # Phase 36: keep Phase 21's selective PC_i -> L1I_i -> L1E_i
                 # topology and same one-step L1I->L1E arrival delay, but add a
                 # persistent inhibitory conductance TAIL after that ordinary
                 # paired discharge lands. Requires prediction_column_to_i_enabled
                 # because this feature is scoped ONLY to the paired predictive
                 # output path, never the global L2E->L1I baseline.
                 # Implementation deliberately reuses Neuron's existing
                 # inhibitory-current decay constants (inh_trace_decay /
                 # inh_trace_normalized) instead of inventing a second floor or
                 # parallel inhibitory rule.
                 prediction_column_persistent_conductance_enabled: bool = False,
                 # Phase 37: explicit paired L2 membrane-shunt ablation,
                 # default OFF. A SwitchI_j event is permitted only when the
                 # current post-prediction residual L1 evidence for L2E_j
                 # coincides with that same neuron's recent-spike trace. This
                 # is a bounded oracle-feasibility ablation, not a claimed
                 # biological conductance model.
                 switchi_paired_shunt_enabled: bool = False,
                 # Phase 38: smallest default-OFF natural paired L2 ownership
                 # mechanism. Each SwitchI_j can shunt ONLY its paired L2E_j,
                 # and may fire only from a coincidence between: (1) current
                 # local learned prediction support for L2E_j carried by the
                 # existing PC_i population, (2) current unexpected/residual
                 # L1 evidence for L2E_j, and (3) that same neuron's recent
                 # spike trace. No labels, oracle owner identity, argmax
                 # dependence, or zero-delay reset.
                 switchi_local_mismatch_enabled: bool = False,
                 switchi_trace_decay: float = 0.75,
                 switchi_coincidence_threshold: float = 0.15,
                 switchi_shunt_frac: float = 0.5,
                 # Phase 21: fixed/pretrained L1I regulation, KEPT AS A
                 # SEPARATE factorial variable from the input-topology flag
                 # above (per the independent review's correction #6 --
                 # do not change input topology and inhibitory plasticity
                 # simultaneously without isolated controls). Default OFF
                 # reproduces the existing learned L1I regulation exactly
                 # (random init, ChargeBasedRule learning). When True: every
                 # L1Ii incoming weight (whether global N_OUT-dim or the
                 # single selective PCi input, depending on the flag above)
                 # is fixed at L1I's own resolved threshold (one physical
                 # source event alone sufficient), and L1I's own
                 # learning_rate is pinned to 0 -- same "pretrained
                 # recruitment" pattern as Phase 17's
                 # pretrained_l2i_recruitment, applied to L1I instead of L2I.
                 pretrained_l1i_regulation: bool = False,
                 # Capacity rule for the minimal experiment (see the prompt's
                 # "Threshold, Cap, Floor" section). l2e_weight_cap_frac sets each
                 # L2E positive feedforward weight cap to frac*thr_l2, so three
                 # maximally strong active afferents reach threshold (1/3 for the
                 # 3-pixel line patterns). Default 1.0 preserves the prior cap.
                 l2e_weight_cap_frac: float = 1.0,
                 # Positive-afferent weight FLOOR (L2E feedforward and E->I positive
                 # afferents). None keeps legacy behaviour (L2E floor =
                 # L2E_MIN_WEIGHT_FLOOR, E->I unfloored); the minimal experiment
                 # sets 1. Negative inhibitory gates are never floored here -- they
                 # are bounded by magnitude in apply_inhibition.
                 pos_weight_floor: int | None = None,
                 # L2E feedforward INITIALIZATION (see balanced_feedforward_init).
                 # 'balanced': task-independent doubly-balanced Sinkhorn init
                 # -- narrow jitter, then row/col-normalized so every L2E has equal
                 # total incoming weight and every pixel equal total outgoing weight,
                 # scaled to the legacy mean (125). A FAIR developmental start: no
                 # neuron/pixel privileged, no task structure. 'legacy_wide' is the
                 # unconstrained Uniform(50,200) init and is the default.
                 l2e_init_mode: str = 'legacy_wide',
                 # Jitter eps for the balanced init: Z[j,i] ~ Uniform(1-eps, 1+eps).
                 # eps=0 -> exactly uniform (perfect symmetry); eps>0 -> small UNBIASED
                 # differences the learning rules must amplify. Ignored in legacy mode.
                 l2e_init_jitter: float = L2E_INIT_JITTER,
                 # ---- Phase 3: seeded engine-owned geometry (see the module-level
                 # comment above L1_JITTER_FRAC). topology_seed is INDEPENDENT of
                 # `seed` (weight init) -- geometry and learned weights vary
                 # independently. Positions are recomputed from topology_seed on
                 # every _build() (reset/apply_config/weight-reseed all call
                 # _build()), so they are DETERMINISTIC and therefore fixed across
                 # those calls; only reseed_topology() changes topology_seed.
                 topology_seed: int = 1,
                 # DEFAULT True: every existing caller/test that doesn't pass this
                 # gets the EXACT legacy ring/grid positions, byte-identical. False
                 # selects the new seeded jittered/irregular geometry. The legacy
                 # layout stays selectable here as an ablation, not removed.
                 symmetric_geometry: bool = True,
                 # TEMPORARY compatibility shim (Phase 3; see module comment): when
                 # True (the default), the DELIVERY distances distance_weighting
                 # reads for the L1E->L2E pathway are always computed from the
                 # legacy reference geometry regardless of `symmetric_geometry`, so
                 # switching to the new geometry cannot by itself change any neural
                 # dynamics. Phase 4 (below) adds FOUR NEW, separately-ablated
                 # experimental pathways that use the real new geometry directly --
                 # this flag is explicitly preserved unchanged as the
                 # "legacy-distance baseline" and continues to govern ONLY the
                 # L1E->L2E pathway.
                 legacy_distance_compat: bool = True,
                 # ---- Phase 4: per-connection distance/influence, audited
                 # separately per pathway (see the module comment above
                 # INFLUENCE_SAFE_MAX). ONE shared, configurable power law for the
                 # four NEW pathways below (deliberately separate from the legacy
                 # L1E->L2E distance_power/_ref/_min above). Defaults (ref==min)
                 # make it a pure ATTENUATION law -- never amplifies.
                 infl_power: float = 2.0,    # inverse-square: the initial experiment
                 infl_ref: float = 1.0,
                 infl_min: float = 1.0,
                 # Each pathway's OWN ablation flag, ALL DEFAULT OFF ("do not enable
                 # every pathway together" -- isolated, one-at-a-time experimentation).
                 infl_l2e_l2i: bool = False,
                 infl_l2i_l2e: bool = False,
                 infl_l2e_l1i: bool = False,
                 infl_l1i_l1e: bool = False):
        # Decouple the SENSORY input rate from the INTRINSIC competition clock.
        # input_period: steps between external input samples. The default is 1:
        #   a held pixel supplies drive continuously, every simulation step.
        # cycle_period: the intrinsic gamma-like clock that structures L2
        #   competition and L2I evidence integration. FIXED regardless of the
        #   input rate. It retains volley_period as its default, independently of
        #   the now-continuous sensory drive.
        input_period = 1 if input_period is None else input_period
        cycle_period = volley_period if cycle_period is None else cycle_period
        # Separate learning-rate controls for the E and I populations (Phase 1 of
        # the symmetry-breaking plan). Each defaults to the module constant that
        # was previously applied uniformly, so the defaults reproduce prior
        # behavior exactly. l2i_threshold_frac scales L2I from threshold_l2;
        # l1i_threshold_frac then scales L1I from the resolved L2I threshold. Their E->I init range and
        # learning cap scale with that same (possibly lowered) threshold below,
        # so lowering an I threshold does not trivially overdrive it.
        l2e_lr_frac = ETA_FRAC if l2e_lr_frac is None else l2e_lr_frac
        l2i_lr_frac = ETA_FRAC if l2i_lr_frac is None else l2i_lr_frac
        l1i_lr_frac = ETA_FRAC if l1i_lr_frac is None else l1i_lr_frac
        l2_gate_eta = L2_GATE_ETA if l2_gate_eta is None else l2_gate_eta
        self.params = dict(seed=seed, threshold=threshold, threshold_l2=threshold_l2,
                           leak_l1=leak_l1, leak_l2=leak_l2, leak_enabled=leak_enabled,
                           l2i_leak_enabled=l2i_leak_enabled,
                           l1i_leak_enabled=l1i_leak_enabled,
                           learning_rate=learning_rate, weight_cap=weight_cap,
                           refractory=refractory, volley_period=volley_period,
                           input_period=input_period, cycle_period=cycle_period,
                           homeostasis=homeostasis, ca_rate=ca_rate, ca_target=ca_target,
                           homeo_up=homeo_up, homeo_down=homeo_down,
                           l2e_lr_frac=l2e_lr_frac, l2i_lr_frac=l2i_lr_frac,
                           l1i_lr_frac=l1i_lr_frac, l2_gate_eta=l2_gate_eta,
                           l2i_threshold_frac=l2i_threshold_frac,
                           l1i_threshold_frac=l1i_threshold_frac,
                           ei_sat_mult=ei_sat_mult,
                           l1i_ei_init_frac=l1i_ei_init_frac,
                           confidence_consolidation=confidence_consolidation,
                           loser_depression=loser_depression,
                           conf_cap_frac=conf_cap_frac, conf_beta=conf_beta,
                           eta_min=eta_min, eta_loss=eta_loss, loss_gamma=loss_gamma,
                           conf_rho_active=conf_rho_active, conf_rho_dead=conf_rho_dead,
                           conf_ca_dead=conf_ca_dead, conf_grace=conf_grace,
                           signed_depression=signed_depression, eta_off=eta_off,
                           l2e_budget=l2e_budget, event_driven=event_driven,
                           l2_charge_chunks=l2_charge_chunks,
                           l1i_immediate_relay=l1i_immediate_relay,
                           excitatory_flow_rate=excitatory_flow_rate,
                           l2i_excitatory_flow_rate=l2i_excitatory_flow_rate,
                           exc_trace_decay=exc_trace_decay,
                           exc_trace_normalized=exc_trace_normalized,
                           assembly_flow_credit=assembly_flow_credit,
                           assembly_decay_frac=assembly_decay_frac,
                           inhibitory_flow_rate=inhibitory_flow_rate,
                           inh_trace_decay=inh_trace_decay,
                           inh_trace_normalized=inh_trace_normalized,
                           inhibitory_delta_rule=inhibitory_delta_rule,
                           inhibitory_rule_mode=inhibitory_rule_mode,
                           inhibitory_eta_up=inhibitory_eta_up,
                           inhibitory_eta_down=inhibitory_eta_down,
                           inhibitory_p_max=inhibitory_p_max,
                           inhibitory_margin_frac=inhibitory_margin_frac,
                           inhibitory_delta_eta=inhibitory_delta_eta,
                           distance_weighting=distance_weighting,
                           distance_power=distance_power,
                           distance_ref=distance_ref, distance_min=distance_min,
                           lasting_inhibition=lasting_inhibition, inh_decay=inh_decay,
                           inh_boost_frac=inh_boost_frac,
                           l2_inhibition_delay=l2_inhibition_delay,
                           l2_inhibition_frac=l2_inhibition_frac,
                           subtractive_reset=subtractive_reset,
                           l2i_hard_reset_losers=l2i_hard_reset_losers,
                           hard_reset_clear_traces=hard_reset_clear_traces,
                           v_sat_frac=v_sat_frac,
                           l2_gate_eq_frac=l2_gate_eq_frac,
                           signed_spike_learning=signed_spike_learning,
                           structural_free_energy=structural_free_energy,
                           structural_fe_eta_floor=structural_fe_eta_floor,
                           adaptive_threshold=adaptive_threshold,
                           delta_threshold_frac=delta_threshold_frac,
                           tau_threshold=tau_threshold,
                           loser_depression_protection=loser_depression_protection,
                           loser_depression_protection_ca_ref=loser_depression_protection_ca_ref,
                           pretrained_l2i_recruitment=pretrained_l2i_recruitment,
                           prediction_excitatory_enabled=prediction_excitatory_enabled,
                           eta_pred=eta_pred,
                           prediction_column_enabled=prediction_column_enabled,
                           prediction_lateral_weight=prediction_lateral_weight,
                           prediction_feedback_init=prediction_feedback_init,
                           prediction_feedback_max=prediction_feedback_max,
                           prediction_learning_rate=prediction_learning_rate,
                           prediction_threshold=prediction_threshold,
                           prediction_leak=prediction_leak,
                           prediction_feedback_delay=prediction_feedback_delay,
                           prediction_leak_diagnostic_disable=prediction_leak_diagnostic_disable,
                           prediction_column_to_i_enabled=prediction_column_to_i_enabled,
                           prediction_column_to_i_delivery_enabled=(
                               prediction_column_to_i_delivery_enabled),
                           prediction_column_persistent_conductance_enabled=(
                               prediction_column_persistent_conductance_enabled),
                           switchi_paired_shunt_enabled=switchi_paired_shunt_enabled,
                           switchi_local_mismatch_enabled=switchi_local_mismatch_enabled,
                           switchi_trace_decay=switchi_trace_decay,
                           switchi_coincidence_threshold=switchi_coincidence_threshold,
                           switchi_shunt_frac=switchi_shunt_frac,
                           pretrained_l1i_regulation=pretrained_l1i_regulation,
                           l2e_weight_cap_frac=l2e_weight_cap_frac,
                           pos_weight_floor=pos_weight_floor,
                           l2e_init_mode=l2e_init_mode,
                           l2e_init_jitter=l2e_init_jitter,
                           topology_seed=topology_seed,
                           symmetric_geometry=symmetric_geometry,
                           legacy_distance_compat=legacy_distance_compat,
                           infl_power=infl_power, infl_ref=infl_ref, infl_min=infl_min,
                           infl_l2e_l2i=infl_l2e_l2i, infl_l2i_l2e=infl_l2i_l2e,
                           infl_l2e_l1i=infl_l2e_l1i, infl_l1i_l1e=infl_l1i_l1e)
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self):
        p = self.params
        # NEUTERED (reversible): the trace-based flow-rate delivery is permanently
        # OFF. The task is now the minimal loop -- accumulate -> fire -> learn ->
        # inhibit -> chunk (instantaneous charge + chunked WTA race for timing).
        # The flow-rate / current-trace / assembly-flow CODE still exists, but this
        # is the single choke point both __init__ and apply_config funnel through,
        # so pinning the params here means no constructor arg or live config toggle
        # can re-enable trace accumulation. To restore, delete this block. See
        # snn/rules/delivery.py (FlowRateDelivery) and excitatory.py (AssemblyFlowCredit).
        p['excitatory_flow_rate'] = False
        p['l2i_excitatory_flow_rate'] = False
        p['inhibitory_flow_rate'] = False
        p['assembly_flow_credit'] = False
        # INDEPENDENT RNG streams for the three weight inits, derived deterministically
        # from the engine seed (SeedSequence.spawn gives statistically independent
        # children). Feedforward, L2E->L2I, and feedback thus no longer share/consume
        # one stream in a fixed order -- each is reproducible from the seed on its own,
        # and reordering or resizing one init cannot shift the others.
        rng_ff, rng_ei, rng_fb = (np.random.default_rng(s)
                                  for s in np.random.SeedSequence(p['seed']).spawn(3))
        thr_l1 = p['threshold']      # L1 neurons fire on a single pixel hit
        thr_l2 = p['threshold_l2']   # L2 neurons must accumulate many volleys
        # Inhibitory-neuron thresholds (Phase 2): each defaults to its excitatory
        # layer's threshold (frac 1.0 -> unchanged). When lowered, the E->I init
        # range and learning cap below scale with THIS threshold, not the E one.
        thr_l2i = thr_l2 * p['l2i_threshold_frac']   # L2I's own firing threshold
        thr_l1i = thr_l2i * p['l1i_threshold_frac']  # 1.0 => L1I exactly matches L2I

        self.prediction_excitatory_enabled = bool(p['prediction_excitatory_enabled'])
        # Phase 21: selective PCi->Ii input topology REPLACES (not appends
        # to) L1I's incoming array -- n_feedback_inputs becomes 1 (this
        # column's own paired PCi only) instead of N_OUT (all-nine-identical
        # global L2E broadcast). Requires an actual PC population to exist.
        self.prediction_column_to_i_enabled = bool(p['prediction_column_to_i_enabled'])
        if self.prediction_column_to_i_enabled and not p['prediction_column_enabled']:
            raise ValueError(
                "prediction_column_to_i_enabled requires prediction_column_enabled "
                "(selective L1I input needs an actual PC population to draw from).")
        self.prediction_column_to_i_delivery_enabled = bool(
            p['prediction_column_to_i_delivery_enabled'])
        if (self.prediction_column_to_i_delivery_enabled
                and not self.prediction_column_to_i_enabled):
            raise ValueError(
                "prediction_column_to_i_delivery_enabled requires "
                "prediction_column_to_i_enabled (the physical delivery gate only "
                "applies to the paired PC_i -> L1I_i route).")
        self.prediction_column_persistent_conductance_enabled = bool(
            p['prediction_column_persistent_conductance_enabled'])
        if (self.prediction_column_persistent_conductance_enabled
                and not self.prediction_column_to_i_enabled):
            raise ValueError(
                "prediction_column_persistent_conductance_enabled requires "
                "prediction_column_to_i_enabled (the persistent tail is only "
                "defined on the paired PC_i -> L1I_i -> L1E_i path).")
        if (self.prediction_column_persistent_conductance_enabled
                and not self.prediction_column_to_i_delivery_enabled):
            raise ValueError(
                "prediction_column_persistent_conductance_enabled requires "
                "prediction_column_to_i_delivery_enabled (the persistent tail is "
                "only meaningful when PC_i spikes are physically delivered to "
                "L1I_i).")
        self.switchi_paired_shunt_enabled = bool(p['switchi_paired_shunt_enabled'])
        self.switchi_local_mismatch_enabled = bool(p['switchi_local_mismatch_enabled'])
        if self.switchi_local_mismatch_enabled and not bool(p['prediction_column_enabled']):
            raise ValueError(
                "switchi_local_mismatch_enabled requires prediction_column_enabled "
                "(the local mismatch trigger uses the existing PC_i prediction "
                "population as its learned prediction signal).")
        self.switchi_trace_decay = float(np.clip(p['switchi_trace_decay'], 0.0, 1.0))
        self.switchi_coincidence_threshold = float(
            np.clip(p['switchi_coincidence_threshold'], 0.0, 1.0))
        self.switchi_shunt_frac = float(np.clip(p['switchi_shunt_frac'], 0.0, 1.0))
        l1i_n_feedback = 1 if self.prediction_column_to_i_enabled else N_OUT
        self.l1 = InputLayer(n_neurons=N_PIX, threshold=thr_l1,
                             refractory_period=p['refractory'], learning_rate=p['learning_rate'],
                             weight_cap=thr_l1, leak_rate=p['leak_l1'],
                             n_feedback_inputs=l1i_n_feedback,
                             n_prediction_inputs=(1 if self.prediction_excitatory_enabled else 0))
        # L1E: pre-trained pixel encoders — fixed weights, no learning.
        # Fixed-point scale: gate -1*UNIT, excitatory drive +1*UNIT, so one pixel
        # spike delivers UNIT charge == thr_l1 and fires the encoder in one hit.
        for e in self.l1.excitatory_neurons:
            replay_tail = [1.0] if self.prediction_excitatory_enabled else []
            e.weights = np.array([-1.0, 1.0, *replay_tail]) * UNIT
            e.learning_rate = 0.0
            e.weight_budget = None
            # The local-inhibition gate (index 0, magnitude UNIT) is meant to sit
            # frozen at saturation: unscaled its quadratic factor 1 - w^2/w_max was
            # exactly 0 (w = w_max = weight_cap). At the UNIT scale that needs
            # w_max = UNIT*weight_cap == weight_cap^2, so the gate still can't drift.
            e.inhibitory_weight_cap = UNIT * e.weight_cap
        # L1I: incoming (L2E->L1I) weights start randomly in [0.25, 0.5] * thr_l1
        # -- well below L1I's own threshold, not at-or-above it -- so L1I
        # behaves as a genuine temporal integrator early on (several distinct
        # L2E->L1I feedback init. Default (None) draws each SOURCE gate in the
        # [0.25, 0.5] integrator range. l1i_ei_init_frac can collapse that range
        # to one fraction for ablation. The vector is shared across the L1I bank
        # below because these neurons receive the same global winner stream and
        # differ only in which L1E pixel they suppress.
        if p['l1i_ei_init_frac'] is None:
            lo_frac, hi_frac = L1_EI_WEIGHT_INIT_LOW_FRAC, L1_EI_WEIGHT_INIT_HIGH_FRAC
        else:
            lo_frac = hi_frac = p['l1i_ei_init_frac']
        # Every L1I receives the same L2E winner stream and is intended to suppress
        # its paired pixel in phase with the rest of the active input. Give the bank
        # one task-independent feedback vector; independent random vectors create
        # arbitrary phase groups with no pixel-local signal that could correct them.
        # Phase 21: sized to l1i_n_feedback (1 under the selective PCi-input
        # topology, N_OUT under the existing global topology) rather than a
        # hardcoded N_OUT.
        l1i_feedback_init = rng_fb.uniform(lo_frac * thr_l1i, hi_frac * thr_l1i,
                                           size=l1i_n_feedback)
        # Phase 21: fixed/pretrained L1I regulation -- a SEPARATE factorial
        # variable from the input-topology flag above. Default OFF preserves
        # the learned random init exactly. When True: every incoming L1I
        # weight (whichever topology) is fixed at L1I's own resolved
        # threshold (one physical source event alone is sufficient), and
        # L1I's own learning_rate is pinned to 0 -- same pattern as Phase
        # 17's pretrained_l2i_recruitment, applied to L1I instead of L2I.
        self.pretrained_l1i_regulation = bool(p['pretrained_l1i_regulation'])
        if self.pretrained_l1i_regulation:
            l1i_feedback_init = np.full(l1i_n_feedback, thr_l1i)
        for inh in self.l1.inhibitory_neurons:
            inh.threshold = thr_l1i    # Phase 2: L1I's own (possibly lowered) threshold
            # InputLayer constructed L1I with L1E's cap. Raise the cap before
            # assigning L2I-scale feedback weights or SynapseBank.set_weights()
            # would clip every initialization value above the old L1E threshold.
            inh.weight_cap = thr_l1i
            inh.weights = l1i_feedback_init.copy()
            inh.leak_rate = L1I_LEAK_RATE if p['l1i_leak_enabled'] else 0.0
            inh.refractory_period = L1I_FEEDBACK_REFRACTORY
            if self.pretrained_l1i_regulation:
                inh.learning_rate = 0.0

        # Phase 19A: nine per-input-column prediction neurons P0..P8 plus a
        # stored 8x9 L2E->P decoder matrix. The decoder weights live on each
        # Pi's incoming vector for serialization convenience, but Phase 19A
        # does NOT update them -- they are scaffold state only. The future
        # unresolved local-learning question is pixel-specific: Pi would need a
        # postsynaptic local "pixel i was present" teaching signal at the
        # moment a causal L2E event arrives, not a global reconstruction loss
        # or pattern label. That signal is not yet specified here.
        self.eta_pred = float(p['eta_pred'])
        self.prediction_replay_enabled = self.prediction_excitatory_enabled
        self.prediction_decoder_control = PRED_CONTROL_NORMAL
        self.prediction_weight_cap = float(UNIT * thr_l1)
        self.prediction_replay_weight = float(UNIT * thr_l1)
        self._prediction_shuffle_perm = tuple(np.roll(np.arange(N_PIX), 1))
        self.l1p: list = []
        if self.prediction_excitatory_enabled:
            for _i in range(N_PIX):
                pn = Neuron(n_inputs=N_OUT, threshold=thr_l1,
                           refractory_period=p['refractory'], learning_rate=0.0,
                           weight_cap=thr_l1, leak_rate=p['leak_l1'])
                pn._weights_array = np.zeros(N_OUT)
                self.l1p.append(pn)
        self._prediction_pending_decoder: list[dict] = []
        self._prediction_pending_replay: list[dict] = []
        self._prediction_last_decoder_arrivals: list[dict] = []
        self._prediction_last_decoder_integrated: list[dict] = []
        self._prediction_last_replay_arrivals: list[dict] = []
        self._prediction_last_replay_deliveries: list[dict] = []

        # Phase 19-v2 (LPS Lecture 14 LOCAL-COINCIDENCE prediction
        # architecture; see Phase18b_Lecture14_Local_Coincidence_Architecture_
        # Contract.md). A SEPARATE, additively-coexisting mechanism from the
        # Phase 19A scaffold immediately above -- different attribute
        # (self.pcol, not self.l1p), different neuron ids (PC0..PC8, not
        # P0..P8), different synapse ids (colfb{j}->{i}/lat{i}, not
        # decoder{j}->{i}/pred{i}->{i}). Mutually exclusive at build time: the
        # two experiments are conceptually incompatible (different afferent
        # counts, different learning triggers, different lateral wiring) and
        # both default off, so nobody would legitimately enable both at once
        # -- this raises loudly rather than silently corrupting self.neurons.
        if p['prediction_excitatory_enabled'] and p['prediction_column_enabled']:
            raise ValueError(
                "prediction_excitatory_enabled (Phase 19A per-column scaffold) "
                "and prediction_column_enabled (Phase 19-v2 local-coincidence "
                "architecture) are mutually exclusive experimental prediction "
                "mechanisms -- enable only one at a time.")
        self._build_prediction_column_population(p, thr_l1)

        # L2E leak is independently switchable from the shared L2I neuron's fast
        # evidence-window leak.
        eff_leak_l2 = p['leak_l2'] if p['leak_enabled'] else 0.0
        # Active L2 has NO learned L2I->L2E gate: build the column without the
        # index-0 local-I placeholder so each L2E has exactly N_PIX pixel afferents.
        # Competition is the causal, delayed L2E->L2I->L2E event (Phase 7:
        # _resolve_l2_competition schedules, _deliver_scheduled_l2_inhibition
        # applies) plus local competitive depression -- see
        # L2_Hard_Reset_Competitive_Depression_Spec.md.
        self.l2 = CorticalColumn(n_neurons=N_OUT, threshold=thr_l2,
                                 refractory_period=p['refractory'], learning_rate=p['learning_rate'],
                                 weight_cap=thr_l2, leak_rate=eff_leak_l2,
                                 include_local_inhibition=False)
        self.l2.setup_connectivity(n_feedforward_inputs=N_PIX, n_feedback_inputs=0)
        self.l2.finalize_connections()
        # E→I weights start randomly in [0.25, 0.5] * threshold_l2 -- not a
        # repeated constant -- so the 8 sources aren't artificially tied at
        # t=0, and every value in that range is still well below threshold_l2
        # so early competition needs several distinct contributors (see the
        # L2_EI_WEIGHT_INIT_LOW_FRAC note above for the full round-robin ->
        # single-trusted-source rationale, and why this MUST scale with
        # threshold_l2 rather than being a fixed absolute constant). The
        # LEARNING ceiling for these synapses is threshold_l2 itself, set
        # per-neuron below -- much higher than this init range -- so growth
        # can carry a habitually-participating synapse to self-sufficiency.
        if p['pretrained_l2i_recruitment']:
            # Phase 17: pre-trained, task-independent recruitment -- every
            # L2E->L2I synapse starts at exactly thr_l2i (the resolved L2I
            # threshold), so ONE ordinary physical L2E spike alone delivers
            # thr_l2i charge via the unscaled instantaneous delivery path
            # (infl_l2e_l2i, the only thing that would attenuate this specific
            # delivery, stays off and untouched by this flag) and makes L2I
            # reach its own threshold immediately. rng_ei is deliberately NOT
            # consumed in this branch (nothing else reads that stream later),
            # so this cannot perturb rng_ff/rng_fb's determinism either way.
            self.l2.set_lateral_excitation_weights(thr_l2i)
        else:
            self.l2.set_lateral_excitation_weights(
                rng_ei.uniform(L2_EI_WEIGHT_INIT_LOW_FRAC * thr_l2i,
                               L2_EI_WEIGHT_INIT_HIGH_FRAC * thr_l2i, size=N_OUT))
        # Small positive feedforward weights: neurons must accumulate across many
        # volleys initially (LIF phase), then specialise toward single-volley firing
        # (pattern integrator phase). 'balanced' is the optional task-independent
        # Sinkhorn init (equal incoming/outgoing totals, mean 125). DEFAULT
        # 'legacy_wide' is the unconstrained Uniform(50,200) developmental draw.
        # Both keep mean 125 and draw from the dedicated feedforward stream (rng_ff).
        if p['l2e_init_mode'] == 'legacy_wide':
            ff_weights = legacy_wide_feedforward_init(rng_ff, N_OUT, N_PIX)
        elif p['l2e_init_mode'] == 'edge_detector_candidate':
            ff_weights = scaled_legacy_wide_feedforward_init(
                rng_ff, N_OUT, N_PIX, target_mean=EDGE_DETECTOR_CANDIDATE_MEAN)
        elif p['l2e_init_mode'] == 'balanced':
            ff_weights = balanced_feedforward_init(rng_ff, N_OUT, N_PIX,
                                                   jitter=p['l2e_init_jitter'],
                                                   target_mean=L2E_INIT_MEAN)
        else:
            raise ValueError(f"unknown l2e_init_mode '{p['l2e_init_mode']}'")
        self.l2.set_feedforward_weights(ff_weights)
        self.l2.inhibitory_neuron.refractory_period = 0
        self.l2.inhibitory_neuron.threshold = thr_l2i   # Phase 2: L2I's own threshold
        # Short evidence-retention window: much faster than L2E's leak_l2 (its
        # slow multi-volley accumulator), controlled by its own dashboard switch.
        self.l2.inhibitory_neuron.leak_rate = (
            L2I_LEAK_RATE if p['l2i_leak_enabled'] else 0.0
        )

        self.neurons: dict[str, object] = {}
        self.meta: dict[str, dict] = {}
        self._register_neurons()
        # Phase 2: reflect the (possibly lowered) inhibitory thresholds in meta
        # so the dashboard/serialization show each I neuron's real threshold.
        self.meta['L2I']['threshold'] = thr_l2i
        for i in range(N_PIX):
            self.meta[f'L1I{i}']['threshold'] = thr_l1i

        # Budget / cap assignment:
        #   L2E → budget = thr_l2 (positive feedforward weights only).
        #   L1E → no budget (weights fixed, learning disabled).
        #   L1I → cap = thr_l1 itself; L2I → cap = thr_l2 itself. Neither is a
        #   fixed sub-threshold constant: each synapse starts far below its
        #   own neuron's threshold (round-robin phase) but is free to learn
        #   all the way up to it, at which point that one synapse alone is
        #   sufficient (see the L1_EI_*/L2_EI_* notes above -- identical
        #   mechanism for both, just scaled to a different threshold).
        #   Neither L1I nor L2I is weight-budgeted (weight_budget stays None,
        #   homeostasis stays off below) -- each incoming synapse is capped
        #   independently, with no renormalization forcing them to trade off
        #   against each other.
        for nid, n in self.neurons.items():
            if self.meta[nid]['type'] == 'E' and nid.startswith('L2'):
                n.weight_budget = L2E_BUDGET_MULT * thr_l2 if p['l2e_budget'] else None
                # Per-afferent capacity rule (minimal experiment): the positive
                # feedforward weight cap is a fraction of THIS E neuron's threshold
                # (l2e_weight_cap_frac * thr_l2), so three maximally strong active
                # afferents can reach threshold (frac=1/3 for the 3-pixel lines).
                # learning_rate and excitatory_saturation_cap below auto-follow the
                # cap. Default 1.0 reproduces the prior cap == thr_l2.
                n.weight_cap = p['l2e_weight_cap_frac'] * thr_l2
                # Floor for feedforward weights: without this, heavy training on
                # one pattern erodes every OTHER pixel's weight toward 0 (budget
                # renormalization rescales participating and non-participating
                # synapses alike on every update), so switching patterns later
                # accumulates no charge even though L1E still fires correctly.
                # L2E_MIN_WEIGHT_FLOOR is an order of magnitude below the
                # feedforward init range (ff_weights ~ [0.05, 0.20]) -- small
                # enough not to distort normal competition, nonzero enough that
                # every pixel keeps some baseline responsiveness.
                n.min_positive_weight = (p['pos_weight_floor'] if p['pos_weight_floor'] is not None
                                         else L2E_MIN_WEIGHT_FLOOR)
                # No learned L2I->L2E gate on the active path: the inhibitory-gate
                # cap/eta and l2_gate_eq_frac are inert (they only configured the
                # removed negative gate). L2 competition is the causal, delayed
                # L2E->L2I->L2E event + competitive depression
                # (Neuron.apply_delayed_inhibition).
                # Charge-based excitatory rule (see Neuron._update_weights);
                # eta scaled to this neuron's own weight_cap -- see ETA_FRAC note.
                # Phase 1: L2E feedforward learning uses its own l2e_lr_frac.
                # (Both auto-scale: learning_rate = frac * weight_cap, and
                # weight_cap is UNIT-scaled, so eta scales by UNIT as required.)
                n.learning_rate = p['l2e_lr_frac'] * n.weight_cap
                # Feedforward quadratic saturation: the (w/w_cap)^2 form, i.e.
                # w_max = weight_cap**2 so the term is 1 - (w/weight_cap)^2 and the
                # equilibrium is weight_cap ITSELF (not sqrt). Moves the per-gate
                # equilibrium from ~2828 to weight_cap (=8000): gates stay far from
                # saturation for longer, so participating pixels can pile more
                # weight onto a neuron's key pixels before the budget clips the
                # sum -- sharper receptive fields / bigger winner-vs-rival margins.
                n.excitatory_saturation_cap = n.weight_cap ** 2
                # Homeostatic synaptic scaling: recruits silent units and tames
                # over-active ones by regulating each neuron's own firing rate to a
                # set-point (see Neuron._homeostatic_scaling). When on, this
                # REPLACES the fixed weight budget as the resource regulator, so the
                # total is set by activity, not a hard constant.
                n.homeostasis = p['homeostasis']
                n.ca_rate = p['ca_rate']
                n.ca_target = p['ca_target']
                n.homeo_up = p['homeo_up']
                n.homeo_down = p['homeo_down']
                n.homeo_budget_min = 500   # 0.5 * UNIT, fixed-point weight resource
                n.homeo_budget_max = 2 * thr_l2
                # Confidence-gated consolidation (see neuron_flexible.Neuron and
                # Claude_Confidence_Consolidation_Plan.md): local, label-free
                # protection of mature specialists + loser depression, on L2E only.
                # conf_cap is the effective reachable mature per-gate value: the 8
                # line primitives each have 3 active pixels, so a fully specialized
                # neuron carries ~thr_l2/3 on each of its active gates (conf_cap_frac
                # = 1/3). It scales with thr_l2, so maturity stays scale-invariant.
                n.confidence_consolidation = p['confidence_consolidation']
                n.loser_depression = p['loser_depression']
                n.conf_cap = p['conf_cap_frac'] * thr_l2
                n.conf_beta = p['conf_beta']
                n.eta_min = p['eta_min']
                n.eta_loss = p['eta_loss']
                n.loss_gamma = p['loss_gamma']
                n.conf_rho_active = p['conf_rho_active']
                n.conf_rho_dead = p['conf_rho_dead']
                n.conf_ca_dead = p['conf_ca_dead']
                n.conf_grace = p['conf_grace']
                # Signed-spike depression ("4a"), L2E only. Default off leaves the
                # existing consolidation stack (confidence + loser depression +
                # budget) untouched; when on, OFF gates are also depressed on fire.
                n.signed_depression = p['signed_depression']
                n.eta_off = p['eta_off']
                # Reset-by-subtraction on fire (L2E only; default off). Leaves the
                # winner its residual overshoot instead of a full reset to rest.
                n.subtractive_reset = p['subtractive_reset']
                # Hard-reset inhibition (L2E only; default off). A real L2I->L2E
                # discharge clamps the loser to rest after inhibitory learning has
                # read its pre-reset charge, eliminating loser charge carryover.
                n.l2i_hard_reset_losers = p['l2i_hard_reset_losers']
                n.hard_reset_clear_traces = p['hard_reset_clear_traces']
                # Membrane saturation ceiling (L2E only; None = unbounded). Bounds
                # accumulated charge near threshold so inhibition can regulate it.
                n.v_sat = p['v_sat_frac'] * thr_l2 if p['v_sat_frac'] else None
                # Minimal signed-spike feedforward learning (L2E only; default off).
                # When on it takes over _update_weights entirely (see the neuron).
                n.signed_spike_learning = p['signed_spike_learning']
                # Structural free-energy plasticity gate (L2E / excitatory only).
                # Scales the signed-spike eta by this neuron's own positive-afferent
                # maturity vs its threshold; default off leaves the p-scaled rule.
                n.structural_free_energy = p['structural_free_energy']
                n.structural_fe_eta_floor = p['structural_fe_eta_floor']
                # Phase 10: adaptive-threshold ablation (L2E only; see Neuron
                # for the a_i mechanics). SEPARATE from self.homeostasis
                # (synaptic-scaling homeostasis) and from geometry -- default
                # off leaves check_threshold byte-identical to every existing
                # caller (see Neuron.check_threshold/effective_threshold).
                n.adaptive_threshold = p['adaptive_threshold']
                n.delta_threshold = p['delta_threshold_frac'] * thr_l2
                n.tau_threshold = p['tau_threshold']
                # Phase 15: local developmental protection from L2I loser
                # depression (L2E only; see Neuron.apply_delayed_inhibition/
                # _loser_depression_maturity). SEPARATE from homeostasis,
                # structural_free_energy, and adaptive_threshold above --
                # default off leaves apply_delayed_inhibition's gain
                # byte-identical to every prior phase.
                n.loser_depression_protection = p['loser_depression_protection']
                n.loser_depression_protection_ca_ref = p['loser_depression_protection_ca_ref']
            else:
                n.weight_budget = None
                if self.meta[nid]['type'] == 'I':
                    # Phase 2: the E->I learning ceiling scales with THIS
                    # inhibitory neuron's own (possibly lowered) threshold, not
                    # the E threshold -- otherwise a single source could exceed a
                    # lowered I threshold and trivially overdrive inhibition.
                    n.weight_cap = thr_l2i if nid.startswith('L2') else thr_l1i
                    # Charge-based excitatory rule for these incoming (E->I)
                    # weights too -- same eta-scaled-to-cap principle as L2E
                    # above. Phase 1: L2I and L1I get separate lr fractions.
                    # Phase 21: this generic per-neuron sweep would otherwise
                    # silently overwrite pretrained_l1i_regulation's own
                    # learning_rate=0.0 pinning (set earlier in _build(), see
                    # the L1I init loop) -- skip it for L1I in that mode,
                    # same discipline as the PC distance-weighting fix above.
                    if nid.startswith('L1') and self.pretrained_l1i_regulation:
                        pass
                    else:
                        lr_frac = p['l2i_lr_frac'] if nid.startswith('L2') else p['l1i_lr_frac']
                        n.learning_rate = lr_frac * n.weight_cap
                    # Decouple the saturation ceiling from the hard clip (see
                    # excitatory_saturation_cap in Neuron). The quadratic
                    # rule dw = eta*p*(1 - w^2/w_max) has its natural equilibrium
                    # (dw=0) at w = sqrt(w_max). With w_max = weight_cap**2 the
                    # equilibrium lands EXACTLY on the clip -- so the weight only
                    # ASYMPTOTES toward the cap (dw -> 0 as w -> cap) and never
                    # actually reaches it. ei_sat_mult > 1 pushes the equilibrium
                    # sqrt(w_max) = weight_cap * sqrt(ei_sat_mult) ABOVE the clip,
                    # so dw stays large as w passes the clip and the HARD clip
                    # catches it AT weight_cap in finite time -- the rule stays
                    # nonlinear/saturating in [0, cap] but now actually reaches
                    # the cap (a trained E->I synapse becomes a true single-source
                    # relay: one presynaptic spike is enough to fire the neuron).
                    n.excitatory_saturation_cap = (n.weight_cap ** 2) * p['ei_sat_mult']
                    # Positive-afferent floor for E->I weights (minimal experiment).
                    # Only floors positive weights; the inhibitory sign is untouched.
                    if p['pos_weight_floor'] is not None:
                        n.min_positive_weight = p['pos_weight_floor']
                    # Flow-proportional assembly credit on this inhibitory neuron's
                    # own fire (L2I / L1I): the E->I "assembly evidence" synapses.
                    if nid.startswith('L1'):
                        # L1I membrane charge integrates a sequence of L2 winners.
                        # Credit every contributor in that same membrane window, not
                        # only the final winner that happened to cross threshold.
                        n.assembly_flow_credit = True
                        n.assembly_decay_frac = 0.0
                    else:
                        n.assembly_flow_credit = p['assembly_flow_credit']
                        n.assembly_decay_frac = p['assembly_decay_frac']
                        # Phase 17: pre-trained recruitment pins L2I's own
                        # incoming-excitatory learning rate to exactly 0, so
                        # ChargeBasedRule's dw = eta*p*(1-w^2/w_max) is always
                        # 0 regardless of which L2E fires -- weights set above
                        # never move again. Nothing else about L2I (its
                        # membrane, threshold check, fire(), or the delayed
                        # L2I->L2E delivery path) is touched here.
                        if p['pretrained_l2i_recruitment']:
                            n.learning_rate = 0.0

        # Uniform per-neuron delivery / flow-rate / inhibitory-gate-rule / distance
        # config. The engine's params are the SOURCE OF TRUTH; NeuronConfig is a
        # transport built from them (from_engine_params) and applied population-aware
        # to each neuron -- replacing the scattered per-attribute assignments. See
        # snn/config.py and REFACTOR_PLAN.md Phase 3d.
        cfg = NeuronConfig.from_engine_params(p)
        for nid, n in self.neurons.items():
            cfg.apply_to(n, is_l1e=nid.startswith('L1E'), is_l1i=nid.startswith('L1I'),
                         is_l2i=(nid == 'L2I'))
        # apply_to sets the distance-weighting FLAGS uniformly; now set the actual
        # per-synapse delivery DISTANCES for L2E from the 3D layout (the only neurons
        # with non-trivial source geometry). Must run after apply_to and after the
        # feedforward weights are finalized (set_weights reset distance to ones).
        self._apply_l2e_distances()
        # Phase 4: the four NEW experimental pathways (L2E->L2I, L2I->L2E,
        # L2E->L1I, L1I->L1E). Must also run after apply_to() -- see that
        # method's docstring for why it forces distance_weighting=False on
        # every non-L2E neuron.
        self._apply_experimental_pathway_distances()

        # Phase 19-v2 fix-up: NeuronConfig.apply_to()'s classification is
        # `is_l2e = not (is_l1e or is_l1i or is_l2i)` (snn/config.py), so any
        # neuron id that doesn't start with 'L1E'/'L1I' and isn't 'L2I' falls
        # through and is (mis)classified as an L2E for distance-weighting
        # purposes -- this generic cfg.apply_to() sweep over self.neurons.
        # items() (above) runs AFTER PCi neurons are constructed, so it would
        # otherwise silently turn on distance_weighting (with the LEGACY
        # L1E->L2E distance_ref, wildly mismatched to PCi's own weight
        # scale) on every PCi, inflating delivered charge by orders of
        # magnitude. Reset explicitly here rather than touching the shared
        # classification logic (out of scope for this phase -- distance/
        # geometry code is not to be changed).
        if self.prediction_column_enabled:
            for pc in self.pcol:
                pc.distance_weighting = False
        if self.prediction_column_persistent_conductance_enabled:
            for e in self.l1.excitatory_neurons:
                e.inhibitory_flow_rate = True
                e.inhibitory_persistent_after_discharge = True
                e.inh_trace_decay = p['inh_trace_decay']
                e.inh_trace_normalized = bool(p['inh_trace_normalized'])

        # One-step feedback delay. L1I spikes produced at t inhibit paired L1E
        # neurons at t+1 only; the register is replaced every step.
        self.l1i_feedback_delay = np.zeros(N_PIX)
        initial_pattern = next(iter(PATTERNS))
        self.input_vec = np.array(PATTERNS[initial_pattern], dtype=float)
        self.timestep = 0
        self.spiked = defaultdict(bool)
        self.freq = {nid: deque(maxlen=FREQ_WINDOW) for nid in self.neurons}
        # Phase 10: adaptive-threshold state/trajectory, L2E only (harmless
        # empty history for any other population, since a_i stays 0 there).
        self.threshold_adapt_history = {
            f'L2E{j}': deque(maxlen=FREQ_WINDOW) for j in range(N_OUT)}
        self.emitted: list[str] = []   # synapse IDs that carried a spike this step
        self._pulses: dict[str, float] = {}
        self._holds: dict[str, float] = {}
        self.event_log: deque = deque(maxlen=LOG_MAX)
        self._log_seq = 0
        self._weights_snapshot = self._all_weights()
        self.changed_synapses: list[dict] = []
        self._confidence_snapshot = self._all_confidence()
        self.changed_confidence: list[dict] = []
        self.l2_drive: dict[str, float] = {}          # PRE-WTA snapshot (peak/margin)
        self.l2_charge: dict[str, float] = {}         # POST-inhibition, pre-update diagnostic
        self.switchi_recent_spike_trace = np.zeros(N_OUT, dtype=float)
        self._switchi_last_events: list[dict] = []
        self._switchi_local_last_events: list[dict] = []
        self.switchi_local_elig = np.zeros((N_OUT, N_PIX), dtype=float)
        self._switchi_local_pending: list[dict] = []
        self._switchi_local_last_requests: list[dict] = []
        self._switchi_local_last_deliveries: list[dict] = []
        self._switchi_local_last_residual: list[dict] = []
        self._switchi_local_last_diag: dict = {}
        self.l2_inh_phase_debug: list[dict] = []      # per-inhibited-L2E phase record (see step())
        # Phase 6: the exposed "representation candidate" -- the presentation's
        # first physical L2E threshold crossing, or None until one occurs, or
        # None for the rest of the presentation if that first response was a
        # same-step tie (see _track_presentation/_start_presentation). Set in
        # EXACTLY one place (_track_presentation); never re-derived by argmax,
        # index, hidden charge, weights, geometry, or UI logic.
        self.winner: str | None = None
        self._inh_events: list[tuple] = []   # (neuron_id, event) from this step's discharges
        self._reset_events: list[tuple] = []  # (neuron_id, record) from delivered L2 inhibition
        # Phase 7: causal L2E->L2I->L2E competition state.
        self._l2i_pending: list[dict] = []        # scheduled deliveries, not yet due
        self._l2i_contributors: list[tuple] = []  # (t, 'L2Ej') events since L2I's last fire
        self._last_l2_inhibition_delivery: dict | None = None
        self._l2_inhibition_log: deque = deque(maxlen=LOG_MAX)

        # Auto-cycle: rotate through the patterns, showing each for a short bounded
        # VISIT, and detect training per pattern. Sitting on one pattern can't
        # work -- continuous single-pattern presentation makes the L2 pool
        # round-robin (adaptive lateral inhibition spreads participation), so no
        # single neuron "wins every time". Specialization only shows as a stable
        # pattern->neuron map ACROSS visits. So each visit accumulates L2E spikes,
        # takes the argmax as that visit's winner, and a pattern is "trained" once
        # its winner is the same neuron for trained_streak consecutive rounds.
        # After each visit the cycle advances to the next pattern; when every
        # pattern is trained, auto-cycle disables itself (curriculum complete).
        self.event_driven = self.params['event_driven']   # fire on threshold crossing every step
        # L2 chunked-charge granularity (see step()): deliver this step's L1->L2E
        # drive in K equal chunks, re-attempting resolution after each. K=1
        # reproduces un-chunked delivery. l2_winner_chunk records which chunk
        # resolved the last competition (diagnostic; None if nobody fired).
        self.l2_charge_chunks = max(1, int(self.params['l2_charge_chunks']))
        self.l2_winner_chunk = None
        # L1I feedback firing mode (see step() 2e): immediate deterministic relay
        # (default) vs. trainable threshold integrator.
        self.l1i_immediate_relay = self.params['l1i_immediate_relay']
        # Sparse excitatory flow-rate accumulation (see step() and Neuron). When on
        # it forces effective l2_charge_chunks = 1 (see step()); per-neuron flow
        # flags are configured on the target integrators after neuron registration.
        self.excitatory_flow_rate = self.params['excitatory_flow_rate']
        # Lasting-inhibition state (see step()): a decaying shared inhibitory field.
        self.lasting_inhibition = self.params['lasting_inhibition']
        self.inh_decay = self.params['inh_decay']
        self.inh_boost = self.params['inh_boost_frac'] * self.params['threshold_l2']
        self.l2_inh_field = 0.0
        # Phase 7: causal L2E->L2I->L2E delayed-delivery config (see the
        # constructor docstring above). Threshold_l2-scaled so a config that
        # lowers/raises threshold_l2 keeps the same relative magnitude.
        self.l2_inhibition_delay = max(0, int(self.params['l2_inhibition_delay']))
        self.l2_inhibition_frac = self.params['l2_inhibition_frac']
        self.l2_inhibition_magnitude = self.l2_inhibition_frac * self.params['threshold_l2']
        self.current_pattern = initial_pattern    # name backing self.input_vec
        self.auto_cycle = False
        self.visit_steps = max(1, self.params['cycle_period'])   # steps per pattern visit
        self.trained_streak = 3                   # consecutive same-winner ROUNDS = trained
        self._cycle_order = list(PATTERNS.keys())
        self._visit_step = 0                      # steps elapsed in the current visit
        self._visit_spikes = np.zeros(N_OUT, dtype=int)
        self._pattern_last_winner: dict[str, int | None] = {n: None for n in PATTERNS}
        self._pattern_streak: dict[str, int] = {n: 0 for n in PATTERNS}
        self._pattern_trained: dict[str, bool] = {n: False for n in PATTERNS}

        # ---- Presentation tracking / probes / evidence bookkeeping (observability
        # only -- read-only diagnostics over already-decided physical events; see
        # _track_presentation, present_probe, _l2e_status). A "presentation" is one
        # named pattern/probe shown via set_pattern/present_probe; raw pixel/random/
        # noise edits do not start one (documented scope: named-pattern protocol
        # only, not free-form manual input).
        self.presentation_id = 0
        self.presentation_role: str = 'train'
        self.presentation_pattern: str = initial_pattern
        self.presentation_start_t = 0
        self._presentation_first_spiker: str | None = None
        self._presentation_first_spike_t: int | None = None
        self._presentation_tie = False
        # Phase 6: earliestResponseSet (exact set, not just the tie boolean
        # above), the ordered later responses, and the latency to the second
        # DISTINCT responder -- see _track_presentation/_start_presentation.
        self._presentation_earliest_response_set: list[str] = []
        self._presentation_later_responses: list[tuple[int, str]] = []
        self._presentation_latency_to_second: int | None = None
        self._presentation_l1i_first_source: str | None = None
        self._presentation_l1i_first_t: int | None = None
        # Phase 9: causal L1I predictive-feedback chain (see _start_presentation).
        self._presentation_l1i_first_source_set: list[str] = []
        self._presentation_l1i_first_arrival_t: int | None = None
        self._presentation_l1i_first_targets: list[str] = []
        self._presentation_l1i_first_delivery: dict | None = None
        self._l1i_delivery_capture_pending = False
        self._presentation_l2i_first_source: str | None = None
        self._presentation_l2i_first_t: int | None = None
        self._presentation_last_l2_winner: int | None = None
        self._last_eligible: list[int] = []
        self.presentation_log: deque = deque(maxlen=50)
        self._pattern_first_responder_log: dict[str, deque] = {}
        self._neuron_first_responder_counts: dict[str, dict[str, int]] = {}
        self._neuron_total_spikes: dict[str, int] = defaultdict(int)
        self._neuron_last_fired_t: dict[str, int] = {}

        # Presentation-scoped plasticity freeze (see Neuron.plasticity_frozen and
        # present_probe). Mirrored onto every neuron by _set_plasticity_frozen.
        self.plasticity_frozen = False
        self._probe_active = False
        self.probe_steps_total = 0
        self._probe_steps_elapsed = 0
        self._probe_resume_pattern: str | None = None
        self._probe_resume_input: np.ndarray | None = None
        # Phase 10: pre-probe snapshot of each L2E's adaptive-threshold state
        # a_i (see present_probe/_end_probe) -- None when no probe is active.
        self._probe_threshold_adapt_snapshot: dict[int, float] | None = None

        # Establishes presentation #1 (id goes 0 -> 1; nothing to log yet).
        self._start_presentation(initial_pattern, 'train')

        self._log('backend', f'network built (seed={p["seed"]}, immediate delivery, '
                             f'{len(self.neurons)} neurons, {len(self.synapses)} synapses)')

    def _build_prediction_column_population(self, p, thr_l1):
        """Build nine two-compartment coincidence pyramidal cells.

        L1Ei explicitly targets PCi's fixed BASAL compartment.  Every L2Ej
        explicitly targets every PCi's plastic APICAL compartment through
        decoder d[j,i].  Their ordinary neuron soma receives charge only after
        same-delivery-step coincidence.  The default-off path builds nothing.
        """
        self.prediction_column_enabled = bool(p['prediction_column_enabled'])
        self.prediction_lateral_weight = float(p['prediction_lateral_weight'])
        self.prediction_feedback_init = float(p['prediction_feedback_init'])
        self.prediction_feedback_max = float(p['prediction_feedback_max'])
        self.prediction_learning_rate = float(p['prediction_learning_rate'])
        self.prediction_threshold = float(p['prediction_threshold'])
        # DIAGNOSTIC CONTROL ONLY (Part 5's explicit no-leak-diagnostic
        # requirement): forces the membrane leak to 0.0 regardless of
        # prediction_leak, to reproduce the unbounded-accumulation failure
        # mode that motivates having a real leak at all. Never used outside
        # that one diagnostic test/run.
        self.prediction_leak = (0.0 if p['prediction_leak_diagnostic_disable']
                                else float(p['prediction_leak']))
        self.prediction_feedback_delay = max(1, int(p['prediction_feedback_delay']))
        self.pcol: list = []
        if self.prediction_column_enabled:
            for _i in range(N_PIX):
                soma = Neuron(n_inputs=1, threshold=self.prediction_threshold,
                           refractory_period=p['refractory'], learning_rate=0.0,
                           weight_cap=self.prediction_feedback_max,
                           leak_rate=self.prediction_leak)
                soma._weights_array = np.array([1.0])
                pc = CoincidencePyramidalCell(
                    soma=soma, basal_source=f'L1E{_i}',
                    apical_sources=[f'L2E{j}' for j in range(N_OUT)],
                    basal_weight=self.prediction_lateral_weight,
                    apical_weights=[self.prediction_feedback_init] * N_OUT,
                    coincidence_threshold=self.prediction_threshold)
                self.pcol.append(pc)
        # Delayed FIFO queues carrying the queued R_j->PCi feedback AND
        # S_i->PCi lateral delivery vectors TOGETHER -- same one-step-
        # register precedent as l1i_feedback_delay, generalized to
        # prediction_feedback_delay steps. Invariant: exactly
        # `prediction_feedback_delay` vectors are always queued in EACH deque
        # between step() calls -- each step popleft()s both fronts (the pair
        # queued exactly `delay` steps ago, from the SAME originating step)
        # for delivery, then append()s this step's own l2e/l1e pair to both
        # backs. Pre-filled with `delay` zero vectors so the first `delay`
        # steps correctly deliver nothing (no S_i/L2Ej has fired yet).
        # CORRECTED TIMING (per the offline feasibility review): the lateral
        # S_i->PCi connection is delayed EXACTLY like the feedback path --
        # there is no same-step lateral delivery in this engine (see step()
        # for the full rationale).
        self.l2e_to_pcol_queue = deque(
            np.zeros(N_OUT) for _ in range(self.prediction_feedback_delay))
        self.s_to_pcol_queue = deque(
            np.zeros(N_PIX) for _ in range(self.prediction_feedback_delay))
        # Passive provenance travels beside (and never controls) the two
        # physical vectors.  One metadata list occupies each delay slot.
        self.pcol_delivery_metadata_queue = deque(
            [] for _ in range(self.prediction_feedback_delay))
        self._prediction_column_last_deliveries = []
        self._prediction_column_last_output_delivery = []
        self._prediction_column_last_conductance = []

    def _prediction_column_origin_class(self, records, pixel_index):
        """Classify an arrived physical pair without affecting its delivery."""
        origins = {record['origin_pattern'] for record in records
                   if record.get('origin_pattern') is not None}
        if len(origins) > 1:
            return 'mixed'
        if not origins or self.current_pattern in origins:
            return 'current-correct'
        origin = next(iter(origins))
        origin_vector = PATTERNS.get(origin, PROBES.get(origin, [0] * N_PIX))
        current_vector = PATTERNS.get(
            self.current_pattern, PROBES.get(self.current_pattern, [0] * N_PIX))
        if origin_vector[pixel_index] and current_vector[pixel_index]:
            return 'stale-same-pixel'
        return 'stale-wrong-pixel'

    def _apply_prediction_column_learning(self, pc):
        """Update only physically delivered apical decoder connections.

        A same-step basal event gates learning.  No trace, label, ownership,
        rival, or nonlocal state participates.  The firing decision is resolved
        before this method, so it always uses d_before_learning.
        """
        if not (pc.basal.active and pc.apical.active):
            return
        w_max = self.prediction_feedback_max
        for connection in pc.apical_connections:
            if not any(event.source == connection.source and event.signal > 0.0
                       for event in pc.apical.deliveries):
                continue
            growth = self.prediction_learning_rate * (1.0 - connection.weight / w_max) ** 2
            connection.weight = float(np.clip(connection.weight + growth, 0.0, w_max))

    def _compute_geometry(self):
        """Returns (l1e_xy, l1i_xy, l2e_xy), each an (n,2) array of (x,y) --
        z is fixed per population (0.0 / -2.0 / _Z) and applied by the caller,
        matching the legacy layout. `symmetric_geometry=True` reproduces the
        EXACT legacy deterministic positions (byte-identical); False draws the
        seeded jittered/irregular geometry from `topology_seed` via a
        dedicated RNG stream (independent of the weight-init `seed`)."""
        if self.params['symmetric_geometry']:
            legacy_xy = _legacy_l1_xy()
            return legacy_xy, legacy_xy.copy(), np.array([[x, y] for x, y, _ in L2_HOMES])
        rng_l1e, rng_l1i, rng_l2e = (np.random.default_rng(s) for s in
                                     np.random.SeedSequence(self.params['topology_seed']).spawn(3))
        l1e_xy = _jittered_l1e_xy(rng_l1e)
        l1i_xy = _paired_l1i_xy(rng_l1i, l1e_xy)
        l2e_xy = _irregular_l2e_xy(rng_l2e)
        return l1e_xy, l1i_xy, l2e_xy

    def _register_neurons(self):
        # Engine-owned geometry (Phase 3): computed once here per _build(), and
        # cached on self._geometry_xy so _apply_l2e_distances (and any future
        # diagnostic) can reuse the SAME positions rather than redrawing them --
        # positions are otherwise deterministic given topology_seed, but caching
        # avoids a second RNG draw sequence entirely.
        l1e_xy, l1i_xy, l2e_xy = self._compute_geometry()
        self._geometry_xy = dict(l1e=l1e_xy, l1i=l1i_xy, l2e=l2e_xy)
        for i in range(N_PIX):
            nid = f'L1E{i}'
            self.neurons[nid] = self.l1.excitatory_neurons[i]
            self.meta[nid] = dict(id=nid, label=f'in {i}', layer='L1', type='E',
                                  threshold=self.params['threshold'],
                                  pos=[round(float(l1e_xy[i, 0]), 4), round(float(l1e_xy[i, 1]), 4), 0.0])
        for i in range(N_PIX):
            nid = f'L1I{i}'
            self.neurons[nid] = self.l1.inhibitory_neurons[i]
            self.meta[nid] = dict(id=nid, label=f'inh {i}', layer='L1', type='I',
                                  threshold=self.params['threshold'],
                                  pos=[round(float(l1i_xy[i, 0]), 4), round(float(l1i_xy[i, 1]), 4), -2.0])
        if self.prediction_excitatory_enabled:
            for i in range(N_PIX):
                nid = f'P{i}'
                self.neurons[nid] = self.l1p[i]
                self.meta[nid] = dict(id=nid, label=f'pred {i}', layer='L1', type='P',
                                      pixel_index=i, threshold=self.params['threshold'],
                                      pos=[round(float(l1e_xy[i, 0]), 4), round(float(l1e_xy[i, 1]), 4), 1.0])
        if self.prediction_column_enabled:
            for i in range(N_PIX):
                nid = f'PC{i}'
                self.neurons[nid] = self.pcol[i]
                self.meta[nid] = dict(id=nid, label=f'pred-col {i}', layer='L1', type='P',
                                      pixel_index=i, threshold=self.prediction_threshold,
                                      pos=[round(float(l1e_xy[i, 0]), 4), round(float(l1e_xy[i, 1]), 4), 1.5])
        for j in range(N_OUT):
            nid = f'L2E{j}'
            self.neurons[nid] = self.l2.excitatory_neurons[j]
            self.meta[nid] = dict(id=nid, label=f'out {j}', layer='L2', type='E',
                                  threshold=self.params['threshold_l2'],
                                  pos=[round(float(l2e_xy[j, 0]), 4), round(float(l2e_xy[j, 1]), 4), _Z])
        self.neurons['L2I'] = self.l2.inhibitory_neuron
        # L2I stays fixed at the exact center -- brief SS6 allows this ("does not
        # need mathematical perfection... central placement reduces extreme
        # unfairness"); no jitter is applied to the single global neuron.
        self.meta['L2I'] = dict(id='L2I', label='inhib', layer='L2', type='I',
                                threshold=self.params['threshold_l2'], pos=[0.0, 0.0, 6.0])

        self.synapses: list[dict] = []
        for j in range(N_OUT):
            for i in range(N_PIX):
                self.synapses.append(dict(id=f'ff{i}->{j}', source=f'L1E{i}', target=f'L2E{j}', kind='feedforward'))
        # Structural (unweighted) L2I->L2E delayed-inhibition fanout: conveys the
        # scheduled/delivered event (Phase 7), NOT a synaptic weight. It stays
        # visible (the inhibitory fanout still exists) but carries weight=null
        # and never appears in weight snapshots, weight-change tracking, or the
        # weights graph.
        for j in range(N_OUT):
            self.synapses.append(dict(id=f'reset->{j}', source='L2I', target=f'L2E{j}',
                                      kind='reset_inhibition'))
        for j in range(N_OUT):
            self.synapses.append(dict(id=f'{j}->inh', source=f'L2E{j}', target='L2I', kind='excitation'))
        for i in range(N_PIX):
            self.synapses.append(dict(id=f'li{i}', source=f'L1I{i}', target=f'L1E{i}', kind='inhibition'))
        # Phase 21: the selective PCi->Ii topology REPLACES the global
        # N_OUT-wide L2E->L1I feedback fanout with a single one-to-one
        # PCi->L1Ii synapse per column (kind='col_inhibition_feedback') --
        # L1Ii's own incoming array is genuinely 1-wide in that mode (see
        # _build()), so the old N_OUT `fb{j}->{i}` ids would not correspond
        # to anything real.
        if self.prediction_column_to_i_enabled:
            for i in range(N_PIX):
                self.synapses.append(dict(id=f'pcinh{i}', source=f'PC{i}',
                                          target=f'L1I{i}', kind='col_inhibition_feedback'))
        else:
            for j in range(N_OUT):
                for i in range(N_PIX):
                    self.synapses.append(dict(id=f'fb{j}->{i}', source=f'L2E{j}', target=f'L1I{i}', kind='feedback'))
        if self.prediction_excitatory_enabled:
            for j in range(N_OUT):
                for i in range(N_PIX):
                    self.synapses.append(dict(id=f'decoder{j}->{i}', source=f'L2E{j}',
                                              target=f'P{i}', kind='decoder'))
            for i in range(N_PIX):
                self.synapses.append(dict(id=f'pred{i}->{i}', source=f'P{i}',
                                          target=f'L1E{i}', kind='prediction_replay'))
        if self.prediction_column_enabled:
            for j in range(N_OUT):
                for i in range(N_PIX):
                    self.synapses.append(dict(id=f'colfb{j}->{i}', source=f'L2E{j}',
                                              target=f'PC{i}', target_compartment='apical',
                                              kind='col_feedback'))
            for i in range(N_PIX):
                self.synapses.append(dict(id=f'lat{i}', source=f'L1E{i}',
                                          target=f'PC{i}', target_compartment='basal',
                                          kind='col_lateral'))

    def _apply_l2e_distances(self):
        """Populate each L2E's per-afferent DELIVERY distance: euclidean(L2E_home,
        pixel_pos) for the nine pixel afferents (index i; the active L2E has no
        index-0 placeholder). With distance_weighting on, the delivered charge is
        weight * (distance_ref/max(d,distance_min))^distance_power, so a farther
        pixel contributes less -- charge dissipates along the 'axon'. Stored
        weights are untouched; this scales DELIVERY only.

        TEMPORARY (Phase 3 `legacy_distance_compat`, default True; see the module
        comment above L1_JITTER_FRAC): the reference geometry used HERE is the
        legacy ring/grid (L2_HOMES + _legacy_l1_xy()), regardless of whether
        `symmetric_geometry` is on -- so distance_weighting's already-live effect
        on delivered charge stays numerically identical to the pre-Phase-3
        baseline no matter which geometry is actually placed/rendered. When False,
        distances are computed from the REAL positions in self._geometry_xy
        (set by _register_neurons/reseed_topology) -- Phase 4's intended path."""
        if self.params['legacy_distance_compat']:
            pix_xy = _legacy_l1_xy()
            homes_xyz = np.array([[x, y, z] for x, y, z in L2_HOMES])
        else:
            pix_xy = self._geometry_xy['l1e']
            homes_xyz = np.column_stack([self._geometry_xy['l2e'], np.full(N_OUT, _Z)])
        pix_xyz = np.column_stack([pix_xy, np.zeros(N_PIX)])
        for j in range(N_OUT):
            n = self.l2.excitatory_neurons[j]
            if n._weights_array is None or len(n._weights_array) == 0:
                continue
            n.distance = np.linalg.norm(pix_xyz - homes_xyz[j], axis=1)

    def _apply_experimental_pathway_distances(self):
        """Phase 4: real-geometry distance/influence for the four NEW,
        independently-ablated experimental pathways (L2E->L2I, L2I->L2E,
        L2E->L1I, L1I->L1E). Completely separate from the legacy L1E->L2E
        distance_weighting/legacy_distance_compat machinery above, which this
        method never touches. Must run AFTER cfg.apply_to() in _build() --
        NeuronConfig.apply_to() explicitly sets distance_weighting=False on
        every non-L2E neuron (see snn/config.py), so this is the thing that
        turns it back on, population-by-population, for whichever of these
        four flags is actually enabled. Called from both _build() and
        reseed_topology() so a topology-only reseed keeps these pathways in
        sync with the current geometry too.

        L1I->L1E note: each L1E's afferent array is [inhibitory gate (index 0,
        from its paired L1I), external pixel (index 1, abstract, no spatial
        meaning)]. Index 1's distance is set to `infl_ref` exactly, which makes
        its (ref/max(ref,min))^power delivery factor == 1.0 regardless of
        geometry -- effective_weights() (used by receive_input, NOT by
        apply_inhibition) must never attenuate the sensory pixel channel."""
        p = self.params
        power, ref, d_min = p['infl_power'], p['infl_ref'], p['infl_min']

        l2e_xy, l1i_xy, l1e_xy = (self._geometry_xy['l2e'], self._geometry_xy['l1i'],
                                  self._geometry_xy['l1e'])
        l2e_xyz = np.column_stack([l2e_xy, np.full(N_OUT, _Z)])
        l1i_xyz = np.column_stack([l1i_xy, np.full(N_PIX, -2.0)])
        l1e_xyz = np.column_stack([l1e_xy, np.zeros(N_PIX)])
        l2i_xyz = np.array([0.0, 0.0, 6.0])

        # ---- L2E <-> L2I: one shared distance array, two independent pathways ----
        d_l2e_l2i = np.linalg.norm(l2e_xyz - l2i_xyz, axis=1)          # (N_OUT,)
        l2i = self.l2.inhibitory_neuron
        l2i.distance_weighting = bool(p['infl_l2e_l2i'])
        l2i.distance_power, l2i.distance_ref, l2i.distance_min = power, ref, d_min
        l2i.distance = d_l2e_l2i
        infl_l2e_l2i_vals = _power_law_influence(d_l2e_l2i, ref, d_min, power)
        for j, e in enumerate(self.l2.excitatory_neurons):
            e.competitive_reset_influence = (
                float(infl_l2e_l2i_vals[j]) if p['infl_l2i_l2e'] else 1.0)

        # ---- L2E -> L1I: per-L1I distance row to all N_OUT L2E ----
        # Phase 21: under the selective PCi->Ii topology, L1Ii's incoming
        # array is genuinely 1-wide (its own paired PCi only, not any L2E) --
        # the N_OUT-shaped geometric L2E->L1I distance concept does not
        # apply to that single, same-column connection, so this pathway's
        # distance-weighting stays off and untouched for L1I in that mode
        # (matches distance_weighting's own class default -- never swept in
        # here, same discipline as the PC distance-weighting fix above).
        if not self.prediction_column_to_i_enabled:
            for i, inh in enumerate(self.l1.inhibitory_neurons):
                d_row = np.linalg.norm(l2e_xyz - l1i_xyz[i], axis=1)      # (N_OUT,)
                inh.distance_weighting = bool(p['infl_l2e_l1i'])
                inh.distance_power, inh.distance_ref, inh.distance_min = power, ref, d_min
                inh.distance = d_row

        # ---- L1I -> L1E: paired distance (index 0 real, every excitatory input
        # slot neutralized so sensory and optional replay channels never inherit
        # this inhibitory-path attenuation bookkeeping) ----
        for i, e in enumerate(self.l1.excitatory_neurons):
            d_pair = float(np.linalg.norm(l1e_xyz[i] - l1i_xyz[i]))
            e.distance_weighting = bool(p['infl_l1i_l1e'])
            e.distance_power, e.distance_ref, e.distance_min = power, ref, d_min
            e.distance = np.array([d_pair, *([ref] * (len(e.weights) - 1))])

        # Cached for pathway_influence_report() -- avoids recomputing geometry.
        self._pathway_geometry = dict(l2e_xyz=l2e_xyz, l1i_xyz=l1i_xyz,
                                      l1e_xyz=l1e_xyz, l2i_xyz=l2i_xyz,
                                      d_l2e_l2i=d_l2e_l2i)

    def pathway_influence_report(self) -> dict:
        """Full per-connection distance/influence audit across all FIVE
        pathways (brief SS7): source, target, distance, influence, raw weight,
        effective transmission, and whether influence is actually being
        applied (each pathway's own ablation flag) -- plus min/median/max
        influence and a `safe` flag per pathway. L1E->L2E reuses the existing
        legacy distance_weighting/legacy_distance_compat machinery (Phase 2/3,
        UNCHANGED). L2I->L2E has no learned weight (a fixed-magnitude, causally
        delayed structural event -- see l2_inhibition_frac/_delay): raw_weight/
        effective are reported as None there -- influence scales ONLY the
        competitive-depression gain (see Neuron.apply_delayed_inhibition),
        never the delivered inhibitory magnitude itself."""
        p = self.params
        report: dict[str, dict] = {}

        # ---- L1E -> L2E (legacy pathway; Phase 2/3, unchanged) ----
        delivery = self._delivery_diagnostics()
        entries = []
        applied = bool(p['distance_weighting'])
        for j in range(N_OUT):
            for i in range(N_PIX):
                d = delivery.get(f'ff{i}->{j}')
                if d is None:
                    continue
                entries.append(dict(source=f'L1E{i}', target=f'L2E{j}',
                                    distance=d['distance'], influence=d['influence'],
                                    raw_weight=round(float(self.l2.excitatory_neurons[j]._weights_array[i]), 4),
                                    effective=d['effective'], applied=applied))
        report['l1e_l2e'] = _summarize_pathway(entries)

        # ---- L2E -> L2I / L2I -> L2E (share one distance array) ----
        d_arr = self._pathway_geometry['d_l2e_l2i']
        infl_arr = _power_law_influence(d_arr, p['infl_ref'], p['infl_min'], p['infl_power'])
        l2i = self.l2.inhibitory_neuron

        applied = bool(p['infl_l2e_l2i'])
        entries = []
        for j in range(N_OUT):
            w = float(l2i._weights_array[j])
            eff = w * float(infl_arr[j]) if applied else w
            entries.append(dict(source=f'L2E{j}', target='L2I',
                                distance=round(float(d_arr[j]), 4),
                                influence=round(float(infl_arr[j]), 4),
                                raw_weight=round(w, 4), effective=round(eff, 4),
                                applied=applied))
        report['l2e_l2i'] = _summarize_pathway(entries)

        applied = bool(p['infl_l2i_l2e'])
        entries = []
        for j in range(N_OUT):
            entries.append(dict(source='L2I', target=f'L2E{j}',
                                distance=round(float(d_arr[j]), 4),
                                influence=round(float(infl_arr[j]), 4),
                                raw_weight=None, effective=None, applied=applied))
        report['l2i_l2e'] = _summarize_pathway(entries)

        # ---- L2E -> L1I ----
        l2e_xyz, l1i_xyz = self._pathway_geometry['l2e_xyz'], self._pathway_geometry['l1i_xyz']
        applied = bool(p['infl_l2e_l1i'])
        entries = []
        for i, inh in enumerate(self.l1.inhibitory_neurons):
            d_row = np.linalg.norm(l2e_xyz - l1i_xyz[i], axis=1)
            infl_row = _power_law_influence(d_row, p['infl_ref'], p['infl_min'], p['infl_power'])
            for j in range(N_OUT):
                w = float(inh._weights_array[j])
                eff = w * float(infl_row[j]) if applied else w
                entries.append(dict(source=f'L2E{j}', target=f'L1I{i}',
                                    distance=round(float(d_row[j]), 4),
                                    influence=round(float(infl_row[j]), 4),
                                    raw_weight=round(w, 4), effective=round(eff, 4),
                                    applied=applied))
        report['l2e_l1i'] = _summarize_pathway(entries)

        # ---- L1I -> L1E (paired; index 0 only, the real inhibitory gate) ----
        l1e_xyz = self._pathway_geometry['l1e_xyz']
        applied = bool(p['infl_l1i_l1e'])
        entries = []
        for i, e in enumerate(self.l1.excitatory_neurons):
            d_pair = float(np.linalg.norm(l1e_xyz[i] - l1i_xyz[i]))
            infl = float(_power_law_influence(d_pair, p['infl_ref'], p['infl_min'], p['infl_power']))
            w = float(-e._weights_array[0])   # magnitude (stored as a negative gate)
            eff = w * infl if applied else w
            entries.append(dict(source=f'L1I{i}', target=f'L1E{i}',
                                distance=round(d_pair, 4), influence=round(infl, 4),
                                raw_weight=round(w, 4), effective=round(eff, 4),
                                applied=applied))
        report['l1i_l1e'] = _summarize_pathway(entries)

        return report

    # --------------------------------------------------------------- controls
    def reset(self):
        self._build()

    def reseed(self):
        """Draw a fresh random seed and rebuild from new random initial weights,
        preserving every other tunable -- so it works under ANY plasticity/config
        combination (only the seed-driven random draws change: L2E feedforward,
        E->I, L1I). Like reset(), this rebuilds the network and wipes learned
        state -- reseeding *is* a randomized reset. Returns the new seed (which
        becomes the current seed, so a subsequent Reset reproduces this network)."""
        self.params['seed'] = int(np.random.SeedSequence().generate_state(1)[0])
        self._build()
        return self.params['seed']

    def reseed_topology(self):
        """Draw a fresh topology seed and regenerate ONLY the engine's geometry
        (positions) -- unlike reset()/reseed(), this does NOT rebuild the
        network: every learned weight, confidence value, and in-progress
        pattern/probe/auto-cycle state is left exactly as it was. This is the
        ONLY thing that changes engine-owned coordinates outside of
        `symmetric_geometry` toggling (positions are otherwise deterministic
        given topology_seed, so they stay fixed across reset/training/probes --
        see the module comment above L1_JITTER_FRAC). Returns the new
        topology_seed. A no-op on the actual positions when
        symmetric_geometry=True (the legacy layout has no seed dependence)."""
        self.params['topology_seed'] = int(np.random.SeedSequence().generate_state(1)[0])
        l1e_xy, l1i_xy, l2e_xy = self._compute_geometry()
        self._geometry_xy = dict(l1e=l1e_xy, l1i=l1i_xy, l2e=l2e_xy)
        for i in range(N_PIX):
            self.meta[f'L1E{i}']['pos'] = [round(float(l1e_xy[i, 0]), 4), round(float(l1e_xy[i, 1]), 4), 0.0]
            self.meta[f'L1I{i}']['pos'] = [round(float(l1i_xy[i, 0]), 4), round(float(l1i_xy[i, 1]), 4), -2.0]
        for j in range(N_OUT):
            self.meta[f'L2E{j}']['pos'] = [round(float(l2e_xy[j, 0]), 4), round(float(l2e_xy[j, 1]), 4), _Z]
        self._apply_l2e_distances()   # keep distance state consistent with the (possibly legacy-pinned) reference
        self._apply_experimental_pathway_distances()   # Phase 4: keep the four new pathways in sync too
        self._log('control', f'topology reseeded (topology_seed={self.params["topology_seed"]})')
        return self.params['topology_seed']

    # Parameters the dashboard is allowed to change live. Anything not listed here
    # is rejected so a stray key can't silently no-op or corrupt self.params.
    TUNABLE = ('signed_depression', 'eta_off', 'l2e_budget', 'l2e_lr_frac',
               'confidence_consolidation', 'loser_depression', 'eta_loss',
               'eta_min', 'conf_cap_frac', 'leak_l2', 'event_driven',
               'subtractive_reset', 'l2i_hard_reset_losers',
               'hard_reset_clear_traces', 'refractory', 'v_sat_frac',
               'signed_spike_learning', 'structural_free_energy',
               'structural_fe_eta_floor', 'seed', 'l2_charge_chunks',
               'l1i_immediate_relay', 'excitatory_flow_rate',
               'l2i_excitatory_flow_rate', 'exc_trace_decay',
               'exc_trace_normalized', 'inhibitory_flow_rate', 'inh_trace_decay',
               'inh_trace_normalized', 'inhibitory_delta_rule', 'inhibitory_rule_mode',
               'inhibitory_eta_up', 'inhibitory_eta_down', 'inhibitory_p_max',
               'inhibitory_margin_frac', 'inhibitory_delta_eta',
               'distance_weighting', 'distance_power', 'distance_ref', 'distance_min',
               'assembly_flow_credit', 'assembly_decay_frac',
               'l2e_init_mode', 'l2e_init_jitter', 'leak_enabled',
               'l2i_leak_enabled', 'l1i_leak_enabled',
               # Phase 3 geometry ablation toggles. topology_seed is deliberately
               # NOT here -- it has its own dedicated verb, reseed_topology(),
               # not the generic config panel (see that method's docstring).
               'symmetric_geometry', 'legacy_distance_compat',
               # Phase 4: the four NEW experimental pathways' own ablation flags
               # plus their one shared, configurable power law.
               'infl_l2e_l2i', 'infl_l2i_l2e', 'infl_l2e_l1i', 'infl_l1i_l1e',
               'infl_power', 'infl_ref', 'infl_min',
               # Phase 7: causal L2E->L2I->L2E delayed-inhibition scheduling.
               'l2_inhibition_delay', 'l2_inhibition_frac',
               # Phase 10: adaptive-threshold ablation (separate from homeostasis).
               'adaptive_threshold', 'delta_threshold_frac', 'tau_threshold',
               # Phase 15: local developmental protection from L2I loser
               # depression (separate from homeostasis/structural_free_energy/
               # adaptive_threshold).
               'loser_depression_protection', 'loser_depression_protection_ca_ref',
               # Phase 17: pre-trained, task-independent L2E->L2I recruitment
               # (LPS Lecture 14 mapping; separate from every mechanism above).
               'pretrained_l2i_recruitment',
               # Phase 19: corrected per-input-column prediction architecture
               # (LPS Lecture 14 mapping; separate from every mechanism above).
               'prediction_excitatory_enabled', 'eta_pred',
               # Phase 19-v2: local-coincidence prediction-column architecture
               # (LPS Lecture 14 mapping; mutually exclusive with the flag
               # immediately above -- see _build_prediction_column_population).
               'prediction_column_enabled', 'prediction_lateral_weight',
               'prediction_feedback_init', 'prediction_feedback_max',
               'prediction_learning_rate', 'prediction_threshold',
               'prediction_leak', 'prediction_feedback_delay',
               'prediction_leak_diagnostic_disable',
               # Phase 21: selective local predictive inhibition (PCi->Ii),
               # kept as two SEPARATE factorial variables.
               'prediction_column_to_i_enabled',
               'prediction_column_to_i_delivery_enabled',
               'prediction_column_persistent_conductance_enabled',
               # Phase 37: paired L2 oracle-feasibility shunt.
               'switchi_paired_shunt_enabled', 'switchi_trace_decay',
               'switchi_coincidence_threshold', 'switchi_shunt_frac',
               'pretrained_l1i_regulation')

    def apply_config(self, overrides: dict):
        """Merge tunable overrides into self.params and rebuild the network in
        place (same object -- all external references stay valid). Rebuilding
        restarts learning from fresh weights, which is the intended semantics of
        changing a structural/plasticity parameter. Unknown keys are ignored;
        bool/int params are coerced from the JSON the frontend sends."""
        applied = {}
        for k, v in overrides.items():
            if k not in self.TUNABLE:
                continue
            if k in ('signed_depression', 'confidence_consolidation', 'loser_depression',
                     'l2e_budget', 'event_driven', 'subtractive_reset',
                     'l2i_hard_reset_losers', 'hard_reset_clear_traces',
                     'signed_spike_learning', 'structural_free_energy',
                     'l1i_immediate_relay',
                     'excitatory_flow_rate', 'l2i_excitatory_flow_rate',
                     'exc_trace_normalized',
                     'inhibitory_flow_rate', 'inh_trace_normalized',
                     'inhibitory_delta_rule', 'distance_weighting',
                     'assembly_flow_credit', 'leak_enabled', 'l2i_leak_enabled',
                     'l1i_leak_enabled', 'symmetric_geometry', 'legacy_distance_compat',
                     'infl_l2e_l2i', 'infl_l2i_l2e', 'infl_l2e_l1i', 'infl_l1i_l1e',
                     'adaptive_threshold', 'loser_depression_protection',
                     'pretrained_l2i_recruitment', 'prediction_excitatory_enabled',
                     'prediction_column_enabled', 'prediction_leak_diagnostic_disable',
                     'prediction_column_to_i_enabled',
                     'prediction_column_to_i_delivery_enabled',
                     'prediction_column_persistent_conductance_enabled',
                     'switchi_paired_shunt_enabled',
                     'pretrained_l1i_regulation'):
                v = bool(v)
            elif k in ('seed', 'refractory', 'l2_charge_chunks', 'l2_inhibition_delay',
                       'prediction_feedback_delay'):
                v = int(v)
            elif k == 'l2e_init_mode':
                # Exposed as a dashboard TOGGLE (bool): on -> balanced, off ->
                # legacy_wide. A raw string is also accepted (programmatic callers).
                v = ('balanced' if v else 'legacy_wide') if isinstance(v, bool) else str(v)
            elif k == 'inhibitory_rule_mode':
                v = str(v)
            else:
                v = float(v)
            self.params[k] = v
            applied[k] = v
        self._build()
        self._log('control', f'config applied: {applied}')
        return applied

    def set_feedforward_weight(self, j: int, i: int, weight: float) -> float:
        """Manually set L2E neuron j's feedforward weight FROM pixel i (afferent index
        i; the active L2E has no index-0 placeholder), clipped to [0, this neuron's
        per-afferent cap]. Used by the dashboard RF panel to push a neuron toward
        winner/loser by hand -- typically while paused, then step/resume to see the
        effect. Returns the applied (clipped) value."""
        if not (0 <= j < N_OUT and 0 <= i < N_PIX):
            raise IndexError(f"L2E index j={j} or pixel i={i} out of range")
        n = self.l2.excitatory_neurons[j]
        cap = float(n.weight_cap)
        w = float(np.clip(weight, 0.0, cap))
        arr = n._weights_array.copy()
        arr[i] = w
        n._weights_array = arr
        self._log('control', f'L2E{j} <- pixel {i} weight set to {w:.1f}')
        return w

    def set_pattern(self, name: str):
        if name not in PATTERNS:
            raise KeyError(name)
        self._cancel_probe_if_active()
        self.input_vec = np.array(PATTERNS[name], dtype=float)
        self.current_pattern = name
        self._visit_step = 0                 # start a fresh visit window
        self._visit_spikes[:] = 0
        self._start_presentation(name, 'train')
        self._log('control', f'pattern set: {name}')

    def set_auto_cycle(self, enabled: bool, streak: int | None = None,
                       visit_steps: int | None = None):
        """Enable/disable auto-cycling and (optionally) its thresholds. Starts the
        cycle from the currently-shown pattern; per-pattern training history is
        cleared so a new run measures training fresh."""
        self.auto_cycle = bool(enabled)
        if streak is not None:
            self.trained_streak = max(1, int(streak))
        if visit_steps is not None:
            self.visit_steps = max(1, int(visit_steps))
        self._visit_step = 0
        self._visit_spikes[:] = 0
        for n in PATTERNS:
            self._pattern_last_winner[n] = None
            self._pattern_streak[n] = 0
            self._pattern_trained[n] = False
        self._log('control', f'auto-cycle {"on" if self.auto_cycle else "off"} '
                             f'(trained_streak={self.trained_streak}, '
                             f'visit_steps={self.visit_steps})')
        return dict(enabled=self.auto_cycle, streak=self.trained_streak,
                    visit_steps=self.visit_steps)

    def _auto_cycle_tick(self):
        """Called at the END of each step() while auto_cycle is on. Accumulates
        this visit's L2E spikes; when the visit window closes, resolves the visit
        winner (argmax), updates the current pattern's consecutive-round streak,
        marks it trained at the threshold, then advances to the next pattern.
        When every pattern is trained the cycle disables itself."""
        for j in range(N_OUT):
            if self.spiked[f'L2E{j}']:
                self._visit_spikes[j] += 1
        self._visit_step += 1
        if self._visit_step < self.visit_steps:
            return

        p = self.current_pattern
        winner = int(self._visit_spikes.argmax()) if self._visit_spikes.sum() > 0 else None
        prev = self._pattern_last_winner[p]
        if winner is not None and winner == prev:
            self._pattern_streak[p] += 1
        else:
            self._pattern_streak[p] = 1 if winner is not None else 0
        self._pattern_last_winner[p] = winner
        if not self._pattern_trained[p] and self._pattern_streak[p] >= self.trained_streak:
            self._pattern_trained[p] = True
            self._log('learning', f'auto-cycle: "{p}" TRAINED '
                                  f'-> L2E{winner} won {self._pattern_streak[p]} rounds')

        if all(self._pattern_trained.values()):
            self.auto_cycle = False
            self._log('control', 'auto-cycle: all patterns trained -- curriculum complete')
            self._visit_step = 0
            self._visit_spikes[:] = 0
            return

        order = self._cycle_order
        idx = order.index(p) if p in order else -1
        self.set_pattern(order[(idx + 1) % len(order)])   # resets the visit window

    def set_input(self, vec):
        self._cancel_probe_if_active()
        self.input_vec = np.array(vec, dtype=float).reshape(N_PIX)
        self._log('control', 'input vector set')

    def toggle_pixel(self, i: int):
        self._cancel_probe_if_active()
        self.input_vec[i] = 0.0 if self.input_vec[i] > 0.5 else 1.0

    def clear_input(self):
        self._cancel_probe_if_active()
        self.input_vec = np.zeros(N_PIX)
        self._log('control', 'input cleared')

    def random_pattern(self):
        self._cancel_probe_if_active()
        self.input_vec = (np.random.default_rng().random(N_PIX) > 0.5).astype(float)
        self._log('control', 'random input')

    def inject_noise(self, prob: float = 0.15):
        self._cancel_probe_if_active()
        flip = np.random.default_rng().random(N_PIX) < prob
        self.input_vec = np.where(flip, 1.0 - self.input_vec, self.input_vec)
        self._log('control', f'noise injected (p={prob:.2f})')

    def stimulate(self, neuron_id: str, magnitude: float = 1.0, continuous: bool = False):
        if neuron_id not in self.neurons:
            raise KeyError(neuron_id)
        if continuous:
            self._holds.pop(neuron_id, None) if magnitude == 0 else self._holds.__setitem__(neuron_id, magnitude)
        else:
            self._pulses[neuron_id] = self._pulses.get(neuron_id, 0.0) + magnitude
        self._log('control', f'stimulate {neuron_id} (+{magnitude:g}{", hold" if continuous else ""})')

    def _stored_prediction_decoder_matrix(self) -> np.ndarray:
        mat = np.zeros((N_OUT, N_PIX))
        if not self.prediction_excitatory_enabled:
            return mat
        for i, pn in enumerate(self.l1p):
            mat[:, i] = pn._weights_array.astype(float)
        return mat

    def _effective_prediction_decoder_matrix(self) -> np.ndarray:
        mat = self._stored_prediction_decoder_matrix()
        if self.prediction_decoder_control == PRED_CONTROL_DISABLED:
            return np.zeros_like(mat)
        if self.prediction_decoder_control == PRED_CONTROL_SHUFFLED:
            return mat[:, self._prediction_shuffle_perm]
        return mat

    def _prediction_decoder_dict(self, mat: np.ndarray) -> dict[str, list[float]]:
        return {f'L2E{j}': [round(float(mat[j, i]), 4) for i in range(N_PIX)] for j in range(N_OUT)}

    def set_prediction_decoder_weight(self, l2e_index: int, pixel_index: int, value: float):
        if not self.prediction_excitatory_enabled:
            raise RuntimeError('prediction excitatory scaffold is disabled')
        if not (0 <= l2e_index < N_OUT):
            raise IndexError(l2e_index)
        if not (0 <= pixel_index < N_PIX):
            raise IndexError(pixel_index)
        clipped = min(max(float(value), 0.0), self.prediction_weight_cap)
        self.l1p[pixel_index]._weights_array[l2e_index] = clipped

    def set_prediction_decoder_control(self, mode: str):
        if mode not in PREDICTION_CONTROL_MODES:
            raise ValueError(mode)
        self.prediction_decoder_control = mode
        self._log('control', f'prediction decoder control: {mode}')

    def _schedule_prediction_decoder_events(self, l2e, t: int):
        self._prediction_pending_decoder = []
        if not self.prediction_excitatory_enabled:
            return
        eff = self._effective_prediction_decoder_matrix()
        pending = []
        for j in range(N_OUT):
            if not l2e[j]:
                continue
            for i in range(N_PIX):
                w = float(eff[j, i])
                if w <= WEIGHT_EPS:
                    continue
                pending.append(dict(id=f'decoder{j}->{i}', source=f'L2E{j}', target=f'P{i}',
                                    source_index=j, pixel_index=i, scheduled_step=t,
                                    arrival_step=t + 1, weight=round(w, 4),
                                    control=self.prediction_decoder_control))
        self._prediction_pending_decoder = pending

    def _deliver_prediction_decoder_events(self, t: int) -> np.ndarray:
        self._prediction_last_decoder_arrivals = [dict(rec) for rec in self._prediction_pending_decoder]
        self._prediction_last_decoder_integrated = []
        charge = np.zeros(N_PIX)
        sources = [[] for _ in range(N_PIX)]
        for rec in self._prediction_last_decoder_arrivals:
            i = int(rec['pixel_index'])
            charge[i] += float(rec['weight'])
            sources[i].append(rec['source'])
        for i, pn in enumerate(self.l1p):
            if charge[i] <= WEIGHT_EPS:
                continue
            v_pre = float(pn.potential)
            applied = pn.refractory_timer <= 0
            if applied:
                pn.potential += charge[i]
            self._prediction_last_decoder_integrated.append(
                dict(target=f'P{i}', pixel_index=i, arrival_step=t,
                     sources=list(sources[i]), charge=round(float(charge[i]), 4),
                     applied=applied, refractory=int(pn.refractory_timer),
                     v_pre=round(v_pre, 4), v_post=round(float(pn.potential), 4)))
        return charge

    def _schedule_prediction_replay_events(self, p_spiked, t: int):
        self._prediction_pending_replay = []
        if not (self.prediction_excitatory_enabled and self.prediction_replay_enabled):
            return
        self._prediction_pending_replay = [
            dict(id=f'pred{i}->{i}', source=f'P{i}', target=f'L1E{i}', pixel_index=i,
                 scheduled_step=t, arrival_step=t + 1,
                 weight=round(float(self.prediction_replay_weight), 4))
            for i in range(N_PIX) if p_spiked[i]
        ]

    def _prediction_replay_inputs(self, t: int) -> np.ndarray:
        self._prediction_last_replay_arrivals = [dict(rec) for rec in self._prediction_pending_replay]
        self._prediction_last_replay_deliveries = []
        replay = np.zeros(N_PIX)
        if not (self.prediction_excitatory_enabled and self.prediction_replay_enabled):
            return replay
        for rec in self._prediction_last_replay_arrivals:
            i = int(rec['pixel_index'])
            replay[i] = 1.0
            self._prediction_last_replay_deliveries.append(
                dict(source=rec['source'], target=rec['target'], pixel_index=i,
                     delivery_step=t, replay_input=1.0,
                     replay_weight=round(float(self.prediction_replay_weight), 4),
                     sensory_pixel_active=bool(self.input_vec[i] > 0.5)))
        return replay

    def _resolve_l2_competition(self, l2, l2e, t):
        """PHASE 7 -- causal L2E->L2I->L2E competition (replaces the retired
        argmax immediate-reset tiebreak; see July_14_Geometric_Influence_
        Temporal_Winner_Brief.txt SS9 and Neuron.apply_delayed_inhibition).

        EVERY L2E that is `eligible` (above its own threshold) this step FIRES
        -- physically, via its own normal fire() (captures charge, discharges
        on its own terms, starts its own refractory window, learns). There is
        no mechanical argmax pick and no neuron is denied its spike because
        another also crossed threshold: "later L2E spikes before inhibition
        arrives are valid and remain ranked" (brief SS9). Each firer is logged
        as a contributor (t, id) since L2I's last fire -- L2I's OWN threshold
        crossing is what actually resolves the competition, not this method.

        L2I accumulates the full multi-hot firing vector exactly as it always
        has (receive_input); if THAT crosses L2I's own threshold, L2I fires
        (on its own terms, same as before) and a delayed, uniform inhibitory
        delivery is SCHEDULED (not applied) for l2_inhibition_delay steps
        later -- see _deliver_scheduled_l2_inhibition, called at the top of
        step(). No neuron is reset here; `inhibited` is always [] and
        `_reset_events` is untouched by this method (populated later, at
        delivery time, by whichever targets the scheduled event actually
        reaches).

        Mutates `l2e` in place (sets a 1 for every firer, not just one).
        Returns (l2i, inhibited, first_firer); first_firer is None (and L2I is
        left UNTOUCHED) when nobody crossed, so a caller running this per
        charge-chunk can drive L2I's no-winner integration exactly once after
        the chunk loop instead of K times. `t` is the current outer timestep.
        """
        eligible = [j for j, e in enumerate(l2.excitatory_neurons) if e.check_threshold()]
        # earliestResponseSet's source (Causal Story): the FULL eligible set at
        # the step that resolves the competition, read by _track_presentation
        # to detect an ambiguous same-step tie (Phase 6 semantics unchanged --
        # ALL of these neurons now actually fire, but the representation
        # candidate is still None on a same-step tie; see that method).
        self._last_eligible = eligible
        if not eligible:
            return 0.0, [], None
        for j in eligible:
            l2.excitatory_neurons[j].fire()
            l2e[j] = 1.0
            self._l2i_contributors.append((t, f'L2E{j}'))
        # L2I accumulates every actual arriving L2E event this step (not a
        # one-hot "the winner"); it fires on its OWN threshold crossing exactly
        # as before.
        l2.inhibitory_neuron.receive_input(l2e, t=t)
        l2i = 0.0
        if l2.inhibitory_neuron.check_threshold():
            v_pre_l2i = float(l2.inhibitory_neuron.potential)
            l2.inhibitory_neuron.fire()
            l2i = 1.0
            v_post_l2i = float(l2.inhibitory_neuron.potential)
            contributors = list(self._l2i_contributors)
            self._l2i_contributors = []
            self._l2i_pending.append(dict(
                fire_t=t, deliver_at=t + self.l2_inhibition_delay,
                contributors=contributors,
                l2i_v_pre=round(v_pre_l2i, 4), l2i_v_post=round(v_post_l2i, 4),
                magnitude=self.l2_inhibition_magnitude))
        return l2i, [], eligible[0]

    def _deliver_scheduled_l2_inhibition(self, t):
        """PHASE 7 -- apply every delayed L2I->L2E delivery scheduled (by
        _resolve_l2_competition) whose deliver_at has arrived. Called at the
        very top of step(), BEFORE this step's own L1E/L2E processing, so a
        due delivery lands on the membrane before new charge accumulates --
        the same one-step-register precedent as l1i_feedback_delay. Delivery
        is UNIFORM across all N_OUT L2E targets (no ID-based exemption): a
        target still in its own post-spike refractory window is skipped
        entirely by apply_delayed_inhibition (so a neuron that fired to
        trigger this very event typically -- not by exemption, but because it
        is still refractory -- escapes being hit by its own consequence).
        Read/mutate only via Neuron.apply_delayed_inhibition; builds
        _reset_events / l2_inh_phase_debug / _l2_inhibition_log from the
        result. Returns the list of L2E indices actually reached (applied)."""
        self.l2_inh_phase_debug = []
        due = [rec for rec in self._l2i_pending if rec['deliver_at'] <= t]
        if not due:
            return []
        self._l2i_pending = [rec for rec in self._l2i_pending if rec['deliver_at'] > t]
        applied_targets: list[int] = []
        for rec in due:
            targets = []
            for j, e in enumerate(self.l2.excitatory_neurons):
                out = e.apply_delayed_inhibition(rec['magnitude'])
                if out['applied']:
                    self._reset_events.append((f'L2E{j}', out))
                    applied_targets.append(j)
                targets.append(dict(id=f'L2E{j}', applied=out['applied'],
                                    v_pre=round(out['v_pre'], 4), v_post=round(out['v_post'], 4),
                                    p_loss=round(out['p_loss'], 4),
                                    depressed=len(out['depressed_indices']),
                                    # Phase 15: this target's own protection-gate
                                    # value at this exact event (1.0 when the
                                    # flag is off) -- exposes the maturity/
                                    # depression-magnitude relationship directly,
                                    # never re-derived from anything else.
                                    maturity=round(out['maturity'], 4)))
            delivery = dict(fire_t=rec['fire_t'], deliver_at=t,
                            contributors=[f'{ct}:{cid}' for ct, cid in rec['contributors']],
                            l2i_v_pre=rec['l2i_v_pre'], l2i_v_post=rec['l2i_v_post'],
                            magnitude=round(rec['magnitude'], 4), targets=targets)
            self._l2_inhibition_log.append(delivery)
            self._last_l2_inhibition_delivery = delivery
            self.l2_inh_phase_debug = delivery['targets']
        return applied_targets

    def _apply_switchi_paired_shunt(self, ff_vec, t):
        """Phase 37: explicit paired L2 membrane-shunt ablation.

        This is intentionally not presented as a conductance model. A SwitchI_j
        event is a local coincidence detector over two already-local quantities:
        current residual post-prediction L1 evidence for L2E_j and that same
        neuron's recent-spike trace. If the coincidence passes threshold, only
        the paired L2E_j membrane is attenuated this step.
        """
        self._switchi_last_events = []
        if not self.switchi_paired_shunt_enabled:
            return
        thr_l2 = float(self.params['threshold_l2']) or 1.0
        for j, e in enumerate(self.l2.excitatory_neurons):
            residual_drive = float(np.dot(np.maximum(effective_weights(e), 0.0), ff_vec))
            trace_before = float(self.switchi_recent_spike_trace[j])
            residual_norm = min(max(residual_drive / thr_l2, 0.0), 1.0)
            trace_norm = min(max(trace_before, 0.0), 1.0)
            coincidence = residual_norm * trace_norm
            fired = bool(
                residual_norm > 0.0 and trace_norm > 0.0
                and coincidence >= self.switchi_coincidence_threshold)
            v_pre = float(e.potential)
            delta = 0.0
            if fired and e.refractory_timer <= 0:
                delta = v_pre * self.switchi_shunt_frac
                e.potential = max(e.potential - delta, e.resting_potential)
            self._switchi_last_events.append(dict(
                target=f'L2E{j}',
                t=t,
                residual_drive=round(residual_drive, 4),
                residual_norm=round(residual_norm, 4),
                trace_before=round(trace_before, 4),
                coincidence=round(coincidence, 4),
                fired=fired,
                shunt_frac=round(self.switchi_shunt_frac, 4),
                v_pre=round(v_pre, 4),
                v_post=round(float(e.potential), 4),
                delta=round(delta, 4)))

    def _switchi_prediction_decoder_row(self, j: int) -> np.ndarray:
        if not self.prediction_column_enabled:
            return np.zeros(N_PIX, dtype=float)
        return np.array([self.pcol[i].decoder_weights[j] for i in range(N_PIX)], dtype=float)

    def _deliver_scheduled_switchi_local(self, t):
        self._switchi_local_last_deliveries = []
        if not self.switchi_local_mismatch_enabled:
            return []
        remaining = []
        delivered = []
        for rec in self._switchi_local_pending:
            if rec['deliver_at'] > t:
                remaining.append(rec)
                continue
            j = int(rec['target_index'])
            e = self.l2.excitatory_neurons[j]
            v_pre = float(e.potential)
            delta = 0.0
            applied = False
            if e.refractory_timer <= 0:
                delta = v_pre * self.switchi_shunt_frac
                e.potential = max(e.potential - delta, e.resting_potential)
                applied = delta > 0.0
            row = dict(
                target=f'L2E{j}',
                fire_t=rec['fire_t'],
                deliver_at=t,
                request_value=round(float(rec['request_value']), 4),
                residual_pixels=list(rec['residual_pixels']),
                contributors=list(rec['contributors']),
                applied=applied,
                v_pre=round(v_pre, 4),
                v_post=round(float(e.potential), 4),
                delta=round(delta, 4),
            )
            delivered.append(row)
        self._switchi_local_pending = remaining
        self._switchi_local_last_deliveries = delivered
        return delivered

    def _update_switchi_local_eligibility(self, pcol_spiked):
        if not self.switchi_local_mismatch_enabled:
            return
        self.switchi_local_elig *= self.switchi_trace_decay
        pred_scale = max(float(self.prediction_feedback_max), 1.0)
        for i, fired in enumerate(pcol_spiked):
            if fired <= 0.5:
                continue
            for j in range(N_OUT):
                delivered = any(
                    rec['target'] == f'PC{i}' and rec['source'] == f'L2E{j}'
                    and rec['signal'] > 0.0
                    for rec in self._prediction_column_last_deliveries
                )
                if not delivered:
                    continue
                strength = min(max(self.pcol[i].decoder_weights[j] / pred_scale, 0.0), 1.0)
                old = float(self.switchi_local_elig[j, i])
                self.switchi_local_elig[j, i] = old + strength * (1.0 - old)

    def _queue_switchi_local_requests(self, l1e_vec, pcol_spiked, t):
        self._switchi_local_last_events = []
        self._switchi_local_last_requests = []
        self._switchi_local_last_residual = []
        if not self.switchi_local_mismatch_enabled:
            self._switchi_local_last_diag = dict(
                pc_firing_events=0, residual_events=0, nonzero_eligibility=0,
                overlap_events=0, queued_requests=0, delivered_events=len(self._switchi_local_last_deliveries),
                max_request_value=0.0, request_threshold=round(self.switchi_coincidence_threshold, 4))
            return
        residual_vec = np.logical_and(np.array(l1e_vec, dtype=float) > 0.5,
                                      np.array(pcol_spiked, dtype=float) <= 0.5).astype(float)
        residual_pixels = [int(i) for i, v in enumerate(residual_vec) if v > 0.5]
        self._switchi_local_last_residual = [
            dict(pixel_index=i, residual=True, basal_present=bool(l1e_vec[i] > 0.5), pc_fired=False)
            for i in residual_pixels
        ]
        max_request = 0.0
        overlap_events = 0
        for j in range(N_OUT):
            contributors = []
            request = 0.0
            for i in residual_pixels:
                elig = float(self.switchi_local_elig[j, i])
                if elig <= 0.0:
                    continue
                overlap_events += 1
                request += elig
                contributors.append(dict(pixel_index=i, elig=round(elig, 4)))
            max_request = max(max_request, request)
            row = dict(
                target=f'L2E{j}',
                t=t,
                residual_pixels=list(residual_pixels),
                request_value=round(request, 4),
                contributors=contributors,
                threshold=round(self.switchi_coincidence_threshold, 4),
                queued=bool(request >= self.switchi_coincidence_threshold and contributors),
                deliver_at=t + 2,
            )
            self._switchi_local_last_events.append(row)
            if row['queued']:
                self._switchi_local_pending.append(dict(
                    target_index=j,
                    fire_t=t,
                    deliver_at=t + 2,
                    request_value=float(request),
                    residual_pixels=list(residual_pixels),
                    contributors=contributors,
                ))
                self._switchi_local_last_requests.append(dict(row))
        self._switchi_local_last_diag = dict(
            pc_firing_events=int(np.sum(np.array(pcol_spiked, dtype=float) > 0.5)),
            residual_events=len(residual_pixels),
            nonzero_eligibility=int(np.count_nonzero(self.switchi_local_elig > 0.0)),
            overlap_events=int(overlap_events),
            queued_requests=len(self._switchi_local_last_requests),
            delivered_events=len(self._switchi_local_last_deliveries),
            max_request_value=round(float(max_request), 4),
            request_threshold=round(self.switchi_coincidence_threshold, 4),
        )

    # ------------------------------------------------------------------- step
    def step(self) -> dict:
        l1, l2 = self.l1, self.l2
        t = self.timestep

        # 1. L1E: [paired I1's previous spike (local inhibition), external pixel].
        #    A held pixel supplies drive every input_period steps; input_period=1
        #    (default) is constant presentation.
        #    L2 competition resolves EVERY step by default (event_driven, the
        #    canonical per-step single-winner flow). With event_driven OFF it
        #    instead resolves once per cycle_period steps (the INTRINSIC clock),
        #    decoupling winner identity from how fast input arrives -- see the
        #    input_period/cycle_period note in __init__.
        #    Excitatory pixel drive goes through receive_input; the inhibitory
        #    discharge is delivered as its own event via apply_inhibition, which
        #    also runs the inhibitory-gate plasticity rule. The net membrane before
        #    threshold (ext - |w_inh|) is identical to the old summed delivery, so
        #    spike timing and event ordering are unchanged.
        input_arrives = (t % self.params['input_period'] == 0)
        cycle_boundary = (t % self.params['cycle_period'] == 0)
        self._inh_events = []
        self._reset_events = []
        self._prediction_column_last_output_delivery = []
        self._prediction_column_last_conductance = []
        self._switchi_local_last_events = []
        self._switchi_local_last_requests = []
        self._switchi_local_last_residual = []
        self._switchi_local_last_diag = {}
        self._deliver_scheduled_switchi_local(t)
        # Phase 7: apply any delayed L2I->L2E delivery scheduled on a previous
        # step and now due, BEFORE this step's own L1E/L2E processing -- same
        # one-step-register precedent as l1i_feedback_delay below.
        l2_inhibition_delivered = self._deliver_scheduled_l2_inhibition(t)

        # Phase 19A: deliver already-scheduled prediction events only. Decoder
        # arrivals were queued by last step's physical L2E spikes, so they land
        # at t+1 only; replay arrivals were queued by last step's physical P
        # spikes, so they land at t+1 relative to P and therefore no earlier
        # than t+2 relative to the original L2E event.
        p_spiked = np.zeros(N_PIX)
        replay_inputs = np.zeros(N_PIX)
        if self.prediction_excitatory_enabled:
            self._deliver_prediction_decoder_events(t)
            replay_inputs = self._prediction_replay_inputs(t)

        for i, e in enumerate(l1.excitatory_neurons):
            ext = 1.0 if (input_arrives and self.input_vec[i] > 0.5) else 0.0
            if self.prediction_excitatory_enabled:
                e.receive_input(np.array([0.0, ext, replay_inputs[i]]))
            else:
                e.receive_input(np.array([0.0, ext]))
            if self.prediction_column_persistent_conductance_enabled:
                tail_before = float(e.inh_trace)
                delivered_tail = float(e.advance_inhibitory_conductance())
                self._prediction_column_last_conductance.append(dict(
                    target=f'L1E{i}',
                    delivered_tail=round(delivered_tail, 4),
                    tail_before=round(tail_before, 4),
                    tail_after=round(float(e.inh_trace), 4),
                    pending_after=round(float(e.inh_trace_pending), 4)))
            # L1I feedback is a one-step delayed pulse. With constant presentation,
            # a pulse at t exactly cancels its paired pixel drive at t+1 and is then
            # consumed when this register is replaced at the end of the step.
            inh = float(self.l1i_feedback_delay[i]) if input_arrives else 0.0
            if inh > 0.5:
                inh_vec = np.array([1.0, *([0.0] * (len(e.weights) - 1))])
                for ev in e.apply_inhibition(inh_vec):
                    self._inh_events.append((f'L1E{i}', ev))

        # Phase 9: capture the delivery/effect record for the FIRST L1I
        # predictive-feedback fire this presentation. _inh_events above is
        # freshly built for THIS step from the l1i_feedback_delay register set
        # at the end of the PREVIOUS step -- exactly the delivery the flagged
        # fire scheduled one step ago (see _track_presentation).
        if self._l1i_delivery_capture_pending:
            self._presentation_l1i_first_delivery = (
                dict(t=t, events=[dict(neuron=nid, **ev) for nid, ev in self._inh_events])
                if self._inh_events else dict(t=t, events=[]))
            self._l1i_delivery_capture_pending = False

        self._apply_stim()

        if self.prediction_excitatory_enabled:
            for i, pn in enumerate(self.l1p):
                if p_spiked[i]:
                    continue
                if pn.check_threshold():
                    pn.fire()
                    p_spiked[i] = 1.0

        # 2a. L1E fires (no competition).
        l1e = np.array([1.0 if e.check_threshold() else 0.0 for e in l1.excitatory_neurons])
        for k, e in enumerate(l1.excitatory_neurons):
            if l1e[k]:
                e.fire()

        # Phase 19-v2 (LPS Lecture 14 LOCAL-COINCIDENCE prediction
        # architecture; corrected timing per the offline feasibility review
        # -- exact commit reviewed d91e7f7): PCi delivery + physical fire +
        # decoder learning. BOTH afferents are QUEUED at the end of the step
        # that produced them and arrive TOGETHER at t+1 -- there is no
        # same-step S_i->PCi delivery. A same-step lateral path is not
        # physically available in this engine's step() ordering (P threshold
        # checks would otherwise have to run before L1E/L2E resolve this
        # SAME step, and routing it through _apply_stim() would contaminate
        # the very sensory evidence that produced the L2E response); queuing
        # both together removes any phase mismatch between them, which is
        # what actually makes a nonempty feasible coincidence window exist
        # (see Phase19_Local_Coincidence_Shadow_Report.md's calibration).
        #   indices 0..7: R_j->PCi feedback, POPPED from the delayed queue --
        #                 the L2E vector queued exactly
        #                 prediction_feedback_delay steps ago.
        #   index 8:      S_i->PCi lateral coincidence, POPPED from its OWN
        #                 parallel delayed queue -- the L1E vector queued
        #                 from the SAME originating step as the L2E vector
        #                 above (never same-step, never independently timed).
        # Delivered together in ONE receive_input call so both land on PCi's
        # membrane in the SAME physical integration step. SHADOW ONLY in
        # this phase: PCi's own spike has zero effect on any other neuron
        # (no PCi->Ii->Si wiring yet -- deferred per the contract). Decoder
        # learning triggers ONLY on PCi's own physical spike -- see
        # _apply_prediction_column_learning for the delta rule AND the
        # separate S_i-eligibility gate (mature feedback-only firing must
        # remain physically possible; LEARNING additionally requires this
        # delivery's own lateral component to have been active).
        pcol_spiked = np.zeros(N_PIX)
        if self.prediction_column_enabled:
            dec_vec_pcol = self.l2e_to_pcol_queue.popleft()
            lat_vec_pcol = self.s_to_pcol_queue.popleft()
            arrival_metadata = self.pcol_delivery_metadata_queue.popleft()
            delivered_records = []
            for i, pc in enumerate(self.pcol):
                pc.deliver_basal(lat_vec_pcol[i], t)
                for j in range(N_OUT):
                    pc.deliver_apical(j, dec_vec_pcol[j], t)
                target_records = [record for record in arrival_metadata
                                  if record['target'] == f'PC{i}']
                origin_class = self._prediction_column_origin_class(target_records, i)
                for record in target_records:
                    delivered_records.append(dict(record, delivered_step=t,
                                                  origin_class=origin_class))
            self._prediction_column_last_deliveries = delivered_records
            for i, pc in enumerate(self.pcol):
                should_fire = pc.resolve_coincidence(t)
                if not self.plasticity_frozen:
                    self._apply_prediction_column_learning(pc)
                if should_fire:
                    pc.fire()
                    pcol_spiked[i] = 1.0
            self._update_switchi_local_eligibility(pcol_spiked)

        # 2b/2c. Deliver L1E->L2E feedforward charge and resolve L2 competition.
        #     PHASE 7: every L2E that crosses threshold this step FIRES (no
        #     argmax pick, no immediate reset of anyone). Each firer's event is
        #     logged as a contributor to the shared inhibitory neuron L2I, which
        #     accumulates them toward ITS OWN threshold exactly as before. Only
        #     when L2I itself crosses threshold and fires does it SCHEDULE a
        #     delayed, uniform inhibitory delivery to the whole pool (fixed
        #     magnitude = l2_inhibition_frac * threshold_l2), applied
        #     l2_inhibition_delay steps later by
        #     _deliver_scheduled_l2_inhibition -- called at the top of THIS
        #     method, before this step's own processing. See
        #     _resolve_l2_competition for the full mechanism.
        #
        #     Chunked charge (l2_charge_chunks = K): this step's feedforward drive
        #     can arrive in K equal chunks (weight_ji/K per active synapse) WITHIN
        #     this frozen outer timestep. After each chunk resolution is
        #     re-attempted; the FIRST chunk that produces a threshold-crosser
        #     resolves the competition and the remaining chunks are skipped
        #     (consolidation-first: the earliest strong responder(s) fire before
        #     rivals pile up charge). The clock does not advance and no leak/update
        #     runs between chunks. K=1 (default) delivers the full drive in a
        #     single chunk and reproduces the un-chunked behavior exactly.
        ff_vec = np.zeros(L2E_FANIN)
        for i in range(N_PIX):
            if l1e[i]:
                ff_vec[i] = 1.0

        self._apply_switchi_paired_shunt(ff_vec, t)
        self._queue_switchi_local_requests(l1e, pcol_spiked, t)

        l2e = np.zeros(N_OUT)
        l2i = 0.0
        inhibited = []
        self.l2_winner_chunk = None
        # EXPLICIT PHASE ORDER (flow-rate; see the flow-rate section of the
        # methodology doc): per outer timestep each L2E goes
        #   V_start -> (receive_input: advance trace to t-1, inject new drive,
        #   one same-timestep integrate = V_before_inhibition) -> threshold/WTA ->
        #   L2I inhibition on non-winners (V_after_inhibition) -> leak (V_end).
        # No excitatory trace is advanced again for an inhibited L2E in the same
        # timestep (receive_input already set exc_trace_last_t = t, so any later
        # advance_trace(t) is a no-op). l2_drive is the PRE-WTA snapshot (peak/margin
        # consumers); l2_charge is the post-inhibition, pre-update diagnostic. The
        # dashboard reports the live end-of-step membrane for every population.

        if self.lasting_inhibition:
            # Alternate mechanism (opt-in): deliver the full drive un-chunked and
            # resolve through a decaying shared inhibitory field. L2I pumps the
            # field when it fires; the field hyperpolarizes the whole L2E pool every
            # step and decays with inh_decay, so a pattern's specialist keeps the
            # field up and rivals stay locked out for a finite window.
            for e in l2.excitatory_neurons:
                e.receive_input(ff_vec, t=t)
            self.l2_drive = {f'L2E{j}': float(e.potential) for j, e in enumerate(l2.excitatory_neurons)}
            self.l2_inh_field *= (1.0 - self.inh_decay)
            field = self.l2_inh_field
            eligible = [j for j, e in enumerate(l2.excitatory_neurons)
                        if e.refractory_timer <= 0 and e.potential >= e.threshold + field]
            self._last_eligible = eligible   # diagnostic only, see _resolve_l2_competition
            if eligible:
                winner = max(eligible, key=lambda j: l2.excitatory_neurons[j].potential)
                l2.excitatory_neurons[winner].fire()
                l2e[winner] = 1.0
                inhibited = [j for j in eligible if j != winner]
                l2.inhibitory_neuron.receive_input(l2e, t=t)
                if l2.inhibitory_neuron.check_threshold():
                    l2.inhibitory_neuron.fire()
                    l2i = 1.0
                    self.l2_inh_field += self.inh_boost
        elif cycle_boundary or self.event_driven:
            # Standard per-step argmax competition, delivered in K charge chunks.
            # Competition resolves EVERY step (event_driven, default) OR once per
            # cycle (event_driven OFF: only on the intrinsic cycle boundary).
            # Flow-rate mode is the finer temporal model, so it FORCES effective
            # K = 1 (chunking is ignored while flow-rate is on) -- the trace itself
            # spreads a volley's charge over time.
            K = 1 if self.excitatory_flow_rate else self.l2_charge_chunks
            resolved = False
            for chunk in range(K):
                for e in l2.excitatory_neurons:
                    e.receive_input(ff_vec, charge_scale=1.0 / K, t=t)
                # Pre-WTA membrane snapshot at the current evaluation point (charge
                # viz / winner-margin diagnostics read this).
                self.l2_drive = {f'L2E{j}': float(e.potential) for j, e in enumerate(l2.excitatory_neurons)}
                l2i, inhibited, winner = self._resolve_l2_competition(l2, l2e, t)
                if winner is not None:
                    self.l2_winner_chunk = chunk
                    resolved = True
                    break
            if not resolved:
                # Full drive arrived and nobody crossed: L2I still integrates the
                # (empty) winner vector and may fire from residual charge.
                l2.inhibitory_neuron.receive_input(l2e, t=t)
                l2i = 1.0 if l2.inhibitory_neuron.check_threshold() else 0.0
                if l2i:
                    l2.inhibitory_neuron.fire()
        else:
            # Non-resolving step (event_driven OFF, between cycle boundaries): the
            # drive is delivered in full and accumulates on the membrane; the
            # competition waits for the next cycle boundary.
            for e in l2.excitatory_neurons:
                e.receive_input(ff_vec, t=t)
            self.l2_drive = {f'L2E{j}': float(e.potential) for j, e in enumerate(l2.excitatory_neurons)}

        # PHASE 7: retain the charge AFTER inhibition and BEFORE the membrane update
        # for phase diagnostics. This read-only snapshot does not advance traces or
        # mutate any neuron; dynamic_state() reports the later live membrane phase.
        self.l2_charge = {f'L2E{j}': float(e.potential) for j, e in enumerate(l2.excitatory_neurons)}
        self.switchi_recent_spike_trace = np.maximum(
            self.switchi_recent_spike_trace * self.switchi_trace_decay, l2e)

        if self.prediction_excitatory_enabled:
            self._schedule_prediction_decoder_events(l2e, t)

        # Phase 19-v2: queue THIS step's L2E spikes AND THIS step's L1E
        # (S_i) spikes TOGETHER as the PC population's delayed delivery pair
        # (both arrive prediction_feedback_delay steps from now, on the SAME
        # future step -- see the popleft() calls above and the queues' FIFO
        # invariant in _build_prediction_column_population). Queuing both
        # from the SAME originating step, rather than delivering the lateral
        # term same-step, is the corrected timing -- see the delivery block
        # above for the full rationale.
        if self.prediction_column_enabled:
            self.l2e_to_pcol_queue.append(l2e.copy())
            self.s_to_pcol_queue.append(l1e.copy())
            scheduled = []
            for j in range(N_OUT):
                if not l2e[j]:
                    continue
                for i in range(N_PIX):
                    scheduled.append(dict(
                        source=f'L2E{j}', target=f'PC{i}',
                        target_compartment='apical', scheduled_step=t,
                        arrival_step=t + self.prediction_feedback_delay,
                        origin_pattern=self.current_pattern))
            for i in range(N_PIX):
                if l1e[i]:
                    scheduled.append(dict(
                        source=f'L1E{i}', target=f'PC{i}',
                        target_compartment='basal', scheduled_step=t,
                        arrival_step=t + self.prediction_feedback_delay,
                        origin_pattern=self.current_pattern))
            self.pcol_delivery_metadata_queue.append(scheduled)

        # 2d. Deliver L2E winner spike immediately to all L1I neurons (feedback).
        #     l2e is length N_OUT with a 1 at the winner index, matching each
        #     L1I neuron's N_OUT-dimensional afferent weight vector. (t carries the
        #     flow-rate current trace when L1I is a trainable integrator; ignored in
        #     immediate-relay mode, where L1I's flow flag is off.)
        # Phase 21: selective PCi->Ii delivery REPLACES the global L2E
        # broadcast when prediction_column_to_i_enabled is on -- each L1Ii
        # receives only its OWN paired PCi's just-computed spike this step
        # (pcol_spiked, already resolved earlier in this same step() call,
        # before L2 competition -- see the PC delivery block above), never
        # the other eight columns' PCi. Delivered same-step (immediate),
        # matching the existing L2E->L1I feedback's own same-step
        # convention -- this is the first time PCi's own output affects any
        # other neuron (Phase 19/20 were shadow-only, zero output).
        if self.prediction_column_to_i_enabled:
            delivered_pc_feedback = (
                pcol_spiked.copy() if self.prediction_column_to_i_delivery_enabled
                else np.zeros(N_PIX))
            for i, inh in enumerate(l1.inhibitory_neurons):
                signal = float(delivered_pc_feedback[i])
                inh.receive_input(np.array([signal]), t=t)
                self._prediction_column_last_output_delivery.append(dict(
                    source=f'PC{i}',
                    target=f'L1I{i}',
                    delivery_enabled=bool(self.prediction_column_to_i_delivery_enabled),
                    attempted_spike=bool(pcol_spiked[i] > 0.5),
                    delivered_signal=signal))
        else:
            for inh in l1.inhibitory_neurons:
                inh.receive_input(l2e, t=t)

        # 2e. L1I fires after receiving L2E feedback.
        if self.l1i_immediate_relay:
            # Immediate deterministic relay (default): any L1I that received a
            # nonzero L2E feedback signal fires THIS step -- no membrane
            # accumulation, no learned-threshold crossing, no dependence on L1I
            # feedback-weight training. l2e is delivered identically to every L1I
            # (2d), so a winner (l2e nonzero) makes every L1I relay. Output stays
            # binary and the downstream L1I->L1E inhibition path is unchanged.
            if self.prediction_column_to_i_enabled:
                l1i = np.array([1.0 if row['delivered_signal'] > 0.5 else 0.0
                                for row in self._prediction_column_last_output_delivery])
            else:
                fb_present = 1.0 if np.any(l2e > 0) else 0.0
                l1i = np.full(len(l1.inhibitory_neurons), fb_present)
        else:
            # Trainable threshold integrator: fire only when accumulated feedback
            # crossed L1I's own (learned/leaky) threshold.
            l1i = np.array([1.0 if n.check_threshold() else 0.0 for n in l1.inhibitory_neurons])
        for k, n in enumerate(l1.inhibitory_neurons):
            if l1i[k]:
                n.fire()

        # 3. Collect synapse IDs that carried a spike this step (for edge flash).
        self.emitted = []
        for i in range(N_PIX):
            if l1e[i]:
                for j in range(N_OUT):
                    self.emitted.append(f'ff{i}->{j}')
        for j in range(N_OUT):
            if l2e[j]:
                for i in range(N_PIX):
                    self.emitted.append(f'fb{j}->{i}')
                self.emitted.append(f'{j}->inh')
        for rec in self._prediction_last_decoder_arrivals:
            self.emitted.append(rec['id'])
        # Phase 7: the L2I->L2E fanout edge now flashes on actual DELIVERY
        # (this step's due deliveries, applied above at the top of step()),
        # not on an immediate same-step reset.
        for j in l2_inhibition_delivered:
            self.emitted.append(f'reset->{j}')
        for i in range(N_PIX):
            if l1i[i]:
                self.emitted.append(f'li{i}')
        for rec in self._prediction_last_replay_arrivals:
            self.emitted.append(rec['id'])

        # 4. Advance membrane state (leak + refractory countdown).
        for e in l1.excitatory_neurons:
            e.update()
        for n in l1.inhibitory_neurons:
            n.update()
        for e in l2.excitatory_neurons:
            e.update()
        l2.inhibitory_neuron.update()
        if self.prediction_excitatory_enabled:
            for pn in self.l1p:
                pn.update()
            self._schedule_prediction_replay_events(p_spiked, t)
        if self.prediction_column_enabled:
            for pc in self.pcol:
                pc.update()

        # 5. Bookkeeping.
        self._record_spikes(l1e, l1i, l2e, l2i,
                           pred=(p_spiked if self.prediction_excitatory_enabled else None),
                           pred_col=(pcol_spiked if self.prediction_column_enabled else None))
        # Phase 10: adaptive-threshold trajectory (end-of-step a_i, post-decay).
        for j, e in enumerate(l2.excitatory_neurons):
            self.threshold_adapt_history[f'L2E{j}'].append(round(float(e.threshold_adapt), 4))
        # Evidence bookkeeping for the Causal Story / evidence-based RF status:
        # cumulative spike counts and last-fired step, read off this step's actual
        # spike flags (no inference). step_winner_idx reads which single index of
        # the (already WTA-decided) one-hot l2e vector is set -- not a competitive
        # argmax, just "which entry is 1".
        for nid, spk in self.spiked.items():
            if spk:
                self._neuron_total_spikes[nid] += 1
                self._neuron_last_fired_t[nid] = t
        step_winner_idx = int(np.argmax(l2e)) if l2e.any() else None
        self._track_presentation(step_winner_idx, bool(l2i), l1i, t)
        # Queue this step's L1I spikes as one-step inhibition for t+1. Replacing
        # rather than OR-latching the register is what permits the E/silent/E rhythm.
        self.l1i_feedback_delay = l1i.copy()
        self.timestep += 1
        self._detect_weight_changes()
        self._detect_confidence_changes()
        self._log_inhibitory_events()
        # Auto-cycle is training-patterns-only by construction (_cycle_order is
        # built from PATTERNS.keys()); pause its ticking while a probe is up so a
        # probe's steps/current_pattern never feed the training bookkeeping.
        if self.auto_cycle and not self._probe_active:
            self._auto_cycle_tick()
        if self._probe_active:
            self._probe_steps_elapsed += 1
            if self._probe_steps_elapsed >= self.probe_steps_total:
                self._end_probe(restore=True)
        return self.dynamic_state()

    def _log_inhibitory_events(self):
        """Surface inhibitory-discharge plasticity into the event log for the
        dashboard. Only events that actually moved a gate (|delta_w| > eps) are
        logged, so a saturated gate (delta_w == 0) doesn't flood the panel; the
        full per-event debug record always lives on each neuron's
        last_inhibitory_events."""
        for nid, ev in self._inh_events:
            if abs(ev['delta_w']) > WEIGHT_EPS:
                self._log('inhibition',
                          f"{nid} gate: Vpre={ev['v_pre']:.3f} θ={ev['theta']:.2f} "
                          f"p={ev['p']:.2f} |w| {ev['w_before']:.3f}->{ev['w_after']:.3f} "
                          f"(Δ={ev['delta_w']:+.4f})")

    def _apply_stim(self):
        for nid, mag in list(self._pulses.items()):
            self.neurons[nid].potential += mag
        self._pulses.clear()
        for nid, mag in self._holds.items():
            self.neurons[nid].potential += mag

    def _record_spikes(self, l1e, l1i, l2e, l2i, pred=None, pred_col=None):
        for i in range(N_PIX):
            self.spiked[f'L1E{i}'] = bool(l1e[i]); self.freq[f'L1E{i}'].append(l1e[i])
            self.spiked[f'L1I{i}'] = bool(l1i[i]); self.freq[f'L1I{i}'].append(l1i[i])
        # Phase 19: P population spike/frequency tracking, same convention as
        # every other population -- untouched (pred is None) when
        # prediction_excitatory_enabled is off.
        if pred is not None:
            for i in range(N_PIX):
                self.spiked[f'P{i}'] = bool(pred[i]); self.freq[f'P{i}'].append(pred[i])
        # Phase 19-v2: PC population spike/frequency tracking, same convention
        # -- untouched (pred_col is None) when prediction_column_enabled is off.
        if pred_col is not None:
            for i in range(N_PIX):
                self.spiked[f'PC{i}'] = bool(pred_col[i]); self.freq[f'PC{i}'].append(pred_col[i])
        for j in range(N_OUT):
            self.spiked[f'L2E{j}'] = bool(l2e[j]); self.freq[f'L2E{j}'].append(l2e[j])
        self.spiked['L2I'] = bool(l2i); self.freq['L2I'].append(l2i)


    # ------------------------------------------------------- presentation / probes
    def _start_presentation(self, name: str, role: str):
        """Begin a new named presentation (a training pattern or a probe shown via
        set_pattern/present_probe). Archives the JUST-ENDED presentation's causal
        summary onto presentation_log -- brief SS9's required fields, recorded,
        never inferred -- and folds its first-responder identity into the
        per-pattern/per-neuron evidence history used by the Causal Story and the
        evidence-based receptive-field status, UNLESS that first response was a
        same-step tie (Phase 6: an ambiguous same-step set gets no winner-
        specific credit). Observability only: reads already-decided physical
        events, never mutates a neuron or a weight.

        Phase 6 field mapping (brief SS9's terms -> this engine's names):
          physicalFirstSpiker      -> first_spiker (raw fact: recorded even
                                       during a tie -- see self.winner for the
                                       separate, credit-bearing concept)
          physicalFirstSpikeStep   -> first_spike_t
          earliestResponseSet      -> earliest_response_set (the exact set of
                                       L2E ids eligible at the first-spike step;
                                       sameStepTie == len(...) > 1)
          later L2E spike order    -> later_responses ([(t, nid), ...])
          latency to second        -> latency_to_second_response
        """
        if self.presentation_id > 0:
            self.presentation_log.append(dict(
                id=self.presentation_id, pattern=self.presentation_pattern,
                role=self.presentation_role, start_t=self.presentation_start_t,
                end_t=self.timestep,
                first_spiker=self._presentation_first_spiker,
                first_spike_t=self._presentation_first_spike_t,
                same_step_tie=self._presentation_tie,
                earliest_response_set=list(self._presentation_earliest_response_set),
                later_responses=list(self._presentation_later_responses),
                latency_to_second_response=self._presentation_latency_to_second,
                l1i_first_source=self._presentation_l1i_first_source,
                l1i_first_t=self._presentation_l1i_first_t,
                l1i_first_source_set=list(self._presentation_l1i_first_source_set),
                l1i_first_arrival_t=self._presentation_l1i_first_arrival_t,
                l1i_first_targets=list(self._presentation_l1i_first_targets),
                l1i_first_delivery=self._presentation_l1i_first_delivery,
                l2i_first_source=self._presentation_l2i_first_source,
                l2i_first_t=self._presentation_l2i_first_t))
            # No winner-specific credit for an ambiguous same-step tie: only a
            # clean (non-tied) first response feeds the evidence history that
            # the Causal Story / evidence-based RF status read.
            if self._presentation_first_spiker is not None and not self._presentation_tie:
                hist = self._pattern_first_responder_log.setdefault(
                    self.presentation_pattern, deque(maxlen=20))
                hist.append(self._presentation_first_spiker)
                counts = self._neuron_first_responder_counts.setdefault(
                    self._presentation_first_spiker, {})
                counts[self.presentation_pattern] = counts.get(self.presentation_pattern, 0) + 1
        self.presentation_id += 1
        self.presentation_role = role
        self.presentation_pattern = name
        self.presentation_start_t = self.timestep
        self._presentation_first_spiker = None
        self._presentation_first_spike_t = None
        self._presentation_tie = False
        self._presentation_earliest_response_set = []
        self._presentation_later_responses = []
        self._presentation_latency_to_second = None
        self._presentation_l1i_first_source = None
        self._presentation_l1i_first_t = None
        # Phase 9: causal L1I predictive-feedback chain -- arrival (a real
        # L2E delivery reaches L1I) is tracked separately from threshold
        # crossing (L1I itself fires), since a slow trainable integrator can
        # take more than one step to cross after the causal event arrives.
        self._presentation_l1i_first_source_set = []
        self._presentation_l1i_first_arrival_t = None
        self._presentation_l1i_first_targets = []
        self._presentation_l1i_first_delivery = None
        self._l1i_delivery_capture_pending = False
        self._presentation_l2i_first_source = None
        self._presentation_l2i_first_t = None
        self._presentation_last_l2_winner = None
        # The representation candidate resets with the presentation: no
        # carryover credit from a previous presentation before new evidence
        # (a fresh first spike) arrives.
        self.winner = None

    def _credit_source(self, idx: int | None) -> str | None:
        """L2E id for `idx`, UNLESS more than one L2E genuinely fired on the
        step this attribution is being read for. Phase 9 (corrected):
        `self._last_eligible` is the FULL set of L2E that fired on the
        CURRENT step (Phase 7 lets every threshold-crosser fire, so this can
        exceed one member on ANY step, not just a presentation's first
        spike) -- checking it directly here, at the moment of attribution,
        replaces the earlier Phase 6 check (which only compared against the
        presentation's first-spike tie flag and so missed a genuine same-step
        multi-firer event on a LATER step). An ambiguous same-step set gets no
        source-specific credit for L1I OR L2I attribution -- never resolved
        by index priority, hidden charge, or weight inspection, only by the
        recorded fact of how many neurons actually fired together."""
        if idx is None:
            return None
        if len(self._last_eligible) > 1:
            return 'ambiguous'
        return f'L2E{idx}'

    def _track_presentation(self, step_winner_idx: int | None, l2i_fired: bool, l1i_arr, t: int):
        """Presentation-scoped causal tracking, called once per step() from
        already-decided physical results (step_winner_idx is read off this step's
        one-hot l2e vector, l2i_fired/l1i_arr off this step's actual discharge
        arrays) -- it decides nothing and mutates no neuron/weight/membrane.

        Phase 6: self.winner (the representation candidate) is set in EXACTLY
        one place -- right here, the instant the presentation's first physical
        L2E threshold crossing occurs -- to that neuron's id, UNLESS
        self._last_eligible (populated by _resolve_l2_competition/the
        lasting_inhibition branch for the step that resolved it) names more
        than one neuron, in which case the response is an ambiguous same-step
        tie and self.winner stays None for the rest of this presentation. This
        is never re-derived by argmax, index, hidden charge, weights,
        geometry, or UI logic -- see the module comment above the (retired)
        episode mechanism for what this replaced. Phase 7 removed the old
        argmax immediate-reset tiebreak entirely: every neuron named in
        _last_eligible now actually fires (step_winner_idx just reads which
        index happens to be lowest among simultaneous same-step firers, purely
        for this raw `first_spiker` fact); the same-step-tie/no-credit logic
        below is unaffected either way."""
        if step_winner_idx is not None:
            nid = f'L2E{step_winner_idx}'
            self._presentation_last_l2_winner = step_winner_idx
            if self._presentation_first_spiker is None:
                self._presentation_first_spiker = nid
                self._presentation_first_spike_t = t
                self._presentation_earliest_response_set = [f'L2E{j}' for j in sorted(self._last_eligible)]
                self._presentation_tie = len(self._presentation_earliest_response_set) > 1
                self.winner = None if self._presentation_tie else nid
            else:
                # A later physical response (brief: "later L2E spike order"),
                # recorded in full -- including a repeat spike from the same
                # neuron, which is itself meaningful ("the winner fired again").
                self._presentation_later_responses.append((t, nid))
                if (self._presentation_latency_to_second is None
                        and nid != self._presentation_first_spiker):
                    self._presentation_latency_to_second = t - self._presentation_first_spike_t
        if l2i_fired and self._presentation_l2i_first_t is None:
            self._presentation_l2i_first_t = t
            self._presentation_l2i_first_source = (
                self._credit_source(step_winner_idx) if step_winner_idx is not None
                else (self._credit_source(self._presentation_last_l2_winner) or 'residual'))
        # Phase 9: ARRIVAL -- the first step a real L2E delivery reaches L1I
        # (step_winner_idx is not None iff l2e was nonzero this step, i.e. a
        # genuine causal event was just delivered via receive_input), recorded
        # independently of whether L1I has crossed its own threshold yet.
        # self._last_eligible (this step's actual firer set) is the source
        # SET -- recorded even when ambiguous (brief SS9-style raw fact).
        if step_winner_idx is not None and self._presentation_l1i_first_arrival_t is None:
            self._presentation_l1i_first_arrival_t = t
            self._presentation_l1i_first_source_set = [f'L2E{j}' for j in sorted(self._last_eligible)]
        if np.any(l1i_arr > 0.5) and self._presentation_l1i_first_t is None:
            self._presentation_l1i_first_t = t
            self._presentation_l1i_first_source = self._credit_source(self._presentation_last_l2_winner)
            self._presentation_l1i_first_targets = [f'L1I{i}' for i in range(len(l1i_arr)) if l1i_arr[i] > 0.5]
            # DELIVERY/EFFECT: the resulting L1I->L1E inhibitory pulse lands
            # ONE STEP LATER (l1i_feedback_delay's fixed one-step register --
            # see step()); flag it so the NEXT step's freshly-built
            # _inh_events (populated at the top of step(), before this flag is
            # checked) can be captured as the first delivery+effect record.
            self._l1i_delivery_capture_pending = True

    def _set_plasticity_frozen(self, frozen: bool):
        self.plasticity_frozen = frozen
        for n in self.neurons.values():
            n.plasticity_frozen = frozen

    def present_probe(self, name: str, steps: int | None = None):
        """Show a held-out PROBE for a presentation-scoped, plasticity-FROZEN
        window: real physical dynamics (spikes/inhibition/resets) run exactly as
        normal, but every weight-mutating call is a no-op for the duration (see
        Neuron.plasticity_frozen). Automatically restores whatever pattern/input
        was showing before once the window elapses (see step()). Does not touch
        auto-cycle's own bookkeeping (_visit_step/_visit_spikes/_pattern_streak
        for the paused training pattern are simply not advanced meanwhile)."""
        if name not in PROBES:
            raise KeyError(name)
        if self._probe_active:
            self._end_probe(restore=False)
        self._probe_resume_pattern = self.current_pattern
        self._probe_resume_input = self.input_vec.copy()
        self.probe_steps_total = max(1, int(steps) if steps is not None else self.visit_steps)
        self._probe_steps_elapsed = 0
        self._probe_active = True
        self.input_vec = np.array(PROBES[name], dtype=float)
        self.current_pattern = name
        # Phase 10: snapshot each L2E's adaptive-threshold state a_i before the
        # probe. Real physical dynamics (including spike-local a_i increments
        # and per-step decay) stay LIVE during the probe -- like membrane
        # potential, a_i is not frozen -- but it is restored unconditionally
        # in _end_probe so probe evaluation can never alter subsequent
        # training, regardless of how the probe ends (elapsed or cancelled).
        self._probe_threshold_adapt_snapshot = {
            j: float(e.threshold_adapt) for j, e in enumerate(self.l2.excitatory_neurons)}
        # Deliberately do NOT touch _visit_step/_visit_spikes here -- those belong
        # to auto-cycle's paused training pattern and must come back untouched.
        self._start_presentation(name, 'probe')
        self._set_plasticity_frozen(True)
        self._log('control', f'probe presented: {name} '
                             f'({self.probe_steps_total} steps, plasticity frozen)')

    def _end_probe(self, restore: bool):
        self._probe_active = False
        self._set_plasticity_frozen(False)
        # Phase 10: restore each L2E's adaptive-threshold state a_i to its
        # pre-probe snapshot -- unconditionally, whether the probe elapsed
        # naturally (restore=True) or was cancelled by manual input
        # (restore=False), since either way the goal is the same: probe
        # evaluation must not leak into subsequent training.
        if self._probe_threshold_adapt_snapshot is not None:
            for j, e in enumerate(self.l2.excitatory_neurons):
                e.threshold_adapt = self._probe_threshold_adapt_snapshot.get(j, 0.0)
            self._probe_threshold_adapt_snapshot = None
        if restore:
            self.input_vec = self._probe_resume_input
            self.current_pattern = self._probe_resume_pattern
            # _visit_step/_visit_spikes were never touched during the probe (see
            # present_probe), so auto-cycle resumes exactly where it paused.
            role = 'train' if self.current_pattern in PATTERNS else 'manual'
            self._start_presentation(self.current_pattern, role)
        self._log('control', 'probe ended: plasticity resumed')

    def _cancel_probe_if_active(self):
        """Manual input controls (set_input/toggle_pixel/random/clear/noise) end an
        in-progress probe WITHOUT restoring the pre-probe pattern -- the user is
        now driving a different, unnamed input, so there is nothing to resume."""
        if self._probe_active:
            self._end_probe(restore=False)

    # ------------------------------------------------------------- weight diff
    def _all_weights(self) -> dict:
        w = {}
        for j in range(N_OUT):
            arr = self.l2.excitatory_neurons[j]._weights_array
            for i in range(N_PIX):
                w[f'ff{i}->{j}'] = float(arr[i])
        iw = self.l2.inhibitory_neuron._weights_array
        for j in range(N_OUT):
            w[f'{j}->inh'] = float(iw[j])
        for i in range(N_PIX):
            w[f'li{i}'] = float(self.l1.excitatory_neurons[i].weights[0])
            fbw = self.l1.inhibitory_neurons[i].weights
            # Phase 21: fbw is genuinely 1-wide under the selective PCi->Ii
            # topology (see _build()) -- report the single pcinh{i} weight
            # instead of indexing into N_OUT entries that no longer exist.
            if self.prediction_column_to_i_enabled:
                w[f'pcinh{i}'] = float(fbw[0])
            else:
                for j in range(N_OUT):
                    w[f'fb{j}->{i}'] = float(fbw[j])
        # Phase 19A: stored decoder matrix plus fixed local replay edges.
        if self.prediction_excitatory_enabled:
            stored = self._stored_prediction_decoder_matrix()
            for j in range(N_OUT):
                for i in range(N_PIX):
                    w[f'decoder{j}->{i}'] = float(stored[j, i])
            for i in range(N_PIX):
                w[f'pred{i}->{i}'] = float(self.prediction_replay_weight)
        # Phase 19-v2: learned R_j->PCi feedback matrix plus the fixed
        # S_i->PCi lateral-coincidence edges (reported for observability;
        # never learned, never appears in changed_synapses beyond its one
        # constant value at build time).
        if self.prediction_column_enabled:
            for i in range(N_PIX):
                pcw = self.pcol[i].decoder_weights
                for j in range(N_OUT):
                    w[f'colfb{j}->{i}'] = float(pcw[j])
                w[f'lat{i}'] = float(self.pcol[i].basal_connection.weight)
        return w

    def _detect_weight_changes(self):
        now = self._all_weights()
        self.changed_synapses = [dict(id=sid, weight=round(v, 4))
                                 for sid, v in now.items()
                                 if abs(v - self._weights_snapshot.get(sid, v)) > WEIGHT_EPS]
        self._weights_snapshot = now

    def _all_confidence(self) -> dict:
        """Per-synapse confidence for the L2E feedforward receptive fields, keyed by
        the same synapse ids as _all_weights (ff{i}->{j}). Confidence is the L2E
        neuron's trust that opening each EXCITATORY gate helps it fire (see
        neuron_flexible.Neuron), so only the feedforward (positive) synapses are reported --
        the negative L2I->L2E gate has its own inhibitory plasticity and no
        excitatory-trust value. The field is always safe to serialize because
        every neuron allocates a confidence vector during connection finalization."""
        c: dict[str, float] = {}
        for j in range(N_OUT):
            conf = self.l2.excitatory_neurons[j].confidence
            for i in range(N_PIX):
                c[f'ff{i}->{j}'] = float(conf[i])
        return c

    def _detect_confidence_changes(self):
        now = self._all_confidence()
        self.changed_confidence = [dict(id=sid, confidence=round(v, 4))
                                   for sid, v in now.items()
                                   if abs(v - self._confidence_snapshot.get(sid, v)) > WEIGHT_EPS]
        self._confidence_snapshot = now

    def _budget_usage(self, nid: str):
        """(budget, budget_used) for an L2E neuron, else (None, None). budget_used
        is the current sum of positive (feedforward) weights vs its fixed budget."""
        n = self.neurons[nid]
        if self.meta[nid]['type'] == 'E' and nid.startswith('L2') and n.weight_budget is not None:
            w = n.weights
            return float(n.weight_budget), float(w[w > 0].sum())
        return None, None

    def _l2e_status(self, j: int) -> dict:
        """Evidence-based receptive-field status for L2E{j} -- built ONLY from
        actually-observed spikes/first-responder history (see _track_presentation
        and _start_presentation), never from a weight-sum guess at whether the
        neuron COULD fire. Replaces the prior client-side (receptive.js) "dead"
        heuristic, which computed its own top-3-weight/threshold guess that could
        diverge from the engine's actual behavior (Phase 1 audit finding)."""
        nid = f'L2E{j}'
        total = self._neuron_total_spikes.get(nid, 0)
        last_t = self._neuron_last_fired_t.get(nid)
        first_counts = dict(self._neuron_first_responder_counts.get(nid, {}))
        if total == 0:
            status = 'unrecruited'      # never observed to fire at all
        elif last_t is not None and (self.timestep - last_t) <= STATUS_RECENT_WINDOW:
            status = 'active'           # fired within the recent window
        else:
            status = 'quiet'            # has fired historically, not recently
        return dict(status=status, spikes_total=total, last_fired_step=last_t,
                    first_responder_counts=first_counts,
                    patterns_led=sorted(first_counts.keys()))

    def _delivery_diagnostics(self) -> dict:
        """Per-feedforward-synapse distance / influence / effective-transmission,
        computed the SAME WAY effective_weights() computes delivery (see
        snn/rules/delivery.py) regardless of whether distance_weighting is
        currently enabled -- so the audited quantities (brief SS7/14) are always
        observable, not just when the toggle happens to be on. Read-only; never
        mutates a weight."""
        p = self.params
        out: dict[str, dict] = {}
        for j in range(N_OUT):
            n = self.l2.excitatory_neurons[j]
            d = n._distance
            if n._weights_array is None or d is None or len(d) == 0:
                continue
            influence = (p['distance_ref'] / np.maximum(d, p['distance_min'])) ** p['distance_power']
            w = n._weights_array
            effective = w * influence if p['distance_weighting'] else w
            for i in range(len(d)):
                out[f'ff{i}->{j}'] = dict(distance=round(float(d[i]), 4),
                                          influence=round(float(influence[i]), 4),
                                          effective=round(float(effective[i]), 4))
        return out

    # ----------------------------------------------------------------- access
    def firing_freq(self, nid: str) -> float:
        d = self.freq[nid]
        return float(sum(d) / len(d)) if d else 0.0

    def activation(self, nid: str) -> float:
        thr = self.meta[nid]['threshold'] or 1.0
        return float(self.neurons[nid].potential / thr)

    def _log(self, kind: str, message: str):
        self._log_seq += 1
        self.event_log.append(dict(seq=self._log_seq, t=self.timestep, kind=kind, message=message))

    def _detected_named_input(self) -> dict | None:
        vec = self.input_vec.astype(int).tolist()
        for name, pat in PATTERNS.items():
            if vec == list(map(int, pat)):
                return dict(name=name, role=PATTERN_ROLE.get(name, 'train'))
        for name, pat in PROBES.items():
            if vec == list(map(int, pat)):
                return dict(name=name, role=PATTERN_ROLE.get(name, 'probe'))
        return None

    def _prediction_output_state(self) -> str:
        if not self.prediction_column_enabled:
            return 'OFF'
        if not self.prediction_column_to_i_enabled:
            return 'shadow'
        if not self.prediction_column_to_i_delivery_enabled:
            return 'shadow'
        if self.prediction_column_persistent_conductance_enabled:
            return 'persistent'
        return 'instantaneous'

    def _ownership_summary(self) -> dict:
        history = list(self.presentation_log)
        clean = [row for row in history
                 if not row.get('same_step_tie') and row.get('first_spiker')]
        owner_counts: dict[str, int] = {}
        owner_patterns: dict[str, set[str]] = {}
        pattern_counts: dict[str, dict[str, int]] = {}
        for row in clean:
            owner = row['first_spiker']
            pattern = row['pattern']
            owner_counts[owner] = owner_counts.get(owner, 0) + 1
            owner_patterns.setdefault(owner, set()).add(pattern)
            pcounts = pattern_counts.setdefault(pattern, {})
            pcounts[owner] = pcounts.get(owner, 0) + 1
        modal_owner = None
        modal_owner_count = 0
        if owner_counts:
            modal_owner, modal_owner_count = max(owner_counts.items(), key=lambda kv: (kv[1], kv[0]))
        collisions = [
            dict(owner=owner, patterns=sorted(patterns))
            for owner, patterns in sorted(owner_patterns.items())
            if len(patterns) > 1
        ]
        modal_by_pattern = {
            pattern: max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
            for pattern, counts in pattern_counts.items() if counts
        }
        distinct_owners = len(set(modal_by_pattern.values()))
        return dict(
            total_presentations=len(history),
            clean_presentations=len(clean),
            same_step_ties=sum(1 for row in history if row.get('same_step_tie')),
            modal_owner=modal_owner,
            modal_owner_count=modal_owner_count,
            first_responder_share=(
                round(float(modal_owner_count / len(clean)), 4) if clean else 0.0),
            collisions=collisions,
            distinct_owners=distinct_owners,
        )

    def _feedforward_weight_summary(self) -> dict:
        ff = np.array([self._all_weights()[f'ff{i}->{j}'] for j in range(N_OUT) for i in range(N_PIX)],
                      dtype=float)
        pos = ff[ff > 0]
        return dict(
            exact_zero_count=int(np.sum(np.isclose(ff, 0.0))),
            min_weight=round(float(ff.min()) if ff.size else 0.0, 4),
            min_positive_weight=round(float(pos.min()) if pos.size else 0.0, 4),
        )

    def _pc_summary(self) -> dict:
        if not self.prediction_column_enabled:
            return dict(enabled=False, current_spikes=0, max_activation=0.0,
                        spike_history_total=0, mature_columns=0)
        pcs = [self.neurons[f'PC{i}'] for i in range(N_PIX)]
        max_activation = max(
            (float(pc.potential) / max(float(pc.threshold), 1.0) for pc in pcs),
            default=0.0)
        spike_history_total = sum(self._neuron_total_spikes.get(f'PC{i}', 0) for i in range(N_PIX))
        mature_columns = sum(1 for i in range(N_PIX)
                             if self._neuron_total_spikes.get(f'PC{i}', 0) > 0)
        return dict(
            enabled=True,
            current_spikes=int(sum(1 for i in range(N_PIX) if self.spiked[f'PC{i}'])),
            max_activation=round(float(max_activation), 4),
            spike_history_total=int(spike_history_total),
            mature_columns=int(mature_columns),
        )

    def simulator_status(self) -> dict:
        named = self._detected_named_input()
        l2e_states = [self._l2e_status(j) for j in range(N_OUT)]
        ownership = self._ownership_summary()
        weights = self._feedforward_weight_summary()
        switchi_firing = sum(1 for row in self._switchi_local_last_events if row.get('fired'))
        return dict(
            detected_pattern=named['name'] if named else 'manual',
            detected_role=named['role'] if named else 'manual',
            prediction_output_state=self._prediction_output_state(),
            ownership=ownership,
            active_l2e=sum(1 for row in l2e_states if row['status'] != 'unrecruited'),
            unrecruited_l2e=sum(1 for row in l2e_states if row['status'] == 'unrecruited'),
            pc=self._pc_summary(),
            exact_zero_feedforward=weights['exact_zero_count'],
            min_feedforward_weight=weights['min_weight'],
            min_positive_feedforward_weight=weights['min_positive_weight'],
            switchi_local_firing=switchi_firing,
        )

    # ------------------------------------------------------------ serialization
    def topology(self) -> dict:
        weights = self._all_weights()
        confidence = self._all_confidence()
        delivery = self._delivery_diagnostics()
        neurons = [dict(**self.meta[nid]) for nid in self.neurons]
        # The structural reset fanout has no weight: serialize kind='reset_inhibition'
        # with weight=null so it never reads as a learned magnitude.
        synapses = [dict(**s,
                         weight=(None if s['kind'] == 'reset_inhibition'
                                 else round(weights.get(s['id'], 0.0), 4)),
                         confidence=round(confidence[s['id']], 4) if s['id'] in confidence else None,
                         # Per-connection distance/influence/effective-transmission
                         # (feedforward synapses only; brief S7's required
                         # per-connection inspector fields, previously absent
                         # end-to-end -- see the Phase 1 audit).
                         **delivery.get(s['id'], {}))
                    for s in self.synapses]
        return dict(neurons=neurons, synapses=synapses, layers=['L1', 'L2'],
                    patterns=list(PATTERNS.keys()),
                    pattern_vectors={k: list(map(int, v)) for k, v in PATTERNS.items()},
                    # Held-out probes (never trained -- see PROBES) and shared
                    # pattern-role metadata, so the frontend never re-derives or
                    # hardcodes which names are trainable vs. held-out.
                    probes=list(PROBES.keys()),
                    probe_vectors={k: list(map(int, v)) for k, v in PROBES.items()},
                    pattern_roles=dict(PATTERN_ROLE),
                    # Geometry descriptor (Phase 3): lets the UI clearly label
                    # when distance/influence numbers are a TEMPORARY legacy-
                    # reference placeholder rather than computed from the
                    # (possibly jittered) positions actually shown -- see
                    # legacy_distance_compat's docstring in _apply_l2e_distances.
                    # Never presented as if the pinned numbers came from the new
                    # coordinates: `legacy_distance_compat_active` is only True
                    # when the two could actually diverge (irregular geometry +
                    # the compat shim both on).
                    geometry=dict(symmetric=self.params['symmetric_geometry'],
                                 topology_seed=self.params['topology_seed'],
                                 legacy_distance_compat=self.params['legacy_distance_compat'],
                                 legacy_distance_compat_active=(
                                     self.params['legacy_distance_compat']
                                     and not self.params['symmetric_geometry'])),
                    grid=dict(rows=3, cols=3),
                    prediction=dict(
                        enabled=self.prediction_excitatory_enabled,
                        decoder_shape=[N_OUT, N_PIX],
                        p_ids=[f'P{i}' for i in range(N_PIX)] if self.prediction_excitatory_enabled else [],
                        pixel_mapping={f'P{i}': i for i in range(N_PIX)} if self.prediction_excitatory_enabled else {},
                        replay_weight=round(float(self.prediction_replay_weight), 4)
                        if self.prediction_excitatory_enabled else None,
                        learning_note=('Phase 19A scaffolds storage/delivery only; a future local '
                                       'L2E->P rule needs a pixel-local teaching signal for Pi, '
                                       'not labels or a global reconstruction error.')
                    ),
                    prediction_column=dict(
                        enabled=self.prediction_column_enabled,
                        pc_ids=[f'PC{i}' for i in range(N_PIX)]
                        if self.prediction_column_enabled else [],
                        roles=['basal', 'apical'] if self.prediction_column_enabled else [],
                        decoder_shape=[N_OUT, N_PIX],
                        output_route='PC_i -> L1I_i -> L1E_i'
                        if self.prediction_column_to_i_enabled else None,
                        output_delivery_enabled=(
                            self.prediction_column_to_i_delivery_enabled
                            if self.prediction_column_to_i_enabled else False),
                        persistent_conductance=(
                            self.prediction_column_persistent_conductance_enabled
                            if self.prediction_column_to_i_enabled else False),
                        output_state=self._prediction_output_state()),
                    switchi_paired_l2_shunt=dict(
                        enabled=self.switchi_paired_shunt_enabled,
                        output_route='SwitchI_j -> L2E_j' if self.switchi_paired_shunt_enabled else None,
                        trace_decay=round(float(self.switchi_trace_decay), 4),
                        coincidence_threshold=round(float(self.switchi_coincidence_threshold), 4),
                        shunt_frac=round(float(self.switchi_shunt_frac), 4)),
                    switchi_local_l2_ownership=dict(
                        enabled=self.switchi_local_mismatch_enabled,
                        trigger=('R_i(t) = basal L1_i present and PC_i failed to fire; '
                                 'request_j = sum_i elig[j,i] * R_i(t); delivery at t+2'),
                        output_route='SwitchI_j -> L2E_j' if self.switchi_local_mismatch_enabled else None,
                        trace_decay=round(float(self.switchi_trace_decay), 4),
                        coincidence_threshold=round(float(self.switchi_coincidence_threshold), 4),
                        shunt_frac=round(float(self.switchi_shunt_frac), 4)),
                    init_modes=dict(
                        default='legacy_wide',
                        available=['legacy_wide', 'edge_detector_candidate', 'balanced'],
                        edge_detector_candidate=dict(
                            source='legacy_wide',
                            target_mean=EDGE_DETECTOR_CANDIDATE_MEAN,
                            preserves_relative_random_differences=True,
                            note='Measured developmental candidate only; does not solve ownership by itself.')),
                    params=self.params)

    def dynamic_state(self) -> dict:
        stored_decoder = self._stored_prediction_decoder_matrix()
        effective_decoder = self._effective_prediction_decoder_matrix()
        neurons = []
        for nid, n in self.neurons.items():
            # Report one coherent phase for every population: the live membrane at
            # the end of the completed step. Previously L2E used the pre-update
            # l2_charge snapshot while L2I used this post-update value, which hid
            # L2E leak but exposed L2I leak/reset in the same chart. l2_drive and
            # l2_charge remain available internally as phase diagnostics.
            pot = float(n.potential)
            thr = self.meta[nid]['threshold'] or 1.0
            budget, budget_used = self._budget_usage(nid)
            neurons.append(dict(id=nid, potential=round(pot, 4),
                                activation=round(pot / thr, 4),
                                spiked=self.spiked[nid], freq=round(self.firing_freq(nid), 4),
                                refractory=int(n.refractory_timer),
                                budget=round(budget, 4) if budget is not None else None,
                                budget_used=round(budget_used, 4) if budget_used is not None else None,
                                assembly=(self.winner if nid == self.winner else None),
                                # Optional flow-rate diagnostic: current-trace amplitude.
                                **({'exc_trace': round(float(n.exc_trace), 4)}
                                   if self.excitatory_flow_rate and n.excitatory_flow_rate else {}),
                                # Evidence-based RF status (L2E only) -- see _l2e_status.
                                **({'rf_status': self._l2e_status(int(nid[3:]))}
                                   if nid.startswith('L2E') else {}),
                                # Phase 10: adaptive-threshold state (L2E only;
                                # a_i is 0 and effective_threshold == threshold
                                # for every other population always).
                                **({'threshold_adapt': round(float(n.threshold_adapt), 4),
                                   'effective_threshold': round(float(n.effective_threshold), 4)}
                                   if nid.startswith('L2E') else {})))
        return dict(timestep=self.timestep, running=False, neurons=neurons,
                    changed_synapses=self.changed_synapses,
                    changed_confidence=self.changed_confidence,
                    emitted=self.emitted,
                    input=self.input_vec.astype(int).tolist(), winner=self.winner,
                    autocycle=dict(enabled=self.auto_cycle, pattern=self.current_pattern,
                                   target=self.trained_streak, visit_steps=self.visit_steps,
                                   last_winner=self._pattern_last_winner.get(self.current_pattern),
                                   streak=self._pattern_streak.get(self.current_pattern, 0),
                                   trained=sum(1 for v in self._pattern_trained.values() if v),
                                   total=len(self._pattern_trained),
                                   trained_map={n: self._pattern_trained[n] for n in self._cycle_order}),
                    l2_charge_chunks=self.l2_charge_chunks,
                    l2_winner_chunk=self.l2_winner_chunk,
                    l2_inh_phases=self.l2_inh_phase_debug,
                    # Pre-WTA (l2_drive) / post-inhibition-pre-update (l2_charge)
                    # per-L2E membrane snapshots -- previously computed internally
                    # every step but never serialized (Phase 1 audit: "pre/post
                    # integration diagnostics" gap).
                    l2_drive={k: round(v, 4) for k, v in self.l2_drive.items()},
                    l2_charge={k: round(v, 4) for k, v in self.l2_charge.items()},
                    # Raw per-event L1I/L2I inhibitory-gate-plasticity records for
                    # this step (previously only summarized into the text event log).
                    inh_events=[dict(neuron=nid, **ev) for nid, ev in self._inh_events],
                    # Backend-driven Causal Story (brief SS9's required fields:
                    # first physical L2E responder, same-step tie, first L1I/L2I
                    # source, recorded -- never inferred/re-derived client-side).
                    probe=dict(active=self._probe_active,
                              steps_total=self.probe_steps_total,
                              steps_elapsed=self._probe_steps_elapsed),
                    causal_story=dict(
                        presentation_id=self.presentation_id,
                        pattern=self.presentation_pattern,
                        role=self.presentation_role,
                        start_t=self.presentation_start_t,
                        plasticity_frozen=self.plasticity_frozen,
                        # Phase 6: physicalFirstSpiker/physicalFirstSpikeStep --
                        # raw facts, recorded even during a same-step tie (see
                        # `winner` above for the separate, credit-bearing
                        # representation candidate, which is None when tied).
                        first_spiker=self._presentation_first_spiker,
                        first_spike_t=self._presentation_first_spike_t,
                        same_step_tie=self._presentation_tie,
                        earliest_response_set=list(self._presentation_earliest_response_set),
                        later_responses=list(self._presentation_later_responses),
                        latency_to_second_response=self._presentation_latency_to_second,
                        l1i_first_source=self._presentation_l1i_first_source,
                        l1i_first_t=self._presentation_l1i_first_t,
                        # Phase 9: full causal L1I predictive-feedback chain --
                        # arrival (real L2E delivery reaches L1I) is separate
                        # from threshold_t (L1I itself fires); source_set is
                        # the raw contributor list (recorded even when
                        # ambiguous); targets are which L1I fired; delivery is
                        # the resulting L1I->L1E pulse's recorded effect one
                        # step later. Nothing here is inferred -- every field
                        # is read off an already-decided physical event.
                        l1i_first_source_set=list(self._presentation_l1i_first_source_set),
                        l1i_first_arrival_t=self._presentation_l1i_first_arrival_t,
                        l1i_first_targets=list(self._presentation_l1i_first_targets),
                        l1i_first_delivery=self._presentation_l1i_first_delivery,
                        l2i_first_source=self._presentation_l2i_first_source,
                        l2i_first_t=self._presentation_l2i_first_t,
                        history=list(self.presentation_log)[-10:]),
                    # Phase 7: causal L2E->L2I->L2E competition, backend-recorded
                    # (never inferred from neuron IDs or final spike counts).
                    # pending: deliveries scheduled but not yet due (contributing
                    # sources + arrival times, L2I pre/post charge at ITS
                    # threshold crossing, scheduled delivery step, magnitude).
                    # last_delivery/log: deliveries actually APPLIED (per-target
                    # competitor pre/post charge and whether delivery reached
                    # that target -- a refractory target is skipped, not forced).
                    l2_inhibition=dict(
                        delay=self.l2_inhibition_delay,
                        magnitude=round(self.l2_inhibition_magnitude, 4),
                        pending=[dict(fire_t=rec['fire_t'], deliver_at=rec['deliver_at'],
                                     contributors=[f'{ct}:{cid}' for ct, cid in rec['contributors']],
                                     l2i_v_pre=rec['l2i_v_pre'], l2i_v_post=rec['l2i_v_post'],
                                     magnitude=round(rec['magnitude'], 4))
                                for rec in self._l2i_pending],
                        last_delivery=self._last_l2_inhibition_delivery,
                        log=list(self._l2_inhibition_log)[-10:]),
                    prediction=dict(
                        enabled=self.prediction_excitatory_enabled,
                        replay_enabled=self.prediction_replay_enabled,
                        decoder_control=self.prediction_decoder_control,
                        plasticity_frozen=self.plasticity_frozen,
                        sensory_input_present=bool(np.any(self.input_vec > 0.5)),
                        p_ids=[f'P{i}' for i in range(N_PIX)] if self.prediction_excitatory_enabled else [],
                        pixel_mapping={f'P{i}': i for i in range(N_PIX)} if self.prediction_excitatory_enabled else {},
                        stored_decoder=self._prediction_decoder_dict(stored_decoder),
                        effective_decoder=self._prediction_decoder_dict(effective_decoder),
                        local_replay={f'P{i}': dict(target=f'L1E{i}',
                                                    weight=round(float(self.prediction_replay_weight), 4))
                                      for i in range(N_PIX)} if self.prediction_excitatory_enabled else {},
                        pending=dict(decoder=list(self._prediction_pending_decoder),
                                     replay=list(self._prediction_pending_replay)),
                        arrived=dict(decoder=list(self._prediction_last_decoder_arrivals),
                                     replay=list(self._prediction_last_replay_arrivals)),
                        integrated=dict(decoder=list(self._prediction_last_decoder_integrated)),
                        delivered=dict(replay=list(self._prediction_last_replay_deliveries)),
                        weight_cap=round(float(self.prediction_weight_cap), 4)
                        if self.prediction_excitatory_enabled else None,
                        learning_note=('Phase 19A does not implement active L2E->P plasticity. '
                                       'A future local rule must use only signals local to Pi and '
                                       'its incoming decoder synapses.')),
                    prediction_column=dict(
                        enabled=self.prediction_column_enabled,
                        spiked={f'PC{i}': bool(self.spiked[f'PC{i}']) for i in range(N_PIX)}
                        if self.prediction_column_enabled else {},
                        compartments={
                            f'PC{i}': dict(
                                basal_sources=list(pc.last_basal_sources),
                                apical_sources=list(pc.last_apical_sources),
                                basal_charge=round(float(pc.last_basal_charge), 4),
                                apical_charge=round(float(pc.last_apical_charge), 4),
                                coincidence_step=pc.last_coincidence_step,
                                d_before_learning=pc.last_d_before_learning)
                            for i, pc in enumerate(self.pcol)}
                        if self.prediction_column_enabled else {},
                        pending_deliveries=[dict(record) for slot in
                                            self.pcol_delivery_metadata_queue
                                            for record in slot]
                        if self.prediction_column_enabled else [],
                        last_deliveries=list(self._prediction_column_last_deliveries)
                        if self.prediction_column_enabled else [],
                        last_output_delivery=list(self._prediction_column_last_output_delivery)
                        if self.prediction_column_enabled else [],
                        last_conductance=list(self._prediction_column_last_conductance)
                        if self.prediction_column_enabled else [],
                        output_delivery_enabled=(
                            self.prediction_column_to_i_delivery_enabled
                            if self.prediction_column_enabled else False),
                        persistent_conductance_enabled=(
                            self.prediction_column_persistent_conductance_enabled
                            if self.prediction_column_enabled else False)),
                    switchi_paired_l2_shunt=dict(
                        enabled=self.switchi_paired_shunt_enabled,
                        recent_spike_trace={f'L2E{j}': round(float(v), 4)
                                            for j, v in enumerate(self.switchi_recent_spike_trace)},
                        last_events=list(self._switchi_last_events)
                        if self.switchi_paired_shunt_enabled else []),
                    switchi_local_l2_ownership=dict(
                        enabled=self.switchi_local_mismatch_enabled,
                        recent_spike_trace={f'L2E{j}': round(float(v), 4)
                                            for j, v in enumerate(self.switchi_recent_spike_trace)},
                        eligibility={
                            f'L2E{j}': [round(float(v), 4) for v in self.switchi_local_elig[j]]
                            for j in range(N_OUT)
                        } if self.switchi_local_mismatch_enabled else {},
                        pending=[dict(rec) for rec in self._switchi_local_pending]
                        if self.switchi_local_mismatch_enabled else [],
                        last_residual=list(self._switchi_local_last_residual)
                        if self.switchi_local_mismatch_enabled else [],
                        last_requests=list(self._switchi_local_last_requests)
                        if self.switchi_local_mismatch_enabled else [],
                        last_deliveries=list(self._switchi_local_last_deliveries)
                        if self.switchi_local_mismatch_enabled else [],
                        last_events=list(self._switchi_local_last_events)
                        if self.switchi_local_mismatch_enabled else [],
                        diagnostics=dict(self._switchi_local_last_diag)
                        if self.switchi_local_mismatch_enabled else {}),
                    simulator_status=self.simulator_status(),
                    # Phase 10: adaptive-threshold ablation state/trajectory
                    # (L2E only; a_i and its history stay 0/empty for every
                    # other population always, and for L2E itself whenever the
                    # flag is off).
                    adaptive_threshold=dict(
                        enabled=self.params['adaptive_threshold'],
                        delta_threshold=round(self.l2.excitatory_neurons[0].delta_threshold, 4)
                            if N_OUT else 0.0,
                        tau_threshold=self.params['tau_threshold'],
                        state={f'L2E{j}': round(float(e.threshold_adapt), 4)
                              for j, e in enumerate(self.l2.excitatory_neurons)},
                        effective_threshold={f'L2E{j}': round(float(e.effective_threshold), 4)
                                            for j, e in enumerate(self.l2.excitatory_neurons)},
                        history={nid: list(hist) for nid, hist in self.threshold_adapt_history.items()}),
                    stats=self.stats(), log=list(self.event_log)[-12:])

    def stats(self) -> dict:
        active = sum(1 for nid in self.neurons if abs(self.neurons[nid].potential) > 1e-3)
        firing = sum(1 for nid in self.neurons if self.spiked[nid])
        pots = [self.neurons[nid].potential for nid in self.neurons]
        weights = list(self._all_weights().values())
        rate = float(np.mean([self.firing_freq(nid) for nid in self.neurons]))
        return dict(total=len(self.neurons), active=active, firing=firing,
                    avg_activation=round(float(np.mean(np.abs(pots))), 4),
                    firing_rate=round(rate, 4), avg_weight=round(float(np.mean(weights)), 4),
                    winner=self.winner)
