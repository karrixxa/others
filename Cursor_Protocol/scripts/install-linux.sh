#!/usr/bin/env bash
# Install Triad protocol from this repo into ~/.cursor (Linux / macOS).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CURSOR_HOME="${HOME}/.cursor"

echo "Installing Triad protocol from:"
echo "  ${PROTO_ROOT}"
echo "To:"
echo "  ${CURSOR_HOME}"
echo ""

mkdir -p "${CURSOR_HOME}/skills" "${CURSOR_HOME}/rules" "${CURSOR_HOME}/scripts"

cp -f "${PROTO_ROOT}/triad-default.json" "${CURSOR_HOME}/triad-default.json"
cp -f "${PROTO_ROOT}/rules/triad-global-default.mdc" "${CURSOR_HOME}/rules/triad-global-default.mdc"

rm -rf "${CURSOR_HOME}/skills/research-code-validate-pipeline"
cp -r "${PROTO_ROOT}/skills/research-code-validate-pipeline" "${CURSOR_HOME}/skills/"

rm -rf "${CURSOR_HOME}/skills/triad-project-init"
cp -r "${PROTO_ROOT}/skills/triad-project-init" "${CURSOR_HOME}/skills/"

cp -f "${PROTO_ROOT}/scripts/apply-triad-user-rules.py" "${CURSOR_HOME}/scripts/" 2>/dev/null || true

echo "Installed:"
echo "  triad-default.json"
echo "  rules/triad-global-default.mdc"
echo "  skills/research-code-validate-pipeline/"
echo "  skills/triad-project-init/"
echo ""
echo "Reload Cursor (Developer: Reload Window), then optionally run project init:"
echo "  bash Cursor_Protocol/skills/triad-project-init/scripts/init-triad.sh"
