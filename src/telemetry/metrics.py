import time
from typing import Dict, Any, List
from src.telemetry.logger import logger

class PerformanceTracker:
    """
    Tracking industry-standard metrics for LLMs.
    """
    def __init__(self):
        self.session_metrics = []

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """
        Logs a single request metric to our telemetry.
        """
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "cost_estimate": self._calculate_cost(model, usage) # Mock cost calculation
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        Calculates the estimated monetary cost of the LLM generation based on
        official pricing models (per 1,000,000 tokens).
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        model_key = model.lower()
        
        # Local model runs on CPU - cost is absolutely $0.00
        if "local" in model_key or "phi" in model_key:
            return 0.0
            
        # Gemini 1.5 Flash / Gemini 2.0 Flash pricing
        if "gemini" in model_key:
            input_rate = 0.075 / 1_000_000   # $0.075 per 1M input tokens
            output_rate = 0.300 / 1_000_000  # $0.300 per 1M output tokens
            return (prompt_tokens * input_rate) + (completion_tokens * output_rate)
            
        # GPT-4o pricing
        if "gpt-4o" in model_key:
            input_rate = 2.50 / 1_000_000    # $2.50 per 1M input tokens
            output_rate = 10.00 / 1_000_000  # $10.00 per 1M output tokens
            return (prompt_tokens * input_rate) + (completion_tokens * output_rate)
            
        # Default fallback
        return ((prompt_tokens + completion_tokens) / 1000) * 0.002

# Global tracker instance
tracker = PerformanceTracker()
