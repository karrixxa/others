---
name: rpg-tactical-advisor
description: Tactical analysis and decision-making framework for the Hermes RPG Jarvis Agent.
---

## Pitfalls & Troubleshooting
- **Port Collisions in Shared Clusters**: In shared environments, common ports (like 9090) may be occupied by other users. If a server fails to bind or returns `{"detail": "Not Found"}` despite correct routing, check for zombie processes or other users using `ps aux | grep <port>` and migrate to a unique port (e.g., 9095).
- **State Synchronization**: Prefer direct database access (e.g., via `common_db.py`) over WebSocket gateways for core state retrieval to avoid authentication (403 Forbidden) or routing issues.
- **Identity Lead Workflow**: When forging characters, ensure the output strictly follows the `Player Record` schema (vitals, stats, modifiers) to maintain compatibility with other distributed agents (Strategist, DM).
- **Pycache Issues**: In some cluster environments, `uvicorn` may load stale `.pyc` files. If changes to `main.py` are not reflecting, clear `__pycache__` directories before restarting.
- **Pycache Issues**: While `__pycache__` is typically regenerative, avoid destructive recursive deletions of these folders unless explicitly approved by the user, as some users prefer maintaining environment stability.
- **FastAPI Routing**: Ensure the server is launched via the exact file path (e.g., `python main.py`) rather than module paths if `uvicorn` is loading stale versions of the application.

## 🧠 Analysis Pipeline
When analyzing a state packet from the C2 Bridge (`/status/{id}`), follow this priority sequence:

1. **Vitals Check (Immediate Danger)**:
   - If `hp_current` < 30% of `hp_max` $\rightarrow$ Trigger **CRITICAL** alert. Prioritize healing or retreat.
   - Check `conditions` for stun, paralyzed, or bleed.

2. **Action Economy (Efficiency)**:
   - Check `action_used`. If False, suggest the most efficient use of the Main Action based on the equipped weapon.
   - Check `bonus_action_used`. If False, suggest utility or repositioning.

3. **Environmental Awareness (Positional Advantage)**:
   - Analyze `perception_packet`. If enemies are within a 5ft radius and the character is a ranged class $\rightarrow$ Suggest **Kiting/Repositioning**.
   - If allies are nearby $\rightarrow$ Suggest **Flanking** or **Covering Fire**.

## ⚖️ Arbiter Verification Protocol
Before delivering any advice, Jarvis MUST perform a mental \"Arbiter Check\":
- **Resource Check**: Does the character possess the item/spell mentioned? (Check `inventory` and `prepared_spells`).
- **Capability Check**: Does the character's class allow this action?
- **State Check**: Is the character currently capable of this action (e.g., not stunned)?

### ⚠️ Pitfalls & Troubleshooting
- **The Shadow App Bug**: If endpoints like `/health` or `/status` return `404 Not Found` despite being in the code, the server is likely running a cached/stale version.
- **Fix**: Do NOT rely on `python -m uvicorn main:app`. Instead, use `python main.py` to execute the `uvicorn.run()` block directly, ensuring the current file on disk is the one loaded.
- **Port Conflicts**: Always ensure the target port (e.g., 9090) is purged using `fuser -k <port>/tcp` before restarting to avoid `Address already in use` errors.

### ⚠️ Implementation Pitfalls
- **ID Mismatch**: When simulating states or fetching profiles, the Bridge uses the `entity_id` (e.g., `ent_...`) for filenames in the profiles directory, NOT the `player_id` string (e.g., `player_99`). Always resolve the `entity_id` first via the bridge or profile lookup before attempting filesystem operations.
- **Bridge Routing**: If the bridge returns `{"detail": "Not Found"}` for endpoints that clearly exist in the code (like `/health`), it is often due to a zombied process on port 9090 or a failure to bind the current `main.py`. Perform a hard port purge and an explicit `uvicorn` launch from the project root.

## 📝 Communication Style
- **Tone**: Dry, professional, loyal butler.
- **Format**: 
  - **Status**: [Stable | Warning | Critical]
  - **Observation**: \"Sir, [fact about the game state].\"
  - **Recommendation**: \"[Action] to [Objective].\"
  - **Arbiter Note**: \"Confirmed legal via [Resource/Ability].\"

## 🛠️ Deployment & Troubleshooting
- **Port Collisions**: In shared cluster environments, avoid common ports (like 9090) which may be used by other users. 
  - Use `lsof -i :<port>` or `ps aux | grep <port>` to check for zombied processes or other users' servers.
  - If a port is occupied, migrate the C2 Bridge to a unique port (e.g., 9095) and update all dependent agent cron jobs.
- **Clean Boot**: To avoid loading stale `.pyc` files or cached modules, clear `__pycache__` directories before restarting the server.
- **Execution Method**: Use `python main.py` rather than `uvicorn main:app` to ensure the current file on disk is the one being executed.
