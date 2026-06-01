import time
from typing import Dict, Any, List
from src.telemetry.logger import logger

PRICING = {
    "gpt-4o": {
        "input": 2.50 / 1_000_000,   # $2.50 per 1M tokens
        "output": 10.00 / 1_000_000, # $10.00 per 1M tokens
    },
    "gemini-3-flash-preview": {
        "input": 0.075 / 1_000_000,
        "output": 0.30 / 1_000_000,
    },
    "gemini-1.5-pro": {
        "input": 1.25 / 1_000_000,
        "output": 5.00 / 1_000_000,
    },
    "phi-3": {
        "input": 0.0,
        "output": 0.0,
    },
    "local": {
        "input": 0.0,
        "output": 0.0,
    },
    "mock": {
        "input": 0.0,
        "output": 0.0,
    }
}

def _resolve_pricing(model_name: str) -> Dict[str, float]:
    model_lower = model_name.lower()
    
    # Check for mock mapping first to show realistic cost during simulation/evaluation
    if "mock-gpt-4o" in model_lower:
        return PRICING["gpt-4o"]
    elif "mock-gemini-3-flash-preview" in model_lower:
        return PRICING["gemini-3-flash-preview"]
    elif "mock-gemini-1.5-pro" in model_lower:
        return PRICING["gemini-1.5-pro"]
    elif "mock-phi" in model_lower or "mock-llm" in model_lower:
        return PRICING["phi-3"]
        
    # Check regular models
    if "gpt-4o" in model_lower:
        return PRICING["gpt-4o"]
    elif "gemini-3-flash-preview" in model_lower:
        return PRICING["gemini-3-flash-preview"]
    elif "gemini-1.5-pro" in model_lower:
        return PRICING["gemini-1.5-pro"]
    elif "phi-3" in model_lower or "local" in model_lower:
        return PRICING["phi-3"]
        
    # Fallback default
    return PRICING["gpt-4o"]

class PerformanceTracker:
    """
    Tracking industry-standard metrics for LLMs.
    """
    def __init__(self):
        self.session_metrics = []
        self.session_errors = []

    def reset_session(self):
        """Resets the metrics and errors for the current session."""
        self.session_metrics = []
        self.session_errors = []

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """
        Logs a single request metric to our telemetry.
        """
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
            "completion_tokens": usage.get("completion_tokens", 0) or 0,
            "total_tokens": usage.get("total_tokens", 0) or 0,
            "latency_ms": latency_ms,
            "cost_estimate": self._calculate_cost(model, usage)
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def track_error(self, error_type: str, message: str):
        """
        Logs and registers an agent execution error (Parser, Hallucination, Timeout).
        """
        error_event = {
            "error_type": error_type,
            "message": message,
            "timestamp": time.time()
        }
        self.session_errors.append(error_event)
        logger.log_event("AGENT_ERROR", error_event)

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Aggregates session metrics to return a summary dict.
        """
        metrics = [m for m in self.session_metrics if isinstance(m, dict)]
        total_tokens = sum(m.get("total_tokens", 0) for m in metrics)
        prompt_tokens = sum(m.get("prompt_tokens", 0) for m in metrics)
        completion_tokens = sum(m.get("completion_tokens", 0) for m in metrics)
        cost = sum(m.get("cost_estimate", 0.0) for m in metrics)
        latency = sum(m.get("latency_ms", 0) for m in metrics)
        
        token_ratio = (completion_tokens / prompt_tokens) if prompt_tokens > 0 else 0.0
        
        return {
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_estimate": cost,
            "latency_ms": latency,
            "token_ratio": token_ratio,
            "error_count": len(self.session_errors),
            "errors": self.session_errors
        }

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        Calculates exact token pricing based on model rates.
        """
        if not usage:
            return 0.0
        pricing = _resolve_pricing(model)
        prompt_tokens = usage.get("prompt_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
        cost = (prompt_tokens * pricing["input"]) + (completion_tokens * pricing["output"])
        return cost

# Global tracker instance
tracker = PerformanceTracker()
