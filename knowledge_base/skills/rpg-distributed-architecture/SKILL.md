---
name: rpg-distributed-architecture
description: Framework for implementing and maintaining a decoupled, distributed RPG backend using a C2 (Command and Control) pattern.
---

# RPG Distributed Architecture

This skill governs the design and maintenance of a decoupled RPG backend where the Game Engine (Client) interacts with a Gateway, which routes requests to specialized services (Identity, World, Combat) and a shared state layer.

## Core Architectural Components

1. **The Gateway (Port 10001):** The sole entry point for the Client. Handles routing, auth, and state synchronization.
2. **Identity Manager/Forge (Port 9090):** Handles character creation, stat generation, and inventory management.
3. **Shared State Layer (common_db.py):** A JSON-based persistence layer. All services read/write to this to ensure a single source of truth.
4. **Turn Orchestrator:** A sequential queue system that prevents action collisions in multiplayer combat.

## Implementation Workflow

### 1. Character Lifecycle
- **Forge $\rightarrow$ Spawn $\rightarrow$ World**: Characters must be created via the Identity Manager, then explicitly "spawned" into a sector to become visible to other players.
- **Entity IDs**: Use unique IDs (e.g., `ent_name_random`) as the primary key across all JSON profiles and sector lists.

### 2. Multiplayer Synchronization
- **Sector System**: Track players in `sector_{id}.json` files.
- **Polling**: The Client should poll `/world/current_sector` to update the local representation of other players.
- **Targeted Actions**: Implement actions as `Actor $\rightarrow$ Target` (e.g., `/action/targeted`) to allow support roles (Healers) to modify other entities' states.

### 3. Game Logic & Math (5e Standard)
- **Modifiers**: Calculate as `(score - 10) // 2`.
- **Vitals**: HP Max should be derived from Constitution.
- **Encumbrance**: Calculate as `current_weight > (Strength * 15)`.

## Pitfalls & Debugging

- **Zombie Processes**: In Linux environments, FastAPI/Uvicorn processes can hang on ports. Use `fuser -k <port>/tcp` to clear ports before restarting services.
- **Stat Desync**: Never cache stats in the Game Engine. Always treat the Gateway/DB as the absolute truth.
- **Void Spawning**: Always ensure a default starting sector (e.g., `sector_start_01.json`) exists before allowing the first spawn to prevent 404s.

## Verification Script
Run a smoke test that:
1. Creates a character.
2. Spawns them into a sector.
3. Performs a targeted action (e.g., heal).
4. Verifies the state change in the JSON profile.
