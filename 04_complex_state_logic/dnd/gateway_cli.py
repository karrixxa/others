import os
import json
import requests
import sys
from common_db import db

class UnifiedGateway:
    def __init__(self):
        self.current_entity_id = None
        self.current_profile = None
        
        # Distributed Endpoints per Manual v1.0
        self.gateway_url = "http://localhost:10001"
        self.identity_url = "http://localhost:9090"
        
        self.options = {
            "classes": {
                "1": {"name": "Fighter", "desc": "A master of martial combat, skilled with every weapon and armor, serving as the unbreakable shield of the party."},
                "2": {"name": "Rogue", "desc": "A specialist in stealth, precision, and subterfuge, striking from the shadows with lethal efficiency."},
                "3": {"name": "Wizard", "desc": "A scholarly seeker of arcane knowledge, weaving complex spells to reshape reality and devastate foes."},
                "4": {"name": "Cleric", "desc": "A divine conduit of a deity's power, capable of healing the wounded and smiting the wicked with holy light."},
                "5": {"name": "Ranger", "desc": "A warden of the wild, blending martial prowess with primal magic to track and eliminate the most dangerous prey."},
                "6": {"name": "Bard", "desc": "A virtuoso of music and magic, using art to inspire allies, manipulate minds, and weave stories into power."}
            },
            "species": {
                "1": {"name": "Human", "desc": "Versatile and ambitious, humans are the most adaptable of the races, capable of excelling in any calling."},
                "2": {"name": "Elf", "desc": "Graceful and long-lived, elves possess a natural affinity for magic and an acute sense of the world around them."},
                "3": {"name": "Dwarf", "desc": "Stout, hardy, and stubborn, dwarves are masters of stone and metal, built for endurance and frontline combat."},
                "4": {"name": "Tiefling", "desc": "Tainted by infernal bloodlines, tieflings are often misunderstood outcasts with a natural talent for fire and manipulation."},
                "5": {"name": "Orc", "desc": "Powerful and relentless, orcs are born for battle, possessing a raw strength that can overwhelm any foe."},
                "6": {"name": "Halfling", "desc": "Small in stature but big in spirit, halflings are nimble, lucky, and often underestimated by their enemies."}
            },
            "backgrounds": {
                "1": {"name": "Soldier", "desc": "A veteran of a professional army, disciplined and accustomed to the hardships of the front line."},
                "2": {"name": "Acolyte", "desc": "A devoted servant of a temple, steeped in religious lore and divine tradition."},
                "3": {"name": "Criminal", "desc": "A former member of a guild or gang, skilled in the arts of theft and deception."},
                "4": {"name": "Sage", "desc": "A lifelong scholar who has spent more time in libraries than in the open world."},
                "5": {"name": "Noble", "desc": "Born into a family of wealth and influence, accustomed to command and luxury."},
                "6": {"name": "Outlander", "desc": "A survivor of the wild places, far from the constraints of civilization."}
            }
        }
        
        self.species_recs = {
            "Fighter": ("Dwarf", "Stout and hardy, perfect for the frontline."),
            "Rogue": ("Elf", "Graceful and agile, ideal for subterfuge."),
            "Wizard": ("Human", "Versatile and ambitious, a classic seeker of lore."),
            "Cleric": ("Dwarf", "Deeply devoted and resilient."),
            "Ranger": ("Elf", "Natural affinity for the wild and the bow."),
            "Bard": ("Halfling", "Nimble and charismatic, the heart of the party.")
        }
        
        self.bg_recs = {
            "Fighter": ("Soldier", "A disciplined veteran of a hundred battles."),
            "Rogue": ("Criminal", "A life of theft and shadows prepares one well."),
            "Wizard": ("Sage", "Years of study in ancient libraries."),
            "Cleric": ("Acolyte", "Raised in the halls of a Great Temple."),
            "Ranger": ("Outlander", "At home only in the untamed wild."),
            "Bard": ("Noble", "A refined upbringing with an ear for music.")
        }

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_jarvis_header(self):
        print("\n" + "═"*60)
        if not self.current_profile:
            print(" 🤖 JARVIS | SYSTEM STANDBY (Authority Mode)")
        else:
            name = "Unknown"
            if "identity" in self.current_profile:
                name = self.current_profile["identity"].get("name", "Unknown")
            elif "character" in self.current_profile:
                name = self.current_profile["character"].get("name", "Unknown")
            print(f" 🤖 JARVIS | ACTIVE: {name} [{self.current_entity_id}]")
        print("═"*60)

    def resolve_choice(self, prompt, mapping):
        while True:
            choice = input(f"{prompt}\n> ").strip().lower()
            if not choice: continue
            if choice in mapping: return mapping[choice]["name"]
            for key, val in mapping.items():
                if val["name"].lower() == choice: return val["name"]
            print("That is not a valid option. Please try again.")

    def render_character_sheet(self):
        if not self.current_profile: return
        profile = self.current_profile
        
        if "identity" in profile:
            ident = profile["identity"]
            name, char_class, species, bg = ident.get("name", "U"), ident.get("class", "U"), ident.get("species", "U"), ident.get("background", "U")
        elif "character" in profile:
            char = profile["character"]
            name, char_class, species, bg = char.get("name", "U"), char.get("class", "U"), char.get("species", "U"), char.get("background", "U")
        else:
            name = char_class = species = bg = "Unknown"

        stats = profile.get("gameplay_profile", {}).get("ability_scores", profile.get("character", {}).get("stats", {}))
        
        combat = profile.get("gameplay_profile", {}).get("combat", {})
        vitals = {
            "hp_max": combat.get("max_hp", profile.get("character", {}).get("vitals", {}).get("hp_max", 0)),
            "hp_current": combat.get("current_hp", profile.get("character", {}).get("vitals", {}).get("hp_current", 0)),
            "ac": combat.get("armor_class", profile.get("character", {}).get("vitals", {}).get("ac", 10))
        }

        skills = profile.get("gameplay_profile", {}).get("skills", profile.get("character", {}).get("skills", {}))

        def get_mod(score): 
            try: return (int(score) - 10) // 2
            except: return 0

        print("\n" + "="*40)
        print("🛡️  HERMES UNIFIED CHARACTER SHEET")
        print("="*40)
        print(f"NAME:        {name:<15} CLASS:      {char_class}")
        print(f"SPECIES:    {species:<15} BACKGROUND: {bg}")
        print(f"ENTITY ID:  {self.current_entity_id}")
        print("="*40)
        print("\n📊 ABILITY SCORES")
        print(f"{'Stat':<15} Score   Mod")
        for stat, score in stats.items():
            print(f"{stat:<15} {score:<7} {get_mod(score)}")
        
        if skills:
            print("\n🎯 SKILL PROFICIENCIES")
            print(f"{'Skill':<15} Bonus")
            for skill, bonus in skills.items():
                print(f"{skill:<15} {bonus}")

        print("\n" + "="*40)
        print("⚔️  COMBAT STATS")
        print("="*40)
        print(f"Max HP:           {vitals['hp_max']}")
        print(f"Current HP:       {vitals['hp_current']}")
        print(f"Armor Class:      {vitals['ac']}")
        print("="*40 + "\n")

    def handle_creation(self):
        self.clear_screen()
        self.print_jarvis_header()
        name = input("\nJarvis: And how shall the world know you? (Enter Name): ").strip()
        while not name:
            name = input("A name is required. Please enter your name: ").strip()

        print("\nJarvis: Let us begin with your calling. Please choose your Class:")
        for i, val in self.options['classes'].items():
            print(f"{i}. {val['name']:<10} | {val['desc']}")
        selected_class = self.resolve_choice("Select Class (Number or Name):", self.options['classes'])

        rec_species, rec_reason = self.species_recs.get(selected_class, ("Human", "A versatile choice"))
        print(f"\nJarvis: A {selected_class}, quite bold. Based on this, I recommend the {rec_species} species.")
        print(f"Reasoning: {rec_reason}")
        confirm_species = input(f"Shall we proceed with {rec_species}? (yes/no): ").lower()
        selected_species = rec_species if confirm_species == 'yes' else self.resolve_choice("\nJarvis: Very well. Choose Species:", self.options['species'])

        rec_bg, rec_bg_reason = self.bg_recs.get(selected_class, ("Outlander", "A survivor of the wild."))
        print(f"\nJarvis: And your background? I suggest the {rec_bg} path. {rec_bg_reason}")
        confirm_bg = input(f"Proceed with {rec_bg}? (yes/no): ").lower()
        selected_background = rec_bg if confirm_bg == 'yes' else self.resolve_choice("\nJarvis: Very well. Choose Background:", self.options['backgrounds'])

        try:
            print("\nJarvis: Finalizing your identity in the archives...")
            payload = {"name": name, "class": selected_class, "species": selected_species, "background": selected_background}
            res = requests.post(f"{self.identity_url}/finalize_character", json=payload).json()
            
            entity_id = res.get("entity_id")
            if not entity_id:
                print("❌ Identity Manager failed to return an Entity ID.")
                return

            self.current_entity_id = entity_id
            print(f"Jarvis: Identity established. You are now registered as {entity_id}.")

            print("Jarvis: Synchronizing with the world sector...")
            sector_res = requests.get(f"{self.gateway_url}/world/current_sector", params={"user_id": entity_id}).json()
            
            if "description" in sector_res:
                print(f"\\n📍 SPAWN SUCCESSFUL: {sector_res['description']}")
            else:
                print("\\n⚠️ Spawned, but sector data is still stabilizing.")
            
            self.load_character(entity_id)
            self.render_character_sheet()

        except Exception as e:
            print(f"\n\n❌ Distributed Birth Loop Failed: {e}")

    def load_character(self, entity_id):
        try:
            profile_path = f"/home/cxiong/hermes_rpg/profiles/profile_{entity_id}.json"
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    self.current_profile = json.load(f)
                self.current_entity_id = entity_id
                return True
        except Exception as e:
            print(f"Load failed: {e}")
        return False

    def get_party_briefing(self):
        if not self.current_entity_id: return "No active entity to track party for, sir."
        try:
            party_data = [
                {"name": "Kaelen", "role": "Tank", "hp": "45/50", "status": "Optimal", "dist": "5ft"},
                {"name": "Mira", "role": "Healer", "hp": "12/30", "status": "CRITICAL", "dist": "12ft"},
                {"name": "Thorne", "role": "DPS", "hp": "28/35", "status": "Wounded", "dist": "8ft"},
            ]
            briefing = "\\n--- 👥 PARTY TACTICAL OVERVIEW ---\\n"
            alerts = [m['name'] for m in party_data if m['status'] == "CRITICAL"]
            for m in party_data:
                briefing += f"{m['name']} ({m['role']}): {m['hp']} | {m['status']} | Dist: {m['dist']}\\n"
            briefing += f"\\n⚠️ WARNING: {', '.join(alerts)} is critical!" if alerts else "\\n✅ Party stable."
            return briefing
        except Exception as e:
            return f"Sensors offline: {e}"

    def get_sector_info(self):
        if not self.current_entity_id: return "Sir, you are not yet in the world."
        try:
            res = requests.get(f"{self.gateway_url}/world/current_sector", params={"user_id": self.current_entity_id}).json()
            return f"\\n📍 CURRENT SECTOR:\\n{res.get('description', 'No description available.')}\\nResidents: {', '.join(res.get('entities', []))}"
        except Exception as e:
            return f"World synchronization failed: {e}"

    def move_player(self, direction):
        if not self.current_entity_id: return "You cannot move without an identity, sir."
        dirs = {"n": (0, 1), "s": (0, -1), "e": (1, 0), "w": (-1, 0)}
        if direction not in dirs: return "Invalid direction. Please use N, S, E, or W."
        
        dx, dy = dirs[direction]
        try:
            res = requests.post(f"{self.gateway_url}/move", json={"user_id": self.current_entity_id, "dx": dx, "dy": dy}).json()
            return f"Jarvis: Moving {direction.upper()}... {res.get('message', 'Position updated.')}"
        except Exception as e:
            return f"Movement failed: {e}"

    def targeted_action(self, target_id, action):
        if not self.current_entity_id: return "Identity required for actions, sir."
        try:
            payload = {"actor_id": self.current_entity_id, "target_id": target_id, "action": action}
            res = requests.post(f"{self.gateway_url}/action/targeted", json=payload).json()
            return f"Jarvis: Executing {action} on {target_id}... {res.get('result', 'Action processed.')}"
        except Exception as e:
            return f"Action failed: {e}"

    def check_turn(self):
        if not self.current_entity_id: return "Identity required to check turns, sir."
        try:
            res = requests.get(f"{self.gateway_url}/turn/status", params={"user_id": self.current_entity_id}).json()
            status = res.get("status", "Waiting")
            return f"Jarvis: Your turn status is currently: {status}"
        except Exception as e:
            return f"Turn sync failed: {e}"

    def game_loop(self):
        self.clear_screen()
        while True:
            self.print_jarvis_header()
            if not self.current_profile:
                print("\\nCommands:\\n  /create\\n  /load [id]\\n  /exit")
            else:
                name = self.current_profile.get("identity", {}).get("name", "Unknown")
                print(f"\\nActive: {name}")
                print("Commands:\\n  /stats    - Show Sheet\\n  /sector   - View Room\\n  /move [dir] - N,S,E,W\\n  /action [id] [act] - Target action\\n  /turn     - Sync Turn\\n  /party    - Tactical Briefing\\n  /exit     - Quit")

            cmd_input = input("\\n> ").strip()
            if not cmd_input: continue
            parts = cmd_input.split()
            cmd = parts[0].lower()
            
            if cmd == '/exit': break
            elif cmd == '/create': self.handle_creation()
            elif cmd == '/load' and len(parts) > 1:
                if self.load_character(parts[1]): print(f"\\n\\n✅ {parts[1]} loaded.")
                else: print("❌ Not found.")
            elif cmd == '/stats': self.render_character_sheet()
            elif cmd == '/sector': print(self.get_sector_info())
            elif cmd == '/move' and len(parts) > 1: print(self.move_player(parts[1].lower()))
            elif cmd == '/action' and len(parts) > 2: print(self.targeted_action(parts[1], parts[2]))
            elif cmd == '/turn': print(self.check_turn())
            elif cmd == '/party':
                if self.current_profile: print(f"\\n{self.get_party_briefing()}")
                else: print("\\nJarvis: Identity required for party monitoring, sir.")
            else:
                print("\\nJarvis: That command is not currently mapped.")

if __name__ == "__main__":
    gateway = UnifiedGateway()
    gateway.game_loop()
