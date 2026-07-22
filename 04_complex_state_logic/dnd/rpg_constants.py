import json
import math
import uuid
import os
from difflib import get_close_matches


import math
import uuid
import os
from difflib import get_close_matches

# ── Paths ─────────────────────────────────────────────────────────────────────
OPTIONS_PATH   = "/home/cxiong/hermes_rpg/character_options.json"
CHARACTERS_DIR = "/home/cxiong/hermes_rpg/characters"
STATE_DIR      = "/home/cxiong/hermes_rpg/states"


# ═════════════════════════════════════════════════════════════════════════════
#  REFERENCE DATA  (verified from D&D 5e PHB)
# ═════════════════════════════════════════════════════════════════════════════

# Saving throw proficiencies per class (PHB confirmed)
SAVE_PROFICIENCIES = {
    "Fighter": ["Strength", "Constitution"],
    "Rogue":   ["Dexterity", "Intelligence"],
    "Wizard":  ["Intelligence", "Wisdom"],
    "Cleric":  ["Wisdom", "Charisma"],
    "Ranger":  ["Strength", "Dexterity"],
    "Bard":    ["Dexterity", "Charisma"],
}

# Spellcasting ability per class (non-casters = None)
SPELLCASTING_ABILITY = {
    "Fighter": None,
    "Rogue":   None,
    "Wizard":  "Intelligence",
    "Cleric":  "Wisdom",
    "Ranger":  "Wisdom",
    "Bard":    "Charisma",
}

# Spell slots at level 1 per class
SPELL_SLOTS_LV1 = {
    "Fighter": {},
    "Rogue":   {},
    "Wizard":  {"1": {"total": 2, "remaining": 2}},
    "Cleric":  {"1": {"total": 2, "remaining": 2}},
    "Ranger":  {},   # Rangers get spells at level 2
    "Bard":    {"1": {"total": 2, "remaining": 2}},
}

# Starting cantrips per class at level 1
STARTING_CANTRIPS = {
    "Fighter": [],
    "Rogue":   [],
    "Wizard":  ["Fire Bolt", "Prestidigitation", "Mage Hand"],
    "Cleric":  ["Sacred Flame", "Guidance", "Spare the Dying"],
    "Ranger":  [],
    "Bard":    ["Vicious Mockery", "Prestidigitation", "Minor Illusion"],
}

# Starting prepared spells per class at level 1
STARTING_SPELLS = {
    "Fighter": [],
    "Rogue":   [],
    "Wizard":  ["Magic Missile", "Shield", "Sleep", "Detect Magic"],
    "Cleric":  ["Healing Word", "Bless", "Cure Wounds", "Guiding Bolt"],
    "Ranger":  [],
    "Bard":    ["Healing Word", "Charm Person", "Thunderwave", "Faerie Fire"],
}

# Armor & weapon proficiencies per class
CLASS_PROFICIENCIES = {
    "Fighter": {
        "armor":   ["light", "medium", "heavy", "shields"],
        "weapons": ["simple", "martial"],
        "tools":   [],
    },
    "Rogue": {
        "armor":   ["light"],
        "weapons": ["simple", "hand crossbows", "longswords", "rapiers", "shortswords"],
        "tools":   ["thieves tools"],
    },
    "Wizard": {
        "armor":   [],
        "weapons": ["daggers", "darts", "slings", "quarterstaffs", "light crossbows"],
        "tools":   [],
    },
    "Cleric": {
        "armor":   ["light", "medium", "shields"],
        "weapons": ["simple"],
        "tools":   [],
    },
    "Ranger": {
        "armor":   ["light", "medium", "shields"],
        "weapons": ["simple", "martial"],
        "tools":   [],
    },
    "Bard": {
        "armor":   ["light"],
        "weapons": ["simple", "hand crossbows", "longswords", "rapiers", "shortswords"],
        "tools":   ["three musical instruments of your choice"],
    },
}

# Languages per species and background
SPECIES_LANGUAGES = {
    "Human":    ["Common"],
    "Elf":      ["Common", "Elvish"],
    "Dwarf":    ["Common", "Dwarvish"],
    "Halfling": ["Common", "Halfling"],
    "Orc":      ["Common", "Orc"],
    "Tiefling": ["Common", "Infernal"],
}

