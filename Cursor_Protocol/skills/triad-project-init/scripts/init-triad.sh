#!/usr/bin/env bash
# Initialize persistent Triad workflow for the current project (Linux / macOS).
# Usage: bash Cursor_Protocol/skills/triad-project-init/scripts/init-triad.sh [--reset]

set -euo pipefail

RESET=false
if [[ "${1:-}" == "--reset" ]]; then
  RESET=true
fi

PROJECT_ROOT="$(pwd)"
CURSOR_DIR="${PROJECT_ROOT}/.cursor"
CONFIG_PATH="${CURSOR_DIR}/triad.json"
SCRIPTS_DIR="${CURSOR_DIR}/scripts"
RULES_DIR="${CURSOR_DIR}/rules"
TARGET_RULE="${RULES_DIR}/triad-persistent.mdc"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${CURSOR_DIR}" "${SCRIPTS_DIR}" "${RULES_DIR}"

if [[ ! -f "${TARGET_RULE}" ]]; then
  for template in \
    "${CURSOR_DIR}/templates/triad-persistent.mdc" \
    "${SCRIPT_DIR}/../templates/triad-persistent.mdc" \
    "${HOME}/.cursor/skills/triad-project-init/templates/triad-persistent.mdc"; do
    if [[ -f "${template}" ]]; then
      cp "${template}" "${TARGET_RULE}"
      echo "Created ${TARGET_RULE}"
      break
    fi
  done
fi

cp "${SCRIPT_DIR}/init-triad.sh" "${SCRIPTS_DIR}/init-triad.sh"
chmod +x "${SCRIPTS_DIR}/init-triad.sh"

if [[ -f "${CONFIG_PATH}" && "${RESET}" != "true" ]]; then
  echo "Triad config already exists at ${CONFIG_PATH}"
  echo "Use --reset to change workflow or agent."
  cat "${CONFIG_PATH}"
  exit 0
fi

echo ""
echo "=== Triad Project Init ==="
echo ""
echo "Select workflow for this project (locked until you re-run with --reset):"
echo "  1) Full Pipeline — Thulle orchestrates Research -> Code -> Validate"
echo "  2) Single Agent — work directly with one agent"
echo ""
read -r -p "Enter 1 or 2 [default: 1]: " workflow_choice
workflow_choice="${workflow_choice:-1}"

case "${workflow_choice}" in
  2) workflow="single-agent" ;;
  *) workflow="full-pipeline" ;;
esac

if [[ "${workflow}" == "full-pipeline" ]]; then
  active_agent="thulle"
  echo ""
  echo "Full Pipeline uses Thulle as the user-facing orchestrator."
else
  echo ""
  echo "Select agent for this project:"
  echo "  1) Thulle — Orchestrator"
  echo "  2) Tech-Priest Dominus — Research"
  echo "  3) High Marshal Helbrecht — Implementation"
  echo "  4) General Tyborc — Validation"
  echo ""
  read -r -p "Enter 1-4 [default: 3]: " agent_choice
  agent_choice="${agent_choice:-3}"
  case "${agent_choice}" in
    1) active_agent="thulle" ;;
    2) active_agent="dominus" ;;
    3) active_agent="helbrecht" ;;
    4) active_agent="tyborc" ;;
    *) echo "Invalid agent choice: ${agent_choice}" >&2; exit 1 ;;
  esac
fi

project_name="$(basename "${PROJECT_ROOT}")"
initialized_at="$(date +%Y-%m-%d)"

cat > "${CONFIG_PATH}" <<EOF
{
  "version": 1,
  "projectName": "${project_name}",
  "workflow": "${workflow}",
  "activeAgent": "${active_agent}",
  "locked": true,
  "initializedAt": "${initialized_at}",
  "pipelineVersion": 2
}
EOF

echo ""
echo "Triad config written to ${CONFIG_PATH}"
cat "${CONFIG_PATH}"
