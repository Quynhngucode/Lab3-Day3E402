import os
import time
import random
import google.generativeai as genai
from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider
from src.telemetry.metrics import tracker

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-3-flash-preview", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # In Gemini, system instruction is passed during model initialization or as a prefix
        # For simplicity in this lab, we'll prepend it if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        max_retries = 5
        base_delay = 10
        response = None
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(full_prompt)
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    if attempt == max_retries - 1:
                        raise e
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 5)
                    print(f"\n[Gemini] Hit Rate Limit (429). Retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(delay)
                else:
                    raise e

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Gemini usage data is in response.usage_metadata
        content = response.text
        usage = {
            "prompt_tokens": response.usage_metadata.prompt_token_count,
            "completion_tokens": response.usage_metadata.candidates_token_count,
            "total_tokens": response.usage_metadata.total_token_count
        }

        # Track telemetry request metric with cost estimation
        tracker.track_request("google", self.model_name, usage, latency_ms)

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "google"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        max_retries = 5
        base_delay = 10
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(full_prompt, stream=True)
                for chunk in response:
                    yield chunk.text
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
                    if attempt == max_retries - 1:
                        raise e
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 5)
                    print(f"\n[Gemini Stream] Hit Rate Limit (429). Retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(delay)
                else:
                    raise e

