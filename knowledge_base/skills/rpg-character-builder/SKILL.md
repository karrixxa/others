---
name: rpg-character-builder
description: Workflows for designing and implementing procedural character generation systems for RPGs.
---

# RPG Character Builder Workflow

This skill governs the creation of character generation systems that translate high-level player preferences (playstyle) into detailed, game-ready JSON profiles with derived statistics.

## 🛠️ Advanced Logic & Data Contract (v1.0)
- **Schema Alignment**: Every forged character MUST be saved as a **Player Record** using the `common_db.py` interface.
- **Mandatory Fields**: Ensure the following fields are populated: `vitals` (hp_current, hp_max, ac), `position` (sector_id, x, y), and `conditions` (List).
- **Advanced Systems**:
    - **Encumbrance**: Calculate capacity as `Strength * 15`. Implement states: CLEAR, ENCUMBERED, and OVERLOADED.
    - **Weapon Stats**: Map weapon names to a library containing damage dice, damage type, and weight.
    - **Recommendation Engine**: Provide build suggestions (Tank, Assassin, Scholar, Healer) based on user playstyle.
- **Progression**: Implement XP thresholds and attribute growth (e.g., +2 Max HP per level) via the Bridge.
   - **UX Pattern**: Use a "Recommended -> Alternative -> Full Catalog" flow. 
   - **Tier 1 (Recommended)**: Present the top choice based on playstyle.
   - **Tier 2 (Alternative)**: If rejected, suggest a curated "Next Best" alternative with a brief description of why it fits.
   - **Tier 3 (Full Catalog)**: If still rejected, list all available options from the config file with their full descriptions.
   - **Synergy-Based Suggestions**: Use cross-reference maps (e.g., `species_recs`, `bg_recs`) to suggest options that logically complement the selected class (e.g., recommending Elves for Rogues) to create a high-fidelity "Consultant" experience.
   - **The Final Reveal**: Immediately render the full Character Sheet upon successful DB commitment. The user should not have to manually request stats after creation.
   - **Detailed Stat Presentation**: When rendering the final sheet, always calculate and display the numerical modifier alongside the raw score (e.g., `16 (+3)`) using `floor((score - 10) / 2)`.

