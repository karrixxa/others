
import json
import http.server
import socketserver
from datetime import datetime

PORT = 8005

# --- DATABASE (Simplified D&D 2024) ---
OPTIONS = {
    "stat_array": [15, 14, 13, 12, 10, 8],
    "species": {
        "Human": {"trait": "Extra Skill", "speed": 30, "description": "Flexible and adaptable."},
        "Elf": {"trait": "Darkvision", "speed": 30, "description": "Graceful and perceptive."},
        "Dwarf": {"trait": "Poison Resistance", "speed": 25, "description": "Tough and durable."},
        "Halfling": {"trait": "Lucky", "speed": 25, "description": "Small and quick."},
        "Orc": {"trait": "Endurance", "speed": 30, "description": "Strong and hardy."},
        "Tiefling": {"trait": "Fire Resistance", "speed": 30, "description": "Mysterious and charismatic."}
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

class CharacterGeneratorHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self._set_headers()
            self.wfile.write(json.dumps({"message": "Character Generator Agent (Pure Python) is Online"}).encode())
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"status": "error", "message": "Not Found"}).encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = json.loads(self.rfile.read(content_length))
        
        if self.path == "/recommend":
            playstyle = post_data.get("context", {}).get("playstyle", "strong").lower()
            mapping = {
                "strong": {"class": "Fighter", "species": "Orc", "bg": "Soldier", "reason": "High strength and endurance for frontline combat."},
                "sneaky": {"class": "Rogue", "species": "Elf", "bg": "Criminal", "reason": "High dexterity and stealth for infiltration."},
                "magic": {"class": "Wizard", "species": "Human", "bg": "Scholar", "reason": "Max intelligence for powerful spellcasting."},
                "support": {"class": "Cleric", "species": "Dwarf", "bg": "Acolyte", "reason": "High wisdom and toughness for healing."},
                "ranged": {"class": "Ranger", "species": "Elf", "bg": "Outlander", "reason": "High dex and survival skills for distance fighting."},
                "social": {"class": "Bard", "species": "Tiefling", "bg": "Noble", "reason": "High charisma for manipulation and performance."}
            }
            rec = mapping.get(playstyle, mapping["strong"])
            self._set_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "data": {
                    "recommendation": rec,
                    "options": {
                        "classes": list(OPTIONS["classes"].keys()),
                        "species": list(OPTIONS["species"].keys()),
                        "backgrounds": list(OPTIONS["backgrounds"].keys())
                    }
                }
            }).encode())

        elif self.path == "/finalize":
            try:
                name = post_data.get("context", {}).get("name", "Unknown")
                species = post_data.get("context", {}).get("species", "Human")
                char_class = post_data.get("context", {}).get("char_class", "Fighter")
                background = post_data.get("context", {}).get("background", "Noble")
                
                # Stat Calculation
                priority = OPTIONS["classes"][char_class]["priority"]
                array = OPTIONS["stat_array"]
                stats = {stat: score for stat, score in zip(priority, array)}
                modifiers = {k: (v - 10)//2 for k, v in stats.items()}
                
                identity = {
                    "name": name, "species": species, "class": char_class,
                    "background": background,
                    "personality": post_data.get("context", {}).get("personality", "Neutral"),
                    "backstory": post_data.get("context", {}).get("backstory", "")
                }
                
                gameplay = {
                    "stats": stats,
                    "modifiers": modifiers,
                    "hp": OPTIONS["classes"][char_class]["hit_die"] + modifiers["Constitution"],
                    "ac": OPTIONS["classes"][char_class]["base_ac"],
                    "feature": OPTIONS["classes"][char_class]["feature"],
                    "starting_equipment": OPTIONS["classes"][char_class]["starting_equipment"]
                }
                
                self._set_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "data": {"identity": identity, "gameplay": gameplay}
                }).encode())
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"status": "error", "message": "Endpoint not found"}).encode())

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), CharacterGeneratorHandler) as httpd:
        print(f"Pure Python Character Generator running on port {PORT}")
        httpd.serve_forever()
