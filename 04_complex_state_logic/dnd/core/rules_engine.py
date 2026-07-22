import json
import math
import uuid
import os
from difflib import get_close_matches

# ── CONSTANTS & REGISTRIES (Merged from Original Builder) ────────────────────

ARMOR_TABLE = {
    "none": {"base_ac": 10, "type": "none"},
    "leather armor": {"base_ac": 11, "type": "light"},
    "studded leather": {"base_ac": 12, "type": "light"},
    "hide": {"base_ac": 12, "type": "medium"},
    "chain shirt": {"base_ac": 13, "type": "medium"},
    "scale mail": {"base_ac": 14, "type": "medium"},
    "breastplate": {"base_ac": 14, "type": "medium"},
    "half plate": {"base_ac": 15, "type": "medium"},
    "ring mail": {"base_ac": 14, "type": "heavy"},
    "chain mail": {"base_ac": 16, "type": "heavy"},
    "splint": {"base_ac": 17, "type": "heavy"},
    "plate armor": {"base_ac": 18, "type": "heavy"},
    "shield": {"base_ac": 2, "type": "shield"}
}

SAVE_PROFICIENCIES = {
    "Fighter": ["Strength", "Constitution"],
    "Rogue": ["Dexterity", "Intelligence"],
    "Wizard": ["Intelligence", "Wisdom"],
    "Cleric": ["Wisdom", "Charisma"],
    "Ranger": ["Strength", "Dexterity"],
    "Bard": ["Dexterity", "Charisma"]
}

SPELLCASTING_ABILITY = {"Wizard": "Intelligence", "Cleric": "Wisdom", "Bard": "Charisma"}
SPELL_SLOTS_LV1 = {"Wizard": 2, "Cleric": 2, "Bard": 2}
STARTING_CANTRIPS = {
    "Wizard": ["Fire Bolt", "Prestidigitation", "Mage Hand"],
    "Cleric": ["Sacred Flame", "Guidance", "Spare the Dying"],
    "Bard": ["Vicious Mockery", "Prestidigitation", "Minor Illusion"]
}
STARTING_SPELLS = {
    "Wizard": ["Magic Missile", "Shield", "Sleep", "Detect Magic"],
    "Cleric": ["Healing Word", "Bless", "Cure Wounds", "Guiding Bolt"],
    "Bard": ["Healing Word", "Charm Person", "Thunderwave", "Faerie Fire"]
}

CLASS_HIT_DIE = {
    "Fighter": 10, "Rogue": 8, "Wizard": 6, "Cleric": 8, "Ranger": 10, "Bard": 8
}

BACKGROUND_LANGUAGES = {
    "Criminal": ["Thieves Cant"], "Noble": ["One of choice"], "Acolyte": ["Celestial", "One of choice"],
    "Scholar": ["Two of choice"], "Outlander": ["One of choice"], "Soldier": []
}

BACKGROUND_TOOLS = {
    "Criminal": ["Thieves Tools", "Gaming Set"], "Noble": ["Gaming Set"], "Acolyte": [],
    "Soldier": ["Gaming Set", "Vehicles Land"], "Scholar": [], "Outlander": ["Musical Instrument"]
}

BACKGROUND_BONUS_SKILLS = {
    "Criminal": "Deception", "Noble": "History", "Acolyte": "Religion",
    "Soldier": "Intimidation", "Scholar": "History", "Outlander": "Perception"
}

ALL_SKILLS = {
    "Acrobatics": "Dexterity", "Animal Handling": "Wisdom", "Arcana": "Intelligence", 
    "Athletics": "Strength", "Deception": "Charisma", "History": "Intelligence",
    "Insight": "Wisdom", "Intimidation": "Charisma", "Investigation": "Intelligence", 
    "Medicine": "Wisdom", "Nature": "Intelligence", "Perception": "Wisdom",
    "Performance": "Charisma", "Persuasion": "Charisma", "Religion": "Intelligence", 
    "Sleight of Hand": "Dexterity", "Stealth": "Dexterity", "Survival": "Wisdom",
}

