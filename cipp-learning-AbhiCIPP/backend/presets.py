"""
Shared SimulationEngine configuration presets.

MEASUREMENT/CONFIGURATION INFRASTRUCTURE ONLY -- this module changes no
neural equation and no SimulationEngine constructor default. It exists solely
so backend/api.py (the live dashboard) and single_pattern_diagnostic.py (the
read-only diagnostic script) build the engine from the SAME literal override
dict, instead of two independently-typed-out kwarg lists that can silently
drift apart (which is exactly what happened before this patch -- see the
2026-07-13 configuration-mismatch finding).

DASHBOARD_ENGINE_OVERRIDES is copied verbatim from the kwargs backend/api.py
passed to SimulationEngine(...) prior to this patch. Every value here must be
byte-identical to what the dashboard used before; that identity is asserted
by test_presets.py.

This module must NOT import backend.api (or vice versa in a way that
constructs anything): it only defines a plain dict, no FastAPI app, no engine
instance, so it is safe for single_pattern_diagnostic.py to import without
any server-side effects.
"""

from __future__ import annotations

# Copied verbatim from backend/api.py's prior inline SimulationEngine(...) call.
# See that file's comments for the rationale behind each value; this dict is
# the single source of truth for what "the dashboard configuration" means.
DASHBOARD_ENGINE_OVERRIDES: dict = dict(
    signed_spike_learning=True,   # signed +1/-1 feedforward learning (the algorithm)
    l2e_budget=False,             # no positive-weight budget; -1 signal supplies down-pressure
    confidence_consolidation=False,
    loser_depression=True,
    eta_loss=10.0,                # symmetry-breaker strength (0.01 default is far too weak)
    assembly_flow_credit=True,    # flow-proportional E->I credit on L2I/L1I fire
    signed_depression=False,      # inert under signed_spike_learning=True anyway (see
                                   # neuron_flexible.Neuron._update_weights -- the signed
                                   # branch returns before reaching the signed_depression
                                   # block); kept explicit for clarity, not because it
                                   # changes anything while signed_spike_learning is on.
    homeostasis=False,
    refractory=0,                 # inhibition regulates frequency, not a hard lockout
    l2e_weight_cap_frac=1 / 3,
    pos_weight_floor=1,
    l2i_threshold_frac=1 / 7,
    l1i_threshold_frac=1 / 3,
    l2e_lr_frac=0.02,
    ei_sat_mult=4.0,
)

# "constructor" preset intentionally supplies NO overrides: it means "use
# SimulationEngine's own constructor defaults, unmodified." Kept as a named
# preset (rather than just an empty dict inline) so both api.py-style callers
# and the diagnostic's --preset flag refer to the same named concept.
CONSTRUCTOR_ENGINE_OVERRIDES: dict = dict()

PRESETS: dict[str, dict] = {
    "constructor": CONSTRUCTOR_ENGINE_OVERRIDES,
    "dashboard": DASHBOARD_ENGINE_OVERRIDES,
}
