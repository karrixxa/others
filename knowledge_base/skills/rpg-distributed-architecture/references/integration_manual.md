# Distributed RPG Integration Manual

## Endpoint Reference
- **GET /health**: Check Gateway status.
- **GET /recommend/{playstyle}**: Get build suggestions.
- **POST /finalize_character**: Create identity.
- **POST /spawn**: Move entity to world.
- **GET /world/current_sector?user_id={id}**: Get room residents and description.
- **POST /move**: Update x, y coordinates.
- **POST /action/targeted**: actor_id, target_id, action (e.g., heal).
- **GET /turn/status**: Get current active actor and queue.

## Data Formats
### Entity Profile
{
    "identity": { "name": str, "class": str, "species": str },
    "vitals": { "hp_current": int, "hp_max": int, "armor_class": int },
    "position": { "sector_id": str, "x": int, "y": int },
    "gameplay_profile": { "ability_scores": dict, "ability_modifiers": dict }
}

### Sector Profile
{
    "sector_id": str,
    "name": str,
    "description": str,
    "entities": [list of entity_ids],
    "exits": { "north": "sector_id", ... }
}
