import asyncio
import websockets
import json
import uuid
import os
import math
from difflib import get_close_matches

# --- CONFIGURATION ---
GATEWAY_WS_URL = "ws://localhost:10001/ws"
OPTIONS_PATH = "/home/cxiong/hermes_rpg/character_options.json"
# Mandatory path for prodrig integration
PROFILES_DIR = "/home/prodrig/Documents/DND_Project/data/profiles/"

class C2BuilderService:
    def __init__(self):
        with open(OPTIONS_PATH, 'r') as f:
            self.options = json.load(f)

    def generate_profile(self, data):
        """Generates a profile following the C2_ENTITY_SCHEMA.md"""
        name = data.get('name', 'Unknown')
        char_class = data.get('char_class', 'Fighter')
        persona_type = data.get('persona', 'Balanced') # Aggressive/Defensive/Balanced
        
        # Basic IDs
        entity_id = f"ent_{uuid.uuid4().hex[:8]}"
        char_id = f"char_{name.replace(' ','_').lower()}_{uuid.uuid4().hex[:4]}"
        
        # 1. Stat Calculation (Matching the Builder Logic)
        # Fallback to Fighter if class not found
        class_data = self.options['classes'].get(char_class, self.options['classes']['Fighter'])
        priority = class_data['stat_priority']
        stat_array = sorted(self.options['stat_array'], reverse=True)
        scores = {s: stat_array[i] for i, s in enumerate(priority)}
        
        # 2. Derived Stats (5e rules)
        hit_die = class_data.get('hit_die', 8)
        max_hp = hit_die + math.floor((scores['Constitution'] - 10) / 2)
        
        # 3. Persona Weights
        style_weights = {
            "Aggressive": {"aggression": 0.9, "caution": 0.1, "support": 0.3, "social": 0.2},
            "Defensive":  {"aggression": 0.2, "caution": 0.9, "support": 0.4, "social": 0.3},
            "Balanced":   {"aggression": 0.5, "caution": 0.5, "support": 0.5, "social": 0.5},
        }.get(persona_type, {"aggression": 0.5, "caution": 0.5, "support": 0.5, "social": 0.5})

        # Construct Final C2 JSON Profile
        profile = {
            "entity_id": entity_id,
            "character": {
                "id": char_id,
                "name": name,
                "class": char_class,
                "stats": scores,
                "hp": max_hp,
                "ac": 10 + ((scores['Dexterity'] - 10) // 2) # Basic 5e AC
            },
            "agent": {
                "id": f"jarvis_{char_id}",
                "persona": persona_type,
                "weights": style_weights
            },
            "metadata": {
                "version": "1.0",
                "created_at": uuid.uuid4().hex # placeholder timestamp
            }
        }
        return entity_id, profile

    async def handler(self):
        print(f"🚀 C2 Builder Service connecting to {GATEWAY_WS_URL}...")
        try:
            async with websockets.connect(GATEWAY_WS_URL) as websocket:
                print("✅ Connected to Gateway. Listening for FINALIZE_CHARACTER triggers...")
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    if data.get("type") == "FINALIZE_CHARACTER":
                        payload = data.get("payload", {})
                        print(f"🛠 Received request to build character: {payload.get('name')}")
                        
                        entity_id, profile = self.generate_profile(payload)
                        
                        # Storage: Mandatory path for prodrig
                        file_path = os.path.join(PROFILES_DIR, f"profile_{entity_id}.json")
                        try:
                            os.makedirs(PROFILES_DIR, exist_ok=True)
                            with open(file_path, 'w') as f:
                                json.dump(profile, f, indent=4)
                            
                            print(f"💾 Profile saved to {file_path}")
                            
                            # Notify Gateway of success
                            await websocket.send(json.dumps({
                                "type": "CHARACTER_CREATED",
                                "entity_id": entity_id,
                                "status": "success",
                                "path": file_path
                            }))
                        except Exception as e:
                            print(f"❌ File error: {e}")
                            await websocket.send(json.dumps({"type": "ERROR", "message": str(e)}))

        except Exception as e:
            print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    service = C2BuilderService()
    asyncio.run(service.handler())
