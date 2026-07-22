---
name: rpg-collaborative-c2-dev
description: Implementation of decoupled RPG systems with companion AI agents (Collaborative C2 model).
category: software-development
---

# RPG Character & Agent System Implementation
Guidelines for implementing decoupled RPG systems with companion AI agents (Collaborative C2 model).

## Core Architecture
- **Unified Entity**: Link Character (stats/identity) and Agent Persona (tactical weights/tone) via a single `entity_id`.
- **Data Split**:
    - **Registry**: Read-only global rules (Classes, Species, Items).
    - **Profile**: Persistent identity (Stats, Background).
    - **Live State**: High-frequency updates (HP, Position, Conditions).
    - **Plan Buffer**: Non-persistent area for Agent to draft action sequences before committing to the engine.
- **Perception Feed**: Provide agents with raw data (modifiers, exact distance, flags) rather than narrative descriptions.

## Interactive Builder Workflow
When building character creation tools, follow the 'Tiered Guidance' pattern to avoid user frustration:
1. **Primary Recommendation**: Suggest a path based on a high-level playstyle choice.
2. **Curated Alternative**: If rejected, suggest a specific alternative based on class/species synergies.
3. **Full Catalog**: As a final fallback, provide a complete list of options with descriptions from the registry.
4. **Fuzzy Matching**: Always implement fuzzy string matching for user inputs to avoid strict casing/typo failures.

## Technical Pitfalls\n- **Input Buffering**: In CLI environments, ensure authentication loops are robust and handle empty inputs or trailing whitespace without crashing.\n- **DB Synchronization**: Use a separate `lobby_state` table to manage the 'Ready-Up' handshake between the agent, user, and engine.\n- **API Readiness**: When launching the C2 API Bridge (e.g., `main.py`), verify the process is actually listening on the designated port (e.g., 9090) using `netstat -tulpn` before instructing the user to connect. A running process does not always mean the port is open/bound.
