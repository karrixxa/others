from builder import CharacterBuilder, CLASS_FEATURES, SPECIES_TRAITS
import random

# ==================================================================
# CONVERSATIONAL DATA
# ==================================================================
CLASS_DESCRIPTIONS = {
    "Fighter": "Masters of weapons and armor. The most durable class. Second Wind lets you heal yourself in combat as a bonus action.",
    "Rogue": "Experts in stealth and precision. Sneak Attack deals bonus damage when you have advantage or an ally is adjacent.",
    "Wizard": "Powerful arcane spellcasters but very fragile. Magic Missile auto-hits. Best for battlefield control.",
    "Cleric": "Divine casters who heal, buff, and fight in armor. Healing Word restores HP as a bonus action.",
    "Ranger": "Hunters and trackers. Strong at ranged combat and survival. Hunter's Mark deals extra damage.",
    "Bard": "Social spellcasters and support characters. Bardic Inspiration gives allies bonus dice on their rolls.",
}

SPECIES_DESCRIPTIONS = {
    "Human": "Extra skill proficiency. Flexible — works for any class.",
    "Elf": "Darkvision 60ft. Advantage vs charm. Cannot be magically slept.",
    "Dwarf": "Darkvision 60ft. Poison resistance. Tough and resilient.",
    "Halfling": "Lucky — reroll natural 1s on attacks, checks, and saves.",
    "Orc": "Relentless Endurance — drop to 1 HP instead of 0 once per long rest.",
    "Tiefling": "Fire resistance. Darkvision 60ft. Know Thaumaturgy cantrip.",
}

BACKGROUND_DESCRIPTIONS = {
    "Criminal": "Stealth proficiency and a criminal contact. Best for sneaky characters.",
    "Noble": "Persuasion proficiency and social connections. Good for deception.",
    "Acolyte": "Medicine and Religion proficiency. Temple connections.",
    "Soldier": "Athletics and Intimidation proficiency. Military contacts.",
    "Scholar": "Arcana and History proficiency. Academic connections.",
    "Outlander": "Survival and Perception proficiency. Wilderness contacts.",
}

# Golden Path Recommendations: Class -> (Recommended Species, Recommended Background)
GOLDEN_PATHS = {
    "Fighter": ("Human", "Soldier"),
    "Rogue": ("Elf", "Criminal"),
    "Wizard": ("High Elf", "Scholar"), # Note: mapped to Elf in builder
    "Cleric": ("Dwarf", "Acolyte"),
    "Ranger": ("Wood Elf", "Outlander"), # Note: mapped to Elf in builder
    "Bard": ("Tiefling", "Noble"),
}

# Flavor Generator for "You decide" responses
FLAVOR_GENERATOR = {
    "secret": {
        "Criminal": ["You are an exiled noble from a fallen house.", "You stole a cursed artifact you can't get rid of.", "You are a double agent for a rival city."],
        "Noble": ["You are secretly in debt to a dangerous crime lord.", "You aren't the true heir to your family name.", "You practice a forbidden magic in secret."],
        "Acolyte": ["You've lost faith in your deity but pretend otherwise.", "You possess a heretical text from a lost era.", "Your faith was forced upon you."],
        "Soldier": ["You deserted your post during a critical battle.", "You were framed for a war crime you didn't commit.", "You serve a secret military order."],
        "Scholar": ["You discovered a truth that would collapse the current government.", "You are searching for a way to reverse a deadly curse.", "You have a rival who will stop at nothing to ruin you."],
        "Outlander": ["You are the last survivor of a wiped-out tribe.", "You possess a map to a city that shouldn't exist.", "You are hunted by a beast of legend."],
    },
    "deity": {
        "Criminal": ["The God of Thieves and Shadows", "The Lady of Luck and Chance", "None - only in gold I trust"],
        "Noble": ["The God of Order and Justice", "The Solar Deity of Radiance", "The Patron of Wealth"],
        "Acolyte": ["The Great Healer", "The Eternal Flame", "The Silent Watcher"],
        "Soldier": ["The God of War and Strategy", "The Iron Sentinel", "The Spirit of Valor"],
        "Scholar": ["The Keeper of Secrets", "The Infinite Archive", "The Goddess of Logic"],
        "Outlander": ["The Wild Mother", "The Spirit of the Hunt", "The Moon and Stars"],
    },
    "bond": {
        "Criminal": ["A partner in crime who saved my life.", "A sibling I'm trying to buy out of prison.", "A mysterious benefactor."],
        "Noble": ["The honor of my family name.", "A childhood friend who became a commoner.", "A secret lover from a rival house."],
        "Acolyte": ["The sacred texts of my order.", "A mentor who taught me everything.", "The poor and forgotten of the city."],
        "Soldier": ["My old squad, the 'Iron Dogs'.", "A promise made to a fallen comrade.", "The oath of my service."],
        "Scholar": ["A legendary lost tome.", "A teacher whose disappearance is a mystery.", "The pursuit of absolute truth."],
        "Outlander": ["The ancestral lands of my people.", "A loyal animal companion.", "The balance of nature."],
    }
}

