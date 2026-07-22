---
name: rpg-c2-bridge-management
description: Workflows for deploying, debugging, and verifying the Hermes RPG C2 Gateway Bridge and its connection to agent logic.
---

# RPG C2 Bridge Management

This skill governs the lifecycle of the API Bridge that connects AI agents (Builder/Jarvis) to the game engine.

## 🚀 Deployment Workflow
1. **Clean Environment**: Before launching, ensure no "ghost" processes are holding the port.
   `fuser -k 9090/tcp`
2. **Launch (Stable Method)**: Use the absolute path to the virtual environment binary to avoid `uv run` failures inside tmux sessions.
   `tmux new-session -d -s rpg_bridge '/home/cxiong/hermes_rpg/api/.venv/bin/python /home/cxiong/hermes_rpg/api/main.py'`
3. **Verification**: 
   - Browser: `http://localhost:9090/docs` (Swagger UI)
   - Terminal: `netstat -tulpn | grep 9090`

## 🏗 Architectural Patterns (Consultant Mode)
To ensure a "workable game" and prevent state desync in a distributed environment, the Bridge must operate as a **Consultant**, not a Referee.
- **Referee (Avoid)**: Directly calling `db.create_entity` or `db.update_entity` within the API endpoints.
- **Consultant (Preferred)**: Logic endpoints return a `COMMAND_GENERATED` response containing a `commands` array. The Gateway (Source of Truth) then executes these commands against the DB.
- **Data Contract**: All JSON keys must adhere strictly to `DATA_CONTRACT.md` (e.g., `vitals`, `position`, `gameplay_profile`).

## 🛠 Debugging Common Failures

### 1. "Address already in use" (Errno 98)
- **Cause**: A previous instance of the server is still running in the background.
### 🛠 Debugging Common Failures

### 1. "Address already in use" (Errno 98)
- **Cause**: A previous instance of the server is still running in the background, or another user on the shared cluster has claimed the port.
- **Fix**: Try `fuser -k 9090/tcp`. If the port remains occupied (as seen via `netstat -tunlp`), shift the bridge to an alternative port (e.g., 9091) in `main.py` to bypass the collision.

### 2. "500 Internal Server Error" (`stat_priority` or `stat_array`)
- **Cause**: The `character_options.json` file is missing required keys (like `stat_array` or `stat_priority` for a specific class), causing a `KeyError` in `builder.py`.
- **Fix**: Patch `builder.py` to include `.get()` fallbacks instead of direct key access.
- **Fallback Logic**: Use a standard array `[15, 14, 13, 12, 10, 8]` if `stat_array` is missing.

### 3. "Site can't be reached"
- **Cause**: Server is off OR SSH tunnel is missing.
- **Fix**: Ensure tunnel is active: `ssh -L 9090:localhost:9090 <user>@<ip>`.

### 4. "500 Internal Server Error" (`name 'infer_archetype' is not defined`)
- **Cause**: Missing helper functions and data constants (like `ARCHETYPES`, `FEAR_MODIFIERS`, `BOND_MODIFIERS`) in the `jarvis_agent.py` logic.
- **Fix**: Ensure `jarvis_agent.py` includes the synthesis helpers. If the bridge crashes on `/jarvis/ask`, verify that the `synthesize_psychological_brief` function has access to the necessary archetype mapping and modifier dictionaries.
- **Command**: `tmux new-session -d -s rpg_bridge '/home/cxiong/hermes_rpg/api/.venv/bin/python /home/cxiong/hermes_rpg/api/main.py'`

### 5. "Model does not exist" (HTTP 404)
- **Cause**: The model string passed to the Hermes agent (e.g., `gemma4:31b`) does not match the exact ID registered in the vLLM server (e.g., `/vllm_models/gemma-4-31B-it-FP8`).
- **Fix**: Query the vLLM model list via `curl http://<host>:<port>/v1/models` to find the precise `id` string and update the agent launch command.
- **Command**: `hermes -m <exact_model_id>`

## 🔗 C2 Integration Map
- **User/Agent $\rightarrow$ Bridge**: `http://localhost:9090` (REST API)
- **Bridge $\rightarrow$ Game Engine**: `ws://localhost:10001/ws` (WebSockets)

### 6. "Not Found" (HTTP 404) during testing
- **Cause**: The server may be booting slowly, or the request is hitting a dead process.
- **Fix**: Verify the process is actually running with `ps aux | grep uvicorn` and give the server 2-3 seconds to initialize before sending the first `curl` request.
## ⚠️ Critical Pitfalls & Constraints
- **Port Collisions**: On shared clusters, common ports like 9090 may be occupied by other users. Always verify port availability with `fuser -k <port>/tcp` and be prepared to migrate to alternative ports (e.g., 9095) if `Address already in use` occurs.
- **Data Integrity**: Do NOT perform recursive deletions of `__pycache__` or other system folders without explicit, line-by-line user approval, even if attempting to resolve module caching issues.
- **Network Interfaces**: Be aware that `hostname -I` may return link-local addresses (169.254.x.x). Always verify the global network IP (e.g., 10.x.x.x) using `ip addr show` for external integration.
- **DB Consistency**: All agent interactions MUST go through the `common_db.py` library to ensure synchronization across the distributed architecture. Do not use standalone JSON writes for core game state.
