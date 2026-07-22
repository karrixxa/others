import json
import os
import uuid
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# ==================================================================
# PERCEPTION ENGINE
# ==================================================================

class PerceptionEngine:
    def build_perception_packet(self, agent, engine_feed):
        # Get character data
        profile = agent.profile if hasattr(agent, 'profile') else {}
        state = agent.state if hasattr(agent, 'state') else {}
        gp = profile.get('gameplay_profile', {})

        # 1. Sight & Lighting
        species = profile.get('identity', {}).get('species', 'Human')
        has_darkvision = species in ['Elf', 'Dwarf', 'Tiefling']
        lighting = engine_feed.get('lighting_level', 'bright')
        
        if lighting == 'dark' and has_darkvision:
            effective_sight = 'dim'
        elif lighting == 'dark':
            effective_sight = 'blind'
        else:
            effective_sight = lighting

        stealth_env_mod = engine_feed.get('stealth_modifier', 0)
        total_stealth = gp.get('skills', {}).get('Stealth', 0) + stealth_env_mod

        # 2. Spatial Awareness
        enemies = engine_feed.get('enemies', [])
        allies = engine_feed.get('allies', [])
        processed_enemies = []

        for e in enemies:
            dist = e.get('distance_ft', 999)
            visible = True
            if effective_sight == 'blind' and not e.get('makes_noise', False):
                visible = False
            
            processed_enemies.append({
                "name": e.get('name', 'Unknown'),
                "entity_id": e.get('entity_id'),
                "distance_ft": dist,
                "in_melee_range": dist <= 5,
                "in_attack_range": dist <= 60,
                "ac": e.get('ac'),
                "visible": visible,
                "flanking": e.get('flanking', False)
            })

        # 3. Cover & Movement
        cover = engine_feed.get('cover', 'none')
        cover_bonus = {'none': 0, 'half': 2, 'three_quarters': 5, 'full': 999}
        effective_ac = gp.get('combat', {}).get('armor_class', 10) + cover_bonus.get(cover, 0)

        terrain = engine_feed.get('terrain', 'normal')
        movement = state.get('action_economy', {}).get('movement_remaining', 30)
        effective_movement = movement // 2 if terrain == 'difficult' else movement

        # 4. Threat Level
        enemies_in_melee = [e for e in processed_enemies if e['in_melee_range']]
        hp_pct = state.get('combat', {}).get('current_hp', 10) / gp.get('combat', {}).get('max_hp', 10)
        
        if len(enemies_in_melee) > 1: threat_level = 'CRITICAL'
        elif len(enemies_in_melee) == 1 and hp_pct < 0.3: threat_level = 'HIGH'
        elif len(enemies_in_melee) == 1: threat_level = 'MEDIUM'
        elif len(processed_enemies) > 0: threat_level = 'LOW'
        else: threat_level = 'NONE'

        return {
            "entity_id": profile.get('entity_id', 'unknown'),
            "hp_percent": round(hp_pct, 2),
            "enemies": processed_enemies,
            "allies": allies,
            "lighting": lighting,
            "effective_sight": effective_sight,
            "effective_ac": effective_ac,
            "effective_movement": effective_movement,
            "threat_level": threat_level,
            "total_stealth": total_stealth
        }

# ==================================================================
# SYNTHESIS ENGINE
# ==================================================================

ARCHETYPES = {
    "The Survivor": {"tone": "urgent", "risk_level": "low", "bond_effect": "Protective"},
    "The Tactician": {"tone": "analytical", "risk_level": "medium", "bond_effect": "Strategic"},
    "The Maverick": {"tone": "bold", "risk_level": "high", "bond_effect": "Unpredictable"},
    "The Guardian": {"tone": "steady", "risk_level": "low", "bond_effect": "Sacrificial"},
    "The Scholar": {"tone": "curious", "risk_level": "medium", "bond_effect": "Collaborative"},
}

FEAR_MODIFIERS = {
    "fire": {"avoid": "open flames", "suggest": "water-based cover"},
    "heights": {"avoid": "ledges", "suggest": "ground-level paths"},
    "darkness": {"avoid": "unlit corridors", "suggest": "torch-lit areas"},
    "trapped": {"avoid": "dead ends", "suggest": "open exits"},
}

