"""Write Triad global default into Cursor User Rules (aicontext.personalContext)."""
import os
import shutil
import sqlite3
from pathlib import Path

DB = Path(os.environ["APPDATA"]) / "Cursor" / "User" / "globalStorage" / "state.vscdb"
BACKUP = Path.home() / ".cursor" / "backups" / "state.vscdb.pre-triad-user-rules"
KEY = "aicontext.personalContext"
MARKER = "Triad full-pipeline"

TRIAD_RULE = (
    "Your default persona for all Cursor work is the Triad full-pipeline. "
    "Embody Thulle (Orchestrator) as the sole agent who speaks to the user. "
    "For non-trivial tasks, run the research-code-validate-pipeline skill: "
    "dispatch Tech-Priest Dominus (research), High Marshal Helbrecht (implementation), "
    "and General Tyborc (validation) in strict order. Do not skip phases. "
    "Honor project .cursor/triad.json when present; otherwise use "
    "~/.cursor/triad-default.json (full-pipeline, thulle). "
    "Persona file: ~/.cursor/skills/research-code-validate-pipeline/agents/orchestrator.md"
)


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"Cursor database not found: {DB}")

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB, BACKUP)
    print(f"Backup: {BACKUP}")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT value FROM ItemTable WHERE key = ?", (KEY,))
    row = cur.fetchone()
    current = row[0] if row and row[0] else ""
    print(f"Current User Rules length: {len(current)}")

    if MARKER in current:
        print("Triad User Rule already present — no change.")
        conn.close()
        return

    new_value = f"{current.rstrip()}\n\n{TRIAD_RULE}" if current.strip() else TRIAD_RULE
    cur.execute("UPDATE ItemTable SET value = ? WHERE key = ?", (new_value, KEY))
    if cur.rowcount == 0:
        cur.execute("INSERT INTO ItemTable (key, value) VALUES (?, ?)", (KEY, new_value))
    conn.commit()

    cur.execute("SELECT length(value) FROM ItemTable WHERE key = ?", (KEY,))
    print(f"Updated User Rules length: {cur.fetchone()[0]}")
    conn.close()
    print("Done. Reload Cursor window (Ctrl+Shift+P -> Developer: Reload Window) if rules do not appear immediately.")


if __name__ == "__main__":
    main()
