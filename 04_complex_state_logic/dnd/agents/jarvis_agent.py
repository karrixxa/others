import json
from functools import lru_cache
from typing import Dict, Any, Tuple

class JarvisAgent:
    """
    The Courier / Tactical Layer.
    Stateless design: All state is passed in per request.
    LRU Cached: Static rule lookups are cached for performance.
    """
    def __init__(self):
        self.persona = "Tactical Combat AI"
        self.assets_path = "/home/cxiong/hermes_rpg/assets.json"

    @lru_cache(maxsize=128)
    def explain_stat(self, stat_name: str, value: Any) -> str:
        """
        Explains a D&D rule in the context of the player's actual number.
        Cached because rule definitions for a specific value are static.
        """
        explanations = {
            "Passive Perception": f"Your Passive Perception is {value}. This is the score the DM uses to see if you notice things without actively looking. You are reasonably observant.",
            "Armor Class": f"Your AC is {value}. Enemies must roll this number or higher to hit you.",
            "Initiative": f"Your Initiative mod is {value}. This determines how fast you react at the start of combat."
        }
        return explanations.get(stat_name, "This is a standard D&D 5e attribute.")

    def suggest_action(self, character: Dict, state: Dict) -> Dict:
        """
        Stateless analysis of the character's current state.
        """
        gp = character.get('gameplay_profile', {})
        combat = gp.get('combat', {})
        hp_max = combat.get('max_hp', 10)
        hp_cur = state.get('current_hp', hp_max)
        hp_pct = (hp_cur / hp_max) * 100
        
        # Tactical Logic
        if hp_pct < 30:
            advice = "CRITICAL: Health is dangerously low. Prioritize healing or retreat to cover immediately."
            priority = "HIGH"
        elif state.get('action_economy', {}).get('action_used'):
            advice = "Action used. Consider using a Bonus Action or repositioning."
            priority = "NORMAL"
        else:
            attacks = gp.get('attacks', []) # Assuming attacks list in profile
            weapon = attacks[0]['name'] if attacks else "Unarmed"
            advice = f"State Stable. Recommend engaging with {weapon} to maintain pressure."
            priority = "NORMAL"

        return {
            "tactical_advice": advice,
            "priority": priority,
            "context": f"HP at {hp_pct:.1f}%"
        }

    def verify_with_arbiter(self, suggested_advice: str, character: Dict, state: Dict) -> Tuple[bool, str]:
        """
        The Arbiter Check.
        Verifies if the tactical advice is actually legal based on the character's resources.
        """
        # Logic: If advice mentions a weapon/action, check if it exists in character profile
        # Example: "Recommend engaging with Longsword" -> check if 'Longsword' is equipped.
        
        gp = character.get('gameplay_profile', {})
        # Simple keyword verification as a placeholder for the Arbiter logic
        # In a full impl, this would parse the 'suggested_advice' for specific keywords
        
        # Example: If advice mentions "healing" but character has no healing spells/potions
        if "healing" in suggested_advice.lower():
            has_healing = any("healing" in s.lower() for s in gp.get('prepared_spells', []))
            if not has_healing:
                return False, "Character has no healing capabilities available."

        return True, "Action is legal."

    def deliver_response(self, gateway_response: str, character: Dict, state: Dict) -> Dict:
        """
        The Courier Pipeline:
        Gateway -> Courier (Jarvis) -> Arbiter Check -> User/Retry
        """
        is_legal, reason = self.verify_with_arbiter(gateway_response, character, state)
        
        # Extract the profile image from the character's visual_profile
        visual_profile = character.get('visual_profile', {})
        profile_img = visual_profile.get('profile_image', 'images/default.png')

        if not is_legal:
            return {
                "status": "RETRY",
                "error": f"Arbiter Block: {reason}",
                "instruction": "Hermes, please suggest a different tactical response that is legal for this character.",
                "profile_image": profile_img
            }
        
        return {
            "status": "SUCCESS",
            "response": gateway_response,
            "profile_image": profile_img
        }

    def get_visual_manifest(self, character: Dict) -> Dict:
        """
        Translates the character's identity and equipment into a visual asset manifest
        for the game engine's renderer.
        """
        with open(self.assets_path, 'r') as f:
            assets = json.load(f)
        
        identity = character.get('identity', {})
        species = identity.get('species', 'Human')
        char_class = identity.get('class', 'Fighter')
        
        gp = character.get('gameplay_profile', {})
        # Find the currently equipped armor
        # In our builder.py, armor is often stored in the class config or inventory
        # For this implementation, we'll look for a 'equipped_armor' key in the character root or gp
        equipped_armor = character.get('equipped_armor') or gp.get('combat', {}).get('armor_name', 'none')
        
        # Find equipped weapon (usually first attack)
        attacks = gp.get('attacks', [])
        equipped_weapon = attacks[0]['name'] if attacks else "Unarmed"
        
        manifest = {
            "base_model": assets['species'].get(species, assets['species']['Human'])['base_model'],
            "outfit_model": assets['classes'].get(char_class, assets['classes']['Fighter'])['default_outfit'],
            "animation_set": assets['classes'].get(char_class, assets['classes']['Fighter'])['idle_animation'],
            "equipment_slots": {
                "torso": assets['equipment'].get(equipped_armor.lower(), assets['equipment']['none'])['asset_path'],
                "mainhand": assets['weapons'].get(equipped_weapon, "assets/models/weapons/unarmed.fbx")
            }
        }
        return manifest
