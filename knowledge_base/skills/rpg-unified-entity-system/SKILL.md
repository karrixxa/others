---
name: rpg-unified-entity-system
description: Architecture and implementation for binding AI agents to RPG characters via a Unified Entity system.
---

# RPG Character & Entity System Implementation

Guidelines for implementing and extending a Unified Entity system for RPGs, specifically focusing on the transition from flat-file profiles to relational databases for real-time gameplay.

## Core Architecture: The Unified Entity
A "Unified Entity" binds the physical character and the AI companion (Jarvis) via a single `entity_id`.

### 1. Data Layer Split
Divide data into three distinct lifecycle buckets to support real-time DM and AI interaction:
- **Global Registries (Static)**: Read-only tables for classes, species, and items. Updates here propagate to all characters globally.
- **Character Profiles (Persistent)**: Base stats, identity, and RP profiles. Updated rarely (e.g., level-up).
- **Live Game State (Volatile)**: Current HP, temporary conditions, and current location. Updated every turn.

### 2. The Loot Bag Pattern
Items should be stored in a separate container table (`inventory`) referencing a `registry_items` table.
- **Equip Logic**: Changing an equipped item should update the `game_state` (e.g., AC change) without modifying the base `character_stats`.

### 3. Tactical Companion (Jarvis) Integration
- **Persona Binding**: Store agent tactical weights (aggression, caution, etc.) in an `agent_personas` table linked by `entity_id`.
- **Perception Feed**: Implement a "flat" view or complex JOIN query that merges Live State + Base Stats + Equipped Item stats into a single JSON packet for the AI agent. **Requirement (TRD 3.1):** This feed must contain "raw" high-fidelity data (e.g., exact lighting levels, visibility ranges, hidden status flags) rather than narrative descriptions.
- **Plan Buffer**: Use a non-persistent table to draft action sequences (Draft $\rightarrow$ Commit) to avoid triggering engine effects prematurely.

## Implementation Workflow
1. **Initialize Registries**: Populate static data from JSON options.
2. **Unified Build**: Create Character $\rightarrow$ Create Persona $\rightarrow$ Initialize State $\rightarrow$ Mark Lobby Ready.
3. **Interactive Guidance**: When building characters, provide a recommendation-based flow (Playstyle $\rightarrow$ Class $\rightarrow$ Species) rather than a raw form.

## Pitfalls & Lessons
- **Stat Resolution**: Always calculate modifiers (e.g., $\lfloor(score-10)/2\rfloor$) at the point of use or in the state table, not as static values in the profile, to allow for easier buffs/debuffs.
- **Database Constraints**: Ensure `entity_id` is the primary key for the Agent and Lobby states to maintain the Unified Entity bond.
