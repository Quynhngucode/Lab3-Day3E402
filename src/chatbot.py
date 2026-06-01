import os
import json
from typing import List, Dict, Any
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.agent.memory import ShortTermMemory, LongTermMemory

class BaselineChatbot:
    """
    A baseline Chatbot that attempts to answer the user's query in a single direct response.
    It does not follow the Thought-Action-Observation loop and cannot execute tools.
    """
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]]):
        self.llm = llm
        self.tools = tools
        self.short_term_memory = ShortTermMemory()
        self.long_term_memory = LongTermMemory()

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        long_term_summary = self.long_term_memory.get_profile_as_string()
        
        return f"""You are a friendly Movie Booking Chatbot. You DO NOT have the ability to execute tools directly.
However, here are the descriptions of tools that would theoretically be available:
{tool_descriptions}

### USER PROFILE (LONG-TERM MEMORY):
{long_term_summary}

Answer the user directly. Since you cannot run the tools, if the user asks for showtimes, available seats, pricing, or bookings, you must try to guess or hallucinate an answer based on your pre-trained knowledge, or politely decline if you cannot answer. Do NOT use the ReAct format (Thought/Action/Observation). Just talk to the user.
"""

    def run(self, user_input: str) -> str:
        logger.log_event("CHATBOT_START", {"input": user_input, "model": self.llm.model_name})
        
        self.short_term_memory.add_message("user", user_input)
        short_term_history = self.short_term_memory.get_history_as_string()
        
        prompt = f"Short-term conversation history:\n{short_term_history}\n\nUser: {user_input}"
        
        response = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
        content = response.get("content", "").strip()
        
        tracker.track_request(
            provider=response.get("provider", "unknown"),
            model=self.llm.model_name,
            usage=response.get("usage", {}),
            latency_ms=response.get("latency_ms", 0)
        )
        
        self.short_term_memory.add_message("assistant", content)
        logger.log_event("CHATBOT_END", {"response": content})
        return content
