import sqlite3
import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Jarvis RPG API")

DB_PATH = "/home/cxiong/hermes_rpg/hermes_rpg.db"

class PlanRequest(BaseModel):
    actions: List[Dict[str, Any]]

@app.get("/perception/{entity_id}")
async def get_perception(entity_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    char_res = conn.execute("SELECT character_id FROM characters WHERE entity_id = ?", (entity_id,)).fetchone()
    if not char_res:
        conn.close()
        raise HTTPException(status_code=404, detail="Entity not found")
    cid = char_res['character_id']
    sql = "SELECT gs.current_hp, gs.temp_hp, gs.turn_status, cs.strength, cs.dexterity, cs.constitution, cs.intelligence, cs.wisdom, cs.charisma, ri.name as active_weapon, ri.damage_dice as weapon_dmg, GROUP_CONCAT(ac.condition_id) as conditions FROM game_state gs JOIN character_stats cs ON gs.character_id = cs.character_id LEFT JOIN inventory inv ON gs.character_id = inv.character_id AND inv.is_equipped = 1 LEFT JOIN registry_items ri ON inv.item_id = ri.item_id LEFT JOIN active_conditions ac ON gs.character_id = ac.character_id WHERE gs.character_id = ? GROUP BY gs.character_id"
    res = conn.execute(sql, (cid,)).fetchone()
    conn.close()
    if not res:
        raise HTTPException(status_code=404, detail="State not found")
    return dict(res)

@app.post("/plan/draft/{entity_id}")
async def draft_plan(entity_id: str, request: PlanRequest):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO plan_buffer (entity_id, draft_plan, status) VALUES (?, ?, 'DRAFT')", (entity_id, json.dumps(request.actions)))
    conn.commit()
    conn.close()
    return {"status": "Plan drafted in buffer"}

@app.post("/plan/commit/{entity_id}")
async def commit_plan(entity_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    plan = conn.execute("SELECT draft_plan FROM plan_buffer WHERE entity_id = ? AND status = 'DRAFT'", (entity_id,)).fetchone()
    if plan:
        conn.execute("UPDATE plan_buffer SET status = 'COMMITTED' WHERE entity_id = ? ", (entity_id,))
        conn.commit()
        conn.close()
        return {"status": "Plan committed to engine", "plan": json.loads(plan['draft_plan'])}
    conn.close()
    raise HTTPException(status_code=404, detail="No draft plan found to commit")

@app.post("/hp/update/{entity_id}")
async def update_hp(entity_id: str, amount: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    char_res = conn.execute("SELECT character_id FROM characters WHERE entity_id = ?", (entity_id,)).fetchone()
    if not char_res:
        conn.close()
        raise HTTPException(status_code=404, detail="Entity not found")
    cid = char_res['character_id']
    stat_res = conn.execute("SELECT s.constitution, r.base_hit_die FROM character_stats s JOIN characters c ON c.character_id = s.character_id JOIN registry_classes r ON c.class_id = r.class_id WHERE c.character_id = ?", (cid,)).fetchone()
    max_hp = stat_res['base_hit_die'] + ((stat_res['constitution'] - 10) // 2)
    curr_res = conn.execute("SELECT current_hp FROM game_state WHERE character_id = ?", (cid,)).fetchone()
    new_hp = max(0, min(max_hp, curr_res['current_hp'] + amount))
    conn.execute("UPDATE game_state SET current_hp = ? WHERE character_id = ?", (new_hp, cid))
    conn.commit()
    conn.close()
    return {"new_hp": new_hp, "max_hp": max_hp}
