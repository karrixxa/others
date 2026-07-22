
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import random

app = FastAPI(title="Hermes Character Generator Agent")

# --- DATABASE (Simplified D&D 2024) ---
OPTIONS = {
    "stat_array": [15, 14, 13, 12, 10, 8],
    "species": {
        "Human": {"trait": "Extra Skill", "speed": 30},
        "Elf": {"trait": "Darkvision", "speed": 30},
        "Dwarf": {"trait": "Poison Resistance", "speed": 25},
        "Halfling": {"trait": "Lucky", "speed": 25},
        "Orc": {"trait": "Endurance", "speed": 30},
        "Tiefling": {"trait": "Fire Resistance", "speed": 30}
    },
    "classes": {
        "Fighter": {"primary": "Strength", "priority": ["Strength", "Constitution", "Dexterity", "Wisdom", "Charisma", "Intelligence"], "hit_die": 10, "base_ac": 15, "feature": "Second Wind"},
        "Rogue": {"primary": "Dexterity", "priority": ["Dexterity", "Constitution", "Charisma", "Wisdom", "Intelligence", "Strength"], "hit_die": 8, "base_ac": 14, "feature": "Sneak Attack"},
        "Wizard": {"primary": "Intelligence", "priority": ["Intelligence", "Constitution", "Dexterity", "Wisdom", "Charisma", "Strength"], "hit_die": 6, "base_ac": 11, "feature": "Spellcasting"},
        "Cleric": {"primary": "Wisdom", "priority": ["Wisdom", "Constitution", "Strength", "Charisma", "Dexterity", "Intelligence"], "hit_die": 8, "base_ac": 13, "feature": "Healing Word"},
        "Ranger": {"primary": "Dexterity", "priority": ["Dexterity", "Wisdom", "Constitution", "Strength", "Intelligence", "Charisma"], "hit_die": 10, "base_ac": 14, "feature": "Hunter's Mark"},
        "Bard": {"primary": "Charisma", "priority": ["Charisma", "Dexterity", "Constitution", "Wisdom", "Intelligence", "Strength"], "hit_die": 8, "base_ac": 13, "feature": "Bardic Inspiration"}
    },
    "backgrounds": {
        "Criminal": {"skill": "Stealth", "theme": "Underworld"},
        "Noble": {"skill": "Persuasion", "theme": "High Society"},
        "Acolyte": {"skill": "Medicine", "theme": "Temple"},
        "Soldier": {"skill": "Athletics", "theme": "Military"},
        "Scholar": {"skill": "Arcana", "theme": "Academic"}
    }
}

# --- MODELS ---
class BuildRequest(BaseModel):
    user_id: str
    playstyle: str # "strong", "sneaky", "magic", "support", "ranged", "social"

class FinalizeRequest(BaseModel):
    user_id: str
    name: str
    species: str
    char_class: str
    background: str
    personality: str
    backstory: str

# --- LOGIC ---
def calculate_stats(char_class):
    priority = OPTIONS["classes"][char_class]["priority"]
    array = OPTIONS["stat_array"]
    stats = {}
    for stat, score in zip(priority, array):
        stats[stat] = score
    return stats

def get_modifier(score):
    return (score - 10) // 2

@app.get("/")
async def root():
    return {"message": "Character Generator Agent is Online"}

@app.post("/recommend")
async def recommend(req: BuildRequest):
    # Mapping playstyle to a suggested build
    mapping = {
        "strong": {"class": "Fighter", "species": "Orc", "bg": "Soldier", "reason": "High strength and endurance for frontline combat."},
        "sneaky": {"class": "Rogue", "species": "Elf", "bg": "Criminal", "reason": "High dexterity and stealth for infiltration."},
        "magic": {"class": "Wizard", "species": "Human", "bg": "Scholar", "reason": "Max intelligence for powerful spellcasting."},
        "support": {"class": "Cleric", "species": "Dwarf", "bg": "Acolyte", "reason": "High wisdom and toughness for healing."},
        "ranged": {"class": "Ranger", "species": "Elf", "bg": "Outlander", "reason": "High dex and survival skills for distance fighting."},
        "social": {"class": "Bard", "species": "Tiefling", "bg": "Noble", "reason": "High charisma for manipulation and performance."}
    }
    
    rec = mapping.get(req.playstyle.lower(), mapping["strong"])
    return {
        "status": "success",
        "data": {
            "recommendation": rec,
            "options": {
                "classes": list(OPTIONS["classes"].keys()),
                "species": list(OPTIONS["species"].keys()),
                "backgrounds": list(OPTIONS["backgrounds"].keys())
            }
        }
    }

@app.post("/finalize")
async def finalize(req: FinalizeRequest):
    if req.char_class not in OPTIONS["classes"]:
        raise HTTPException(status_code=400, detail="Invalid Class")
    
    stats = calculate_stats(req.char_class)
    modifiers = {k: get_modifier(v) for k, v in stats.items()}
    
    identity = {
        "name": req.name, "species": req.species, "class": req.char_class,
        "background": req.background, "personality": req.personality, "backstory": req.backstory
    }
    
    gameplay = {
        "stats": stats,
        "modifiers": modifiers,
        "hp": OPTIONS["classes"][req.char_class]["hit_die"] + modifiers["Constitution"],
        "ac": OPTIONS["classes"][req.char_class]["base_ac"],
        "feature": OPTIONS["classes"][req.char_class]["feature"],
        "starting_equipment": OPTIONS["classes"][req.char_class]["starting_equipment"]
    }
    
    return {
        "status": "success",
        "data": {
            "identity": identity,
            "gameplay": gameplay
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
