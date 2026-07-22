---
name: rpg-agent-intelligence-routing
description: Guidelines for implementing decoupled AI agents in a game engine using the Courier-Brain-Arbiter pattern to separate data transport from cognitive reasoning.
---

# RPG Agent Architecture & Intelligence Routing

Guidelines for implementing decoupled AI agents within a game engine context, specifically focusing on the "Courier-Brain-Arbiter" pattern.

## 🏗️ Architectural Pattern: The Intelligent Pipe
To prevent AI reasoning from becoming hardcoded in Python scripts (which makes them rigid and hard to tune), use a tiered intelligence routing system:

1. **The Courier (Dumb Pipe)**: 
   - A lightweight Python API (e.g., FastAPI).
   - **Role**: Data aggregation and transport.
   - **Action**: Fetches raw state from the game engine $\rightarrow$ builds a structured "Perception Packet" (JSON) $\rightarrow$ forwards to the Intelligence Layer.
   - **Constraint**: No reasoning, no prompt engineering, and no archetype logic in the code.

2. **The Brain (Hermes Profile)**:
   - A managed Hermes Persona (`persona.md`).
   - **Role**: Cognitive processing and tactical reasoning.
   - **Action**: Receives the Perception Packet $\rightarrow$ filters through persona/archetype $\rightarrow$ generates strategy.
   - **Benefit**: Allows real-time tuning of personality and tactical rules without restarting servers.

3. **The Arbiter (World Truth)**:
   - The central game state/ledger server.
   - **Role**: Authoritative source of truth for world-lore and global state.
   - **Action**: Responds to specific queries from the Brain/Courier regarding facts not present in the immediate perception packet.

## 🛠️ Implementation Workflow
1. **Strip Logic**: Remove all `if/else` reasoning or hardcoded prompts from the Courier script.
2. **Build Perception Packet**: Ensure the Courier sends a raw JSON object containing:
   - Exact stats (HP, AC, Ability Scores).
   - Environmental data (Lighting, Threat Level).
   - Entity lists (Allies, Enemies).
3. **Route via Profile**: Call the Gateway using a specific profile identifier (e.g., `profile: "jarvis"`) to trigger the correct persona.
4. **Format for Generation**: Wrap payloads in a standard `messages` array to ensure the Gateway triggers the LLM generation engine rather than a system state-machine.

## ⚠️ Pitfalls & Lessons Learned
- **The "State Machine" Trap**: Sending custom JSON objects to a Gateway may trigger internal system states (e.g., `state: CREATION`) instead of the AI persona. **Fix**: Wrap the prompt in a `{"messages": [{"role": "user", "content": "..."}]}` structure.
- **Data Hallucinations**: AI agents may try to "guess" stats. **Fix**: Include a "Golden Rule of Data" in the `persona.md` explicitly forbidding guessing and demanding the use of exact numbers from the packet.
- **Process Collision**: In shared server environments, the Gateway may be run by a different user. **Fix**: Verify which PID is holding the port (e.g., `fuser -k 9090/tcp`) and ensure the local Brain process is linked to the correct Gateway endpoint.