BACKGROUND_LANGUAGES = {
    "Criminal":  ["Thieves Cant"],
    "Noble":     ["one language of your choice"],
    "Acolyte":   ["Celestial", "one language of your choice"],
    "Soldier":   [],
    "Scholar":   ["two languages of your choice"],
    "Outlander": ["one language of your choice"],
}

# Tool proficiencies per background
BACKGROUND_TOOLS = {
    "Criminal":  ["Thieves Tools", "one gaming set"],
    "Noble":     ["one gaming set"],
    "Acolyte":   [],
    "Soldier":   ["one gaming set", "vehicles (land)"],
    "Scholar":   [],
    "Outlander": ["one musical instrument"],
}

# Background contacts
BACKGROUND_CONTACTS = {
    "Criminal":  "A criminal contact — a fence, gang leader, or corrupt official",
    "Noble":     "A noble family or court connection with political influence",
    "Acolyte":   "A temple, religious order, or spiritual mentor",
    "Soldier":   "A military unit, commander, or war veteran network",
    "Scholar":   "A university, library, or academic institution",
    "Outlander": "A tribe, wilderness community, or druidic circle",
}

# Background bonus skills (second skill beyond the class skill)
BACKGROUND_BONUS_SKILLS = {
    "Criminal":  "Deception",
    "Noble":     "History",
    "Acolyte":   "Religion",
    "Soldier":   "Intimidation",
    "Scholar":   "History",
    "Outlander": "Survival",
}

# Full 15 D&D conditions (PHB verified)
CONDITIONS = {
    "Blinded": {
        "description": "Cannot see. Attacks against you have advantage; your attacks have disadvantage.",
        "blocked_actions": ["read_text", "spot_hidden_object"],
        "allowed_with_penalty": ["melee_attack", "ranged_attack", "ability_check"],
        "auto_fail": ["sight_based_check"],
    },
    "Charmed": {
        "description": "Cannot attack the charmer. Charmer has advantage on social checks against you.",
        "blocked_actions": ["attack_charmer"],
        "allowed_with_penalty": [],
        "auto_fail": [],
    },
    "Deafened": {
        "description": "Cannot hear. Auto-fail hearing checks.",
        "blocked_actions": [],
        "allowed_with_penalty": [],
        "auto_fail": ["hearing_check"],
    },
    "Frightened": {
        "description": "Disadvantage on checks/attacks while source of fear is in sight. Cannot move closer to it.",
        "blocked_actions": ["move_toward_source"],
        "allowed_with_penalty": ["attack", "ability_check"],
        "auto_fail": [],
    },
    "Grappled": {
        "description": "Speed becomes 0. Ends if grappler is incapacitated.",
        "blocked_actions": ["move"],
        "allowed_with_penalty": [],
        "auto_fail": [],
    },
    "Incapacitated": {
        "description": "Cannot take actions or reactions.",
        "blocked_actions": ["attack", "cast_spell", "reaction", "bonus_action"],
        "allowed_with_penalty": [],
        "auto_fail": [],
    },
    "Invisible": {
        "description": "Cannot be seen. Attacks against you have disadvantage; your attacks have advantage.",
        "blocked_actions": [],
        "allowed_with_penalty": [],
        "auto_fail": [],
        "grants_advantage": ["attack"],
    },
    "Paralyzed": {
        "description": "Incapacitated and cannot move or speak. Auto-fail Str/Dex saves. Attacks have advantage; hits within 5ft are crits.",
        "blocked_actions": ["move", "attack", "cast_spell", "speak", "reaction", "bonus_action"],
        "allowed_with_penalty": [],
        "auto_fail": ["strength_save", "dexterity_save"],
    },
    "Petrified": {
        "description": "Transformed into stone. Incapacitated, unaware of surroundings. Resistance to all damage.",
        "blocked_actions": ["move", "attack", "cast_spell", "speak", "reaction", "bonus_action"],
        "allowed_with_penalty": [],
        "auto_fail": ["strength_save", "dexterity_save"],
    },
    "Poisoned": {
        "description": "Disadvantage on attack rolls and ability checks.",
        "blocked_actions": [],
        "allowed_with_penalty": ["attack", "ability_check"],
        "auto_fail": [],
    },
    "Prone": {
        "description": "Disadvantage on attacks. Attacks within 5ft have advantage; ranged attacks have disadvantage.",
        "blocked_actions": [],
        "allowed_with_penalty": ["melee_attack"],
        "auto_fail": [],
        "movement_cost": "half speed to stand up",
    },
    "Restrained": {
        "description": "Speed 0. Disadvantage on attacks and Dexterity saves. Attacks against you have advantage.",
        "blocked_actions": ["move"],
        "allowed_with_penalty": ["attack", "dexterity_save"],
        "auto_fail": [],
    },
    "Stunned": {
        "description": "Incapacitated. Cannot move. Auto-fail Str/Dex saves. Attacks against you have advantage.",
        "blocked_actions": ["move", "attack", "cast_spell", "reaction", "bonus_action"],
        "allowed_with_penalty": [],
        "auto_fail": ["strength_save", "dexterity_save"],
    },
    "Unconscious": {
        "description": "Incapacitated, cannot move or speak. Unaware. Auto-fail Str/Dex saves. Attacks within 5ft are crits.",
        "blocked_actions": ["move", "attack", "cast_spell", "speak", "reaction", "bonus_action", "use_item"],
        "allowed_with_penalty": [],
        "auto_fail": ["strength_save", "dexterity_save"],
    },
    "Exhaustion": {
        "description": "Tiered condition (1-6). Level 1: disadvantage on checks. Level 2: speed halved. Level 5: speed 0. Level 6: death.",
        "blocked_actions": [],
        "allowed_with_penalty": ["ability_check"],
        "auto_fail": [],
        "tier": 1,
    },
}

