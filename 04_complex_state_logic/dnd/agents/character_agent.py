import json

class BuilderState:
    """
    Tracks the progress of character creation.
    """
    def __init__(self):
        self.preferences = {}
        self.selected_options = {
            "name": None,
            "class": None,
            "species": None,
            "background": None,
            "weapon": None,
        }
        self.details = {
            "bond": None,
            "secret": None,
            "short_goal": None,
            "long_goal": None,
        }
        self.complete = False

    def is_missing(self, key):
        if key in self.selected_options:
            return self.selected_options[key] is None
        if key in self.details:
            return self.details[key] is None
        return True

    def get_all_missing(self):
        missing = []
        for k, v in self.selected_options.items():
            if v is None: missing.append(k)
        for k, v in self.details.items():
            if v is None: missing.append(k)
        return missing

class CharacterAgent:
    """
    The Guided Architect (Improved).
    Now handles confusion and provides helpful explanations.
    """
    def __init__(self):
        self.state = BuilderState()
        self.last_question = None

    def get_next_question(self):
        missing = self.state.get_all_missing()
        if not missing:
            return None

        # Define prompts and the "Explainers" for when users are confused
        self.prompts = {
            "class": {
                "q": "To start, what kind of vibe are you going for? (e.g., 'A powerful spellcaster', 'A sneaky assassin', 'A holy protector')",
                "help": "Think about your playstyle. Do you want to hit things with a sword (Fighter), cast massive fireballs (Wizard), steal things in the dark (Rogue), or heal your friends (Cleric)?"
            },
            "species": {
                "q": "What about your lineage? Are you a classic Human, an elegant Elf, a sturdy Dwarf, or something more exotic like a Tiefling (demon-blood) or Orc?",
                "help": "Species give you unique traits. Humans are versatile, Elves have keen senses, Dwarves are tough, Tieflings have fire resistance and horns, and Orcs are relentlessly strong."
            },
            "background": {
                "q": "Now for your history. Were you a noble, a criminal, a scholar, or perhaps a soldier?",
                "help": "Your background defines who you were before adventuring. A Criminal knows the underworld; a Noble has political ties; a Scholar knows the ancient libraries."
            },
            "name": {
                "q": "We have the build, but you need a name. What shall the world call you?",
                "help": "Just tell me the name you want to use in the game!"
            },
            "bond": {"q": "Who or what is the one thing your character would do anything to protect?", "help": "A bond could be a sibling, a mentor, a hometown, or a sacred relic."},
            "secret": {"q": "Every hero has a secret. What is yours?", "help": "Maybe you stole a royal seal, or you're actually a spy for a rival kingdom."},
            "short_goal": {"q": "What is the immediate thing you are trying to achieve right now?", "help": "Example: 'Find a way into the city' or 'Pay off my gambling debts'."},
            "long_goal": {"q": "In the long run, what is your ultimate ambition?", "help": "Example: 'Become the Archmage of the Tower' or 'Avenge my fallen clan'."}
        }

        # Determine which key we are currently asking about
        current_key = None
        if self.state.selected_options["class"] is None: current_key = "class"
        elif self.state.selected_options["species"] is None: current_key = "species"
        elif self.state.selected_options["background"] is None: current_key = "background"
        elif self.state.selected_options["name"] is None: current_key = "name"
        else:
            for detail in ["bond", "secret", "short_goal", "long_goal"]:
                if self.state.is_missing(detail):
                    current_key = detail
                    break
        
        if current_key:
            self.last_question_key = current_key
            self.last_question = self.prompts[current_key]["q"]
            return self.last_question
        return None

    def process_input(self, user_text):
        text = user_text.lower()
        
        # 1. DETECT CONFUSION / UNCERTAINTY
        confusion_keywords = ["what", "unsure", "idk", "idontknow", "unknown", "explain", "help", "confused", "those"]
        if any(k in text for k in confusion_keywords):
            # Return a special signal that we need to provide help instead of updating state
            return {"status": "needs_help", "message": self.prompts[self.last_question_key]["help"]}

        # 2. MAPPING LOGIC (Extraction)
        updated = False
        
        # Class mapping
        classes = {
            "Wizard": ["magic", "spell", "intelligent", "scholar", "wizard"],
            "Rogue": ["sneaky", "stealth", "thief", "assassin", "rogue", "assassin"],
            "Fighter": ["strong", "warrior", "tank", "sword", "fighter"],
            "Cleric": ["holy", "healing", "priest", "cleric"],
            "Ranger": ["bow", "nature", "hunter", "ranger"],
            "Bard": ["music", "charm", "social", "bard"]
        }
        for cls, keywords in classes.items():
            if any(k in text for k in keywords):
                self.state.selected_options["class"] = cls
                updated = True

        # Species mapping
        species = {
            "Tiefling": ["tiefling", "infernal", "horns"],
            "Elf": ["elf", "elven", "graceful"],
            "Dwarf": ["dwarf", "sturdy", "mountain"],
            "Human": ["human", "versatile"],
            "Orc": ["orc", "strong", "relentless"],
            "Halfling": ["halfling", "small", "lucky"]
        }
        for spec, keywords in species.items():
            if any(k in text for k in keywords):
                self.state.selected_options["species"] = spec
                updated = True

        # Background mapping
        backgrounds = {
            "Scholar": ["scholar", "book", "library", "study"],
            "Criminal": ["criminal", "thief", "underworld", "street"],
            "Noble": ["noble", "wealthy", "court", "family"],
            "Soldier": ["soldier", "army", "war", "military"],
            "Acolyte": ["acolyte", "temple", "faith", "god"],
            "Outlander": ["outlander", "wilds", "forest", "nature"]
        }
        for bg, keywords in backgrounds.items():
            if any(k in text for k in keywords):
                self.state.selected_options["background"] = bg
                updated = True

        # Name extraction
        if self.state.is_missing("name") and not updated and len(text.split()) <= 2:
            self.state.selected_options["name"] = user_text.strip().capitalize()
            updated = True

        # Details extraction
        if not updated:
            current_key = self.last_question_key
            if current_key in ["bond", "secret", "short_goal", "long_goal"]:
                self.state.details[current_key] = user_text
                updated = True

        if updated:
            return {"status": "updated", "state": self.state}
        else:
            return {"status": "unrecognized", "message": "I'm not sure I caught that. Could you try describing it differently?"}
