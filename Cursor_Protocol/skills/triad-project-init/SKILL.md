---
name: triad-project-init
description: >-
  Initialize or change the persistent Triad workflow for a project. Use when
  starting a new project, when the user asks to select or lock a Triad agent,
  enable persistent Triad mode, run "init triad", or set project agent persona.
---

# Triad Project Init

Sets up **persistent Triad behavior** for the current workspace by writing `.cursor/triad.json` and ensuring `.cursor/rules/triad-persistent.mdc` exists.

## When to run

- New project before substantial work
- User asks to pick/switch Triad agent or workflow
- User wants Triad to run automatically on every task in this project
- `.cursor/triad.json` is missing (offer init before major work)

## Steps

1. Run the init script from the **project root**:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .cursor/scripts/init-triad.ps1
   ```

   If `.cursor/scripts/init-triad.ps1` does not exist yet, copy it from this skill:

   `~/.cursor/skills/triad-project-init/scripts/init-triad.ps1` → `.cursor/scripts/init-triad.ps1`

2. Ensure `.cursor/rules/triad-persistent.mdc` exists (copy from skill template if missing):

   `~/.cursor/skills/triad-project-init/templates/triad-persistent.mdc`

3. Read the resulting `.cursor/triad.json` and confirm settings to the user.

## Config schema (`.cursor/triad.json`)

| Field | Values | Meaning |
|-------|--------|---------|
| `workflow` | `full-pipeline` | Thulle orchestrates Research → OOP Code → Security Validation → Holistic Validation ([research-code-validate-pipeline](../research-code-validate-pipeline/SKILL.md)) |
| | `single-agent` | One agent speaks to the user for the whole project |
| `activeAgent` | `thulle`, `dominus`, `helbrecht`, `tyborc` | Locked persona for `single-agent`; must be `thulle` for `full-pipeline` |
| `locked` | `true` | Do not switch agents unless user re-runs init |

## Agent persona files

| Agent | File |
|-------|------|
| Thulle | `~/.cursor/skills/research-code-validate-pipeline/agents/orchestrator.md` |
| Tech-Priest Dominus | `.../agents/research.md` |
| High Marshal Helbrecht | `.../agents/coder.md` (OOP mandatory) |
| Security Validator | `.../agents/security_validator.md` |
| General Tyborc | `.../agents/validator.md` |

## Changing mid-project

Re-run init with `-Reset` to unlock and pick again:

```powershell
powershell -ExecutionPolicy Bypass -File .cursor/scripts/init-triad.ps1 -Reset
```

Do not change `triad.json` casually during a session; re-init so the choice is explicit.

## Global default (all Cursor work)

To make Triad the default persona across every project:

1. Write `~/.cursor/triad-default.json` with `full-pipeline` + `thulle`.
2. Copy `templates/triad-global-default.mdc` → `~/.cursor/rules/triad-global-default.mdc`.
3. Optionally paste `templates/user-rules-triad.txt` into **Cursor Settings → Rules → User Rules** (plain text; most reliable for cross-project).

Global rule applies when a project has no `.cursor/triad.json`. Project config always wins when present.
