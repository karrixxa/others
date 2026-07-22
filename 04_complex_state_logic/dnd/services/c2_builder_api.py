import asyncio
import json
import os
import math
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from uvicorn import run
from typing import Optional, Dict, Any, List

SERVICE_PORT = 9090 
PROFILES_DIR = "/home/cxiong/hermes_rpg/profiles/"

os.makedirs(PROFILES_DIR, exist_ok=True)

app = FastAPI(title="Character Agent (Identity & Asset Authority)")

class CommonDB:
    def get_entity(self, entity_id: str):
        file_path = os.path.join(PROFILES_DIR, f"profile_{entity_id}.json")
        if not os.path.exists(file_path): return None
        with open(file_path, 'r') as f: return json.load(f)
    
    def update_entity(self, entity_id: str, update_dict: Dict):
        file_path = os.path.join(PROFILES_DIR, f"profile_{entity_id}.json")
        entity = self.get_entity(entity_id)
        if not entity: return False
        
        # Support the new 'gameplay_profile' structure
        if "gameplay_profile" in entity:
            target_block = entity["gameplay_profile"]
        else:
            target_block = entity.get('character', {})

        for key, value in update_dict.items():
            if isinstance(value, dict) and key in target_block:
                if isinstance(target_block[key], dict):
                    target_block[key].update(value)
                else:
                    target_block[key] = value
            else:
                target_block[key] = value

        if "gameplay_profile" in entity:
            entity["gameplay_profile"] = target_block
        else:
            entity['character'] = target_block
            
        with open(file_path, 'w') as f: json.dump(entity, f, indent=4)
        return True

db = CommonDB()

# --- Contract Models ---
class Command(BaseModel):
    action: str
    params: Dict[str, Any]

class GatewayRequest(BaseModel):
    commands: List[Command]

