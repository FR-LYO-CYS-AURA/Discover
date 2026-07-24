"""
Suivi de consommation LLM DISCOVER (tokens, coût, durée).

UsageTracker accumule de façon thread-safe les métriques des appels LLM, afin
d'attribuer une consommation par étape de simulation (snapshot avant/après).
"""

import threading
from typing import Dict, Any


class UsageTracker:
    """Accumulateur thread-safe de consommation LLM."""

    def __init__(self):
        self._lock = threading.Lock()
        self.calls = 0
        self.tokens_input = 0
        self.tokens_output = 0
        self.tokens_reasoning = 0
        self.tokens_total = 0
        self.cost = 0.0
        self.duration = 0.0  # secondes cumulées d'appels LLM

    def record(self, tokens_input: int = 0, tokens_output: int = 0,
               tokens_reasoning: int = 0, tokens_total: int = 0,
               cost: float = 0.0, duration: float = 0.0) -> None:
        with self._lock:
            self.calls += 1
            self.tokens_input += int(tokens_input or 0)
            self.tokens_output += int(tokens_output or 0)
            self.tokens_reasoning += int(tokens_reasoning or 0)
            if tokens_total:
                self.tokens_total += int(tokens_total)
            else:
                self.tokens_total += int(tokens_input or 0) + int(tokens_output or 0) + int(tokens_reasoning or 0)
            self.cost += float(cost or 0.0)
            self.duration += float(duration or 0.0)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "calls": self.calls,
                "tokens_input": self.tokens_input,
                "tokens_output": self.tokens_output,
                "tokens_reasoning": self.tokens_reasoning,
                "tokens_total": self.tokens_total,
                "cost": round(self.cost, 6),
                "duration": round(self.duration, 3),
            }

    @staticmethod
    def delta(after: Dict[str, Any], before: Dict[str, Any]) -> Dict[str, Any]:
        """Différence entre deux snapshots (métriques d'une étape)."""
        return {
            "llm_calls": after["calls"] - before["calls"],
            "tokens_input": after["tokens_input"] - before["tokens_input"],
            "tokens_output": after["tokens_output"] - before["tokens_output"],
            "tokens_reasoning": after["tokens_reasoning"] - before["tokens_reasoning"],
            "tokens_total": after["tokens_total"] - before["tokens_total"],
            "cost": round(after["cost"] - before["cost"], 6),
        }
