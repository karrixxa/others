# 📜 C2 Data Contract: The Global Schema

This document defines the mandatory structure for all records in the C2 RPG system. 
Every agent (DM, Strategist, Monster, Character) MUST adhere to these schemas.

---

## 🛠️ Integration Workflow
1. **Import**: Every agent must start with `import common_db`.
2. **Read**: Use `common_db.get_entity(id)` to retrieve records.
3. **Write**: Use `common_db.update_entity(id, update_dict)` to save changes.
4. **Verify**: Check this `DATA_CONTRACT.md` before adding any new fields to a record.

---

## 👥 1. Player Record (`player_{id}`)
**Managed by: Character Agent (Identity Lead)**

| Key | Type | Description |
| :--- | :--- | :--- |
| `id` | String | Unique identifier (e.g., "player_01") |
| `name` | String | Character name |
| `class` | String | Character class (e.g., "Paladin") |
| `level` | Int | Current character level |
| `stats` | Dict | Raw values: `{str, dex, con, int, wis, cha}` |
| `modifiers` | Dict | Calculated bonuses: `{str, dex, con, int, wis, cha}` |
| `proficiency_bonus` | Int | Global bonus based on level |
| `vitals` | Dict | `{hp_current, hp_max, ac}` (Constraint: `hp_max >= hp_current`) |
| `position` | Dict | `{sector_id, x, y}` |
| `resources` | Dict | `{spell_slots: {}, hit_dice: int}` |
| `conditions` | List | Active effects: `["poisoned", "blinded"]` |
| `inventory` | List | List of items: `[{"item_id": "s1", "name": "Sword"}]` |
| `status` | String | Game state: `"active"`, `"combat"`, `"dead"` |

---

## 👹 2. Monster Record (`monster_{id}`)
**Managed by: Monster Agent (Entity Engine)**

| Key | Type | Description |
| :--- | :--- | :--- |
| `id` | String | Unique identifier (e.g., "mob_101") |
| `type` | String | Species/Type (e.g., "Goblin") |
| `cr` | Int | Challenge Rating |
| `stats` | Dict | `{atk, def, spd}` |
| `vitals` | Dict | `{hp_current, hp_max, ac}` |
| `resistances` | List | Damage types ignored: `["fire", "poison"]` |
| `abilities` | List | Special moves: `["Multiattack", "Sneak Attack"]` |
| `position` | Dict | `{sector_id, x, y}` |
| `aggro_target` | String | The `player_id` currently targeted (or `null`) |
| `behavior` | String | AI State: `"aggressive"`, `"ambush"`, `"passive"` |

---

## ⚔️ 3. Combat Encounter Record (`combat_{id}`)
**Managed by: Strategist Agent (The Referee)**

| Key | Type | Description |
| :--- | :--- | :--- |
| `id` | String | Unique identifier (e.g., "fight_501") |
| `sector_id` | String | The sector where the fight is happening |
| `participants` | List | Sorted list of entity IDs based on initiative |
| `current_turn_index` | Int | Index of the entity whose turn it is |
| `round_number` | Int | Current combat round count |
| `status` | String | `"active"`, `"resolved"`, `"interrupted"` |
| `global_modifiers` | List | Encounter-wide effects (e.g., `"rain_slicked"`) |

---

## 🌍 4. World Sector Record (`sector_{id}`)
**Managed by: DM Agent (The Narrator)**

| Key | Type | Description |
| :--- | :--- | :--- |
| `sector_id` | String | Unique identifier (e.g., "forest_01") |
| `name` | String | Name of the area |
| `description` | String | Base narrative text for the area |
| `entities` | List | IDs of all players/monsters currently here |
| `interactables` | List | Objects: `[{"id": "chest_1", "type": "loot"}]` |
| `env_effects` | List | Global modifiers: `["heavy_rain", "darkness"]` |
| `exits` | Dict | Map of connections: `{"north": "sector_02"}` |
| `danger_level` | Int | Scale 1-10 (Used by DM for tone) |

---

## 🚀 Core Component Responsibilities

- **Gateway**: Routing traffic between Browser $\rightarrow$ Agents.
- **DM Agent**: Narrative generation and lore consistency.
- **Strategist Agent**: Combat math and rule enforcement.
- **Monster Agent**: Entity spawning and movement.
- **Character Agent**: Player identity and the "Jarvis" assistant.