BOND_MODIFIERS = {
    "family": {"effect": "heightened protectiveness"},
    "duty": {"effect": "rigid adherence to protocol"},
    "love": {"effect": "emotional vulnerability"},
    "debt": {"effect": "obligatory loyalty"},
}

def infer_archetype(traits):
    if not traits: return "The Survivor"
    t_str = " ".join(traits).lower()
    if "analytical" in t_str or "cautious" in t_str: return "The Tactician"
    if "bold" in t_str or "sarcastic" in t_str: return "The Maverick"
    if "loyal" in t_str or "disciplined" in t_str: return "The Guardian"
    if "curious" in t_str or "reserved" in t_str: return "The Scholar"
    return "The Survivor"

def synthesize_psychological_brief(agent, perception_packet):
    profile = agent.profile if hasattr(agent, 'profile') else {}
    rp = profile.get('roleplay_profile', {})
    
    traits = rp.get('personality_traits', [])
    arch_name = infer_archetype(traits)
    arch = ARCHETYPES.get(arch_name)
    
    fear = rp.get('fear', '').lower()
    bond = rp.get('bond', '').lower()
    
    fear_mod = next((v for k, v in FEAR_MODIFIERS.items() if k in fear), {})
    bond_mod = next((v for k, v in BOND_MODIFIERS.items() if k in bond), {})
    
    # Perception Overrides
    overrides = []
    env_ctx = f"{perception_packet.get('lighting', '')} {perception_packet.get('terrain', '')}"
    if any(k in env_ctx.lower() for k in FEAR_MODIFIERS.keys() if k in fear):
        overrides.append(f"⚠️ FEAR PRESENT: {fear} detected! OVERRIDE ALL TACTICS to avoid it.")
    
    if perception_packet.get('threat_level') == 'CRITICAL' and arch_name == 'The Survivor':
        overrides.append("⚠️ SURVIVAL INSTINCT: Threat is CRITICAL. Prioritize escape immediately.")

    override_text = "\n".join(overrides) + "\n" if overrides else ""
    
    identity = profile.get("identity", {})
    gp = profile.get("gameplay_profile", {})
    scores = gp.get("ability_scores", {})
    stat_str = ", ".join([f"{s}: {v}" for s, v in scores.items()])
    identity_text = f"IDENTITY: {identity.get('species', 'Unknown')} {identity.get('class', 'Unknown')} | STATS: {stat_str}\n"

    return (
        f"\n[PSYCHOLOGICAL BRIEF]\n{identity_text}{override_text}"
        f"Archetype: {arch_name} | Tone: {arch['tone']} | Risk: {arch['risk_level']}\n"
        f"BOND: {bond} -> {arch['bond_effect']}\n"
        f"FEAR: {fear} -> NEVER suggest {fear_mod.get('avoid', 'the feared thing')}. Suggest: {fear_mod.get('suggest', 'safe route')}\n"
    )

# ==================================================================
# FLASK APP (For standalone testing/legacy support)
# ==================================================================

app = Flask(__name__)
CORS(app)

@app.route('/jarvis/ask', methods=['POST'])
def ask():
    data = request.json
    entity_id = data.get('entity_id')
    message = data.get('message')
    engine_feed = data.get('engine_feed', {})
    
    # Simulation of the loop
    try:
        state_path = f'/home/cxiong/hermes_rpg/states/{entity_id}.json'
        with open(state_path, 'r') as f:
            profile = json.load(f)
        
        class AgentInstance:
            def __init__(self, p): 
                self.id = p['entity_id']
                self.profile = p
                self.state = p.get('gameplay_profile', {})
        
        agent = AgentInstance(profile)
        perc = PerceptionEngine()
        packet = perc.build_perception_packet(agent, engine_feed)
        brief = synthesize_psychological_brief(agent, packet)
        
        return jsonify({
            "response": "Tactical analysis complete. (Connect to Hermes Gateway for final prose)",
            "brief": brief,
            "perception": packet
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5001)
