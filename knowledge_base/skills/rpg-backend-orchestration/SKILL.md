---
name: rpg-backend-orchestration
description: Guidelines for implementing and verifying distributed C2 architectures for RPGs, focusing on state synchronization, multiplayer entity management, and turn orchestration.
---

# RPG Backend Orchestration

This skill governs the design, implementation, and verification of distributed game backends where a Gateway routes requests between an Identity Manager (Forge), a State Layer (DB), and a Game Engine (Client).

## Core Architectural Patterns

### 1. Distributed Identity & State
- **Entity-Based Storage:** Store players and NPCs as unique `entity_id`s in separate JSON profiles (e.g., `profile_{id}.json`).
- **Sector-Based Presence:** Use a "Sector" system to track which entities coexist in a spatial area. A sector file should contain a list of `residents` (entity IDs).
- **Single Source of Truth:** The Game Engine must be stateless. All vital stats (HP, AC) and positions must be polled from the backend to prevent desync.

### 2. Multiplayer Interaction Loops
- **Targeted Actions:** Implement actions as `Actor -> Target` relationships (e.g., `POST /action/targeted {actor_id, target_id, action}`).
- **Turn Orchestration:** Use a sequential queue (Turn Queue) to manage action order. The backend should expose the `current_actor` to the engine to lock/unlock UI inputs.

## Verification & Stability Workflow

### 1. The "Chaos" Audit
When verifying multiplayer stability, perform the following tests:
1. **Rapid-Fire Stress:** Execute 50+ sequential DB writes to ensure no corruption or race conditions occur during high-volume updates.
2. **Corruption Recovery:** Intentionally write malformed JSON to a profile and verify the system returns `None` gracefully instead of crashing.
3. **Concurrency Simulation:** Use thread pools to simulate simultaneous joins/leaves in a single sector to ensure file-locking doesn't freeze the server.
4. **Null-Input Handling:** Verify that requests for non-existent entity IDs are handled as 404s/None rather than triggering recursive error loops.

### 2. Common Pitfalls & Fixes
- **DB Argument Mismatch:** Ensure `update_entity` calls always provide the full triplet: `(entity_type, entity_id, update_data)`. Missing the `entity_type` is a common cause of crashes in distributed RPG setups.
- **Zombie Processes:** When restarting servers, use `fuser -k <port>/tcp` or `pkill` to ensure old processes aren't blocking ports.
- **Sector Voids:** Always ensure a "Starting Sector" (e.g., `sector_start_01.json`) exists before spawning players to avoid "void" crashes.

## Integration Guidelines for Game Engines
Provide the engine team with a "Contract" including:
- **Primary Endpoint:** The Gateway URL.
- **The Loops:** Explicit flows for Birth (Creation $\rightarrow$ Spawn), World (Poll $\rightarrow$ Move), and Interaction (Target $\rightarrow$ Turn).
- **Data Contract:** Exact JSON shapes for Entity and Sector records.
