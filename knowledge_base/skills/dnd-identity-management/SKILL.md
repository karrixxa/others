---
name: dnd-identity-management
description: Guidelines for implementing a stateless, command-based Identity and Inventory Manager for a D&D 5e RPG using a C2 architecture.
---

# D&D 5e C2 Identity & Inventory Management

Guidelines for implementing a stateless, command-based Identity and Inventory Manager for a D&D 5e RPG using a C2 (Command-and-Control) architecture.

## 🎯 Core Objectives
- Manage player records (identity, stats, inventory, and state).
- Ensure strict adherence to D&D 5e rules (stat modifiers, HP calculations, level thresholds).
- Maintain statelessness by pulling latest state from `common_db` via a bridge before every action.
- Communicate via the Gateway using a `commands` list (Command Pattern) rather than direct DB writes.

## 🛠️ Implementation Standards

### 1. The "Identity Loop"
Every request must follow this sequence:
1. **Observation**: Pull the most recent entity JSON from the profiles directory.
2. **Think**: Process the request against 5e rules and the `DATA_CONTRACT.md`.
3. **Request**: Return a JSON response containing a `commands` list (Command Pattern) for the Gateway to execute.

#### Mandatory API Contract
To ensure compliance with the C2 ecosystem, the agent MUST implement:
- **GET /status**: Health check returning `{"status": "online", "version": "...", "agent_type": "CHARACTER"}`.
- **POST /action**: Accepts a JSON object `{"commands": [...]}` and returns `{"commands": [...]}`.
- **Statelessness**: The agent proposes mutations (e.g., `update_entity`) rather than writing directly to disk, maintaining the Gateway as the sole authority.

### 2. State Mutation Rules
- **HP Caps**: Always use `min(current_hp + heal_amount, hp_max)` to prevent overflow.
- **Targeted Actions**: Support actions targeting other entities (e.g., "heal player_02"). The agent must verify the target's existence in the DB before proposing a mutation for that specific `entity_id`.
- **Level Ups**: Triggered when `xp >= threshold`. Must increase `hp_max` and `hp_current` based on Constitution modifiers.
- **Resource Resets**: Implement "Rest Hooks" to flip booleans (e.g., `used_this_turn`) and restore spell slots.
- **Inventory**: Use Item Objects (weight, damage, type) instead of plain strings to allow for encumbrance and combat calculations.
- **User-Centric Forge**: When implementing character creation, prioritize a "Name-First" flow to derive the Entity ID from the character's name. Support flexible input (both numeric index and name string) for selection menus.

### 3. Grid Integration (20x20)
The agent must provide the following fields for the Game Engine:
- `threat_range`: Melee reach (typically 5ft/1sq) for opportunity attack triggers.
- `darkvision`: Vision range (e.g., 0ft for Halflings, 60ft for Elves) to determine tile visibility.
- `size`: (Small/Medium) to determine weapon disadvantage and movement.

### 4. Psychological Profiling (Jarvis)
To power a companion AI (Jarvis), include a `roleplay_profile` with:
- **Personality Traits**: (e.g., "Curious, Analytical") to drive archetype detection.
- **Fear/Bond/Flaw**: Specific strings that trigger priority shifts in tactical advice (e.g., a character fearing darkness becomes anxious in dim light).

## ⚠️ Pitfalls & Lessons
- **Direct DB Writes**: NEVER write directly to the profile JSONs from the agent; always return a command to the Gateway to avoid race conditions.
- **Stat Defaults**: Always implement a fallback (e.g., `.get('Constitution', 10)`) to prevent crashes on malformed profiles.
- **Sovereignty**: The Character Agent is the sole authority for the Player Record; other agents (Strategist/DM) must request changes through the Gateway.

## 📁 Support Files
- `references/data_contract.md`: The global schema for Players, Monsters, Combat, and Sectors.
