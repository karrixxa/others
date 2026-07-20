#!/usr/bin/env python3
"""Build the curated Phase 35 research ledger from immutable codex-runs artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

SOURCE_ROOT = Path("/home/cxiong/codex-runs")
LEDGER_ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = "db30ceadbe18cf90e01f6d54dee0203f342b24a8"
BASE = "4764f1758a7399439df2242dfa60819501fc2333"
RELEASE_BUNDLE = "phase35-large-raw-traces-db30cead.tar.gz"
RELEASE_BUNDLE_SHA256 = "81e4ebbd55b6b7196175ebb1e74691be88e050e61423f8ba6c3065ae214a199b"
RELEASE_BUNDLE_SIZE = 5_343_995

AUDITS = [
    dict(slug="claude-gate-a-b-review", source="claude-phase35-gate-a-b-review", agent="Claude",
         verdict="MIXED", commit="4e712a4b7dea033b9191680a4b4e3577d93ca304", runtime="not reported",
         conclusion="Gate A/B reproduced, but the original queue-deletion behavior and four opt-in regressions required repair/reclassification."),
    dict(slug="claude-mature-efficacy", source="claude-phase35-mature-efficacy", agent="Claude",
         verdict="MATURE_ACTIVE_SUPPRESSION_EFFECTIVE_BUT_OWNERSHIP_NEUTRAL", commit=CHECKPOINT, runtime="~100 s",
         conclusion="Naturally matured prediction suppresses explained sensory activity, but does not repair L2 ownership or collision dynamics."),
    dict(slug="claude-oracle-review", source="claude-phase35-oracle-review", agent="Claude",
         verdict="ORACLE_VALID_WITH_COVERAGE_GAPS", commit="oracle-only; production comparison target 4e712a4", runtime="not reported",
         conclusion="The original independent gate enumeration was real, but decoder indexing, clearing, carryover, and exactly-once coverage had gaps."),
    dict(slug="claude-repair-review", source="claude-phase35-repair-review", agent="Claude",
         verdict="REPAIR_VERIFIED_NO_NEW_REGRESSIONS", commit=CHECKPOINT, runtime="not reported",
         conclusion="Queue carryover repair, provenance telemetry, Gate A/B, default-off equivalence, and emergent maturity ordering were independently verified."),
    dict(slug="claude-selective-switch-timing-contract", source="claude-phase35-selective-switch-timing-contract", agent="Claude",
         verdict="LOCAL_SELECTIVE_SWITCH_TIMING_VALID", commit=CHECKPOINT, runtime="static analysis; no simulation",
         conclusion="A local residual-driven selective L2 switch can fit existing step ordering, with accumulation safeguards and explicit negative controls."),
    dict(slug="claude-suppression-causal-reach", source="claude-phase35-suppression-causal-reach", agent="Claude",
         verdict="SUPPRESSION_CHANGES_LATER_ACTIVITY_ONLY", commit=CHECKPOINT, runtime="~116 s",
         conclusion="PC-to-local-I suppression causally affects later sensory activity but cannot alter the already-resolved same-step L2 competition."),
    dict(slug="codex1-conformance-repair", source="codex1-phase35-conformance-repair", agent="Codex 1",
         verdict="QUEUE_FIXED_MATURITY_WAS_ADAPTER_ERROR", commit=CHECKPOINT, runtime="not reported",
         conclusion="Scheduled events now survive switches exactly once; direct production maturity follows the established saturating quadratic update."),
    dict(slug="codex1-exact-tie-audit", source="codex1-phase35-exact-tie-audit", agent="Codex 1",
         verdict="FAST_FIRST_SPIKE_PATH_CAN_RESOLVE_MOST_TIES", commit=CHECKPOINT, runtime="344.88 s",
         conclusion="A one-step first-spike path can precede rivals in 19/29 tied seeds; 10/29 already need same-step symmetry breaking."),
    dict(slug="codex1-implementation", source="codex1-phase35-implementation", agent="Codex 1",
         verdict="GATE_A_B_PASS", commit="4e712a4b7dea033b9191680a4b4e3577d93ca304", runtime="not reported",
         conclusion="Introduced explicit basal/apical dendrites, local coincidence, sparse decoder learning, and paired PC output with default-off compatibility."),
    dict(slug="codex1-paired-failure-audit", source="codex1-phase35-paired-failure-audit", agent="Codex 1",
         verdict="EXISTING_PAIRED_PATH_UNAVAILABLE", commit=CHECKPOINT, runtime="<60 s",
         conclusion="The paired/defer-once path was an external Phase 29 monkeypatch, not a native repaired-lineage mechanism, so no comparison was run."),
    dict(slug="codex1-race-timing-decomposition", source="codex1-phase35-race-timing-decomposition", agent="Codex 1",
         verdict="ACCUMULATION_WINDOW_DOMINATES", commit=CHECKPOINT, runtime="0.99 s offline",
         conclusion="All genuine secondary race spikes occurred before shared L2I threshold crossing; delivery delay and residual charge were not primary."),
    dict(slug="codex1-source-fragmentation", source="codex1-phase35-source-fragmentation", agent="Codex 1",
         verdict="FRAGMENTATION_FROM_PRE_INHIBITION_RACE", commit=CHECKPOINT, runtime="134.90 s",
         conclusion="Decoder-source fragmentation is driven primarily by multiple L2 responders receiving credit before shared inhibition resolves."),
    dict(slug="codex2-decoder-selectivity", source="codex2-phase35-decoder-selectivity", agent="Codex 2",
         verdict="CLEAN_PATTERN_DECODERS_EMERGE", commit=CHECKPOINT, runtime="offline analysis; not reported",
         conclusion="At 25,600 steps, 11 clean complete pattern decoders emerge, but per-seed pattern coverage remains incomplete."),
    dict(slug="codex2-dendrite-oracle", source="codex2-phase35-dendrite-oracle", agent="Codex 2",
         verdict="SEMANTIC_CONTRACT_CONSISTENT", commit="independent oracle; pre-repair comparison target 4e712a4", runtime="not reported",
         conclusion="The original oracle found zero counterexamples over its bounded two-event domain, before later review corrected contract gaps."),
    dict(slug="codex2-full-decoder-coverage", source="codex2-phase35-full-decoder-coverage", agent="Codex 2",
         verdict="COLLISION_BLOCKS_COMPLETE_COVERAGE", commit=CHECKPOINT, runtime="630.38 s",
         conclusion="Longer exposure improves decoder coverage, but persistent L2 ownership collisions prevent robust complete four-pattern coverage."),
    dict(slug="codex2-implementation-conformance", source="codex2-phase35-implementation-conformance", agent="Codex 2",
         verdict="MIXED", commit="4e712a4b7dea033b9191680a4b4e3577d93ca304", runtime="not reported",
         conclusion="Production matched physical gating/locality but exposed real switch-queue loss and an oracle learning-equation mismatch."),
    dict(slug="codex2-long-horizon-maturity", source="codex2-phase35-long-horizon-maturity", agent="Codex 2",
         verdict="MIXED_MATURITY_FAILURE", commit=CHECKPOINT, runtime="263.40 s",
         conclusion="Maturity eventually occurs, delayed by elapsed time and 4–6-source fragmentation; one seed reinforces a collided owner."),
    dict(slug="codex2-mismatch-reduction", source="codex2-phase35-mismatch-reduction", agent="Codex 2",
         verdict="QUEUE_DEFECT_REAL_MATURITY_ORACLE_MISMATCH", commit="4e712a4b7dea033b9191680a4b4e3577d93ca304", runtime="not reported",
         conclusion="Reduced the true queue-loss defect and demonstrated that maturity divergence came from the oracle's linear update, not production."),
    dict(slug="codex2-natural-exposure-audit", source="codex2-phase35-natural-exposure-audit", agent="Codex 2",
         verdict="NATURAL_EXPOSURE_INSUFFICIENT", commit=CHECKPOINT, runtime="46.71 s",
         conclusion="At 3,200 steps no decoder matures; local updates and repaired stale carryover are correct but source-specific exposure is diffuse."),
    dict(slug="codex2-oracle-v2", source="codex2-phase35-oracle-v2", agent="Codex 2",
         verdict="REPAIRED_PRODUCTION_CONFORMS_TO_ORACLE_V2", commit=CHECKPOINT, runtime="not reported",
         conclusion="The corrected oracle agrees with repaired production on gating, learning, maturity ordering, carryover, locality, and default-off behavior."),
]

LARGE_RAW = {
    "codex1-phase35-source-fragmentation/seed-1-trace.json",
    "codex1-phase35-source-fragmentation/seed-2-trace.json",
    "codex1-phase35-source-fragmentation/seed-3-trace.json",
    "codex1-phase35-source-fragmentation/seed-4-trace.json",
    "codex1-phase35-source-fragmentation/seed-5-trace.json",
    "codex1-phase35-source-fragmentation/smoke.json",
    "codex2-phase35-natural-exposure-audit/results.json",
    "codex2-phase35-natural-exposure-audit/timeline.csv",
}

SUPPORT_JSON = {
    "coverage_review.json", "maturity_trace.json", "minimal_counterexamples.json",
    "golden_cases.json", "golden_cases_v2.json", "mismatch_traces.json",
    "mismatch_traces_v2.json",
}
SUPPORT_MD = {
    "implementation_contract.md", "semantic_contract.md", "semantic_contract_v2.md",
    "adapter_audit.md", "diff_review.md",
}
SKIP_DIRS = {".git", ".venv", "venv", "repo", "__pycache__"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_size(path: Path) -> int:
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except FileNotFoundError:
                pass
    return total


def is_commit_candidate(rel: Path) -> bool:
    name = rel.name
    if rel == Path("report.md") or rel == Path("progress.md") or rel == Path("results.json"):
        return True
    if rel.suffix == ".py" and len(rel.parts) <= 3:
        return True
    if name in SUPPORT_JSON or name in SUPPORT_MD:
        return True
    return False


def copy_curated(source: Path, destination: Path, rel: Path) -> Path:
    src = source / rel
    dst = destination / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if rel.name.endswith(".json"):
        try:
            value = json.loads(src.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            shutil.copy2(src, dst)
        else:
            dst.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    else:
        text = src.read_text()
        normalized = "\n".join(line.rstrip() for line in text.rstrip().splitlines()) + "\n"
        dst.write_text(normalized)
    return dst


def write_index() -> None:
    lines = [
        "# Phase 35 Research Ledger", "",
        f"Frozen repaired checkpoint: `{CHECKPOINT}`", "",
        f"Phase 29 base: `{BASE}`", "",
        "This ledger archives completed report-backed Phase 35 work. Original artifact directories remain immutable. Checkout-only directories and the report-less `codex2-phase35-residual-switch-feasibility` run are intentionally excluded.", "",
        "| Audit | Agent | Verdict | Commit/base | Runtime | Key conclusion |", "|---|---|---|---|---|---|",
    ]
    for audit in AUDITS:
        lines.append(
            f"| [{audit['slug']}]({audit['slug']}/report.md) | {audit['agent']} | `{audit['verdict']}` | `{audit['commit']}` | {audit['runtime']} | {audit['conclusion']} |"
        )
    lines.extend(["", "## Artifact policy", "",
                  "Compact reports, results, contracts, and runnable audit/validation scripts are committed. Logs, caches, bytecode, virtual environments, duplicate repositories, implementation bundles, and redundant generated timelines are excluded. Large raw traces are hashed and listed in `ARTIFACT_MANIFEST.json`; they are packaged separately as a GitHub Release asset.", ""])
    (LEDGER_ROOT / "INDEX.md").write_text("\n".join(lines))


def write_architecture_status() -> None:
    text = f"""# Phase 35 Architecture Status

