---
name: rpg-identity-management
description: Guidelines for implementing and maintaining a distributed D&D 5e character system where an Identity Agent manages player state via a central Gateway.
---

# RPG Identity & Inventory Management

## 🎯 Core Architecture
- **The Identity Loop**: Observation (Read from DB) $\rightarrow$ Think (Process logic) $\rightarrow$ Request (Return commands to Gateway).
- **Statelessness**: The agent must never cache character state. Always retrieve the latest record from `common_db` at the start of every request.
- **Sovereign Authority**: The Identity Agent is the primary author of the `Player` schema. All writes must be returned as `commands` to the Gateway, not direct DB writes.

## 🛠️ Implementation Patterns

### 1. The Forge (Character Creation)
- **Flow**: Name First $\rightarrow$ Class $\rightarrow$ Species $\rightarrow$ Background $\rightarrow$ Equipment.
- **Flexible Input**: Implement selection logic that accepts both the index (number) and the name (case-insensitive) of the option.
- **Entity ID**: Generate IDs based on a sanitized version of the character name combined with a unique hash (e.g., `ent_name_hash`).

### 2. Dynamic State Management
- **Vitals**: Maintain strict invariant: `hp_max` must always be $\ge$ `hp_current`.
- **Healing**: Use `min(current + heal, max)` to prevent HP overflow.
- **Leveling**: Trigger attribute growth (e.g., HP increase based on CON) when XP thresholds are met.

### 3. Inventory System
- **Item Objects**: Move from string lists to objects containing `weight`, `damage`, and `type`.
- **Consumption**: Ensure items are removed from the `loot_bag` upon use.

## ⚠️ Pitfalls & Lessons
- **Frontend vs Backend Logic**: Avoid hardcoding "Forge" logic in the CLI. The CLI should be a thin wrapper; the API should hold the logic to prevent "Outdated CLI" errors.
- **Validation Order**: Ensure that "Creation" actions (which generate a new `entity_id`) are processed *before* mandatory `entity_id` validation checks. Placing validation first causes the agent to reject the very request that creates the ID.
- **Port Consistency**: Ensure the API port is synchronized across the backend service, the launch scripts, and the frontend CLI to avoid connection timeouts.
- **Race Condition (Disk I/O)**: When creating entities, the API may return success before the file system has fully flushed the JSON record to disk. The Frontend/CLI must implement a **Retry-and-Wait** loop (e.g., 5 attempts with 100ms delay) during the initial `load_character` call to prevent `NoneType` crashes.
- **Defensive Profile Access**: Always verify that the character profile is a non-null dictionary before calling `.get()` or accessing keys (e.g., `if profile and isinstance(profile, dict):`). This prevents `AttributeError` during rapid state transitions.
- **Persona Constraints**: Ensure tactical companions (e.g., Jarvis) avoid all gendered honorifics (no 'sir' or 'ma'am') to maintain user preference.

## 📝 Data Contract Reference
Refer to `DATA_CONTRACT.md` for mandatory schemas for `Player`, `Monster`, and `World Sector` records.
