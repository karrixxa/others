import sqlite3
import json
from typing import Dict, Any, List, Optional

# ==================================================================
# COMMON DB - SQLITE UPGRADE v2.0
# ==================================================================
# This library ensures high-concurrency data consistency for the
# distributed C2 architecture using SQLite.

class CommonDB:
    def __init__(self, db_path: str = "/home/cxiong/hermes_rpg/data/game_data.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        # check_same_thread=False is required for FastAPI multi-threaded environments
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS entities (entity_type TEXT, entity_id TEXT, data TEXT, PRIMARY KEY (entity_type, entity_id))")
            conn.commit()

    def get_entity(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT data FROM entities WHERE entity_type = ? AND entity_id = ?",
                    (entity_type, entity_id)
                )
                row = cursor.fetchone()
                return json.loads(row[0]) if row else None
        except Exception as e:
            print(f"[CommonDB Error] Failed to get {entity_id}: {e}")
            return None

    def update_entity(self, entity_type: str, entity_id: str, update_data: Dict[str, Any]) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT data FROM entities WHERE entity_type = ? AND entity_id = ?",
                    (entity_type, entity_id)
                )
                row = cursor.fetchone()
                data = json.loads(row[0]) if row else {}

                for key, value in update_data.items():
                    if isinstance(value, dict) and key in data and isinstance(data[key], dict):
                        data[key].update(value)
                    else:
                        data[key] = value

                conn.execute(
                    "INSERT OR REPLACE INTO entities (entity_type, entity_id, data) VALUES (?, ?, ?)",
                    (entity_type, entity_id, json.dumps(data))
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"[CommonDB Error] Failed to update {entity_id}: {e}")
            return False

    def create_entity(self, entity_type: str, entity_id: str, initial_data: Dict[str, Any]) -> bool:
        return self.update_entity(entity_type, entity_id, initial_data)

    def list_entities(self, entity_type: str) -> List[str]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT entity_id FROM entities WHERE entity_type = ?",
                    (entity_type,)
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[CommonDB Error] Failed to list {entity_type}: {e}")
            return []

db = CommonDB()