## Frozen lineage

The current verified implementation is `{CHECKPOINT}`, descended from Phase 29 base `{BASE}` through implementation commit `4e712a4b7dea033b9191680a4b4e3577d93ca304` and the queue-carryover repair.

## Current architecture

- `DendriteCompartment` represents explicit `BASAL` and `APICAL` roles. A `CoincidencePyramidalCell` composes one basal compartment, one apical compartment, an ordinary soma/node, and axonal output.
- L1 sensory excitation targets the paired basal compartment. Every L2E source can reach all nine apical compartments through its local decoder connection `d[j,i]`.
- Coincidence is physical: basal and apical events must be delivered to the same target in the same engine timestep. Scheduling time, origin metadata, and learning traces cannot substitute for delivery-time coincidence.
- Neither branch alone deposits coincidence charge, fires the prediction cell, or updates a decoder. Compartment event state clears at each timestep boundary while already-scheduled queue events persist across presentation switches.
- Decoder learning is source/target local and basal-gated: `delta = eta * (1 - d_before/d_max)^2`, once per distinct delivered positive feedback source. The current event uses `d_before`; a boundary-crossing update can affect only a later valid coincidence.
- Maturity is an emergent charge condition, not a separate Boolean. At the committed defaults, basal contribution 150 plus decoder contribution 350 reaches soma threshold 500.
- The opt-in output route is `PC_i -> paired L1I_i -> paired sensory L1E_i`. The default-off engine remains equivalent to the Phase 29 baseline in the bounded hash and golden comparisons.