# Armor formula reference
ARMOR_TABLE = {
    "Padded":        {"base_ac": 11, "modifier": "Dexterity", "max_dex": None, "type": "light",   "stealth": "disadvantage"},
    "Leather Armor": {"base_ac": 11, "modifier": "Dexterity", "max_dex": None, "type": "light",   "stealth": "normal"},
    "Studded Leather":{"base_ac":12, "modifier": "Dexterity", "max_dex": None, "type": "light",   "stealth": "normal"},
    "Hide":          {"base_ac": 12, "modifier": "Dexterity", "max_dex": 2,    "type": "medium",  "stealth": "normal"},
    "Chain Shirt":   {"base_ac": 13, "modifier": "Dexterity", "max_dex": 2,    "type": "medium",  "stealth": "normal"},
    "Scale Mail":    {"base_ac": 14, "modifier": "Dexterity", "max_dex": 2,    "type": "medium",  "stealth": "disadvantage"},
    "Breastplate":   {"base_ac": 14, "modifier": "Dexterity", "max_dex": 2,    "type": "medium",  "stealth": "normal"},
    "Half Plate":    {"base_ac": 15, "modifier": "Dexterity", "max_dex": 2,    "type": "medium",  "stealth": "disadvantage"},
    "Ring Mail":     {"base_ac": 14, "modifier": None,        "max_dex": None, "type": "heavy",   "stealth": "disadvantage"},
    "Chain Mail":    {"base_ac": 16, "modifier": None,        "max_dex": None, "type": "heavy",   "stealth": "disadvantage"},
    "Splint":        {"base_ac": 17, "modifier": None,        "max_dex": None, "type": "heavy",   "stealth": "disadvantage"},
    "Plate":         {"base_ac": 18, "modifier": None,        "max_dex": None, "type": "heavy",   "stealth": "disadvantage"},
    "Shield":        {"base_ac": 2,  "modifier": None,        "max_dex": None, "type": "shield",  "stealth": "normal"},
    "none":          {"base_ac": 10, "modifier": "Dexterity", "max_dex": None, "type": "none",    "stealth": "normal"},
}