class CreationSession:
    """
    Consultative Character Creation.
    Implements Recommendations, Feedback loops, and Intelligent Auto-fill.
    """
    def __init__(self, session_id):
        self.session_id = session_id
        self.step = 'NAME'
        self.data = {}
        self.builder = CharacterBuilder()
        
        # For the Personal Details loop
        self.detail_index = 0
        self.detail_prompts = [
            ('age', "How old is your character?"),
            ('deity', "Do they serve a deity or follow a specific philosophy?"),
            ('bond', "Who or what do they care about most in this world?"),
            ('secret', "What is a secret they are hiding from everyone?"),
        ]

    def process(self, player_input):
        player_input = player_input.strip()
        if not player_input and self.step != 'PERSONAL_DETAILS': 
            return {"type": "error", "message": "I didn't hear anything. Please respond!"}

        if self.step == 'NAME':
            return self._handle_name(player_input)
        elif self.step == 'CLASS':
            return self._handle_class(player_input)
        elif self.step == 'SPECIES':
            return self._handle_species(player_input)
        elif self.step == 'BACKGROUND':
            return self._handle_background(player_input)
        elif self.step == 'PERSONAL_DETAILS':
            return self._handle_personal_details(player_input)
        elif self.step == 'WEAPON':
            return self._handle_weapon(player_input)
        
        return {"type": "error", "message": "Unknown step."}

    def _handle_name(self, name):
        self.data['name'] = name
        self.step = 'CLASS'
        
        options = "\n\n".join(
            f"  [{i+1}] {cls}\n      {CLASS_DESCRIPTIONS[cls]}"
            for i, cls in enumerate(CLASS_DESCRIPTIONS.keys())
        )
        return {
            "type": "creation_prompt",
            "message": f"A strong name, {name}. Now, let's decide your path. How do you envision yourself fighting and interacting with the world?\n\n{options}\n\nPick a number (1-6) or type the class name:"
        }

    def _handle_class(self, inp):
        classes = list(CLASS_DESCRIPTIONS.keys())
        if inp.isdigit() and 1 <= int(inp) <= len(classes):
            chosen = classes[int(inp) - 1]
        else:
            chosen = self.builder.normalize_choice(inp, classes)
            if not chosen:
                return {"type": "creation_prompt", "message": "I didn't recognize that class. Please pick a number (1-6) or name from the list:"}
        
        self.data['char_class'] = chosen
        self.step = 'SPECIES'
        
        # RECOMMENDED PATH: Species
        rec_species, _ = GOLDEN_PATHS.get(chosen, ("Human", "Criminal"))
        # Normalize "High Elf" -> "Elf" for builder
        rec_species = "Elf" if "Elf" in rec_species else rec_species

        return {
            "type": "creation_prompt",
            "message": f"{chosen}... a fine choice. Given that, I strongly recommend the {rec_species} lineage. It creates a powerful synergy with your class.\n\nDoes that sound right to you? (Yes / No / Other)"
        }

    def _handle_species(self, inp):
        char_class = self.data['char_class']
        rec_species, _ = GOLDEN_PATHS.get(char_class, ("Human", "Criminal"))
        rec_species = "Elf" if "Elf" in rec_species else rec_species

        if inp.lower() in ['yes', 'y', 'yeah', 'sure']:
            chosen = rec_species
        elif inp.lower() in ['no', 'n', 'other', 'something else']:
            options = "\n".join(f"  - {s}: {SPECIES_DESCRIPTIONS[s]}" for s in SPECIES_DESCRIPTIONS)
            return {
                "type": "creation_prompt",
                "message": f"Fair enough. Let's look at the alternatives:\n\n{options}\n\nWhich species are you?"
            }
        else:
            # Assume they typed a species name directly
            all_species = list(SPECIES_DESCRIPTIONS.keys())
            chosen = self.builder.normalize_choice(inp, all_species)
            if not chosen:
                return {"type": "creation_prompt", "message": f"I'm not familiar with that lineage. Try one of these: {', '.join(all_species)}"}

        self.data['species'] = chosen
        self.step = 'BACKGROUND'
        
        # RECOMMENDED PATH: Background
        _, rec_bg = GOLDEN_PATHS.get(char_class, ("Human", "Criminal"))
        return {
            "type": "creation_prompt",
            "message": f"A {chosen} {char_class}. Perfect. For your past, I suggest the {rec_bg} background. It adds a rich layer of motivation and useful skills to your profile.\n\nDoes that fit your vision? (Yes / No / Other)"
        }

    def _handle_background(self, inp):
        char_class = self.data['char_class']
        _, rec_bg = GOLDEN_PATHS.get(char_class, ("Human", "Criminal"))

        if inp.lower() in ['yes', 'y', 'yeah', 'sure']:
            chosen = rec_bg
        elif inp.lower() in ['no', 'n', 'other', 'something else']:
            options = "\n".join(f"  - {b}: {BACKGROUND_DESCRIPTIONS[b]}" for b in BACKGROUND_DESCRIPTIONS)
            return {
                "type": "creation_prompt",
                "message": f"No problem. Let's explore other histories:\n\n{options}\n\nWhich background fits your story?"
            }
        else:
            # Direct input
            all_bgs = list(BACKGROUND_DESCRIPTIONS.keys())
            chosen = self.builder.normalize_choice(inp, all_bgs)
            if not chosen:
                return {"type": "creation_prompt", "message": f"I didn't catch that background. Please choose from: {', '.join(all_bgs)}"}

        self.data['background'] = chosen
        self.step = 'PERSONAL_DETAILS'
        
        key, prompt = self.detail_prompts[self.detail_index]
        return {
            "type": "creation_prompt",
            "message": f"A {chosen} background. That adds a lot of flavor. Now, a few personal details... (If you're unsure, just press Enter or say 'you decide' and I'll handle it)\n\n{prompt}"
        }

    def _handle_personal_details(self, inp):
        key, _ = self.detail_prompts[self.detail_index]
        bg = self.data['background']
        
        # Intelligent Auto-fill logic
        if not inp or inp.lower() in ['i dont know', 'you decide', 'random', 'idk', 'generate']:
            if key in FLAVOR_GENERATOR:
                options = FLAVOR_GENERATOR[key].get(bg, FLAVOR_GENERATOR[key].get("Criminal"))
                final_val = random.choice(options)
                inp = f"[Generated] {final_val}"
            else:
                inp = "Unknown"
        
        self.data[key] = inp
        
        self.detail_index += 1
        if self.detail_index < len(self.detail_prompts):
            _, next_prompt = self.detail_prompts[self.detail_index]
            return {
                "type": "creation_prompt",
                "message": next_prompt
            }
        
        # Move to weapon
        self.step = 'WEAPON'
        char_class = self.data['char_class']
        weapons = self.builder.options.get('weapon_options', {}).get(char_class, [])
        
        if not weapons:
            self.data['weapon'] = 'None'
            return self._finalize()
            
        options = "\n".join(
            f"  [{i+1}] {w['name']} — {w['damage']} {w['type']}. "
            f"Uses {w['ability_used']}. Range: {w.get('range','5ft')}."
            for i, w in enumerate(weapons)
        )
        return {
            "type": "creation_prompt",
            "message": f"Almost there. Finally, choose your starting weapon:\n\n{options}\n\nPick a number:"
        }

    def _handle_weapon(self, inp):
        char_class = self.data['char_class']
        weapons = self.builder.options.get('weapon_options', {}).get(char_class, [])
        
        if inp.isdigit() and 1 <= int(inp) <= len(weapons):
            chosen = weapons[int(inp) - 1]['name']
        else:
            chosen = self.builder.normalize_choice(inp, [w['name'] for w in weapons])
            if not chosen and weapons:
                chosen = weapons[0]['name']
            elif not chosen:
                chosen = 'None'
        
        self.data['weapon'] = chosen
        return self._finalize()

    def _finalize(self):
        try:
            character = self.builder.build_character(
                name = self.data['name'],
                char_class_in = self.data['char_class'],
                species_in = self.data['species'],
                background_in = self.data['background'],
                weapon_name = self.data['weapon'],
                age = self.data.get('age'),
                deity = self.data.get('deity'),
                bond = self.data.get('bond'),
                secret = self.data.get('secret')
            )

            import os, json
            from builder import CHARS_DIR, STATES_DIR
            os.makedirs(CHARS_DIR, exist_ok=True)
            os.makedirs(STATES_DIR, exist_ok=True)

            gp = character.get('gameplay_profile', {})
            combat = gp.get('combat', {})
            max_hp = combat.get('max_hp', 10)
            
            state = {
                "current_hp": max_hp,
                "temporary_hp": 0,
                "conditions": [],
                "death_saves": {"successes": 0, "failures": 0, "stable": False},
                "active_weapon": character['gameplay_profile']['attacks'][0]['name'] if character['gameplay_profile']['attacks'] else None,
                "location": "starting_area",
                "turn_status": "ready",
                "action_economy": {
                    "action_used": False, "bonus_action_used": False, "reaction_used": False,
                    "movement_used": 0, "movement_remaining": combat.get('speed', 30)
                },
                "combat_flags": {
                    "has_advantage": False, "has_disadvantage": False, "can_take_action": True,
                    "can_move": True, "can_speak": True, "can_cast_spells": True, "can_react": True
                },
                "rest_state": {
                    "hit_dice_remaining": 1,
                    "features_available": {"class_feature": True},
                    "spell_slots": character['gameplay_profile'].get('spellcasting', {}).get('spell_slots', {})
                }
            }

            char_path = os.path.join(CHARS_DIR, f"{character['character_id']}.json")
            state_path = os.path.join(STATES_DIR, f"{character['character_id']}_state.json")

            with open(char_path, 'w') as f: json.dump(character, f, indent=2)
            with open(state_path, 'w') as f: json.dump(state, f, indent=2)

            atk = character['gameplay_profile']['attacks'][0] if character['gameplay_profile']['attacks'] else {}
            summary = (
                f"\n--- CHARACTER FINALIZED ---\n"
                f"Name: {self.data['name']} the {self.data['char_class']}\n"
                f"HP: {max_hp} | AC: {combat.get('armor_class')} | Speed: {combat.get('speed')}ft\n"
                f"Main Attack: {atk.get('name', 'Unarmed')} ({atk.get('attack_bonus', 0):+d} / {atk.get('damage', '??')})\n"
                f"Entity ID: {character['entity_id']}\n"
                f"---------------------------\n"
                f"Your profile and state have been synchronized."
            )

            self.step = 'DONE'
            return {
                "type": "FINALIZE_CHARACTER",
                "entity_id": character['entity_id'],
                "message": summary,
                "profile": character,
                "state": state,
            }
        except Exception as e:
            return {"type": "error", "message": f"Finalization failed: {str(e)}"}
