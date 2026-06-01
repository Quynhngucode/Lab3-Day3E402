import os
import time
import google.generativeai as genai
from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        genai.configure(api_key=self.api_key)
        # Don't pre-bake system_instruction here — we inject it per-call using model config
        self._base_model_name = model_name

    def _get_model(self, system_prompt: Optional[str] = None):
        """Create a GenerativeModel, optionally with system_instruction baked in."""
        if system_prompt:
            return genai.GenerativeModel(
                model_name=self._base_model_name,
                system_instruction=system_prompt
            )
        return genai.GenerativeModel(model_name=self._base_model_name)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        model = self._get_model(system_prompt)
        response = model.generate_content(prompt)

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Safely extract usage metadata (field names differ across SDK versions)
        usage_meta = getattr(response, "usage_metadata", None)
        if usage_meta:
            prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
            completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
            total_tokens = getattr(usage_meta, "total_token_count", 0) or (prompt_tokens + completion_tokens)
        else:
            prompt_tokens = completion_tokens = total_tokens = 0

        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }

        # Safely get text content
        try:
            content = response.text
        except Exception:
            content = ""
            for part in response.parts:
                content += getattr(part, "text", "")

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "google"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        model = self._get_model(system_prompt)
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            try:
                yield chunk.text
            except Exception:
                pass
