# Triad protocol manifest

All files tracked under `Cursor_Protocol/` for cross-machine Cursor setup.

## Global config

| File | Install target |
|------|----------------|
| `triad-default.json` | `~/.cursor/triad-default.json` |
| `rules/triad-global-default.mdc` | `~/.cursor/rules/triad-global-default.mdc` |

## Skill: research-code-validate-pipeline

| File | Install target |
|------|----------------|
| `skills/research-code-validate-pipeline/SKILL.md` | `~/.cursor/skills/research-code-validate-pipeline/SKILL.md` |
| `skills/research-code-validate-pipeline/doctrine.md` | `~/.cursor/skills/research-code-validate-pipeline/doctrine.md` |
| `skills/research-code-validate-pipeline/agents/orchestrator.md` | Thulle persona |
| `skills/research-code-validate-pipeline/agents/research.md` | Tech-Priest Dominus persona |
| `skills/research-code-validate-pipeline/agents/coder.md` | High Marshal Helbrecht persona |
| `skills/research-code-validate-pipeline/agents/security_validator.md` | Security Validator persona |
| `skills/research-code-validate-pipeline/agents/validator.md` | General Tyborc persona |

## Skill: triad-project-init

| File | Install target |
|------|----------------|
| `skills/triad-project-init/SKILL.md` | `~/.cursor/skills/triad-project-init/SKILL.md` |
| `skills/triad-project-init/templates/triad-persistent.mdc` | Copied to `.cursor/rules/` on project init |
| `skills/triad-project-init/templates/triad-global-default.mdc` | Reference copy (same as `rules/`) |
| `skills/triad-project-init/templates/user-rules-triad.txt` | Manual paste into Cursor User Rules |
| `skills/triad-project-init/scripts/init-triad.ps1` | Windows project init |
| `skills/triad-project-init/scripts/init-triad.sh` | Linux/macOS project init |

## Scripts

| File | Purpose |
|------|---------|
| `scripts/install-linux.sh` | Copy bundle to `~/.cursor/` on Linux/macOS |
| `scripts/install-windows.ps1` | Copy bundle to `%USERPROFILE%\.cursor\` on Windows |
| `scripts/apply-triad-user-rules.py` | Windows: append Triad text to Cursor User Rules DB |
