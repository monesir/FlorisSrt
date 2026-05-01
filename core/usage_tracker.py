import os
import json
import uuid
import time
from datetime import datetime

class UsageTracker:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_dir = os.path.join(self.base_dir, 'config')
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.ledger_path = os.path.join(self.config_dir, 'usage_ledger.json')
        self.pricing_path = os.path.join(self.config_dir, 'pricing.json')
        
        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.ledger_path):
            with open(self.ledger_path, 'w', encoding='utf-8') as f:
                json.dump({"entries": []}, f, indent=4)
                
        if not os.path.exists(self.pricing_path):
            default_pricing = {
                "pricing": {
                    "openai:gpt-4o": {"input_per_million": 2.5, "output_per_million": 10.0},
                    "openai:gpt-4o-mini": {"input_per_million": 0.15, "output_per_million": 0.60},
                    "deepseek:deepseek-chat": {"input_per_million": 0.14, "output_per_million": 0.28}
                }
            }
            with open(self.pricing_path, 'w', encoding='utf-8') as f:
                json.dump(default_pricing, f, indent=4)

    def record_usage(self, project: str, episode: str, provider: str, model: str, prompt_tokens: int, completion_tokens: int, estimated: bool = False):
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": int(time.time()),
            "project": project,
            "episode": episode,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated": estimated
        }
        
        # Load ledger, append, save
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {"entries": []}
            
        data.setdefault("entries", []).append(entry)
        
        with open(self.ledger_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_ledger(self) -> list:
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("entries", [])
        except Exception:
            return []

    def get_pricing(self) -> dict:
        try:
            with open(self.pricing_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("pricing", {})
        except Exception:
            return {}

    def save_pricing(self, pricing_dict: dict):
        try:
            with open(self.pricing_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {"pricing": {}}
            
        data["pricing"] = pricing_dict
        
        with open(self.pricing_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def calculate_cost(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self.get_pricing()
        key = f"{provider}:{model}"
        if key in pricing:
            rate_in = pricing[key].get("input_per_million", 0)
            rate_out = pricing[key].get("output_per_million", 0)
            
            cost_in = (prompt_tokens / 1_000_000) * rate_in
            cost_out = (completion_tokens / 1_000_000) * rate_out
            return cost_in + cost_out
        return 0.0

    def clear_ledger(self):
        with open(self.ledger_path, 'w', encoding='utf-8') as f:
            json.dump({"entries": []}, f, indent=4)
