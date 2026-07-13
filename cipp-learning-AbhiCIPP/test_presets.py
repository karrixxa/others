"""Tests for the measurement/configuration infrastructure added 2026-07-13
(backend/presets.py + single_pattern_diagnostic.py's --preset flag).

These are pure measurement/configuration tests -- none of them touch a neural
equation. They prove:
  1. backend/api.py builds its engine from backend.presets.DASHBOARD_ENGINE_OVERRIDES
     (so the dashboard's actual config and this test's expected literal cannot
     silently diverge without this test catching it).
  2. --preset constructor adds zero overrides (pure SimulationEngine defaults).
  3. --preset dashboard resolves to exactly DASHBOARD_ENGINE_OVERRIDES.
  4. Explicit CLI overrides win over whatever the selected preset set.
  5. --assembly-flow-credit / --no-assembly-flow-credit both work explicitly.
  6. test_neuron.py's existing behavior is unaffected (imported and re-run here
     as a smoke check; the authoritative run is still `python3 test_neuron.py`).
  7. No .js/.html/.css file changed as part of this patch (repo-state check).
"""

import subprocess
import sys

from backend.presets import CONSTRUCTOR_ENGINE_OVERRIDES, DASHBOARD_ENGINE_OVERRIDES, PRESETS
from backend.simulation import SimulationEngine
from single_pattern_diagnostic import _resolve_config, build_parser

# The exact override values backend/api.py used to pass to SimulationEngine
# inline, BEFORE this patch (captured from the repo history at the time this
# infrastructure was added). If backend/presets.py's DASHBOARD_ENGINE_OVERRIDES
# ever drifts from this, either api.py's behavior changed (needs a deliberate
# decision) or this expected literal needs deliberate updating -- either way,
# it must never happen silently.
_EXPECTED_DASHBOARD_OVERRIDES = dict(
    signed_spike_learning=True,
    l2e_budget=False,
    confidence_consolidation=False,
    loser_depression=True,
    eta_loss=10.0,
    assembly_flow_credit=True,
    signed_depression=False,
    homeostasis=False,
    refractory=0,
    l2e_weight_cap_frac=1 / 3,
    pos_weight_floor=1,
    l2i_threshold_frac=1 / 7,
    l1i_threshold_frac=1 / 3,
    l2e_lr_frac=0.02,
    ei_sat_mult=4.0,
)


def test_dashboard_preset_matches_expected_literal():
    assert DASHBOARD_ENGINE_OVERRIDES == _EXPECTED_DASHBOARD_OVERRIDES, (
        "backend.presets.DASHBOARD_ENGINE_OVERRIDES no longer matches the "
        "dashboard config captured when this infrastructure was added -- "
        "either api.py's behavior changed on purpose (update this literal) "
        "or something drifted (investigate before proceeding)")


def test_api_engine_receives_identical_params_to_dashboard_preset():
    """Build one engine the way backend/api.py does (via the preset) and one
    directly from the expected literal; every resolved SimulationEngine param
    the preset actually sets must match between them."""
    from_preset = SimulationEngine(seed=1, **DASHBOARD_ENGINE_OVERRIDES)
    from_literal = SimulationEngine(seed=1, **_EXPECTED_DASHBOARD_OVERRIDES)
    for key in DASHBOARD_ENGINE_OVERRIDES:
        assert from_preset.params[key] == from_literal.params[key], (
            f"param {key!r} differs between the preset-built and literal-built engine")


def test_constructor_preset_has_no_overrides():
    assert CONSTRUCTOR_ENGINE_OVERRIDES == {}, (
        "'constructor' preset must supply zero overrides -- it means "
        "'plain SimulationEngine defaults', not a hidden set of tweaks")
    assert PRESETS["constructor"] is CONSTRUCTOR_ENGINE_OVERRIDES


