import httpx
from typing import Dict, Any
import os
import sys
import json
import asyncio
import uvicorn
import traceback
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Import the mandatory Shared DB library
sys.path.append('/home/cxiong/hermes_rpg')
from core.common_db import db

app = FastAPI(title="Hermes C2 Gateway Bridge - Distributed Edition")

@app.post("/spawn")
async def spawn_player(request: Dict[str, Any]):
    entity_id = request.get("entity_id")
    if not entity_id:
        raise HTTPException(status_code=400, detail="entity_id is required")
        
    starting_sector = "sector_start_01"
    
    try:
        # 1. Update the entity's position to the starting sector
        db.update_entity("player", entity_id, {"position": {"sector_id": starting_sector, "x": 10, "y": 10}})
        
        # 2. Register the entity in the sector's list of residents
        sector_file = f"/home/cxiong/hermes_rpg/data/sector_{starting_sector}.json"
        
        if os.path.exists(sector_file):
            with open(sector_file, 'r') as f:
                sector_data = json.load(f)
            entities = sector_data.get("entities", [])
            if entity_id not in entities:
                entities.append(entity_id)
                sector_data["entities"] = entities
                with open(sector_file, 'w') as f:
                    json.dump(sector_data, f, indent=4)
        else:
            sector_data = {
                "sector_id": starting_sector,
                "name": "The Awakening Chamber",
                "description": "A cold, stone room dimly lit by flickering torches. The air is thick with dust.",
                "entities": [entity_id],
                "interactables": [],
                "env_effects": [],
                "exits": {"north": "sector_hallway_01"},
                "danger_level": 1
            }
            with open(sector_file, 'w') as f:
                json.dump(sector_data, f, indent=4)
                
        return {"status": "spawned", "sector": starting_sector, "narration": "You open your eyes to find yourself in the Awakening Chamber..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spawn Error: {str(e)}")
