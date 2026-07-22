# Hermes RPG: Engine-to-Backend Integration Manifest
## Project: Distributed C2 Gateway
## Version: 1.0.0 (Port 10005/9090)

This document maps Game Engine events to Backend API calls.

---

### 1. The Birth Sequence (Initialization)
**Goal**: Transform a player's choices into a game-world entity.

| Engine Event | API Endpoint | Method | Payload | Expected Response |
| :--- | :--- | :--- | :--- | :--- |
| **Char Creation Finalized** | `http://localhost:9090/finalize_character` | `POST` | `{"name": "...", "class": "...", "species": "...", "background": "..."}` | `{"entity_id": "ent_..."}` |
| **Enter Game World** | `http://localhost:10005/spawn` | `POST` | `{"entity_id": "ent_..."}` | `{"status": "spawned", "sector": "..."}` |
| **Initial World Load** | `http://localhost:10005/world/current_sector` | `GET` | `?user_id=ent_...` | Sector description and resident list |

---

### 2. The Gameplay Loop (Real-time)
**Goal**: Synchronize movement and state between the visual engine and the C2 backend.

| Engine Event | API Endpoint | Method | Payload | Expected Response |
| :--- | :--- | :--- | :--- | :--- |
| **Player Moves (Grid)** | `http://localhost:10005/move` | `POST` | `{"entity_id": "...", "dx": 1, "dy": 0}` | `{"status": "COMMAND_GENERATED", ...}` |
| **UI Update (Vitals/Stats)**| `http://localhost:10005/status/{id}` | `GET` | N/A | Full vitals, position, and conditions |
| **Entering New Sector** | `http://localhost:10005/world/current_sector` | `GET` | `?user_id=ent_...` | New sector metadata for environment rendering |

---

### 3. Progression & Inventory
**Goal**: Handle character growth and item management.

| Engine Event | API Endpoint | Method | Payload | Expected Response |
| :--- | :--- | :--- | :--- | :--- |
| **Item Picked Up** | `http://localhost:10005/inventory/add` | `POST` | `{"entity_id": "...", "item_name": "...", "weight": 1.0}` | Updated encumbrance status |
| **Character Level Up** | `http://localhost:10005/level_up` | `POST` | `{"entity_id": "..."}` | New HP/Level stats |

---

### 🛠 Integration Implementation Tips for Engine Dev:
1. **Polling vs. Events**: The backend is currently request-response. The engine should poll `/status` every ~1-2 seconds or immediately after a `POST` action to refresh the local state.
2. **Async Requests**: Always call these APIs asynchronously (e.g., `UnityWebRequest` or `async/await` in C#) to prevent the game frame rate from dropping while waiting for the server.
3. **Error Handling**: If a `404` is returned on `/status`, the engine should trigger a "Session Expired" or "Character Not Found" UI state.
4. **Coordinate Mapping**: The backend uses a simple `(x, y)` grid. Map these directly to your engine's tile coordinates or multiply by a constant (e.g., `x * 10`) for 3D world placement.
