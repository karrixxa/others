---
name: rpg-c2-agent-dev
description: Guidelines for implementing decoupled Command-and-Control (C2) AI agents for RPGs, specifically the "Courier" pattern for tactical mediation.
---

# RPG Character & Tactical AI Development
Guidelines for implementing decoupled Command-and-Control (C2) AI agents for roleplaying games, specifically focused on the "Courier" pattern where AI mediates between a game engine and a player.

## Core Architecture: The C2 Model
The system must follow a decoupled loop to ensure tactical consistency and prevent "AI slop":
1. **Perception Feed (Engine $\rightarrow$ Jarvis):** Raw world data (coords, lighting, enemy IDs) is translated into a "Tactical Packet" (Threat levels, effective sight, flanking status).
2. **Psychological Synthesis (Jarvis $\rightarrow$ Persona):** Character traits, bonds, and fears act as filters. A "Psychological Brief" is generated to override optimal tactics with character-driven behavior.
3. **Structured Execution (Jarvis $\rightarrow$ Engine):** The AI provides prose to the user but must be capable of emitting a structured `EXECUTE_ACTION` command (JSON) for the engine to process.

## Implementation Patterns

### 1. The Perception Engine
Do not pass raw engine data directly to the LLM. Use a processing layer to calculate:
- **Effective Sight:** `Lighting Level` + `Darkvision` $\rightarrow$ `Effective Visibility`.
- **Effective AC:** `Base AC` + `Cover Bonus`.
- **Threat Level:** Based on `Enemies in Melee` and `Current HP %`.
- **Tactical Flags:** `Opportunity Attack Risk`, `Sneak Attack Availability`.

### 2. The Behavioral Engine (Soul)
Use a tiered synthesis approach:
SKELETON (Archetype): Sets base risk tolerance and tone (e.g., The Stoic, The Berserker).
FLESH (Modifiers): Specific `FEAR_MODIFIERS` and `BOND_MODIFIERS` that inject `AVOID` and `SUGGEST` directives.
SOUL (Synthesis): Combine these into a "Psychological Brief" that takes precedence over general tactical optimization.

**CRITICAL ARCHITECTURAL PIVOT (The Hermes Profile Model):**
For production-grade intelligence, the Behavioral Engine (Soul) should NOT live in the Courier's Python code. Instead, the Courier must act as a "Dumb Pipe" that sends a raw Perception Packet to a specific Hermes Profile (e.g., `.hermes/profiles/jarvis/persona.md`). 
The logic for archetypes, psychological briefs, and behavioral overrides should be encoded in the `persona.md` as a system prompt, allowing for instant personality tuning without code redeployment.


### 3. Technical Hardening
- **Safe Data Access:** Always use `.get()` with defaults when accessing character JSONs to prevent `KeyError` crashes during partial profile loads.
- **API Wrapper:** Use FastAPI for the hub. Ensure the API handles the mapping between the `CharacterBuilder` and the `JarvisAgent` logic.

## Pitfalls & Lessons
- **Line Number Contamination:** When reading files via agent tools, be careful not to write the tool's line-number markers (`1|...`) back into the source code.
- **Port Collisions:** When running background servers (e.g., Flask/FastAPI), ensure ports are explicitly cleared (`fuser -k`) before restarts to avoid "Address already in use" errors.
- **Build Systems:** For simple API wrappers, avoid complex build-backends (like `hatchling`) in `pyproject.toml` if the project isn't intended as a distributable package; use a simple dependency list to avoid `ValueError` during `uv run`.
