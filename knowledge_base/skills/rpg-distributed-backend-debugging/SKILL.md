---
name: rpg-distributed-backend-debugging
description: Workflows for debugging and stabilizing decoupled RPG backends, specifically managing the Identity Manager and Gateway bridge.
---

# RPG Distributed Backend Debugging

This skill governs the stabilization and verification of the Hermes RPG Distributed C2 architecture, focusing on the interaction between the Identity Manager (Port 9090) and the Gateway (Port 10001).

## Trigger Conditions
- Deploying or troubleshooting the distributed C2 backend.
- Encountering 404 errors on endpoints that exist in code.
- Port bind errors (Errno 98) during service startup.
- Character "Birth Loop" failures where characters are created but not "visible" to the world.

## Operational Workflow

### 1. The "Nuclear Reset" (Ghost Process Clearing)
When experiencing erratic 404s or "Address already in use" errors, do not rely on standard restarts.
1. Kill all Python processes associated with the backend: `pkill -9 python3` (or target specific files like `pkill -9 -f "c2_builder_api.py"`).
2. Use `fuser -k <port>/tcp` to force-clear specific port bindings.
3. Verify ports are clear: `ss -tlnp | grep -E '9090|10001|10005'`.
4. Start services in order: Gateway first, then Identity Manager.

### 2. Port Alignment Verification
Ensure the `SERVICE_PORT` in the code matches the manual and the CLI configuration.
- **Identity Manager**: Must be `9090`.
- **Gateway**: Must be `10001`.
- Check `uvicorn.run` calls at the bottom of the files.

### 3. The "Birth Loop" Integration Bridge
A common failure occurs when the Identity Manager creates a character but doesn't commit it to the shared database used by the Gateway.
- **Verification**: If `/finalize_character` returns 200 but `/spawn` or `/world/current_sector` returns 404, the bridge is broken.
- **Fix**: Ensure the Identity Manager calls `db.update_entity("player", entity_id, profile)` immediately after generating the profile.

### 4. End-to-End (E2E) Verification Suite
Always verify using a scripted probe rather than manual CLI testing to isolate backend logic from CLI UI issues.
- **Test Sequence**:
    1. `POST /finalize_character` $\rightarrow$ Capture `entity_id`.
    2. `POST /spawn` $\rightarrow$ Verify `status: spawned`.
    3. `GET /world/current_sector` $\rightarrow$ Verify sector description is returned.
    4. `POST /move` $\rightarrow$ Verify position update.
    5. `GET /turn/status` $\rightarrow$ Verify turn queue is accessible.

## Pitfalls & Lessons
- **Ghost Interceptors**: In some cluster environments, a port (e.g., 10001) may be intercepted by a system-level process or proxy that persists despite `pkill` or `fuser`. This results in a \"custom\" 404 error (e.g., \"Agent path not found\") that does not exist in the source code. 
- **The Port-Shift Fix**: If a specific port consistently returns a 404 that isn't in the code, shift the service to a new port (e.g., 10001 $\rightarrow$ 10005) to bypass the interceptor.
- **Ghost Processes**: Python/Uvicorn processes can sometimes hang in a way that they hold a port but don't respond to requests, leading to deceptive 404s. Use `pkill -9`.
- **Isolated DBs**: Ensure both services import the same `CommonDB` instance/library; otherwise, characters created in one service are invisible to the other. **CRITICAL**: If the services are run as standalone scripts from different working directories, `import common_db` may fail. Use `sys.path.append('/home/cxiong/hermes_rpg')` before importing the DB to ensure a single shared source of truth.
- **C2 Bridge Delegation**: If a route exists in FastAPI but returns "Agent path not found," the issue is likely in the delegation logic (C2 Bridge) rather than the FastAPI router. Simplify the route to a direct DB action to bypass this if delegation is not strictly required.
