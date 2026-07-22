---
name: rpg-agent-api-stabilization
description: Guidelines for implementing and debugging decoupled C2 agents for game engines, focusing on the Identity and Asset Authority pattern and API contract stabilization.
tags: [rpg, c2, api, fastapi, json-contract]
---

# RPG Agent Integration & API Stabilization

Guidelines for implementing and debugging decoupled Command-and-Control (C2) agents for game engines, specifically focused on the "Identity and Asset Authority" pattern.

## Core API Contract
The Character Agent must implement a REST API with a "Command List" exchange pattern to allow multi-step atomic responses.

### Endpoints
- `GET /status`: Health check. Returns `{"status": "online", "version": "1.0.0", "agent_type": "CHARACTER"}`.
- `POST /action`: Primary command endpoint. Accepts a JSON object containing a `commands` list and returns a similar list.

### Request/Response Schema
Requests and responses MUST follow this shape:
```json
{
  "commands": [
    {
      "action": "action_name",
      "params": { "key": "value" }
    }
  ]
}
```

## Implementation Pitfalls & Fixes

### 1. The "Creation ID" Deadlock
**Problem:** API handlers often check for an `entity_id` at the start of the request. This blocks `create_character` requests because the ID does not exist until the character is created.
**Fix:** Place the `create_character` logic *above* the `entity_id` validation check.

### 2. Storage Location Mismatch (Path Drift)
**Problem:** The API may save profiles to a specific directory (e.g., `/profiles/`), while the CLI or DB utility looks in another (e.g., `/characters/`).
**Fix:** Ensure a single source of truth for the profile root directory. When implementing `load_character` in a CLI, verify the exact path where the API writes JSON files.

### 3. The "Race Condition" Load
**Problem:** The API returns a success message as soon as the write operation is triggered, but the CLI tries to read the file before the OS has finished flushing it to disk, resulting in `None` profiles.
**Fix:** Implement a retry-and-wait loop in the loading function (e.g., 5 attempts with 100ms delay) to ensure the file is accessible.

### 4. Data Structure Drift
**Problem:** CLI rendering logic often assumes a flat "character": {} block, but evolved profiles use fragmented keys like "identity", "gameplay_profile", and "combat".
**Fix:** Implement a "Hybrid Parser" that checks for multiple possible keys:
- Check identity $\rightarrow$ Fallback to character.
- Check gameplay_profile $\rightarrow$ Fallback to character.

### 5. Argument Mismatch in DB Calls
**Problem:** Database utility functions (like `get_entity` in `common_db.py`) may require specific argument signatures (e.g., `(entity_type, entity_id)`) while the CLI calls them with only one argument, leading to silent failures inside `try/except` blocks.
**Fix:** Audit the signature of the DB access layer and ensure the Gateway/CLI passes all required parameters (e.g., always specifying "player" as the entity type).

### 6. Forge-Lite vs. Forge-Full Data Mismatch
**Problem:** The API Forge may generate "Lite" profiles (basic scores only) while the CLI expects "Full" profiles (Skills, Proficiency, etc.), causing a perceived loss of data.
**Fix:** Ensure the `generate_profile` logic in the API calculates the full derived state (Ability $\rightarrow$ Mod $\rightarrow$ Skill Bonus) and saves it under the `gameplay_profile` block.

## Verification Workflow
1. **Health Check:** Verify `/status` returns 200.
2. **Identity Flow:** `/create` $\rightarrow$ API returns `set_active_entity` $\rightarrow$ CLI loads profile $\rightarrow$ Stats render.
3. **Asset Flow:** Request `use_item` $\rightarrow$ API returns `update_entity` (stat increase) AND `notify_user`.