## Validated behavior

Gate A/B construction, explicit routing, single-branch controls, exact same-step coincidence, +/-1 rejection, clearing, no trace-driven firing, ordinary-neuron behavior, sparse learning, pre-learning maturity ordering, exactly-once queue carryover, four-class provenance telemetry, and default-off behavior have all been independently exercised. Corrected oracle v2 reports full agreement with repaired production over its bounded goldens and semantic enumeration.

Natural exposure confirms locality: inactive pixels remain byte-identical, stale switch arrivals are delivered rather than deleted, and long exposure can produce clean complete three-pixel decoders. Once mature, active prediction suppresses explained sensory activity. That suppression acts on later activity and remains ownership-neutral.

## Unresolved collision problem

The upstream L2 ownership failure predates useful prediction output. Shared L2I integrates several responder events before crossing threshold, so multiple L2E neurons physically spike and receive decoder credit during the accumulation window. Offline decomposition found no primary delivery-delay or post-inhibition-residual explanation for the fragmenting spikes.

Consequences observed across completed audits:

- decoder credit fragments across 4–6 L2 sources;
- 3,200-step exposure is insufficient for maturity;
- 25,600-step exposure produces selective decoders but not complete four-pattern coverage;
- persistent ownership collisions can reinforce a common-center decoder;
- 29/40 held-pattern seeds end in exact decoder/count ties, although only 4 are pure same-step crossings from onset;
- a one-step first-spike inhibitory path could precede all tied rivals in 19/29 seeds, while 10/29 already contain same-step rivals and require within-step symmetry breaking.

