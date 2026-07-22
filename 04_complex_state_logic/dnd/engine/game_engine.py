import uuid
from core.rules_engine import RulesEngine
from core.state_manager import StateManager
from core.formatter import print_character_sheet
from agents.character_agent import CharacterAgent
from agents.jarvis_agent import JarvisAgent

class GameEngine:
    def __init__(self):
        self.rules = RulesEngine()
        self.state = StateManager()
        self.char_agent = CharacterAgent()
        self.jarvis = JarvisAgent()
        self.active_character_id = None

    def run_interactive_creation(self):
        print("\n🛡️  WELCOME TO THE HERMES CHARACTER ARCHITECT")
        print("--------------------------------------------------")
        
        while True:
            question = self.char_agent.get_next_question()
            if not question: break
            
            print(f"\n🤖 Agent: {question}")
            user_input = input("👤 You: ").strip()
            if not user_input: continue

            result = self.char_agent.process_input(user_input)
            if result["status"] == "needs_help":
                print(f"\n💡 Guide: {result['message']}")
            elif result["status"] == "unrecognized":
                print(f"\n🤔 Agent: {result['message']}")
            elif result["status"] == "updated":
                print("✅ Got it!")

        print("\n✨ Finalizing your high-detail character sheet...")
        
        choices = self.char_agent.state.selected_options
        details = self.char_agent.state.details
        
        character = self.rules.build_character(
            name=choices["name"] or "Unnamed Hero",
            char_class=choices["class"] or "Rogue",
            species=choices["species"] or "Human",
            background=choices["background"] or "Criminal",
            weapon_name="Shortsword",
            bond=details["bond"],
            secret=details["secret"],
            short_goal=details["short_goal"],
            long_goal=details["long_goal"]
        )
        
        self.state.save_character(character)
        
        # Final Display using the Original Builder's style
        print_character_sheet(character)
        
        initial_state = {
            "current_hp": character['gameplay_profile']['combat']['max_hp'],
            "location": "Starting Area",
            "action_economy": {"action_used": False, "bonus_action_used": False},
        }
        self.state.save_state(character['entity_id'], initial_state)
        self.active_character_id = character['entity_id']
        return character

    def get_tactical_advice(self):
        if not self.active_character_id: return "No character active."
        char = self.state.load_character(self.active_character_id)
        state = self.state.load_state(self.active_character_id)
        return self.jarvis.suggest_action(char, state)

if __name__ == "__main__":
    engine = GameEngine()
    engine.run_interactive_creation()
    print("\n--- Quick Test: Tactical Advice ---")
    print(f"🤖 Jarvis: {engine.get_tactical_advice()['tactical_advice']}")
