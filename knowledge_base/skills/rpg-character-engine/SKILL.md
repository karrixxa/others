---
name: rpg-character-engine
description: Guidelines for implementing high-depth, deterministic RPG character creation and AI-driven tactical companion (Jarvis) systems.
---

# RPG Character Engine & Agent Orchestration

Guidelines for implementing high-depth, deterministic RPG character creation and AI-driven tactical companion (Jarvis) systems.

## Core Architecture
The system must strictly decouple static identity from volatile game state to ensure performance and data integrity.

### 1. Data Separation
- **Character Profile (`characters/{id}.json`)**: Read-only during gameplay. Stores base ability scores, identity, roleplay profile, and fixed proficiencies.
- **Game State (`states/{id}_state.json`)**: Volatile. Stores current HP, position, action economy, and temporary conditions.
- **Rules Registry (`character_options.json`)**: The authoritative source for class/species/background options. Read-only at runtime.

### 2. Deterministic Stat Generation
Avoid random rolls unless explicitly requested. Use the **Standard Array [15, 14, 13, 12, 10, 8]** mapped to class priority:
- **Fighter**: Str > Con > Dex > Wis > Cha > Int
- **Rogue**: Dex > Con > Cha > Wis > Int > Str
- **Wizard**: Int > Wis > Dex > Con > Cha > Str
- **Cleric**: Wis > Con > Str > Cha > Dex > Int
- **Ranger**: Dex > Wis > Con > Str > Int > Cha
- **Bard**: Cha > Dex > Con > Wis > Int > Str

### 3. Character Creation Workflow (The Consultative Interview)
Move from linear forms to a "Co-creation" flow:
1. **Recommendation Loop**: Instead of lists, pitch a "Golden Path" (e.g., Bard -> Tiefling -> Noble). 
   - If User says "Yes" -> Lock in.
   - If User says "No/Other" -> Reveal full options menu.
2. **Intelligent Auto-fill**: For roleplay details (Secrets, Bonds, Deities), allow the user to press Enter or say "you decide". Generate a flavor-text response based on the chosen Background.
3. **Finalization**: Generate the Unified Entity Package (ent_id, char_id, agent_id) and pre-calculate Gateway payloads (`/spawn`, `/stat`).

## 🛠️ Distributed Agent Architecture (User 4 Role)
When implementing this engine as a distributed agent:
- **Agent Server**: Wrap the builder and session logic in a FastAPI server (e.g., `char_agent.py`).
- **Endpoint Strategy**:
    - `/forge/process`: Handle the consultative interview via session-based POST requests.
    - `/character/{id}` and `/state/{id}`: Provide read-only access to profiles and states for other agents (DM, Strategist).
    - `/loot/add`: Handle item additions and return encumbrance status.
    - `/progression/add_xp`: Handle XP gains and trigger level-up logic.
    - `/jarvis/briefing`: A dedicated intelligence endpoint that returns a tactical analysis based on the current state.
- **Network Security**: Use an `X-API-KEY` header for all requests, validated against a secure key store (e.g., `.gateway_keys`).
- **Port Allocation**: Ensure the Character Agent runs on its designated port (e.g., 8004) to avoid collisions. If using 9090, ensure any existing Gateway/Engine process is killed first.

## ⚖️ Loot & Progression Systems
### Loot & Encumbrance
- **Capacity**: `Strength Score * 15 lbs`.
- **Status**: 
  - `CLEAR`: < 50% capacity.
  - `ENCUMBERED`: 50% - 100% capacity.
  - `OVERLOADED`: > 100% capacity.

### Leveling
- Use an XP threshold table (e.g., Lvl 2: 300, Lvl 3: 900).
- Implement a check upon adding XP to trigger `leveled_up: true` and allow stat increases.

The AI companion should operate as a "Cognitive Layer" over the game state.

### 1. The Tools Bridge
The agent must have a toolset to:
- `get_live_state()`: Poll volatile state for immediate tactical awareness.
- `get_character_profile()`: Access narrative anchors (secrets, goals).
- `query_rules()`: Cross-reference the rules registry.
- `push_action()`: Send commands to the game engine.

### 2. Cognitive Snapshotting
Before responding, the agent should generate a **Tactical Summary**:
- **Physical Status**: HP % and condition alerts (e.g., "Critical Health").
- **Environmental Context**: Current location and active gear.
- **Narrative Context**: Current short-term goal and relevant secrets.

## Pitfalls & Lessons
- **Data Contract Mismatch**: High-fidelity builders often require specific keys (e.g., `stat_priority`, `weapon_options`, `speed`, `skills` mapping) in the rules registry. Always verify the JSON structure against the engine's `build_character` method to avoid `KeyError` during the Armament or Stat phases.
- **Grid-Based Movement**: When implementing movement on a coordinate grid (e.g., 20x20), the Gateway MUST implement boundary validation (0-19) and occupancy checks (Collision Detection) before committing the move to the DB.
- **Formatting Errors**: When printing ASCII tables in Python, separate sign formatting (e.g., `+d`) from width alignment (e.g., `<10`) into two steps to avoid `ValueError`.
- **Data Safety**: When rendering character sheets or briefings, always use `.get()` for optional fields (Secrets, Bonds, etc.) to avoid `KeyError` if the user skipped these during creation.
- **UI Persistence**: Avoid excessive `clear_screen()` calls in CLI loops to preserve terminal scroll-back history for the user.
- **Security**: Never grant external agents direct filesystem access. Use an API Gateway with `X-API-KEY` authentication.
