# Cursor Triad Protocol

Portable copy of the **Triad full-pipeline (v2)** Cursor configuration used on this project.

On the primary Windows machine these files normally live under `~/.cursor/` (global Cursor config). They are **not** part of the application repo by default, so a fresh Linux (or other) install will report missing persona files, skills, and rules until you install them.

## What was missing on a new machine

| Path (after install) | Purpose |
|----------------------|---------|
| `~/.cursor/triad-default.json` | Global workflow default (`full-pipeline`, `thulle`) |
| `~/.cursor/rules/triad-global-default.mdc` | Always-on rule: use Triad pipeline |
| `~/.cursor/skills/research-code-validate-pipeline/` | Main pipeline skill + doctrine + 5 agent personas |
| `~/.cursor/skills/triad-project-init/` | Project init skill, templates, scripts |
| `~/.cursor/scripts/apply-triad-user-rules.py` | Optional: inject User Rules on Windows |

Project-level files (created by init, not in this bundle):

| Path | Purpose |
|------|---------|
| `.cursor/triad.json` | Locked workflow for this repo |
| `.cursor/rules/triad-persistent.mdc` | Project Triad rule |
| `.cursor/scripts/init-triad.sh` or `init-triad.ps1` | Re-run to change workflow |

## Linux install (global)

From the repository root:

```bash
chmod +x Cursor_Protocol/scripts/install-linux.sh
./Cursor_Protocol/scripts/install-linux.sh
```

Then **reload Cursor** (Command Palette → *Developer: Reload Window*).

Optional — paste into **Cursor Settings → Rules → User Rules**:

`Cursor_Protocol/skills/triad-project-init/templates/user-rules-triad.txt`

## Windows install (global)

```powershell
powershell -ExecutionPolicy Bypass -File Cursor_Protocol/scripts/install-windows.ps1
```

## Initialize Triad for this project

**Linux / macOS:**

```bash
bash Cursor_Protocol/skills/triad-project-init/scripts/init-triad.sh
```

**Windows:**

```powershell
powershell -ExecutionPolicy Bypass -File Cursor_Protocol/skills/triad-project-init/scripts/init-triad.ps1
```

This writes `.cursor/triad.json` and `.cursor/rules/triad-persistent.mdc` in the project root.

## Pipeline chain of command

```
User → Thulle
  → Tech-Priest Dominus (research)
  → High Marshal Helbrecht (OOP code)
  → Security Validator
  → General Tyborc (holistic validation)
  → User
```

Security Validator **always** runs before Tyborc.

## File layout in this folder

```
Cursor_Protocol/
  triad-default.json
  rules/triad-global-default.mdc
  skills/research-code-validate-pipeline/   # SKILL.md, doctrine.md, agents/*
  skills/triad-project-init/                # SKILL.md, templates/, scripts/
  scripts/install-linux.sh
  scripts/install-windows.ps1
  scripts/apply-triad-user-rules.py         # Windows only (Cursor SQLite DB)
```

See [MANIFEST.md](MANIFEST.md) for the full file list.
