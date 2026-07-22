import json
import math

class CharacterBuilder:
    def __init__(self, options_path):
        with open(options_path, 'r') as f:
            self.options = json.load(f)
        
        self.playstyle_map = {
            "Strong/tanky": ("Fighter", "Soldier", ["Dwarf", "Orc"]),
            "Sneaky/fast": ("Rogue", "Criminal", ["Elf", "Halfling"]),
        }

    def calculate_modifier(self, score):
        return math.floor((score - 10) / 2)

    def build_character(self, playstyle, name):
        cls_name, bg_name, species_list = self.playstyle_map.get(playstyle, ("Rogue", "Criminal", ["Elf"]))
        
        # Stat Assignment logic
        priority = self.options['classes'][cls_name]['stat_priority']
        stat_array = sorted(self.options['stat_array'], reverse=True)
        scores = {stat: stat_array[i] for i, stat in enumerate(priority)}
        
        # Derived calculations
        modifiers = {stat: self.calculate_modifier(score) for stat, score in scores.items()}
        
        # Construct final profile...
        return {"name": name, "scores": scores, "modifiers": modifiers}