# Level progression 1-3 per class
LEVEL_PROGRESSION = {
    "Fighter": {
        1: {"feature": "Second Wind",      "hp_die": "d10", "hp_gain": 10, "description": "Regain 1d10+Fighter level HP as a bonus action once per short rest."},
        2: {"feature": "Action Surge",     "hp_die": "d10", "hp_gain": 6,  "description": "Take one additional action on your turn once per short rest."},
        3: {"feature": "Martial Archetype","hp_die": "d10", "hp_gain": 6,  "description": "Choose a subclass: Champion, Battle Master, or Eldritch Knight."},
    },
    "Rogue": {
        1: {"feature": "Sneak Attack + Expertise", "hp_die": "d8", "hp_gain": 8, "description": "Deal 1d6 extra damage when you have advantage or an ally is adjacent. Double proficiency in two skills."},
        2: {"feature": "Cunning Action",            "hp_die": "d8", "hp_gain": 5, "description": "Dash, Disengage, or Hide as a bonus action."},
        3: {"feature": "Roguish Archetype",         "hp_die": "d8", "hp_gain": 5, "description": "Choose a subclass: Thief, Assassin, or Arcane Trickster."},
    },
    "Wizard": {
        1: {"feature": "Spellcasting + Arcane Recovery", "hp_die": "d6", "hp_gain": 6, "description": "Cast spells using Intelligence. Recover spell slots equal to half Wizard level on short rest."},
        2: {"feature": "Arcane Tradition",               "hp_die": "d6", "hp_gain": 4, "description": "Choose a school of magic: Evocation, Illusion, Conjuration, etc."},
        3: {"feature": "2nd Level Spells",               "hp_die": "d6", "hp_gain": 4, "description": "Gain access to 2nd level spell slots."},
    },
    "Cleric": {
        1: {"feature": "Spellcasting + Divine Domain", "hp_die": "d8", "hp_gain": 8, "description": "Cast spells using Wisdom. Choose a domain (Life, Light, War, etc.) for bonus spells and features."},
        2: {"feature": "Channel Divinity",             "hp_die": "d8", "hp_gain": 5, "description": "Use a divine power once per short rest. Life domain: Preserve Life heals nearby creatures."},
        3: {"feature": "2nd Level Spells",             "hp_die": "d8", "hp_gain": 5, "description": "Gain access to 2nd level spell slots."},
    },
    "Ranger": {
        1: {"feature": "Favored Enemy + Natural Explorer", "hp_die": "d10", "hp_gain": 10, "description": "Advantage on checks vs chosen enemy type. Expertise in chosen terrain."},
        2: {"feature": "Fighting Style + Spellcasting",   "hp_die": "d10", "hp_gain": 6,  "description": "Choose a combat style. Gain access to Ranger spells using Wisdom."},
        3: {"feature": "Ranger Archetype + Primeval Awareness","hp_die":"d10","hp_gain":6, "description": "Choose a subclass: Hunter or Beast Master."},
    },
    "Bard": {
        1: {"feature": "Spellcasting + Bardic Inspiration", "hp_die": "d8", "hp_gain": 8, "description": "Cast spells using Charisma. Give an ally a d6 inspiration die to add to a roll (Charisma modifier uses per long rest)."},
        2: {"feature": "Jack of All Trades + Song of Rest", "hp_die": "d8", "hp_gain": 5, "description": "Add half proficiency to non-proficient checks. Allies heal extra d6 on short rest."},
        3: {"feature": "Bard College + Expertise",          "hp_die": "d8", "hp_gain": 5, "description": "Choose a college. Double proficiency in two skills."},
    },
}

# Class descriptions for Jarvis to explain to players
CLASS_DESCRIPTIONS = {
    "Fighter":  "Masters of weapons and armor. Can fight any way — sword and shield, two weapons, or ranged. Second Wind lets them heal themselves once per short rest. The most straightforward class for beginners.",
    "Rogue":    "Experts in stealth, trickery, and precision strikes. Sneak Attack deals bonus damage when they have advantage or an ally is nearby. Fast and deadly, but fragile if caught in the open.",
    "Wizard":   "Scholars of arcane magic. The most powerful spellcasters but very fragile. A Wizard's spellbook lets them prepare different spells each day. Keep them away from the frontline.",
    "Cleric":   "Divine spellcasters chosen by a god. Can heal allies, buff the party, and still fight in armor. Healing Word restores HP as a bonus action — the most valuable support class in the game.",
    "Ranger":   "Hunters and trackers. Excellent at ranged combat and wilderness survival. Hunter's Mark lets them deal extra damage to a chosen target throughout a fight.",
    "Bard":     "Performers who weave magic into music. Bardic Inspiration gives allies bonus dice on their rolls. Good at everything but rarely the best at any single thing — the ultimate support/utility class.",
}


# ═════════════════════════════════════════════════════════════════════════════
#  PART 1 — CHARACTER BUILDER
# ═════════════════════════════════════════════════════════════════════════════

