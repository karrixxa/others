import json
import os
from datetime import datetime

class PlanBuffer:
    """
    Implements the TRD 2.2 Plan Buffer: A temporary, non-persistent 
    storage area for drafting a sequence of intended actions.
    """
    def __init__(self, storage_dir="/home/cxiong/hermes_rpg/plan_buffers"):
        self.storage_dir = storage_dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)

    def _get_path(self, entity_id):
        return os.path.join(self.storage_dir, f"{entity_id}_plan.json")

    def clear(self, entity_id):
        """Wipes the current plan buffer."""
        path = self._get_path(entity_id)
        if os.path.exists(path):
            os.remove(path)
        return {"status": "cleared", "entity_id": entity_id}

    def add_action(self, entity_id, action):
        """Appends an action to the sequence. Action should be a dict: {type, target, value}."""
        path = self._get_path(entity_id)
        plan = self.get_plan(entity_id)
        
        plan["sequence"].append({
            "timestamp": datetime.now().isoformat(),
            "action": action
        })
        
        with open(path, 'w') as f:
            json.dump(plan, f, indent=2)
        
        return {"status": "added", "current_sequence": plan["sequence"]}

    def get_plan(self, entity_id):
        """Retrieves the current drafted plan."""
        path = self._get_path(entity_id)
        if not os.path.exists(path):
            return {"entity_id": entity_id, "sequence": [], "status": "empty"}
        
        with open(path, 'r') as f:
            return json.load(f)

    def commit_plan(self, entity_id):
        """
        Finalizes the plan for execution. 
        Returns the sequence to be sent to the Game Engine.
        """
        plan = self.get_plan(entity_id)
        sequence = plan.get("sequence", [])
        
        if not sequence:
            return {"status": "error", "message": "Plan buffer is empty."}
        
        # Once committed, we clear the buffer
        self.clear(entity_id)
        
        return {
            "status": "committed",
            "entity_id": entity_id,
            "execution_batch": sequence
        }