@app.get("/world/current_sector")
async def get_current_sector(user_id: str):
    entity = db.get_entity("player", user_id)
    if not entity:
        raise HTTPException(status_code=404, detail="User not found")
    
    sector_id = entity.get("position", {}).get("sector_id", "sector_start_01")
    sector_file = f"/home/cxiong/hermes_rpg/data/sector_{sector_id}.json"
    
    if not os.path.exists(sector_file):
        return {"error": "Sector not found"}
        
    with open(sector_file, 'r') as f:
        sector_data = json.load(f)
    
    return {
        "description": sector_data.get("description", "No description available."),
        "entities": sector_data.get("entities", [])
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CharacterRequest(BaseModel):
    name: str
    char_class: str
    species: str
    background: str
    weapon: str
    persona: str = "balanced"
    bond: Optional[str] = None
    secret: Optional[str] = None

class InventoryRequest(BaseModel):
    entity_id: str
    item_name: str
    weight: float = 1.0
    category: str = "items" # weapons, armor, items

class JarvisRequest(BaseModel):
    entity_id: str
    message: str

class MoveRequest(BaseModel):
    entity_id: str
    dx: int = 0
    dy: int = 0

from core.builder import CharacterBuilder
builder = CharacterBuilder()

@app.get("/health")
async def health():
    return {"status": "C2_BRIDGE_CONSULTANT_MODE_OPERATIONAL", "storage": "common_db.py"}

@app.get("/recommend/{playstyle}")
async def get_recommendation(playstyle: str):
    rec = builder.recommend_build(playstyle)
    return {
        "status": "RECOMMENDATION_GENERATED",
        "suggestion": rec["recommendation"],
        "message": rec["message"],
        "available_options": {
            "classes": list(builder.class_priorities.keys()),
            "species": ["Human", "Elf", "Dwarf", "Halfling", "Orc", "Tiefling"],
            "weapons": ["Longsword", "Warhammer", "Longbow", "Rapier", "Shortsword", "Shortbow", "Quarterstaff", "Dagger", "Mace"]
        },
        "instruction": "You can use these suggestions, or provide your own custom choices in /finalize_character"
    }

@app.post("/character/create")
async def create_character(req: CharacterRequest):
    try:
        char_data = builder.build_character(
            name=req.name,
            char_class_in=req.char_class,
            species_in=req.species,
            background_in=req.background,
            weapon_name=req.weapon,
            bond=req.bond,
            secret=req.secret
        )
        return {
            "status": "COMMAND_GENERATED",
            "commands": [
                {
                    "action": "create_entity",
                    "entity_type": "player",
                    "entity_id": char_data['entity_id'],
                    "data": char_data
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"C2_CREATION_FAILED: {str(e)}")

@app.post("/inventory/add")
async def add_item(req: InventoryRequest):
    try:
        player = db.get_entity("player", req.entity_id)
        if not player: raise HTTPException(status_code=404, detail="Player not found")
        
        loot_bag = player.get("gameplay_profile", {}).get("loot_bag", {})
        category = req.category if req.category in ["weapons", "armor", "items"] else "items"
        
        item_data = {"name": req.item_name, "weight": req.weight}
        loot_bag[category].append(item_data)
        
        strength = player.get("gameplay_profile", {}).get("ability_scores", {}).get("Strength", 10)
        status = builder.check_encumbrance(strength, loot_bag)
        
        conditions = player.get("conditions", [])
        if status == "OVERLOADED" and "Overloaded" not in conditions:
            conditions.append("Overloaded")
        elif status == "CLEAR" and "Overloaded" in conditions:
            conditions.remove("Overloaded")
            
        # Consultant Mode: Return command to Gateway
        return {
            "status": "COMMAND_GENERATED",
            "commands": [
                {
                    "action": "update_entity",
                    "entity_type": "player",
                    "entity_id": req.entity_id,
                    "data": {
                        "gameplay_profile": {**player.get("gameplay_profile", {}), "loot_bag": loot_bag},
                        "conditions": conditions
                    }
                }
            ],
            "meta": {"current_encumbrance": status, "weight": builder.calculate_current_weight(loot_bag)}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"INVENTORY_ERROR: {str(e)}")

@app.post("/inventory/remove")
async def remove_item(req: InventoryRequest):
    try:
        player = db.get_entity("player", req.entity_id)
        if not player: raise HTTPException(status_code=404, detail="Player not found")
        
        loot_bag = player.get("gameplay_profile", {}).get("loot_bag", {})
        category = req.category if req.category in ["weapons", "armor", "items"] else "items"
        
        found = False
        for i, item in enumerate(loot_bag[category]):
            if item.get("name") == req.item_name or item == req.item_name:
                loot_bag[category].pop(i)
                found = True
                break
        
        if not found: raise HTTPException(status_code=404, detail="Item not found in inventory")
        
        strength = player.get("gameplay_profile", {}).get("ability_scores", {}).get("Strength", 10)
        status = builder.check_encumbrance(strength, loot_bag)
        
        conditions = player.get("conditions", [])
        if status == "CLEAR" and "Overloaded" in conditions:
            conditions.remove("Overloaded")
            
        # Consultant Mode: Return command to Gateway
        return {
            "status": "COMMAND_GENERATED",
            "commands": [
                {
                    "action": "update_entity",
                    "entity_type": "player",
                    "entity_id": req.entity_id,
                    "data": {
                        "gameplay_profile": {**player.get("gameplay_profile", {}), "loot_bag": loot_bag},
                        "conditions": conditions
                    }
                }
            ],
            "meta": {"current_encumbrance": status}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"INVENTORY_ERROR: {str(e)}")

@app.post("/move")
async def move_player(req: MoveRequest):
    try:
        player = db.get_entity("player", req.entity_id)
        if not player: raise HTTPException(status_code=404, detail="Player not found")
        
        pos = player.get("position", {"x": 0, "y": 0, "sector_id": "start_zone"})
        new_x = max(0, min(19, pos["x"] + req.dx))
        new_y = max(0, min(19, pos["y"] + req.dy))
        
        # Basic Grid Budget Logic: If dx/dy > 0, check grid_speed
        # In a real game, this would subtract from a daily/turn budget.
        # For now, we just validate the 20x20 bounds.
        
        return {
            "status": "COMMAND_GENERATED",
            "commands": [
                {
                    "action": "update_entity",
                    "entity_type": "player",
                    "entity_id": req.entity_id,
                    "data": {
                        "position": {**pos, "x": new_x, "y": new_y}
                    }
                }
            ],
            "meta": {"new_position": {"x": new_x, "y": new_y}}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MOVEMENT_ERROR: {str(e)}")

@app.get("/status/{entity_id}")
async def get_status(entity_id: str):
    try:
        player = db.get_entity("player", entity_id)
        if not player: raise HTTPException(status_code=404, detail="Player record not found in DB")
        sector_id = player.get('position', {}).get('sector_id', 'start_zone')
        sector = db.get_entity("sector", sector_id) or {"description": "Unknown Area", "entities": []}
        return {
            "status": "C2_STATE_SYNC",
            "entity_id": entity_id,
            "vitals": player.get('vitals', {}),
            "conditions": player.get('conditions', []),
            "position": player.get('position', {}),
            "surroundings": sector,
            "full_profile": player
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"C2_STATUS_FETCH_FAILED: {str(e)}")

@app.post("/level_up")
async def level_up(req: JarvisRequest):
    try:
        player = db.get_entity("player", req.entity_id)
        if not player: raise HTTPException(status_code=404, detail="Player not found")
        new_level = player.get('level', 1) + 1
        vitals = player.get('vitals', {})
        vitals['hp_max'] = vitals.get('hp_max', 10) + 2
        
        # Consultant Mode: Return command to Gateway
        return {
            "status": "COMMAND_GENERATED",
            "commands": [
                {
                    "action": "update_entity",
                    "entity_type": "player",
                    "entity_id": req.entity_id,
                    "data": {"level": new_level, "vitals": vitals}
                }
            ],
            "meta": {"new_level": new_level, "new_hp_max": vitals['hp_max']}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PROGRESSION_FAILED: {str(e)}")

@app.post("/jarvis/ask")
async def ask_jarvis(req: JarvisRequest):
    status = await get_status(req.entity_id)
    return {"status": "READY_FOR_LLM", "context": status, "user_query": req.message}




    
@app.get("/turn/status")
async def get_turn_status():
    from services.turn_orchestrator import get_state
    state = get_state()
    return {
        "current_actor": state["turn_queue"][state["current_turn"]] if state["turn_queue"] else None,
        "queue": state["turn_queue"],
        "index": state["current_turn"],
        "status": state["combat_status"]
    }

@app.post("/action/targeted")
async def targeted_action(request: Dict[str, Any]):
    actor_id = request.get("actor_id")
    target_id = request.get("target_id")
    action_type = request.get("action")
    
    try:
        resp = httpx.post("http://localhost:9090/action", json={
            "user_id": actor_id,
            "request": f"{action_type} {target_id}"
        })
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

uvicorn.run(app, host="0.0.0.0", port=10005)
