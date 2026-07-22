---
name: rpg-collaborative-c2
description: Implementation of decoupled AI-driven game systems using the Collaborative C2 (Command and Control) model.
---
# RPG System Architecture & Agent Integration

Guidelines for implementing decoupled AI-driven game systems where an AI companion acts as the tactical interface between the player and the game engine.

## Core Architecture (Collaborative C2)
The system separates the **Game Engine** (World State Authority) from the **Companion Agent** (Tactical Interface). Players interact with the Agent, who manages a **Plan Buffer** before committing actions to the Engine.

### 1. Data Layer Design
Use a relational structure (e.g., SQLite) to separate identity from volatile state:
- **Global Registries**: Read-only tables for Classes, Species, and Items (prevents data duplication).
- **Identity (Profiles)**: Permanent character data (base stats, background).
- **Live State**: Real-time heartbeat (Current HP, active conditions, location).
- **Loot Bag**: A separate container for items; equipping items modifies active stats without mutating base identity.

### 2. The Unified Entity
Bind the Character and the Agent Persona via a single `entity_id`.
- **Character Object**: Physical stats and identity.
- **Agent Persona**: Tactical weights (Aggression, Caution, etc.) and interaction style.
- **Binding**: Ensures the Agent is permanently synced to the correct character's perception feed.

### 3. The Perception Feed (High-Fidelity Data)
The Agent must ingest "raw" data packets (JSON) rather than narrative descriptions to make tactical decisions.
- Feed should include: Exact HP/Max HP, active weapon modifiers, and raw condition flags.

### 5. The Arbiter-Verification Loop\nTo eliminate AI hallucination of rules, every tactical suggestion must be verified by the deterministic engine before delivery:\n1. **Propose**: Agent suggests an action (e.g., \"Use Second Wind\").\n2. **Verify**: The Courier (Jarvis Agent) calls `validate_action(action_type)` in `builder.py`.\n3. **Filter**: If the engine returns `False` (e.g., \"Action already used\"), the Courier rejects the suggestion and asks the AI for a valid alternative.\n4. **Deliver**: Only verified actions reach the user.\n
To prevent unintended game effects:
1. **Draft**: Agent writes a sequence of actions to a temporary buffer.
2. **Confirm**: Agent presents the plan to the player with [Recommendation] -> [Reason] -> [Risk].
3. **Commit**: Actions only trigger game effects upon a `COMMIT_PLAN` signal.

## Pitfalls & Lessons
- **Input Loop**: Avoid simple `input()` loops for AI-driven characters. Instead, implement an Internal API (e.g., `jarvis_api.py`) that allows the LLM to query the DB via tools.
- **ID Management**: Always provide a "Name Alias" lookup in the Gateway to avoid forcing users to remember long UUIDs (e.g., resolve "Charis" -> "ent_c96f4d62").
- **State Mutation**: Never mutate base ability scores when equipping gear; always apply modifiers during the attack/defense calculation.

## Verification Workflow
- Verify `entity_id` exists across all three tables (Characters, Personas, Lobby) before starting a session.
- Test the "Perception Feed" output to ensure it contains raw data necessary for the chosen tactical persona.
