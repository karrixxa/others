"""
Pong server — serves the HTML page and runs the game loop over WebSocket.
Usage: python3 server.py [port]   (default port 8765)
SSH port-forward: ssh -L 8765:localhost:8765 cxiong@friston.lps.umd.edu
Then open: http://localhost:8765 in your browser.
"""

import asyncio
import json
import math
import random
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import threading
import socket
import os

try:
    import websockets
    from websockets import serve
except ImportError:
    print("Install websockets: pip3 install websockets --break-system-packages")
    sys.exit(1)


  # ─── Constants ───────────────────────────────────────────────────────────
W, H         = 800, 600
PADDLE_W     = 12
PADDLE_H     = 90
BALL_SIZE     = 12
BALL_SPEED   = 5.0        # starting speed
MAX_SPEED    = 14.0
SPEED_INC    = 0.25       # speed increase per hit
WINNING      = 7          # first to this wins
FPS          = 60
TICK         = 1.0 / FPS

# Added Difficulty Profiles
DIFFICULTIES = {
    "easy":   {"speed": 3.0, "error": 40},
    "medium": {"speed": 4.2, "error": 18},
    "hard":   {"speed": 6.0, "error": 5},
}
CURRENT_DIFF = "medium"

# ─── Game State ──────────────────────────────────────────────────────────
class Ball:
    def __init__(self):
        self.reset()

    def reset(self, direction=1):
        self.x = W / 2
        self.y = H / 2
        self.size = BALL_SIZE
        angle = random.uniform(-30, 30)
        rad = math.radians(angle)
        self.vx = direction * BALL_SPEED * math.cos(rad)
        self.vy = BALL_SPEED * math.sin(rad)

    def speed(self):
        return math.hypot(self.vx, self.vy)

    def step(self):
        self.x += self.vx
        self.y += self.vy
        if self.y - self.size / 2 <= 0:
            self.y = self.size / 2
            self.vy = abs(self.vy)
        if self.y + self.size / 2 >= H:
            self.y = H - self.size / 2
            self.vy = -abs(self.vy)

class Paddle:
    def __init__(self, x):
        self.x = x
        self.y = H / 2
        self.w = PADDLE_W
        self.h = PADDLE_H
        self.score = 0

    def clamp(self):
        self.y = max(self.h / 2, min(H - self.h / 2, self.y))

    def rect(self):
        return (self.x - self.w/2, self.y - self.h/2,
                self.x + self.w/2, self.y + self.h/2)

class Game:
    def __init__(self):
        self.player  = Paddle(40)
        self.ai      = Paddle(W - 40)
        self.ball    = Ball()
        self.running = False
        self.paused  = True
        self.winner  = None
        self.rally   = 0
        self._ai_target = H / 2
        # Agent tracking
        self.ai_client = None 

    def _hits(self, paddle):
        l, t, r, b = paddle.rect()
        bx, by, bs = self.ball.x, self.ball.y, self.ball.size / 2
        return l - bs < bx < r + bs and t - bs < by < b + bs

    def _predict(self):
        if self.ball.vx <= 0:
            self._ai_target = H / 2
            return
        bx, by = self.ball.x, self.ball.y
        vx, vy = self.ball.vx, self.ball.vy
        target_x = self.ai.x
        for _ in range(300):
            bx += vx
            by += vy
            if by <= 0:        by = 0;  vy =  abs(vy)
            if by >= H:        by = H;  vy = -abs(vy)
            if bx >= target_x: break
        
        diff_cfg = DIFFICULTIES[CURRENT_DIFF]
        self._ai_target = by + random.uniform(-diff_cfg["error"], diff_cfg["error"])

    def _move_ai(self):
        diff = self._ai_target - self.ai.y
        speed = DIFFICULTIES[CURRENT_DIFF]["speed"]
        move = max(-speed, min(speed, diff))
        self.ai.y += move
        self.ai.clamp()

    def tick(self):
        if self.paused or self.winner:
            return

        self.ball.step()

        if self.ball.vx < 0 and self._hits(self.player):
            self.ball.x  = self.player.x + self.player.w/2 + self.ball.size/2
            self.ball.vx = abs(self.ball.vx)
            offset = (self.ball.y - self.player.y) / (self.player.h / 2)
            self.ball.vy = offset * 6
            self._bump_speed()
            self.rally  += 1
            self._predict()

        if self.ball.vx > 0 and self._hits(self.ai):
            self.ball.x  = self.ai.x - self.ai.w/2 - self.ball.size/2
            self.ball.vx = -abs(self.ball.vx)
            offset = (self.ball.y - self.ai.y) / (self.ai.h / 2)
            self.ball.vy = offset * 6
            self._bump_speed()
            self.rally  += 1
            self._predict()

        # Only run internal AI if no external agent is controlling the paddle
        if self.ai_client is None:
            self._move_ai()

        if self.ball.x < 0:
            self.ai.score += 1
            self._check_winner()
            self.ball.reset(direction=1)
            self.rally = 0
            self._predict()
        elif self.ball.x > W:
            self.player.score += 1
            self._check_winner()
            self.ball.reset(direction=-1)
            self.rally = 0

    def _bump_speed(self):
        spd = self.ball.speed()
        if spd < MAX_SPEED:
            scale = (spd + SPEED_INC) / spd
            self.ball.vx *= scale
            self.ball.vy *= scale

    def _check_winner(self):
        if self.player.score >= WINNING:
            self.winner = "You"
            self.paused = True
        elif self.ai.score >= WINNING:
            self.winner = "Hermes"
            self.paused = True

    def state(self):
        return {
            "ball":   {"x": self.ball.x, "y": self.ball.y, "size": self.ball.size},
            "player": {"y": self.player.y, "score": self.player.score},
            "ai":     {"y": self.ai.y,     "score": self.ai.score},
            "winner": self.winner,
            "paused": self.paused,
            "rally":  self.rally,
            "W": W, "H": H,
            "pw": PADDLE_W, "ph": PADDLE_H,
            "ai_mode": "AGENT" if self.ai_client else "INTERNAL"
        }

    def reset(self):
        self.player.score = 0
        self.ai.score     = 0
        self.rally        = 0
        self.winner       = None
        self.paused       = True
        self.ball.reset()
        self._ai_target   = H / 2
