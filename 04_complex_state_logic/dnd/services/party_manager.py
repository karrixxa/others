
import json
import os

PARTY_FILE = "/home/cxiong/hermes_rpg/profiles/party_registry.json"

def get_party(entity_id):
    if not os.path.exists(PARTY_FILE): return None
    with open(PARTY_FILE, 'r') as f:
        parties = json.load(f)
    for party_id, members in parties.items():
        if entity_id in members:
            return party_id, members
    return None, None

def join_party(entity_id, party_id="party_01"):
    parties = {}
    if os.path.exists(PARTY_FILE):
        with open(PARTY_FILE, 'r') as f:
            parties = json.load(f)
    
    if party_id not in parties:
        parties[party_id] = []
    
    if entity_id not in parties[party_id]:
        parties[party_id].append(entity_id)
    
    with open(PARTY_FILE, 'w') as f:
        json.dump(parties, f, indent=4)
    return party_id
