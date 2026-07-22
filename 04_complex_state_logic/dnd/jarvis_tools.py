import json
import os
import requests

# ==================================================================
# JARVIS RPG TOOLS
# ==================================================================
# These tools provide the "hands" for the Jarvis Agent to interact 
# with the RPG Game Engine and the Rules Registry.

class JarvisTools:
    def __init__(self, gateway_url, api_key, entity_id):
        self.gateway_url = gateway_url
        self.api_key = api_key
        self.entity_id = entity_id
        self.rules_path = '/home/cxiong/hermes_rpg/character_options.json'

    def get_live_state(self):
        """Polls the Game Engine for the current volatile state of the entity."""
        try:
            # In a real deploy, this is an HTTP call. 
            # For now, we read the state JSON as the 'source of truth'
            state_path = f"/home/cxiong/hermes_rpg/states/{self.entity_id.replace('ent_', 'char_')}_state.json"
            if os.path.exists(state_path):
                with open(state_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            return {"error": f"Failed to fetch state: {str(e)}"}
        return {"error": "State file not found."}

    def get_character_profile(self):
        """Reads the static character profile (Identity, Abilities, Roleplay)."""
        try:
            char_path = f"/home/cxiong/hermes_rpg/characters/{self.entity_id.replace('ent_', 'char_')}.json"
            if os.path.exists(char_path):
                with open(char_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            return {"error": f"Failed to fetch profile: {str(e)}"}
        return {"error": "Profile file not found."}

    def query_rules(self, category=None):
        """Queries the character_options.json rules registry."""
        try:
            if not os.path.exists(self.rules_path):
                return {"error": "Rules registry not found."}
            
            with open(self.rules_path, 'r') as f:
                rules = json.load(f)
            
            if category and category in rules:
                return rules[category]
            return rules
        except Exception as e:
            return {"error": f"Rules query failed: {str(e)}"}

    def push_action(self, action_type, target=None, value=None):
        """
        Sends a tactical action to the Gateway.
        Example: push_action('move', target='north', value=30)
        """
        payload = {
            "entity_id": self.entity_id,
            "api_key": self.api_key,
            "action": action_type,
            "target": target,
            "value": value
        }
        
        # This would be a requests.post(f"{self.gateway_url}/api/world/action", json=payload)
        # For the CLI simulation, we log the intent.
        return {"status": "success", "sent_payload": payload}

    def get_tactical_summary(self):
        """
        Aggregates profile and state into a single "Cognitive Snapshot" 
        that the LLM can use to make decisions.
        """
        profile = self.get_character_profile()
        state = self.get_live_state()
        
        if "error" in profile or "error" in state:
            return {"error": "Could not aggregate tactical summary."}

        # Extract the most critical info for an AI's context window
        return {
            "name": profile['identity']['name'],
            "class": profile['identity']['class'],
            "hp": f"{state['current_hp']}/{profile['gameplay_profile']['combat']['max_hp']}",
            "ac": profile['gameplay_profile']['combat']['armor_class'],
            "position": state.get('location', 'unknown'),
            "active_weapon": state.get('active_weapon'),
            "action_economy": state.get('action_economy'),
            "conditions": state.get('conditions'),
            "current_goal": profile['personal']['goals'].get('short_term'),
            "secret": profile['personal']['secret']
        }
