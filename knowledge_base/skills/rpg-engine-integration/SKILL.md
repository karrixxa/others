---
name: rpg-engine-integration
description: Guidelines for integrating high-fidelity logic engines with stateless Gateway interfaces and persistent databases in RPG contexts.
---

# RPG Engine Integration & Data Synchronization

Guidelines for integrating high-fidelity logic engines (like Character Builders) with stateless Gateway interfaces and persistent databases.

## Core Architectural Principles
- **Statelessness**: The agent must never cache character or world state. Every turn must be driven by a fresh poll of the Gateway/DB.
- **Data Contract Alignment**: The engine (Backend) and Interface (Frontend) must share a strict JSON schema. Discrepancies lead to `KeyError` crashes.
- **Boundary Enforcement**: Physical world rules (e.g., 20x20 grids) must be enforced at the Gateway/Interface level to prevent "world-leakage."

## Workflow: Synchronizing Engine & Data
When implementing a high-fidelity feature (e.g., a Character Builder), follow this sequence:
1. **Audit the Engine**: Identify every key the logic requests from the JSON config (e.g., `stat_priority`, `weapon_options`, `speed`, `skills`).
2. **Saturate the JSON**: Ensure the `character_options.json` (or equivalent) contains every required key, even if values are defaults.
3. **Implement Validation**: Add boundary and collision checks *before* sending commands to the bridge.

## Common Pitfalls & Fixes
- **KeyError in Logic**: Occurs when the engine is more "advanced" than the data file. Fix by auditing the `build_character` or similar methods for all `.get()` or `[]` calls.
- **Lite vs. Full Sheets**: Interface tools often default to "Lite" views. Always implement a `render_character_sheet` that calculates derived stats (Modifiers, AC, Passives) on-the-fly from raw scores.
- **Grid Drift**: Relying on the LLM to track coordinates. Fix by implementing a "Clamp" or "Boundary Check" in the Gateway's `handle_move` logic.

## Verification Suite
Before declaring a feature "Engine-Ready," run these probes:
- **Boundary Test**: Attempt to move an entity to coordinates outside the defined grid.
- **Collision Test**: Attempt to move an entity into a space occupied by another.
- **Data Integrity Test**: Create a character through the interface and verify the resulting JSON in the DB contains all calculated fields.
