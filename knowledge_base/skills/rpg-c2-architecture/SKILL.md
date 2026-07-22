---
name: rpg-c2-architecture
description: Framework for implementing Collaborative Command-and-Control (C2) models in AI-driven gaming, decoupling deterministic rules from LLM tactical reasoning.
---
# RPG-C2-Architecture
Skills for implementing Collaborative Command-and-Control (C2) models in AI-driven gaming. Focuses on decoupling deterministic rules engines from LLM-driven tactical agents.

## Core Philosophy
The "Brain Stem" flow: 
User Input -> Orchestrator -> World Truth Gathering -> DM Narration -> Engine Execution -> User.
The AI (Companion Agent) acts as a tactical interface, not the source of truth.

## Architectural Components

### 1. The Rules Engine (The Arbiter)
The sole source of truth for game mechanics.
- Must provide deterministic validation of actions (e.g., `validate_action(action_type)`).
- Should be a pure Python module (e.g., `builder.py`) to prevent AI hallucinations.

### 2. The Courier (Agent Bridge)
The integration layer between the Rules Engine and the LLM.
- **Stateless Design:** Must not store character state in-memory. Load from disk -> process -> flush.
- **LRU Caching:** Use functools.lru_cache for static rule lookups (e.g., stat explanations) to minimize disk I/O in multiplayer environments.
- **Perception Feed:** Extracts a "Slim State" JSON packet from the engine to provide the LLM with raw data without flooding the context window.
- **The Verification Loop:** 
    1. LLM proposes a tactic.
    2. Courier pings the Arbiter for validation.
    3. If invalid, Courier sends a "Rejection" prompt back to the LLM for a corrected proposal.

### 3. The Tactical Profile
The LLM persona configured for tactical advice.
- **Persona:** Concise, direct, and rule-abiding.
- **Modes:** Turn Start (proactive), Question (reactive), and Event (immediate response).
- **Constraint:** Must never invent stats; must always end with a report of remaining action economy.

## Implementation Pitfalls
- **Port Conflicts:** In shared cluster environments, avoid common ports like 8000/8080. Use higher ports (e.g., 9000, 5001) and implement `fuser -k` cleanups before launching.
- **Environment Management:** Always use the project's virtual environment (`/venv/bin/python`) for launching agents to avoid "externally-managed-environment" errors.
- **Hallucination Risk:** Never let the AI determine if a move is legal. Always route the proposal through the deterministic Rules Engine.

## Verification Workflow
1. Launch Rules Engine API.
2. Launch Companion Agent.
3. Trigger a forbidden action (e.g., using a bonus action twice).
4. Verify that the Courier intercepts the proposal, the Arbiter rejects it, and the AI pivots to a legal alternative.

### 4. Asset Mapping & Visuals (Modular Paper-Doll System)
Bridges symbolic names to engine assets to enable dynamic rendering.
- Layered Mapping: Species (Base Model) -> Class (Default Outfit/Anim) -> Equipment (Slot Overrides).
- Visual Manifest: The Courier must generate a JSON map of asset paths (e.g., .fbx, .obj, .anim) based on the character's current profile and equipped items.
- Implementation: Use a central assets.json registry to map symbolic IDs (e.g., Plate Armor) to physical file paths.
