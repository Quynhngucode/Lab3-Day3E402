import os
import time
from typing import Dict, Any, Optional, Generator
from google import genai
from google.genai import types
from src.core.llm_provider import LLMProvider


class GeminiProvider(LLMProvider):
    """
    LLM Provider using the new google-genai SDK (replaces deprecated google-generativeai).
    """
    def __init__(self, model_name: str = "gemini-3-flash-preview", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        self.client = genai.Client(api_key=self.api_key)
        self._base_model_name = model_name

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
        )

        response = self.client.models.generate_content(
            model=self._base_model_name,
            contents=prompt,
            config=config,
        )

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Extract usage metadata safely
        usage_meta = getattr(response, "usage_metadata", None)
        if usage_meta:
            prompt_tokens     = getattr(usage_meta, "prompt_token_count", 0) or 0
            completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
            total_tokens      = getattr(usage_meta, "total_token_count", 0) or (prompt_tokens + completion_tokens)
        else:
            prompt_tokens = completion_tokens = total_tokens = 0

        # Extract text safely
        try:
            content = response.text
        except Exception:
            content = ""
            for candidate in getattr(response, "candidates", []):
                for part in getattr(candidate.content, "parts", []):
                    content += getattr(part, "text", "")

        return {
            "content":           content,
            "usage": {
                "prompt_tokens":     prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens":      total_tokens,
            },
            "latency_ms": latency_ms,
            "provider":   "google",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
        )
        for chunk in self.client.models.generate_content_stream(
            model=self._base_model_name,
            contents=prompt,
            config=config,
        ):
            try:
                yield chunk.text
            except Exception:
                pass
