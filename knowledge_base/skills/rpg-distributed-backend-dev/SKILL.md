---
name: rpg-distributed-backend-dev
description: Workflows for implementing and debugging the Hermes RPG Distributed C2 architecture (Gateway and Identity Manager).
---

# RPG Distributed Backend Development

This skill governs the implementation of the decoupled architecture where character identity and world state are handled by separate microservices.

## Architecture Overview
- **Identity Manager (Port 9090):** Authority for character creation, identity verification, and profile persistence.
- **Gateway (Port 10005):** Authority for world state, sector management, movement, and interaction routing. (Note: Port shifted from 10001 to 10005 to avoid system-level interceptors in some cluster environments).
- **Persistence:** SQLite database (`game_data.db`) using a Unified Entity system (entity_type, entity_id, data_json) for high-concurrency support.

## Core Logic Loops

### 1. The Birth Loop (Creation)
The sequence must be strictly followed to ensure an entity is registered before they enter the world:
1. **Recommend:** AI suggests Class -> Species -> Background based on synergy.
2. **Finalize:** Call `POST /finalize_character` on the Identity Manager (:9090).
3. **Spawn:** Call `POST /spawn` on the Gateway (:10005).
4. **Poll:** Call `GET /world/current_sector` on the Gateway (:10005) to confirm spawn.

### 2. The World Loop (Exploration)
- **Sector State:** Use `GET /world/current_sector?user_id={id}` to fetch the absolute truth of the current room and residents.
- **Movement:** Use `POST /move` with `dx` and `dy` coordinates.
- **State Sync:** Use `GET /status/{entity_id}` for a full dump of vitals, position, and current conditions.

### 3. The Interaction Loop (Combat/Social)
- **Turn Sync:** Use `GET /turn/status` to determine if the entity can act.
- **Targeted Actions:** Use `POST /action/targeted` with `actor_id`, `target_id`, and `action`.
- **Jarvis Intelligence:** Use `POST /jarvis/ask` to retrieve a state-aware context window for LLM processing.

## Common Pitfalls & Debugging
- **Port Mismatches:** Ensure `SERVICE_PORT` in `c2_builder_api.py` is explicitly set to `9090`.
- **Zombie Processes:** When updating backend code, use `fuser -k <port>/tcp` to clear bound ports and avoid "Address already in use" errors or ghost 404s.
- **Data Integrity:** When moving from JSON to SQLite, ensure a migration script is run to preserve entity IDs.
- **Statelessness:** The CLI/Engine must never cache character stats; it should always poll the backend for the current state.
- **Hybrid Storage Desync:** If using both SQLite for entities and JSON for sectors, a desync can occur where the entity is in a sector in the DB but not in the JSON file. Periodically synchronize residents or move sector data to SQLite.
- **Import Pathing:** In distributed structures (e.g., `api/`, `services/`, `core/`), always ensure `sys.path.append` is used or absolute imports are configured to avoid `ModuleNotFoundError` when launching scripts from different subdirectories.

## Verification Workflow
1. **Port Check:** Run `ss -tlnp | grep -E '9090|10005'` to verify both services are listening.
2. **Health Check:** `curl http://localhost:9090/status` and `curl http://localhost:10005/health`.
3. **End-to-End Probe:** Create test character -> Spawn -> Poll Sector -> Move -> Check Status -> Jarvis Ask.