ROLEPLAY_DEFAULTS = {
    ("Rogue", "Criminal"): {"traits":["clever","cautious","sarcastic"], "ideal":"Freedom", "flaw":"Does not trust authority", "motivation":"Prove they are more than their past", "fear":"Being trapped"},
    ("Fighter", "Soldier"): {"traits":["disciplined","loyal","direct"], "ideal":"Honor", "flaw":"Follows orders blindly", "motivation":"Protect others", "fear":"Losing control"},
    ("Wizard", "Scholar"): {"traits":["curious","analytical","reserved"], "ideal":"Knowledge", "flaw":"Underestimates danger", "motivation":"Solve a mystery", "fear":"Losing memories"},
    ("Cleric", "Acolyte"): {"traits":["compassionate","patient","idealistic"], "ideal":"Greater Good", "flaw":"Puts others first to a fault", "motivation":"Heal a community", "fear":"Losing faith"},
    ("Ranger", "Outlander"): {"traits":["perceptive","independent","quiet"], "ideal":"Survival", "flaw":"Distrusts city folk", "motivation":"Searching for something lost", "fear":"Staying in one place"},
    ("Bard", "Noble"): {"traits":["charming","witty","ambitious"], "ideal":"Fame", "flaw":"Needs an audience", "motivation":"Be remembered", "fear":"Being forgotten"},
}

BACKSTORY_DEFAULTS = {
    "Criminal": "Grew up surviving by wits alone on the streets.",
    "Noble": "Born into privilege but disillusioned by power.",
    "Acolyte": "Raised in a temple, shaped by devotion.",
    "Soldier": "Trained for war and scarred by it.",
    "Scholar": "Spent years chasing a question no one else asked.",
    "Outlander": "Grew up far from cities, reading the land.",
}