- **Interactive UX**: When running as a CLI tool:
    - Use clear headers (e.g., `--- 🛡️ HERMES RPG: CHARACTER FORGE 🛡️ ---`).
    - Provide a numbered list of options to allow quick numeric selection.
    - Display the final result as a formatted "Gateway Output" block to verify the JSON contract.
     - **High-Fidelity Menus**: Never list just the name of an option. Always pair the option with its description (e.g., "Fighter | A master of martial combat...") to prevent user disorientation and provide necessary context.
     - **Class-Specific Armory**: Filter weapon choices based on the selected class. Do not present a generic global list; only offer weapons that logically fit the character's calling.
     - **The Final Reveal**: Immediately render the full Character Sheet upon successful DB commitment. The user should not have to manually request stats after creation.
     - **Gateway-Centric State Management (C2 Pattern)**:
         - **Statelessness**: The builder and associated agent (e.g., Jarvis) must NOT cache character data locally.
         - **Command-Based Changes**: Every state change (creation, stat update, position move) must be wrapped in a `commands` list within the JSON response to the Gateway.
         - **Example Format**:
           ```json
           {
             "narration": "You drink the healing potion...",
             "commands": [
               {
                 "action": "update_entity",
                 "params": { "entity_id": "char_01", "data": { "current_hp": 15 } }
               }
             ]
           }
           ```
     - **Input Handling**: Use fuzzy matching (e.g., `difflib.get_close_matches`) or a `normalize_choice()` helper for all user inputs to handle typos, numbers (1-6), or case-insensitivity.
         - **No Silent Defaults**: NEVER use hardcoded fallbacks (e.g., `input or "Rogue"`) for critical identity fields like Class or Species. If an input cannot be normalized to a valid option in the config, the system MUST raise an error or request clarification. Silent defaulting creates \"ghost characters\" that break engine synchronization.
         - **Cinematic Identity Preservation**: Separate the **Narrative/Cinematic Class** (e.g., \"College of Lore Bard\") from the **Base Mechanical Class** (e.g., \"Bard\"). 
             - Save the Cinematic name in the `identity` profile for UI/Narrative use.
             - Use the Base class for all mathematical derivations (HP, Spell Slots, Proficiencies).
         - **Flexibility**: Ensure affirmative/negative prompts (y/n) accept natural variations (e.g., \"yes\", \"yeah\", \"nope\") to reduce user friction.
       - Provide clear headers (e.g., `[ Selecting species ]`) to prevent user disorientation during multi-step flows.
- **Stat Assignment (User-Driven)**: 
    - Use a standard array (e.g., `[15, 14, 13, 12, 10, 8]`).
    - **Dynamic Priority**: If a user provides a specific `stat_priority` (e.g., \"Strength\"), that attribute MUST take the highest value in the array. 
    - **Fallback Logic**: Fill remaining slots based on the class's default `stat_priority` list, ensuring no duplicates and that exactly 6 stats are assigned.
    - Map these values to ability scores.
5. **Calculate Derived Values**:
   - **Modifiers**: `floor((score - 10) / 2)`.
   - **HP**: Base Hit Die + Constitution Modifier.
   - **AC**: Implement specific armor formulas (Light, Medium, Heavy, Shield) rather than a single base value.
   - **Skills/Saves**: Correctly map class-specific saving throw proficiencies and background bonus skills.
6. **Integrate with Gameplay Engine**: Ensure the builder produces a "Unified Entity Package" that can be consumed by a `CharacterManager` for live state tracking (HP, Action Economy, Conditions).
   - **API Integration**: Wrap the builder in a lightweight API (e.g., FastAPI) to maintain a strict separation between the deterministic Rules Engine and the Presentation Layer.
    - **Observability**: Implement immediate logging/printing of the raw `request` object upon receipt of critical endpoints (e.g., `/finalize_character`). This is essential for debugging \"C2-Sync\" issues where the agent's perception of the request differs from the actual payload.
    - **Port Discipline**: In shared cluster environments, strictly verify the target Gateway port (e.g., 10001 vs 9090). Avoid \"Bridge-to-Bridge\" loops where two API layers call each other instead of the intelligence layer.
   - **UI Mapping**: Use a decoupled UI Schema (e.g., `ui_schema.json`) to map API response fields (e.g., `gameplay_profile.combat.hp`) to visual components (e.g., `health_bar`). This prevents the frontend from becoming tightly coupled to the backend's data structure.
   - **Port Management**: In shared environments, be prepared for port collisions. Use `fuser -k <port>/tcp` to clear stubborn processes, and pivot to alternative ports (e.g., 8080) if 8000 is unavailable.
7. **Verification**: Validate the output against official PHB standards for hit dice and primary abilities.

## Pitfalls & Lessons

- **Environment Isolation**: In shared Linux environments, avoid global `pip install`. Use a virtual environment (`python3 -m venv venv`) and call the interpreter via the absolute path (e.g., `/path/to/venv/bin/python`) to avoid `externally-managed-environment` errors and module import failures.
- **Permission Errors**: When working in shared cluster environments (e.g., `/datapool`), prioritize user home directories (e.g., `/home/cxiong/`) for writing project files and config JSONs to avoid `Permission denied` errors during file creation. **Crucial**: When saving to external project directories (e.g., `/home/prodrig/`), ensure the API has necessary write permissions or implements a fail-safe fallback.
- **Calculation Precision**: Always use `math.floor` for ability modifiers to ensure consistent D&D-style rounding.
- **Naming Scope**: When referencing directories for saving profiles (e.g., `CHARS_DIR`), ensure they are defined as global constants or passed explicitly to the builder. Avoid referencing them as attributes of the builder class (e.g., `self.builder.CHARS_DIR`) unless they are explicitly defined in the class `__init__`, as this causes `AttributeError` during the finalization phase of conversational flows.
- **Decoupling**: Keep the `CharacterBuilder` class independent of the specific game data so that adding new classes or species only requires updating the JSON config.
- **Data Integrity**: When updating stat priorities or hit dice, cross-reference with authoritative sources (e.g., D&D Beyond) to prevent "AI slop" or approximate values that break game balance.

## References
- See `templates/character_options.json` for the expected structure of game data.
- See `templates/builder_boilerplate.py` for a reference implementation of the advisor and calculation logic.
