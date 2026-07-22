import sqlite3
import json
import os

DB_PATH = '/home/cxiong/hermes_rpg/game_data.db'

class StateManager:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        # We will drop and recreate the tables to ensure the schema is exactly what the new system needs.
        # In a production app, we'd use migrations, but for the project's current stage, this is safest.
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DROP TABLE IF EXISTS characters')
        cursor.execute('DROP TABLE IF EXISTS character_states')
        
        cursor.execute('''
            CREATE TABLE characters (
                entity_id TEXT PRIMARY KEY,
                build_json TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE character_states (
                entity_id TEXT PRIMARY KEY,
                state_json TEXT,
                FOREIGN KEY (entity_id) REFERENCES characters (entity_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def save_character(self, character):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO characters (entity_id, build_json) VALUES (?, ?)', 
                       (character['entity_id'], json.dumps(character)))
        conn.commit()
        conn.close()

    def save_state(self, entity_id, state):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO character_states (entity_id, state_json) VALUES (?, ?)', 
                       (entity_id, json.dumps(state)))
        conn.commit()
        conn.close()

    def load_character(self, entity_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT build_json FROM characters WHERE entity_id = ?', (entity_id,))
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None

    def load_state(self, entity_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT state_json FROM character_states WHERE entity_id = ?', (entity_id,))
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None