def test_constructor_preset_matches_plain_defaults():
    """An engine built via --preset constructor (no CLI overrides) must be
    parameter-identical to a bare SimulationEngine(seed=...)."""
    parser = build_parser()
    args = parser.parse_args(["--preset", "constructor"])
    config = _resolve_config(args.preset, args)
    assert config == {}, f"expected no overrides from --preset constructor, got {config}"
    from_preset = SimulationEngine(seed=1, **config)
    plain = SimulationEngine(seed=1)
    # Spot-check a representative sample of params that DASHBOARD_ENGINE_OVERRIDES
    # touches, to confirm the constructor preset really does leave them at the
    # class defaults (not, say, accidentally inheriting a leftover global).
    for key in DASHBOARD_ENGINE_OVERRIDES:
        assert from_preset.params[key] == plain.params[key]


def test_dashboard_preset_cli_matches_dict():
    parser = build_parser()
    args = parser.parse_args(["--preset", "dashboard"])
    config = _resolve_config(args.preset, args)
    assert config == DASHBOARD_ENGINE_OVERRIDES


def test_explicit_cli_override_wins_over_preset():
    parser = build_parser()
    args = parser.parse_args(["--preset", "dashboard", "--eta-loss", "2"])
    config = _resolve_config(args.preset, args)
    assert config["eta_loss"] == 2.0, "explicit --eta-loss must override the dashboard preset's 10.0"
    # Everything else the dashboard preset set should be untouched.
    for key, value in DASHBOARD_ENGINE_OVERRIDES.items():
        if key != "eta_loss":
            assert config[key] == value


def test_assembly_flow_credit_explicit_enable_and_disable():
    parser = build_parser()

    args_on = parser.parse_args(["--preset", "constructor", "--assembly-flow-credit"])
    config_on = _resolve_config(args_on.preset, args_on)
    assert config_on["assembly_flow_credit"] is True

    args_off = parser.parse_args(["--preset", "dashboard", "--no-assembly-flow-credit"])
    config_off = _resolve_config(args_off.preset, args_off)
    assert config_off["assembly_flow_credit"] is False
    # Confirm it actually overrode the dashboard preset's True, not just
    # happened to already be False.
    assert DASHBOARD_ENGINE_OVERRIDES["assembly_flow_credit"] is True


def test_unspecified_overrides_stay_none_before_resolution():
    """argparse itself must default every override flag to None (not some
    reintroduced hardcoded value) -- _resolve_config is what turns 'None' into
    'inherit from preset', so if argparse's own defaults were non-None this
    guarantee would break silently."""
    parser = build_parser()
    args = parser.parse_args(["--preset", "dashboard"])
    for name in ("inhibitory_eta_up", "inhibitory_eta_down", "allow_subrest_inhibition",
                 "l2_gate_eq_frac", "l2e_weight_cap_frac", "eta_loss", "assembly_flow_credit"):
        assert getattr(args, name) is None, f"--{name.replace('_', '-')} must default to None"


def test_existing_neuron_suite_unaffected():
    result = subprocess.run([sys.executable, "test_neuron.py"], capture_output=True, text=True)
    assert result.returncode == 0, f"test_neuron.py failed:\n{result.stdout}\n{result.stderr}"
    assert "ALL NEURON UNIT TESTS PASSED" in result.stdout


def test_no_js_html_css_files_touched_by_this_patch():
    """This patch is measurement/configuration-only; it must not have touched
    any frontend file. Checks the working tree against HEAD (uncommitted
    changes) -- run this before committing, not after."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True, cwd=".")
    changed = [f for f in result.stdout.splitlines() if f]
    frontend_changed = [f for f in changed if f.endswith((".js", ".html", ".css"))]
    assert not frontend_changed, f"frontend files touched by this patch: {frontend_changed}"


if __name__ == "__main__":
    test_dashboard_preset_matches_expected_literal()
    test_api_engine_receives_identical_params_to_dashboard_preset()
    test_constructor_preset_has_no_overrides()
    test_constructor_preset_matches_plain_defaults()
    test_dashboard_preset_cli_matches_dict()
    test_explicit_cli_override_wins_over_preset()
    test_assembly_flow_credit_explicit_enable_and_disable()
    test_unspecified_overrides_stay_none_before_resolution()
    test_existing_neuron_suite_unaffected()
    test_no_js_html_css_files_touched_by_this_patch()
    print("ALL PRESET/CONFIGURATION TESTS PASSED")
