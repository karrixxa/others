---
name: rpg-character-intelligence
description: Guidance for implementing dynamic, character-driven AI companions for RPGs using Psychological Synthesis and Perception-linked behavioral overrides.
---
# Skill: rpg-character-intelligence
Guidance for implementing dynamic, character-driven AI companions for RPGs, moving beyond static archetypes to "Psychological Synthesis."

## Concept: The Soul Layer
Instead of assigning a fixed personality label (e.g., "The Stoic"), the agent should synthesize a "Psychological Brief" at runtime. This brief acts as a behavioral filter that overrides general tactical advice based on a character's specific identity.

### The Synthesis Pipeline
1. **Skeleton (Archetype)**: Map personality traits to a base archetype (e.g., Stoic, Berserker, Guardian) to set the structural tone and risk tolerance.
2. **Flesh (Modifiers)**: Extract specific Roleplay Profile data (Bond, Fear, Secret, Motivation).
3. **Soul (Synthesis)**: Combine the above into a narrative brief that gives the AI direct tactical instructions.

## Implementation Patterns

### 1. Archetype Mapping
Map trait combinations to archetypes to avoid manual selection:
- `["disciplined", "loyal", "direct"]` -> **The Guardian** (Protective, steady, focuses on others).
- `["clever", "cautious", "sarcastic"]` -> **The Trickster** (Positioning, advantage, playful).
- `["curious", "analytical", "reserved"]` -> **The Scholar** (Optimal moves, rule-focused).

### 2. Modifier-Based Overrides
Use dictionaries to map specific fears/bonds to tactical "Avoid" and "Suggest" lists:
- **Fear Modifiers**: Map `fire` -> `avoid: [move_toward_fire]` and `suggest: [ranged attack]`.
- **Bond Modifiers**: Map `protects_sibling` -> `priority: [never_leave_bond_exposed]`.

### 3. Perception Integration
The synthesis engine must be linked to the Perception Engine. If the environment contains a "Fear" trigger (e.g., tile_type is 'burning_bridge'), the brief must inject an immediate `⚠️ FEAR PRESENT` override that takes precedence over all other tactical goals.

## Pitfalls & Lessons
- **Stat-Only Logic**: Avoid letting the AI rely solely on stats (e.g., "You have 4HP, retreat"). Combine this with the soul layer: "You have 4HP, but as a Berserker, you will take the hit to deal damage."
- **Generic Briefs**: Descriptions ("The character is afraid of fire") are less effective than directives ("NEVER suggest moving toward fire"). Use imperative language in the synthesis.
- **Data Resilience**: Ensure the `CharacterGameplayAgent` can handle partial JSON profiles (e.g., missing `gameplay_profile`) without crashing (KeyError).

## Verification Workflow
To verify synthesis, create two characters with the same stats but opposing psychological profiles in the same scenario. The advice must differ fundamentally based on their Bond/Fear/Archetype.