The historical paired/defer-once experiment is not a native path in this lineage and must not be treated as verified repaired-lineage production behavior.

## Experimental roadmap

1. Specify a biological first-spike recruitment pathway that closes the shared-L2I accumulation window without labels, owner locks, global argmax, or parameter forcing.
2. Add an explicit sub-step symmetry-breaking contract for genuine same-step crossings; first-spike delivery alone cannot retract a spike already emitted in the same outer timestep.
3. Evaluate the local residual/selective-switch timing contract as a separate mechanism. Preserve its two-event safeguard so a single missed familiar coincidence cannot force a switch.
4. Before integrated Gate C, require iso-seeded controls for random-stream equivalence, identical topology, queue carryover, exactly-once delivery, and default-off hashes.
5. Only after upstream ownership is measurably stable should prediction-to-local-I suppression be tested for four-pattern functional benefit. Do not tune eta, thresholds, delays, inhibition strength, or geometry to manufacture agreement.

## Current decision boundary

Phase 35 dendritic coincidence and local decoder semantics are validated at the repaired checkpoint. The load-bearing unresolved issue is upstream L2 physical competition: accumulation-window races and a minority of true same-step symmetries prevent robust ownership and complete decoder coverage. Prediction suppression should not be credited with solving that earlier failure.
"""
    (LEDGER_ROOT / "ARCHITECTURE_STATUS.md").write_text(text)


def main() -> None:
    LEDGER_ROOT.mkdir(parents=True, exist_ok=True)
    # Rebuild only generated ledger targets; preserve this builder under tools/.
    for audit in AUDITS:
        generated_dir = LEDGER_ROOT / audit["slug"]
        if generated_dir.exists():
            shutil.rmtree(generated_dir)
    for generated_name in ("INDEX.md", "ARCHITECTURE_STATUS.md", "ARTIFACT_MANIFEST.json", "SHA256SUMS"):
        generated_path = LEDGER_ROOT / generated_name
        if generated_path.exists():
            generated_path.unlink()
    manifest = {
        "schema_version": 1,
        "checkpoint": CHECKPOINT,
        "source_root": str(SOURCE_ROOT),
        "release_bundle": RELEASE_BUNDLE,
        "release_bundle_sha256": RELEASE_BUNDLE_SHA256,
        "release_bundle_size_bytes": RELEASE_BUNDLE_SIZE,
        "release_bundle_local_path": str(
            SOURCE_ROOT / "phase35-research-ledger-release" / RELEASE_BUNDLE),
        "audits": [],
        "files": [],
        "excluded_incomplete": [
            "/home/cxiong/codex-runs/codex2-phase35-residual-switch-feasibility",
            "/home/cxiong/codex-runs/codex2-phase35-base-checkout",
            "/home/cxiong/codex-runs/codex2-phase35-natural-exposure-checkout",
            "/home/cxiong/codex-runs/codex2-phase35-v2-checkout.bv1HPm",
            "/home/cxiong/codex-runs/codex2-phase35-checkout.gqJzv8",
        ],
    }

    for audit in AUDITS:
        src = SOURCE_ROOT / audit["source"]
        dst = LEDGER_ROOT / audit["slug"]
        if not (src / "report.md").is_file():
            raise RuntimeError(f"completed audit lacks report: {src}")
        dst.mkdir(parents=True, exist_ok=True)
        manifest["audits"].append({**audit, "original_path": str(src)})

        seen_skipped_dirs = set()
        for root, dirs, files in os.walk(src):
            root_path = Path(root)
            retained_dirs = []
            for dirname in dirs:
                child = root_path / dirname
                if (dirname in SKIP_DIRS or dirname.startswith("repo") or
                        dirname.endswith("-repo") or dirname.endswith("checkout")):
                    rel_dir = child.relative_to(src)
                    if rel_dir not in seen_skipped_dirs:
                        seen_skipped_dirs.add(rel_dir)
                        manifest["files"].append({
                            "original_path": str(child), "audit": audit["slug"],
                            "disposition": "excluded_generated_bulk", "kind": "directory_tree",
                            "size_bytes": tree_size(child), "reason": "duplicate repository, cache, or environment tree",
                        })
                else:
                    retained_dirs.append(dirname)
            dirs[:] = retained_dirs

            for filename in files:
                path = root_path / filename
                rel = path.relative_to(src)
                source_key = f"{audit['source']}/{rel.as_posix()}"
                size = path.stat().st_size
                digest = sha256(path)
                if source_key in LARGE_RAW:
                    manifest["files"].append({
                        "original_path": str(path), "audit": audit["slug"],
                        "disposition": "stored_separately", "release_bundle": RELEASE_BUNDLE,
                        "size_bytes": size, "sha256": digest, "reason": "large raw per-step trace/timeline",
                    })
                elif is_commit_candidate(rel):
                    archived = copy_curated(src, dst, rel)
                    manifest["files"].append({
                        "original_path": str(path), "archived_path": str(archived.relative_to(LEDGER_ROOT.parent.parent)),
                        "audit": audit["slug"], "disposition": "committed",
                        "original_size_bytes": size, "original_sha256": digest,
                    })
                else:
                    manifest["files"].append({
                        "original_path": str(path), "audit": audit["slug"],
                        "disposition": "excluded_generated_bulk", "size_bytes": size,
                        "sha256": digest, "reason": "log, bundle, redundant aggregate, or generated timeline",
                    })

        if not (dst / "results.json").exists():
            if audit["source"] == "codex2-phase35-natural-exposure-audit":
                synthetic = json.loads((src / "results.json").read_text())
                removed = {}
                for run in synthetic.get("runs", []):
                    seed = str(run.get("seed"))
                    removed[seed] = {}
                    for key in ("timeline", "stale_queue_events", "presentation_log"):
                        value = run.pop(key, [])
                        removed[seed][key] = len(value)
                synthetic["_ledger_compaction"] = {
                    "removed_generated_collections": removed,
                    "full_results_disposition": "stored_separately",
                    "release_bundle": RELEASE_BUNDLE,
                }
            else:
                synthetic = {
                    "ledger_synthesized": True, "reason": "original audit did not provide results.json",
                    "verdict": audit["verdict"], "commit": audit["commit"], "runtime": audit["runtime"],
                    "conclusion": audit["conclusion"], "original_report": str(src / "report.md"),
                }
            result_path = dst / "results.json"
            result_path.write_text(json.dumps(synthetic, sort_keys=True, separators=(",", ":")) + "\n")
            manifest["files"].append({
                "original_path": None,
                "archived_path": str(result_path.relative_to(LEDGER_ROOT.parent.parent)),
                "audit": audit["slug"], "disposition": "committed",
                "generated": ("compact projection with raw collections stored separately"
                              if audit["source"] == "codex2-phase35-natural-exposure-audit"
                              else "compact ledger summary because no original results.json existed"),
            })

    write_index()
    write_architecture_status()
    manifest_path = LEDGER_ROOT / "ARTIFACT_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    checksummed = []
    for path in sorted(LEDGER_ROOT.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            checksummed.append(f"{sha256(path)}  {path.relative_to(LEDGER_ROOT).as_posix()}")
    (LEDGER_ROOT / "SHA256SUMS").write_text("\n".join(checksummed) + "\n")


if __name__ == "__main__":
    main()