class ForgeLogic:
    def generate_profile(self, name, char_class, species, background):
        clean_name = name.lower().replace(' ', '_')
        entity_id = f"ent_{clean_name}_{os.urandom(2).hex()}"
        
        # Basic Ability Scores
        scores = {"Strength": 12, "Dexterity": 14, "Constitution": 13, "Intelligence": 10, "Wisdom": 12, "Charisma": 8}
        # Add racial bonuses (simplified)
        if species == "Elf": scores["Dexterity"] += 2
        if species == "Dwarf": scores["Constitution"] += 2
        if species == "Human": 
            for s in scores: scores[s] += 1

        # Derived Stats
        proficiency_bonus = 2
        hp_max = 10 + math.floor((scores['Constitution'] - 10) / 2)
        
        # Skill mapping based on class
        class_skills = {
            "Fighter": ["Athletics", "Intimidation"],
            "Rogue": ["Stealth", "Sleight of Hand", "Acrobatics", "Deception"],
            "Wizard": ["Arcana", "History", "Investigation"],
            "Cleric": ["Medicine", "Religion", "Insight"],
            "Ranger": ["Survival", "Animal Handling", "Perception"],
            "Bard": ["Performance", "Persuasion", "Deception"]
        }
        proficient_skills = class_skills.get(char_class, ["Perception"])
        
        # Calculate all skill scores
        all_skills = {"Acrobatics": 0, "Animal Handling": 0, "Arcana": 0, "Athletics": 0, "Deception": 0, "History": 0, "Insight": 0, "Intimidation": 0, "Investigation": 0, "Medicine": 0, "Nature": 0, "Perception": 0, "Performance": 0, "Persuasion": 0, "Religion": 0, "Sleight of Hand": 0, "Stealth": 0, "Survival": 0}
        
        # Map ability scores to skills
        skill_map = {
            "Strength": ["Athletics"],
            "Dexterity": ["Acrobatics", "Sleight of Hand", "Stealth"],
            "Intelligence": ["Arcana", "History", "Investigation", "Nature", "Religion"],
            "Wisdom": ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
            "Charisma": ["Deception", "Intimidation", "Performance", "Persuasion"]
        }
        
        for stat, score in scores.items():
            mod = (score - 10) // 2
            for skill in skill_map.get(stat, []):
                bonus = proficiency_bonus if skill in proficient_skills else 0
                all_skills[skill] = mod + bonus

        profile = {
            "entity_id": entity_id,
            "identity": {
                "name": name,
                "class": char_class,
                "species": species,
                "background": background,
                "level": 1,
                "xp": 0
            },
            "gameplay_profile": {
                "proficiency_bonus": proficiency_bonus,
                "ability_scores": scores,
                "skills": all_skills,
                "proficient_skills": proficient_skills,
                "combat": {
                    "max_hp": hp_max,
                    "current_hp": hp_max,
                    "armor_class": 10 + ((scores['Dexterity'] - 10) // 2),
                    "speed": 30,
                    "initiative": (scores['Dexterity'] - 10) // 2,
                    "hit_die": "d8" if char_class == "Rogue" else "d10"
                },
                "position": {"sector_id": "start_01", "x": 10, "y": 10}
            }
        }
        return entity_id, profile

forge = ForgeLogic()

class CharacterAgent:
    async def handle_command(self, cmd: Command):
        action = cmd.action
        params = cmd.params
        
        # 1. Handle Character Creation FIRST (No entity_id exists yet)
        if action == "create_character":
            try:
                details = params.get("details", "")
                parts = details.split(",")
                if len(parts) < 4:
                    return [{"action": "notify_user", "params": {"text": "Error: Missing character details."}}]
                
                name, char_class, species, background = [p.strip() for p in parts]
                ent_id, profile = forge.generate_profile(name, char_class, species, background)
                
                file_path = os.path.join(PROFILES_DIR, f"profile_{ent_id}.json")
                with open(file_path, 'w') as f: 
                    json.dump(profile, f, indent=4)
                
                return [
                    {"action": "notify_user", "params": {"text": f"Identity established. Welcome, {name}. Your record is now committed as {ent_id}."}},
                    {"action": "set_active_entity", "params": {"entity_id": ent_id}}
                ]
            except Exception as e:
                return [{"action": "notify_user", "params": {"text": f"Forge Error: {str(e)}"}}]

        # 2. Now check for entity_id for all other actions
        entity_id = params.get("entity_id")
        if not entity_id:
            return [{"action": "notify_user", "params": {"text": "Error: No entity_id provided."}}]

        # 3. Handle Asset/Stat Requests
        entity = db.get_entity(entity_id)
        if not entity:
            return [{"action": "notify_user", "params": {"text": "Entity not found in archives."}}]

        if action == "use_item":
            item_id = params.get("item_id")
            inventory = entity['character'].get('inventory', {}).get('items', [])
            
            if item_id not in inventory:
                return [{"action": "notify_user", "params": {"text": f"You do not possess {item_id}."}}]
            
            if "healing_potion" in item_id:
                vitals = entity['character']['vitals']
                current_hp = vitals['hp_current']
                max_hp = vitals['hp_max']
                new_hp = min(current_hp + 10, max_hp)
                inventory.remove(item_id)
                
                return [
                    {"action": "update_entity", "params": {
                        "entity_id": entity_id, 
                        "data": {"vitals": {"hp_current": new_hp}, "inventory": {"items": inventory}}
                    }},
                    {"action": "notify_user", "params": {"text": "You drink the potion. You feel a surge of warmth as your wounds close."}}
                ]

        if action == "update_stat":
            stat_name = params.get("stat")
            new_value = params.get("value")
            return [
                {"action": "update_entity", "params": {
                    "entity_id": entity_id, 
                    "data": {"stats": {stat_name: new_value}}
                }},
                {"action": "notify_user", "params": {"text": f"Stat {stat_name} updated to {new_value}."}}
            ]

        return [{"action": "notify_user", "params": {"text": f"Action {action} not recognized by Character Agent."}}]


agent = CharacterAgent()

@app.post("/finalize_character")
async def finalize_character(request: Request):
    try:
        data = await request.json()
        name = data.get("name")
        char_class = data.get("class")
        species = data.get("species")
        background = data.get("background")
        
        if not all([name, char_class, species, background]):
            raise HTTPException(status_code=400, detail="Missing required character details")
            
        ent_id, profile = forge.generate_profile(name, char_class, species, background)
        
        file_path = os.path.join(PROFILES_DIR, f"profile_{ent_id}.json")
        with open(file_path, 'w') as f:
            json.dump(profile, f, indent=4)
        
        # Bridge to Shared DB so Gateway can see it
        import sys
        sys.path.append('/home/cxiong/hermes_rpg')
        from core.common_db import db
        db.update_entity("player", ent_id, profile)
        
        return {"entity_id": ent_id, "status": "Identity Established"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    return {"status": "online", "version": "1.0.0", "agent_type": "CHARACTER"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
