
import asyncio
import json
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import socketserver
import websockets
from websockets import serve

from logic import Game, W, H, PADDLE_W, PADDLE_H, BALL_SIZE, FPS, TICK

# ─── Shared game instance + connected clients ─────────────────────────────
game    = Game()
clients = set()

async def game_loop():
    while True:
        t0 = asyncio.get_event_loop().time()
        game.tick()
        if clients:
            msg = json.dumps({"type": "state", **game.state()})
            await asyncio.gather(*[c.send(msg) for c in list(clients)],
                                 return_exceptions=True)
        elapsed = asyncio.get_event_loop().time() - t0
        await asyncio.sleep(max(0, TICK - elapsed))

async def handler(ws):
    clients.add(ws)
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            action = msg.get("action")
            if action == "move":
                dy = float(msg.get("dy", 0))
                game.player.y += dy
                game.player.clamp()
            elif action == "ai_move":
                # This client is now the AI agent
                game.ai_client = ws
                dy = float(msg.get("dy", 0))
                game.ai.y += dy
                game.ai.clamp()
            elif action == "start":
                if game.winner:
                    game.reset()
                game.paused = False
            elif action == "reset":
                game.reset()
    finally:
        if game.ai_client == ws:
            game.ai_client = None
        clients.discard(ws)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Pong vs AI Agent</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0a0a0a; display: flex; flex-direction: column;
         align-items: center; justify-content: center; height: 100vh;
         font-family: 'Courier New', monospace; color: #eee; }
  h1   { font-size: 1.1rem; letter-spacing: .3em; margin-bottom: 10px;
         color: #aaa; text-transform: uppercase; }
  canvas { border: 1px solid #222; box-shadow: 0 0 20px rgba(0,0,0,0.5); }
  #info { margin-top: 12px; font-size: .78rem; color: #555; }
</style>
</head>
<body>
<h1 id="title">Pong &mdash; You vs Hermes</h1>
<canvas id="c" width="800" height="600"></canvas>
<div id="info">W/S or mouse to move &nbsp;|&nbsp; SPACE to start &nbsp;|&nbsp; R to reset</div>
<script>
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
const W = 800, H = 600;

let state = null;
let lastState = null;
let lerpFactor = 0;
const ws  = new WebSocket(`ws://${location.hostname}:8765`);

ws.onmessage = e => { 
    lastState = state;
    state = JSON.parse(e.data); 
    lerpFactor = 0;
};
ws.onclose   = () => { document.getElementById('info').textContent = 'Disconnected — refresh to reconnect'; };

const MOVE = 7;
const keys = {};
document.addEventListener('keydown', e => {
  keys[e.key] = true;
  if (e.key === ' ')  { e.preventDefault(); send({action:'start'}); }
  if (e.key === 'r' || e.key === 'R') send({action:'reset'});
});
document.addEventListener('keyup',  e => { keys[e.key] = false; });

canvas.addEventListener('mousemove', e => {
  const rect = canvas.getBoundingClientRect();
  const my   = e.clientY - rect.top;
  if (state) {
    const dy = my - state.player.y;
    send({action:'move', dy: Math.max(-MOVE, Math.min(MOVE, dy))});
  }
});

function send(obj) {
  if (ws.readyState === 1) ws.send(JSON.stringify(obj));
}

setInterval(() => {
  if (keys['w'] || keys['W'] || keys['ArrowUp'])   send({action:'move', dy:-MOVE});
  if (keys['s'] || keys['S'] || keys['ArrowDown'])  send({action:'move', dy: MOVE});
}, 16);

function lerp(a, b, t) { return a + (b - a) * t; }

function draw() {
  if (!state) return;
  
  // Simple interpolation for smoothness
  lerpFactor += 0.2; // Speed of transition to new state
  if (lerpFactor > 1) lerpFactor = 1;

  const s = state;
  const prev = lastState || state;
  
  const curBallX = lerp(prev.ball.x, s.ball.x, lerpFactor);
  const curBallY = lerp(prev.ball.y, s.ball.y, lerpFactor);
  const curPlayerY = lerp(prev.player.y, s.player.y, lerpFactor);
  const curAiY = lerp(prev.ai.y, s.ai.y, lerpFactor);

  const pw = s.pw, ph = s.ph;

  document.getElementById('title').textContent = s.ai_mode === 'AGENT' 
    ? 'Pong &mdash; You vs AI Agent' 
    : 'Pong &mdash; You vs Hermes';

  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, W, H);

  ctx.setLineDash([10, 10]);
  ctx.strokeStyle = '#222';
  ctx.lineWidth   = 2;
  ctx.beginPath(); ctx.moveTo(W/2, 0); ctx.lineTo(W/2, H); ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle   = '#333';
  ctx.font        = 'bold 64px Courier New';
  ctx.textAlign   = 'center';
  ctx.fillText(s.player.score, W/2 - 100, 80);
  ctx.fillText(s.ai.score,     W/2 + 100, 80);

  ctx.font      = '11px Courier New';
  ctx.fillStyle = '#444';
  ctx.fillText('YOU',    W/2 - 100, 100);
  ctx.fillText(s.ai_mode === 'AGENT' ? 'AGENT' : 'HERMES', W/2 + 100, 100);

  ctx.fillStyle = '#eee';
  ctx.beginPath();
  roundRect(ctx, 40 - pw/2, curPlayerY - ph/2, pw, ph, 4);
  ctx.fill();

  ctx.fillStyle = s.ai_mode === 'AGENT' ? '#f4a' : '#4af';
  ctx.beginPath();
  roundRect(ctx, W-40 - pw/2, curAiY - ph/2, pw, ph, 4);
  ctx.fill();

  ctx.fillStyle = '#fff';
  ctx.beginPath();
  ctx.arc(curBallX, curBallY, s.ball.size/2, 0, Math.PI*2);
  ctx.fill();

  if (s.winner) {
    overlay(s.winner === 'You' ? '🎉 You win!' : '🤖 AI wins!',
            'Press SPACE to play again');
  } else if (s.paused) {
    overlay('Pong vs AI', 'Press SPACE to start');
  }

  if (!s.paused && s.rally > 4) {
    ctx.fillStyle = '#333';
    ctx.font      = '12px Courier New';
    ctx.textAlign = 'center';
    ctx.fillText(`rally ${s.rally}`, W/2, H - 14);
  }
  
  requestAnimationFrame(draw);
}

function overlay(title, sub) {
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  ctx.fillRect(0, 0, W, H);
  ctx.textAlign = 'center';
  ctx.fillStyle = '#eee';
  ctx.font      = 'bold 36px Courier New';
  ctx.fillText(title, W/2, H/2 - 16);
  ctx.fillStyle = '#666';
  ctx.font      = '14px Courier New';
  ctx.fillText(sub, W/2, H/2 + 18);
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.moveTo(x+r, y);
  ctx.arcTo(x+w, y,   x+w, y+h, r);
  ctx.arcTo(x+w, y+h, x,   y+h, r);
  ctx.arcTo(x,   y+h, x,   y,   r);
  ctx.arcTo(x,   y,   x+w, y,   r);
  ctx.closePath();
}

requestAnimationFrame(draw);
</script>
</body>
</html>
"""

def http_server(port):
    import socketserver, io
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            body = HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type',   'text/html; charset=utf-8')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *a): pass
    with socketserver.TCPServer(('', port), H) as srv:
        srv.serve_forever()

async def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    http_port = port - 1
    t = threading.Thread(target=http_server, args=(http_port,), daemon=True)
    t.start()
    print(f"\\n  Pong vs Hermes/Agent")
    print(f"  ──────────────────────────────────────────")
    print(f"  WebSocket  →  ws://localhost:{port}")
    print(f"  Browser    →  http://localhost:{http_port}")
    print(f"\\n  SSH tunnel command (run on your LOCAL machine):")
    print(f"    ssh -L {port}:localhost:{port} -L {http_port}:localhost:{http_port} cxiong@friston.lps.umd.edu")
    print(f"\\n  Then open http://localhost:{http_port} in your browser.")
    print(f"  Ctrl+C to stop.\\n")
    asyncio.create_task(game_loop())
    async with serve(handler, 'localhost', port):
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())
