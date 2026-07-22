---
name: rpg-distributed-backend-integration
description: Guidelines for implementing and verifying distributed Command-and-Control (C2) architectures for RPG systems.
---

# Distributed RPG Backend Integration

Guidelines for implementing and verifying distributed Command-and-Control (C2) architectures for RPG systems, specifically the Hermes RPG model.

## Core Architecture
- **Gateway (Port 10001):** The primary hub for world state, movement, and interactions.
- **Identity Manager (Port 9090):** The authority for character creation, identity finalization, and profile storage.
- **Statelessness:** The client (CLI/Engine) must be stateless. It should not store player stats locally but poll the backend for the current "Absolute Truth."

## The Three Core Loops

### 1. The Birth Loop (Onboarding)
Sequence: `Recommend` $\rightarrow$ `Finalize` $\rightarrow$ `Spawn` $\rightarrow$ `Poll Sector`.
- **Recommendation:** Suggest Class $\rightarrow$ Species $\rightarrow$ Background based on synergy maps.
- **Finalize:** `POST /finalize_character` to the Identity Manager to generate an `entity_id` and JSON profile.
- **Spawn/Poll:** Immediately call `GET /world/current_sector?user_id={id}` via the Gateway to confirm the entity is physically present in the world.

### 2. The World Loop (Exploration)
- **Sector Info:** `GET /world/current_sector` to retrieve room descriptions and lists of present entities (Residents).
- **Movement:** `POST /move` with `dx` and `dy` coordinates.

### 3. The Interaction Loop (Combat/Social)
- **Targeted Action:** `POST /action/targeted` with `actor_id`, `target_id`, and `action`.
- **Turn Sync:** `GET /turn/status` to verify if the current entity is active.

## Pitfalls & Verification
- **Port Mismatches:** Ensure Identity Manager is on 9090 and Gateway is on 10001. Check for "address already in use" errors during deployment.
- **Endpoint Alignment:** Verify that the Identity Manager actually implements `/finalize_character` and not just a generic `/action` endpoint.
- **Entity Binding:** All requests to the Gateway must include a valid `user_id` or `entity_id` to maintain the "Personal Jarvis" experience across multiple sessions.

## Verification Workflow
1. Check if ports are listening: `ss -tlnp | grep -E '9090|10001'`.
2. Run an End-to-End (E2E) script: Create Character $\rightarrow$ Verify Spawn $\rightarrow$ Move $\rightarrow$ Check Turn.
