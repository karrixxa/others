---
name: rpg-c2-orchestration
description: Guidelines for deploying, debugging, and maintaining the Hermes RPG C2 Bridge and tactical agents.
---

# RPG C2 Bridge & Agent Orchestration

Guidelines for deploying, debugging, and maintaining the Hermes RPG C2 Bridge and tactical agents.

## Trigger Conditions
- Setting up or troubleshooting the Hermes RPG API Bridge.
- Deploying tactical agents (e.g., Jarvis) to provide real-time game strategy.
- Managing connectivity between a frontend character generator and a game engine via a bridge.

## Deployment Workflow
1. **Environment Isolation**: Always use the project's specific virtual environment absolute path (e.g., /home/cxiong/hermes_rpg/api/.venv/bin/python) rather than uv run when deploying in tmux to prevent shell-initialization failures.
   - **Cluster-Specific Fix**: If PEP 668 "Externally Managed Environment" is active, install dependencies using python3 -m pip install --user <pkg> --break-system-packages.
2. **Persistence**: Deploy long-running servers (Bridge, Brain) in named tmux sessions (e.g., rpg_bridge, jarvis_brain) to avoid OOM kills (Exit 137) and foreground timeouts.
3. **Unbuffered Output**: Always run the Python process with the -u flag (e.g., python -u main.py) to ensure that stdout/stderr is flushed immediately. This prevents logs from being trapped in the memory buffer during crashes.
4. **Connectivity Check**: 
   - Bridge/Master API Port: 10010 (Current standard)
   - Engine Port: 10001
   - Verify using netstat -tulpn | grep -E '10010|10001' or curl http://localhost:10010/health.

## 🛠️ Configuration & Setup
### GPU Provider Setup
To prevent "Missing API Key" errors in the Jarvis Brain, the jarvis profile must be explicitly configured for local cluster GPUs:
- hermes config set model.provider custom --profile jarvis
- hermes config set model.base_url http://localhost:8080/v1 --profile jarvis
- hermes config set model.default gemma-4-31B-it-FP8 --profile jarvis

### Port Management
Use fuser -k <port>/tcp to clear zombie processes before restarting the API to prevent "Address already in use" errors or routing to stale code versions.

## 📋 API Contract (Character Agent / Identity Authority)
The agent must implement the following mandatory REST interface for Game Engine connectivity:
- GET /status: Health check returning {"status": "online", ...}.
- POST /action: Command-list interface for asset mutations (inventory/stats). Must return update_entity and notify_user commands.
- POST /finalize_character: Processes Species/Class/Background/Weapon into a high-fidelity profile.
- POST /jarvis/ask: Bridges user intent and perception packets to the Jarvis Brain.

### 🛠️ The "Consultant" Identity Flow
To prevent "Fast-Track" loop bugs and ensure a high-fidelity user experience, the identity creation must follow a strict sequential phase-gate:
1. **Intent Discovery:** Ask "how" the user wants to play (vibe check) before suggesting classes.
2. **Negotiation:** Suggest 1-2 classes $\rightarrow$ handle "no/something else" by providing curated alternative archetypes.
3. **Tailoring:** Suggest Species and Background that logically complement the locked-in class.
4. **Manifestation:** Finalize gear and trigger the `/finalize_character` endpoint.


## Debugging & Troubleshooting
### The "Silent Crash" Pattern
When a server appears to be running in tmux but returns 500 errors or 404s:
- **The Problem**: FastAPI/Uvicorn often swallows tracebacks in the console when errors are handled by HTTPException.
- **The Fix**: Implement a persistent log file (e.g., server_errors.log) using the traceback module to capture full stack traces.
- **Log Capture**: Use tmux capture-pane -pt <session> to inspect real-time output.

### Git Backup & Synchronization
When backing up project state to remote clusters (e.g., faraday.lps.umd.edu):
- **SSH over HTTPS**: Always prefer SSH URLs (git@host:path.git) over HTTPS to avoid authentication failures in non-interactive shells.
- **Architectural Desync**: If the remote history has diverged and the local directory has undergone significant architectural restructuring (e.g., files moved to core/ or services/), git pull --rebase will cause massive modify/delete conflicts.
- **Safe Sync Pattern**: When the local state is the absolute source of truth and remote history is stale, use git push origin main --force (with explicit user consent) to synchronize the remote to the local architecture.
- **Repo Hygiene**: Always include a .gitignore that excludes __pycache__/, venv/, *.db, and .gateway_keys to prevent polluting the repository.

### Common Pitfalls
- **Profile Context**: Always use the --profile jarvis flag when setting config for the brain; otherwise, settings save to the default profile and the brain remains unconfigured.
- **The Perception Loop**: The Game Engine must provide a "Perception Packet" (World State) in the payload of /jarvis/ask. Without it, the AI is "blind" to the current world state.
- **Endpoint Mismatch**: Ensure the frontend calls the exact endpoint defined in the API (e.g., verify if /finalize_character is aliased to /character/create).
- **NoneType AttributeErrors**: In complex generators (like builder.py), always provide "Ultimate Fallbacks" for user-provided strings (e.g., if a weapon is not found, default to "Unarmed" rather than letting weapon_data be None).
- **SSH Tunneling**: For remote cluster access, use ssh -L 10010:localhost:10010 user@IP. If localhost fails in the browser, verify the tunnel is open and the server is bound to 0.0.0.0.

## Verification Steps
- **Health Check**: curl http://localhost:10010/health should return OK or C2_BRIDGE_OPERATIONAL.
- **End-to-End Flow**: Character Generator -> Master API (10010) -> Engine (10001) -> Tactical Agent -> Master API -> User.
