import os
import sys
import pytest
from typing import Dict, Any, Optional, Generator

# Add src to path to allow import of src modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.llm_provider import LLMProvider

class ChatbotBaseline:
    """
    A simple Chatbot Baseline that communicates directly with the LLM without ReAct loop or tools.
    """
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, user_input: str) -> Dict[str, Any]:
        import time
        start_time = time.time()
        
        system_prompt = (
            "You are a helpful cinema chatbot assistant. You can chat with users, "
            "but you do NOT have tools to query real schedules, calculate precise VIP prices, or book tickets."
        )
        
        result = self.llm.generate(user_input, system_prompt=system_prompt)
        content = result.get("content", "").strip()
        usage = result.get("usage", {})
        latency_ms = int((time.time() - start_time) * 1000)
        
        return {
            "final_answer": content,
            "metrics": {
                "total_steps": 1,
                "latency_ms": latency_ms,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
        }


class MockLLMProvider(LLMProvider):
    """
    A Mock LLM Provider to return deterministic responses for the Chatbot.
    """
    def __init__(self, response_text: str):
        super().__init__(model_name="mock-phi-3", api_key="mock_key")
        self.response_text = response_text

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        return {
            "content": self.response_text,
            "usage": {
                "prompt_tokens": 80,
                "completion_tokens": 120,
                "total_tokens": 200
            },
            "latency_ms": 100,
            "provider": "mock"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.response_text


def test_chatbot_simple_query():
    """
    Test 1: Simple informational query.
    Chatbot baseline can easily answer conversational questions in a single turn.
    """
    mock_response = (
        "Chào bạn! Phim Doctor Strange hiện tại không chiếu rạp, nhưng vé Standard ở rạp chúng tôi thường là 85.000 VND "
        "và vé VIP là 120.000 VND. Bạn có muốn chọn xem phim khác đang hot không?"
    )
    
    mock_llm = MockLLMProvider(mock_response)
    chatbot = ChatbotBaseline(llm=mock_llm)
    
    query = "Doctor Strange có lịch chiếu mấy giờ vậy?"
    result = chatbot.run(query)
    
    # Assertions
    assert result["final_answer"] is not None
    assert "Doctor Strange" in result["final_answer"]
    assert result["metrics"]["total_steps"] == 1
    assert result["metrics"]["total_tokens"] == 200


def test_chatbot_complex_query_incapability():
    """
    Test 2: Complex multi-step query (Checking schedule, calculating price, and booking).
    A standard chatbot will decline or fail because it does not have tools.
    """
    mock_response = (
        "Tôi xin lỗi, vì tôi là Chatbot thông thường nên tôi không thể kiểm tra số lượng ghế trống thực tế "
        "hoặc tự động áp dụng mã voucher để đặt vé trực tiếp cho bạn được. Vui lòng truy cập website của chúng tôi "
        "hoặc liên hệ hotline để đặt vé."
    )
    
    mock_llm = MockLLMProvider(mock_response)
    chatbot = ChatbotBaseline(llm=mock_llm)
    
    query = "Đặt giúp tôi 2 ghế VIP phim Avengers hôm nay áp mã voucher SUMMER20 nhé."
    result = chatbot.run(query)
    
    # Assertions
    assert "không thể" in result["final_answer"]  # Decline action
    assert "đặt vé trực tiếp" in result["final_answer"]
    assert result["metrics"]["total_steps"] == 1  # Standard chatbot always takes exactly 1 step


def test_chatbot_efficiency():
    """
    Test 3: Token and step efficiency comparison.
    Shows that Chatbot has extremely low latency and token usage (1 step, 200 tokens)
    compared to the 3-4 steps and thousands of tokens required by the ReAct Agent.
    """
    mock_llm = MockLLMProvider("Chào bạn!")
    chatbot = ChatbotBaseline(llm=mock_llm)
    
    result = chatbot.run("Hi")
    
    # Verifying single turn characteristics
    assert result["metrics"]["total_steps"] == 1
    assert result["metrics"]["total_tokens"] <= 250