class RulesEngine:
    def __init__(self, options_path='/home/cxiong/hermes_rpg/character_options.json'):
        self.options = {
            "classes": {
                "Fighter": {"stat_priority": ["Strength", "Constitution", "Dexterity", "Wisdom", "Intelligence", "Charisma"], "skill_options": ["Athletics", "Perception"], "armor": "plate armor", "default_items": ["Rations", "Torch"]},
                "Rogue": {"stat_priority": ["Dexterity", "Intelligence", "Constitution", "Wisdom", "Charisma", "Strength"], "skill_options": ["Stealth", "Acrobatics"], "armor": "leather armor", "default_items": ["Thieves Tools", "Rope"]},
                "Wizard": {"stat_priority": ["Intelligence", "Constitution", "Dexterity", "Wisdom", "Charisma", "Strength"], "skill_options": ["Arcana", "History"], "armor": "none", "default_items": ["Spellbook", "Ink"]},
                "Cleric": {"stat_priority": ["Wisdom", "Strength", "Constitution", "Intelligence", "Charisma", "Dexterity"], "skill_options": ["Medicine", "Religion"], "armor": "chain mail", "default_items": ["Holy Symbol", "Shield"]},
                "Ranger": {"stat_priority": ["Dexterity", "Wisdom", "Constitution", "Strength", "Intelligence", "Charisma"], "skill_options": ["Survival", "Nature"], "armor": "studded leather", "default_items": ["Quiver", "Hunting Trap"]},
                "Bard": {"stat_priority": ["Charisma", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Strength"], "skill_options": ["Performance", "Persuasion"], "armor": "leather armor", "default_items": ["Lute", "Costume"]},
            },
            "species": {"Human": {"speed": 30, "trait": "Versatile"}, "Elf": {"speed": 30, "trait": "Keen Senses"}, "Dwarf": {"speed": 25, "trait": "Toughness"}, "Halfling": {"speed": 25, "trait": "Lucky"}, "Orc": {"speed": 30, "trait": "Relentless"}, "Tiefling": {"speed": 30, "trait": "Infernal Legacy"}},
            "backgrounds": {"Criminal": {"skill": "Stealth", "theme": "Underworld"}, "Noble": {"skill": "History", "theme": "Court"}, "Acolyte": {"skill": "Religion", "theme": "Faith"}, "Soldier": {"skill": "Athletics", "theme": "Military"}, "Scholar": {"skill": "History", "theme": "Academic"}, "Outlander": {"skill": "Survival", "theme": "Wilds"}},
            "stat_array": [15, 14, 13, 12, 10, 8],
            "skills": ALL_SKILLS,
            "weapon_options": {
                "Fighter": [{"name": "Longsword", "type": "martial", "damage": "1d8", "ability_used": "Strength", "range": "5ft"}],
                "Rogue": [{"name": "Shortsword", "type": "simple", "damage": "1d6", "ability_used": "Dexterity", "range": "5ft"}],
                "Wizard": [{"name": "Quarterstaff", "type": "simple", "damage": "1d6", "ability_used": "Strength", "range": "5ft"}],
                "Cleric": [{"name": "Mace", "type": "simple", "damage": "1d6", "ability_used": "Strength", "range": "5ft"}],
                "Ranger": [{"name": "Longbow", "type": "martial", "damage": "1d8", "ability_used": "Dexterity", "range": "150ft"}],
                "Bard": [{"name": "Rapier", "type": "martial", "damage": "1d8", "ability_used": "Dexterity", "range": "5ft"}],
            }
        }
        if os.path.exists(options_path):
            with open(options_path, 'r') as f:
                self.options = json.load(f)

    def mod(self, score):
        return math.floor((score - 10) / 2)

    def calculate_ac(self, armor_name, dex_mod):
        armor = ARMOR_TABLE.get(armor_name.lower(), ARMOR_TABLE["none"])
        t = armor["type"]
        if t == "none": return 10 + dex_mod
        if t == "light": return armor["base_ac"] + dex_mod
        if t == "medium": return armor["base_ac"] + min(dex_mod, 2)
        if t == "heavy": return armor["base_ac"]
        return 10 + dex_mod

    def build_character(self, name, char_class, species, background, weapon_name, 
                        user_id=None, age=None, appearance=None, deity=None, 
                        bond=None, secret=None, short_goal=None, long_goal=None):
        
        # 1. Normalized inputs
        final_class = char_class if char_class in self.options['classes'] else "Rogue"
        final_species = species if species in self.options['species'] else "Human"
        final_bg = background if background in self.options['backgrounds'] else "Criminal"

        # 2. Ability Scores
        priority = self.options['classes'][final_class]['stat_priority']
        stat_array = sorted(self.options['stat_array'], reverse=True)
        scores = {s: stat_array[i] for i, s in enumerate(priority)}
        modifiers = {s: self.mod(v) for s, v in scores.items()}

        # 3. Saving Throws
        proficiency = 2
        prof_saves = SAVE_PROFICIENCIES.get(final_class, [])
        saves = {stat: modifiers[stat] + (proficiency if stat in prof_saves else 0) 
                 for stat in ["Strength","Dexterity","Constitution","Intelligence","Wisdom","Charisma"]}

        # 4. Skills
        skills = {skill: modifiers[ability] for skill, ability in ALL_SKILLS.items()}
        proficient_skills = set()
        for s in self.options['classes'][final_class].get('skill_options', []):
            ability = ALL_SKILLS.get(s, "Wisdom")
            skills[s] = modifiers[ability] + proficiency
            proficient_skills.add(s)
        bg_data = self.options['backgrounds'].get(final_bg, {"skill": "Stealth"})
        bg_skill = bg_data['skill']
        skills[bg_skill] = modifiers[ALL_SKILLS.get(bg_skill, "Wisdom")] + proficiency
        proficient_skills.add(bg_skill)
        bonus_skill = BACKGROUND_BONUS_SKILLS.get(final_bg)
        if bonus_skill:
            skills[bonus_skill] = modifiers[ALL_SKILLS.get(bonus_skill, "Wisdom")] + proficiency
            proficient_skills.add(bonus_skill)

        # 5. Combat Stats
        hit_die = CLASS_HIT_DIE.get(final_class, 8)
        max_hp = hit_die + modifiers['Constitution']
        armor_name = self.options['classes'][final_class].get('armor', 'none')
        ac = self.calculate_ac(armor_name, modifiers['Dexterity'])
        speed = self.options['species'].get(final_species, {"speed": 30})['speed']

        # 6. Attacks
        class_weapons = self.options['weapon_options'].get(final_class, [])
        weapon_data = next((w for w in class_weapons if w['name'].lower() == weapon_name.lower()), None)
        if not weapon_data and class_weapons: weapon_data = class_weapons[0]
        attacks = []
        if weapon_data:
            stat_used = weapon_data['ability_used']
            attacks.append({
                "name": weapon_data['name'], "attack_bonus": proficiency + modifiers[stat_used],
                "damage": f"{weapon_data['damage']}{modifiers[stat_used]:+d}", "range": weapon_data.get('range', '5ft')
            })

        # 7. Spellcasting
        spellcasting = None
        if final_class in SPELLCASTING_ABILITY:
            ability = SPELLCASTING_ABILITY[final_class]
            spellcasting = {
                "ability": ability, "dc": 8 + proficiency + modifiers[ability],
                "attack": proficiency + modifiers[ability],
                "slots": {1: {"total": SPELL_SLOTS_LV1.get(final_class, 2), "remaining": SPELL_SLOTS_LV1.get(final_class, 2)}},
                "cantrips": STARTING_CANTRIPS.get(final_class, []), "spells": STARTING_SPELLS.get(final_class, []),
            }

        # 8. IDs & Roleplay
        char_id = f"char_{name.replace(' ', '_').lower()}"
        entity_id = f"ent_{uuid.uuid4().hex[:8]}"
        agent_id = f"jarvis_{char_id}"
        uid = user_id or f"user_{name.replace(' ', '_').lower()}"
        
        rp_key = (final_class, final_bg)
        rp = ROLEPLAY_DEFAULTS.get(rp_key, {"traits":["resourceful"], "ideal":"Survival", "flaw":"Alone", "motivation":"Purpose", "fear":"Failure"})

        return {
            "entity_id": entity_id, "user_id": uid, "character_id": char_id, "agent_id": agent_id,
            "identity": {"name": name, "species": final_species, "class": final_class, "background": final_bg,
                         "alignment": "True Neutral", "level": 1, "xp": 0},
            "roleplay_profile": {"personality_traits": rp["traits"], "ideal": rp["ideal"], "bond": bond or "Protects a loved one",
                                 "flaw": rp["flaw"], "motivation": rp["motivation"], "fear": rp["fear"],
                                 "backstory": BACKSTORY_DEFAULTS.get(final_bg, "A wanderer.")},
            "personal": {"age": age, "appearance": appearance, "homeland": "Unknown", "deity": deity,
                         "goals": {"short_term": short_goal, "long_term": long_goal}, "secret": secret},
            "gameplay_profile": {
                "proficiency_bonus": proficiency, "ability_scores": scores, "ability_modifiers": modifiers,
                "saving_throws": saves, "skills": skills, "proficient_skills": list(proficient_skills),
                "combat": {"max_hp": max_hp, "current_hp": max_hp, "armor_class": ac, "speed": speed, "initiative": modifiers['Dexterity'], "hit_die": f"d{hit_die}"},
                "features": {"class": "TBD", "species": "TBD", "background": "TBD"},
                "attacks": attacks, "spellcasting": spellcasting,
                "passive_scores": {"passive_perception": 10 + skills.get("Perception", 0), "passive_insight": 10 + skills.get("Insight", 0), "passive_investigation": 10 + skills.get("Investigation", 0)}
            },
            "inventory": {"equipped_weapon": weapon_data['name'] if weapon_data else None, "equipped_armor": armor_name,
                           "shield_equipped": False, "loot_bag": {"weapons": [weapon_data['name']] if weapon_data else [], "armor": [armor_name] if armor_name != 'none' else [], "items": self.options['classes'][final_class].get('default_items', []), "gold": 10}}
        }

    def validate(self, character):
        gp = character['gameplay_profile']
        if gp['combat']['max_hp'] < 1: return ["HP too low"]
        return []
