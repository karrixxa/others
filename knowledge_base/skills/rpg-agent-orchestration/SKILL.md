---
name: rpg-agent-orchestration
description: Guidelines for implementing and maintaining a decoupled AI agent system serving as an Identity & Asset Authority for a game engine.
---

# RPG Agent Orchestration & Identity Authority

Guidelines for implementing and maintaining a decoupled AI agent system serving as an "Identity & Asset Authority" for a game engine.

## Core Architecture
The system follows a hub-and-spoke model where the AI Agent (The Authority) manages the state of entities, and the Game Engine (The Client) handles the rendering and input.

### The Mandatory API Contract
To ensure stability between the AI Agent and the Game Engine, the following endpoints are required:
- `GET /status`: Health check returning `{"status": "online", "version": "...", "agent_type": "CHARACTER"}`.
- `POST /action`: Processes a JSON command list for asset/stat mutations. Returns a list of `update_entity` and `notify_user` commands.
- `POST /jarvis/ask`: Tactical reasoning endpoint. Requires a "Perception Packet" (World State) to prevent AI blindness.

## Identity Creation: The Consultant Flow
Avoid static forms. Use a Guided Narrative approach to determine character identity:
1. **Intent Discovery:** Ask for "vibes" or playstyles (e.g., "Do you want to be a shadow or a bastion?").
2. **Class Negotiation:** Recommend classes based on vibes; provide curated alternatives if the user rejects the first suggestion.
3. **Identity Tailoring:** Suggest Species and Backgrounds that complement the chosen class.
4. **Finalization:** Confirm starting weapon and trigger the `/finalize_character` logic.

## Common Pitfalls & Fixes
- **AI Blindness:** If the agent provides generic advice, verify that the Game Engine is sending a full Perception Packet (current HP, nearby threats, environment) in the `POST /jarvis/ask` payload.
- **Provider Collision:** In shared GPU clusters, avoid hardcoded localhost:8080 URLs. Use named providers (e.g., gpu_2) or employ a port-hunting strategy (checking common vLLM ports like 8000-8010) to locate the actual model endpoint.
- **Profile-First Bottleneck:** Ensure the API allows "Guest/New User" access during character creation. Do not return 404 Profile Not Found before the character is actually finalized.
- **Persona Looping:** If the agent becomes "too helpful" and skips the consultant flow, enforce a Phase-Gate system in the persona.md to forbid skipping steps.

## Git/GitHub Workflow for Remote Clusters
When managing a project that exists both on a local high-performance cluster (e.g., Kant) and a remote Git repository (e.g., GitLab):
- **Ghost Cleanup Pattern**: If the local environment contains legacy scraps, temporary test files, or redundant environments (e.g., `venv_new/`) that are not needed on the remote server but must be preserved locally, use the "Ghost Cleanup" approach:
  1. Update `.gitignore` to include the files/folders to be hidden from Git.
  2. Use `git rm -r --cached <paths>` to remove the files from the Git index without deleting them from the disk.
  3. Commit and push.
- **Protection Guard**: Be aware that `main` branches are often protected. If a `force push` is blocked, create a feature branch (e.g., `feat/character-builder`) to sync state.
- **Path Precision**: When performing bulk removals from cache, use a script or loop to handle files individually to avoid shell parsing errors with special characters (e.g., backticks in filenames).
