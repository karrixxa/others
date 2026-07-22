---
name: rpg-distributed-agent-dev
description: Guidelines for implementing decoupled, distributed game agents (Identity, Strategist, Monster, DM) using a shared data contract.
---

# RPG Distributed Agent Development

This skill governs the creation and integration of specialized agents within a distributed RPG engine where different agents manage different domain responsibilities (Identity, Strategy, Entity, Narrative) synchronized via a central state.

## 🛠️ Architecture & Data Contract
Agents MUST NOT invent new database keys. All interactions must follow the established Data Contract:

### 1. Shared Data Layer (`common_db.py`)
All agents must use a shared database utility to prevent state drift.
- **Read:** `get_entity(entity_type, entity_id)`
- **Write:** `update_entity(entity_type, entity_id, update_data)` (must use deep merging for nested dicts like `vitals` or `stats`).

### 3. Decoupled State Pattern
To prevent write-collisions between agents (e.g., Identity updating a background while Strategist updates HP), split data into two record types:
- **Static Profile (`player_id`):** Permanent identity, base stats, and biography. Managed by the Identity Lead.
- **Volatile State (`state_id`):** Current HP, location, active buffs, and action economy. Read/Written by Strategist and Entity Engine.
- **Synthesis:** The Jarvis interface must merge these two records at runtime to provide a complete tactical briefing.
- **Pathing:** Ensure the shared DB utility has a dedicated `states/` directory separate from `characters/` to avoid namespace collisions.

## 🚀 Implementation Workflow

### 1. Service-Oriented Transition
Move from local scripts (CLI tools) to API services (e.g., FastAPI).
- **Reasoning:** Distributed agents cannot share memory; they must communicate via HTTP/WebSockets.
- **Deployment:** Run services on dedicated ports (e.g., Identity on 9090) to allow the Gateway to route requests.

### 2. The "Cognitive Interface" (Jarvis Pattern)
When building a player-facing assistant:
- **State Synthesis:** Do not just dump JSON. Call `get_tactical_summary` or similar to synthesize raw vitals into a polished, persona-driven briefing.
- **Persona Constraints:** Embed specific communication constraints (e.g., avoiding gendered language) directly into the agent's system prompt/persona file.

## ⚠️ Pitfalls & Debugging

### Virtual Environment & Dependency Failures
- **Permission Errors during Pip Install:** On shared clusters, `pip` may crash when scanning directories outside the user's home (e.g., `PermissionError: [Errno 13]`).
- **The Fix:** Use `uv` for package management. If `uv` is not in the path, use `uv pip install --python <path_to_venv_python> <packages>`. This avoids the legacy environment scans that cause permission crashes.

### Data Integrity
- **HP Validation:** When updating vitals, the Identity Lead must ensure `hp_max >= hp_current` to avoid logical corruption.
- **ID Normalization:** Ensure consistent ID prefixes (`player_`, `monster_`, `sector_`) across all agents to prevent file-system collisions.
