---
name: rpg-distributed-backend
description: Guidelines for implementing and maintaining a distributed Command-and-Control (C2) architecture for RPG systems to support multiplayer synchronization.
---

# RPG Backend Architecture (Distributed C2)

Guidelines for implementing and maintaining a distributed Command-and-Control (C2) architecture for RPG systems. This pattern separates identity management, world state, and gateway routing to support multiplayer synchronization.

## Core Architecture
The system operates as a hub-and-spoke model to prevent desync and state corruption:
1. **The Gateway (Router):** The sole entry point for the Game Engine. It translates client requests into backend actions.
2. **Identity Manager (Forge):** Handles character creation, stat generation, and entity-specific logic (e.g., targeted heals).
3. **Shared State (DB):** A centralized data layer (e.g., JSON profiles) ensuring all agents and players see a consistent world.

## Implementation Workflows

### 1. Character Lifecycle
- **Forge $\rightarrow$ Spawn $\rightarrow$ World:** Characters must be formally 'spawned' into a sector after creation.
- **Entity-Based Identity:** Use unique `entity_id`s for all players and NPCs to avoid naming collisions and allow parallel state tracking.

### 2. Multiplayer Synchronization
- **Sector System:** Divide the world into sectors. Track residents in each sector to enable multiplayer proximity and visibility.
- **Turn Orchestration:** Use a sequential queue (`turn_queue`) to manage action order. The Gateway should provide a `/turn/status` endpoint so the Engine can lock/unlock UI based on the active actor.
- **Targeted Actions:** Implement actions as `(Actor, Target, Action)` tuples rather than self-only effects to enable support roles (Healers/Buffers).

### 3. Logic & Math (5e Standard)
- **Modifiers:** Use the formula `(Score - 10) // 2`.
- **Encumbrance:** Calculate based on Strength (e.g., `Str * 15`). Check this before allowing inventory additions.
- **Vitals:** Link Max HP to Constitution modifiers at creation.

## Pitfalls & Lessons Learned
- **Logic Gutting:** Avoid stripping core logic classes (e.g., `CharacterBuilder`) down to just "briefing" or "view" functions. Ensure generation logic and validation logic stay bundled with the class.
- **Statelessness:** The Game Engine should be treated as a "dumb shell." Never calculate stats or turn order in the Engine; always fetch the absolute truth from the Gateway.
- **Desync Prevention:** For multiplayer, use a single source of truth for the turn pointer and entity positions to prevent "ghosting" or turn-skipping.

## Integration Blueprint
When handing off to a frontend/engine team, provide:
- Exact Gateway endpoints (URLs).
- JSON payload examples for requests and responses.
- The state-sync loop (Poll Sector $\rightarrow$ Render $\rightarrow$ Move/Act $\rightarrow$ Sync).
