---
name: rpg-character-forge
description: Guidelines for implementing the Hermes RPG Character Forge and Gateway synchronization.
---

# RPG Character Engine Integration

Guidelines for implementing and maintaining the Hermes RPG Character Forge and Gateway.

## Core Architecture
- **Consultant Pattern**: The Bridge/Agent must not execute direct DB writes. It must return JSON commands (e.g., `create_entity`, `update_entity`) to the Gateway (the Authority), which then applies changes to the database.
- **Statelessness**: Agents should rely on the Gateway's current state for every turn rather than caching character data locally.

## Character Creation Flow (The Forge)
The creation process must follow a guided "Consultant" sequence:
1. **Class Selection**: Display all classes with full descriptions from the data registry.
2. **Species Recommendation**: 
   - Suggest a synergistic species based on the chosen class.
   - If the user rejects (`no`), suggest a specific alternative.
   - If rejected again, display the full species catalog with descriptions.
3. **Background Selection**: Display all backgrounds with full descriptions.
4. **Armory**: Provide a class-specific weapon list.
5. **Finalization**: Collect character name and commit as a `create_entity` command.
6. **The Reveal**: Immediately render the full character sheet upon successful database commitment.

### ⚠️ Critical Implementation Pitfalls
- **The Race Condition:** API file writes may not be instantaneous. The CLI must implement a **Retry-and-Wait** loop (e.g., 5 attempts with 0.1s delay) when loading a newly created profile to avoid `FileNotFound` or `NoneType` errors.
- **The Entity ID Sequence:** The `create_character` action must be processed *before* any `entity_id` validation checks, as the ID is generated during this step.
- **Database Arguments:** Ensure `common_db.get_entity` is called with both `(entity_type, entity_id)` to avoid signature mismatches.
- **Storage Alignment:** Verify the API and CLI are targeting the same directory (e.g., `/profiles/` vs `/characters/`).
- **Data Structure Hybridity:** When rendering sheets or updating stats, the code must support both the legacy `character` block and the modern `gameplay_profile` structure.


## Data Synchronization Pitfalls
To avoid `KeyError` crashes and "generic" descriptions, ensure `character_options.json` contains:
- `description`: For every class, species, and background.
- `stat_priority`: A list of stats ordered by importance for each class (e.g., `["Strength", "Constitution", ...]`).
- `weapon_options`: A registry of weapon objects mapped by class name.
- `stat_array`: The base pool of numbers (e.g., `[15, 14, 13, 12, 10, 8]`) used for distribution.

## Verification Steps
- Verify that the Gateway (`gateway_cli.py`) is pulling descriptions directly from the `CharacterBuilder` options rather than using hardcoded fallbacks.
- Ensure the final payload sent to the Bridge matches the `DATA_CONTRACT.md` (vitals, identity, gameplay_profile).
