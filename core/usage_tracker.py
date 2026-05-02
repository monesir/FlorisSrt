import os
import json
import uuid
import time
import shutil

class UsageTracker:
    def __init__(self, run_id=None):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.usage_dir = os.path.join(self.base_dir, 'app_data', 'usage')
        os.makedirs(self.usage_dir, exist_ok=True)
        
        self.ledger_path = os.path.join(self.usage_dir, 'usage_ledger.json')
        self.pricing_path = os.path.join(self.usage_dir, 'pricing.json')
        
        self.run_id = run_id or str(uuid.uuid4())
        self.buffer = []
        
        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.ledger_path):
            self._write_atomic({"entries": []}, self.ledger_path)
                
        if not os.path.exists(self.pricing_path):
            default_pricing = {
                "pricing": {
                    "openai:gpt-4o": {"input_per_million": 2.5, "output_per_million": 10.0},
                    "openai:gpt-4o-mini": {"input_per_million": 0.15, "output_per_million": 0.60},
                    "deepseek:deepseek-chat": {"input_per_million": 0.14, "output_per_million": 0.28}
                }
            }
            self._write_atomic(default_pricing, self.pricing_path)

    def _write_atomic(self, data, path):
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_path, path)
        except Exception as e:
            print(f"Error writing atomic: {e}")

    def record_usage(self, project: str, episode: str, provider: str, model: str, prompt_tokens: int, completion_tokens: int, estimated: bool = False):
        entry = {
            "id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "timestamp": int(time.time()),
            "project": project,
            "episode": episode,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated": estimated
        }
        
        self.buffer.append(entry)
        if len(self.buffer) >= 10:
            self.flush()

    def flush(self):
        if not self.buffer:
            return
            
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {"entries": []}
            
        data.setdefault("entries", []).extend(self.buffer)
        self._write_atomic(data, self.ledger_path)
        self.buffer.clear()

    def get_ledger(self, limit=1000) -> list:
        # Load ledger and return the last `limit` entries
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                entries = data.get("entries", [])
                return entries[-limit:] if limit else entries
        except Exception:
            return []
            
    def get_current_run_stats(self) -> tuple:
        """Returns (tokens, cost) for the latest run_id in the ledger/buffer"""
        tokens = 0
        cost = 0.0
        
        all_entries = self.get_ledger(limit=None) + self.buffer
        if not all_entries:
            return tokens, cost
            
        latest_run_id = all_entries[-1].get("run_id")
        
        for entry in all_entries:
            if entry.get("run_id") == latest_run_id:
                p_tok = entry.get("prompt_tokens", 0)
                c_tok = entry.get("completion_tokens", 0)
                prov = entry.get("provider", "")
                model = entry.get("model", "")
                tokens += (p_tok + c_tok)
                cost += self.calculate_cost(prov, model, p_tok, c_tok)
                
        return tokens, cost

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
        self._write_atomic(data, self.pricing_path)

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
        if os.path.exists(self.ledger_path):
            backup_path = self.ledger_path + f".backup_{int(time.time())}"
            shutil.copy2(self.ledger_path, backup_path)
            
        self._write_atomic({"entries": []}, self.ledger_path)
        self.buffer.clear()
