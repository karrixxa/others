import requests
import json
import time
import sys

# ==================================================================
# CONFIGURATION
# ==================================================================
GATEWAY_URL = "http://localhost:9091"  # Adjust if the Gateway is on a different host
POLL_INTERVAL = 1.0  # Seconds between state checks

class JarvisBridge:
    def __init__(self):
        self.last_state_hash = None

    def get_game_state(self):
        """Fetch the current world state from the Gateway."""
        try:
            response = requests.get(f"{GATEWAY_URL}/state", timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[ERROR] Failed to connect to Gateway: {e}")
        return None

    def send_commands(self, commands):
        """Send a list of state-changing commands to the Gateway."""
        if not commands:
            return
        
        try:
            payload = {"commands": commands}
            response = requests.post(f"{GATEWAY_URL}/execute", json=payload, timeout=2)
            if response.status_code == 200:
                print(f"[SUCCESS] Executed {len(commands)} commands.")
                return response.json()
        except Exception as e:
            print(f"[ERROR] Failed to send commands: {e}")
        return None

    def run_loop(self):
        """
        Main loop to bridge the Game Engine and the Agent.
        In a real deployment, this would be called by the Hermes Agent framework,
        but as a standalone, it monitors the state.
        """
        print(f"Jarvis Bridge Active. Monitoring Gateway at {GATEWAY_URL}...")
        try:
            while True:
                state = self.get_game_state()
                if state:
                    # Calculate a simple hash to see if something actually changed
                    state_hash = hash(json.dumps(state, sort_keys=True))
                    if state_hash != self.last_state_hash:
                        print("\n[STATE CHANGE DETECTED]")
                        # In a live Hermes session, this state would be injected into the prompt.
                        # For this bridge, we print the summary for the agent.
                        self.summarize_state(state)
                        self.last_state_hash = state_hash
                
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nBridge shut down.")

    def summarize_state(self, state):
        """Creates a high-fidelity tactical briefing for the Jarvis Agent."""
        entities = state.get("entities", {})
        if not entities:
            return "The world is currently empty. No entities detected."

        briefing = ["### 🗺️ TACTICAL WORLD SNAPSHOT"]
        
        # Separate players and threats for better agent reasoning
        players = []
        threats = []

        for eid, data in entities.items():
            pos = data.get("position", {"x": 0, "y": 0})
            vitals = data.get("vitals", {})
            hp = vitals.get("current_hp", 0)
            max_hp = vitals.get("max_hp", 0)
            name = data.get("identity", {}).get("name", eid)
            
            entry = f"- {name} [{eid}]: Pos({pos['x']},{pos['y']}) | HP: {hp}/{max_hp}"
            
            if "player" in eid:
                players.append(entry)
            else:
                threats.append(entry)

        if players:
            briefing.append("\n**Active Operatives:**")
            briefing.extend(players)
        
        if threats:
            briefing.append("\n**Detected Threats:**")
            briefing.extend(threats)
        
        final_report = "\n".join(briefing)
        print("\n" + "═"*60)
        print("🤖 JARVIS TACTICAL FEED")
        print("═"*60)
        print(final_report)
        print("═"*60)
        return final_report

if __name__ == "__main__":
    bridge = JarvisBridge()
    bridge.run_loop()
