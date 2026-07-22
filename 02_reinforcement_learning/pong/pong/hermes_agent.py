import asyncio
import json
import websockets
import math

async def run_agent():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        print(f"Connected to Pong server at {uri}")
        
        # Initialize as the AI agent
        await websocket.send(json.dumps({"action": "ai_move", "dy": 0}))
        
        last_state = None
        while True:
            try:
                message = await websocket.recv()
                state = json.loads(message)
                
                if state.get("type") == "state":
                    # Extract relevant info
                    ball_y = state["ball"]["y"]
                    ai_y = state["ai"]["y"]
                    ball_vx = state["ball"]["vx"] if "vx" in state["ball"] else 0 # Server doesn't send vx by default in the provided code, but let's check
                    
                    # Simple logic: Move towards ball.y
                    # Note: The server we wrote didn't send vx/vy in game.state(), 
                    # just x, y, size. So we just track current Y.
                    
                    dy = 0
                    error_margin = 10
                    if abs(ai_y - ball_y) > error_margin:
                        dy = 5 if ai_y < ball_y else -5
                    
                    # Send movement
                    await websocket.send(json.dumps({"action": "ai_move", "dy": dy}))
                    
                    if state["winner"]:
                        print(f"Game Over! Winner: {state['winner']}")
                        break
            except Exception as e:
                print(f"Error: {e}")
                break

if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        pass
