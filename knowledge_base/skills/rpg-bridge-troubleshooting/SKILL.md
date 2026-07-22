---
name: rpg-bridge-troubleshooting
description: Debugging and stabilizing the Hermes RPG C2 Bridge and Game Engine connectivity.
---

# RPG Bridge Troubleshooting

This skill governs the maintenance and debugging of the C2 Bridge connecting the Hermes Agent to the Game Engine.

## Core Architecture
- **Bridge/Identity Port**: 9090 (REST API - handles Identity/Character Builder)
- **Engine Port**: 10001 (WebSocket)
- **Flow**: Website $\rightarrow$ Bridge (9090) $\rightarrow$ Engine (10001) $\rightarrow$ Jarvis Brain $\rightarrow$ Bridge $\rightarrow$ Website.

## Common Failure Patterns & Fixes

### 1. The "Silent Crash" (tmux/uv)
- **Symptom**: `tmux ls` shows the session, but `curl localhost:9090/health` fails.
- **Root Cause**: `uv run` can fail to resolve the environment inside a non-interactive tmux shell.
- **Fix**: Use the absolute path to the venv python binary.
- **Command**: `tmux new-session -d -s rpg_bridge '/home/cxiong/hermes_rpg/api/.venv/bin/python /home/cxiong/hermes_rpg/api/main.py'`

### 2. The "Jarvis Brain Not Starting" (Gateway Profile)
- **Symptom**: Attempting to run Jarvis via `hermes gateway run --profile jarvis -m <model> --provider <gpu>` fails with `unrecognized arguments`.
- **Root Cause**: The `hermes gateway run` command does not accept model/provider flags directly; these are handled by the profile configuration in `config.yaml`.
- **Fix**: Launch using only the profile flag: `/home/cxiong/.hermes/hermes-agent/venv/bin/hermes gateway run --profile jarvis`.

### 3. The "NoneType" 500 Error (Character Builder)
- **Symptom**: `/finalize_character` returns 500 Internal Server Error.
- **Root Cause**: Missing or mismatched input for `weapon_name` or `stat_array` causing `None.get()` calls in `builder.py`.
- **Fix**: Implement defensive defaults in `builder.py`. Ensure `weapon_data` falls back to "Unarmed" and `stat_array` falls back to the Standard Array `[15, 14, 13, 12, 10, 8]`.

### 3. The "Ghost Function" (Jarvis Agent)
- **Symptom**: `/jarvis/ask` returns 500 with `name 'infer_archetype' is not defined`.
- **Root Cause**: Missing helper functions and data dictionaries (`ARCHETYPES`, `FEAR_MODIFIERS`) in `jarvis_agent.py`.
- **Fix**: Ensure the synthesis engine includes the archetype inference logic and the associated modifier tables.

### 4. Connection/Tunnel Issues
- **Symptom**: Browser cannot reach `http://localhost:9090/docs`.
- **Fix**: Establish an SSH tunnel from the local machine to the cluster.
- **Command**: `ssh -L 9090:localhost:9090 cxiong@<SERVER_IP>`

## Verification Workflow
1. **Check Bridge**: `curl http://localhost:9090/health`
2. **Check Engine**: `netstat -tulpn | grep 10001`
3. **Check Logs**: `tmux capture-pane -t rpg_bridge` (Use this immediately after a crash to capture the traceback).
