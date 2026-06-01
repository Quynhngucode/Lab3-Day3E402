import os
import sys
import pytest
from typing import Dict, Any, Optional, Generator

# Add src to path to allow import of src modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.llm_provider import LLMProvider
from src.agent.agent import ReActAgent

class MockLLMProvider(LLMProvider):
    """
    A Mock LLM Provider to test the ReActAgent logic without making external API calls
    or loading massive local models.
    """
    def __init__(self, responses: list):
        super().__init__(model_name="mock-phi-3", api_key="mock_key")
        self.responses = responses
        self.call_count = 0

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if self.call_count < len(self.responses):
            response_text = self.responses[self.call_count]
        else:
            response_text = "Final Answer: Tất cả các bước đã hoàn thành."
        
        self.call_count += 1
        
        return {
            "content": response_text,
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 50,
                "total_tokens": 200
            },
            "latency_ms": 100,
            "provider": "mock"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield "Mock stream not implemented"


def test_react_agent_happy_path():
    """
    Test the standard 3-step ReAct agent loop for movie ticket booking.
    Steps:
      1. Check movie schedule
      2. Calculate total price
      3. Book ticket
      4. Return Final Answer
    """
    responses = [
        # Step 1: Check Movie Schedule
        "Thought: Tôi cần kiểm tra lịch chiếu phim Avengers tại rạp Beta hôm nay để biết suất chiếu và giá cơ bản.\n"
        "Action: check_movie_schedule\n"
        "Action Input: {\"movie_name\": \"avengers\", \"cinema_name\": \"Beta\", \"date\": \"2026-06-01\"}",
        
        # Step 2: Calculate total price
        "Thought: Đã có giá vé cơ bản là 90,000 VND. Bây giờ tôi sẽ tính tổng tiền cho 2 vé ghế VIP.\n"
        "Action: calculate_total_price\n"
        "Action Input: {\"base_price\": 90000, \"quantity\": 2, \"seat_type\": \"vip\"}",
        
        # Step 3: Book ticket
        "Thought: Tổng số tiền cần thanh toán là 270,000 VND. Tôi sẽ tiến hành đặt vé phim Avengers tại rạp Beta suất chiếu 18:00.\n"
        "Action: book_movie_ticket\n"
        "Action Input: {\"movie_name\": \"avengers\", \"cinema_name\": \"Beta\", \"showtime\": \"18:00\", \"seat_type\": \"vip\", \"quantity\": 2, \"total_price\": 270000}",
        
        # Step 4: Final Answer
        "Thought: Việc đặt vé đã thành công tốt đẹp. Tôi sẽ cung cấp câu trả lời cuối cùng cho khách hàng.\n"
        "Final Answer: Đã đặt thành công 2 vé VIP phim Avengers tại rạp Beta suất chiếu 18:00. Tổng tiền là 270,000 VND. Mã đặt vé của bạn là BK123456. Chúc bạn xem phim vui vẻ!"
    ]
    
    mock_llm = MockLLMProvider(responses)
    agent = ReActAgent(llm=mock_llm, max_steps=5)
    
    query = "Đặt 2 vé VIP xem phim Avengers tại Beta hôm nay."
    result = agent.run_with_trace(query)
    
    # Assertions
    assert result["final_answer"] is not None
    assert "BK123456" in result["final_answer"]
    assert len(result["steps"]) == 4
    
    # Check individual steps
    assert result["steps"][0]["action"] == "check_movie_schedule"
    assert result["steps"][1]["action"] == "calculate_total_price"
    assert result["steps"][2]["action"] == "book_movie_ticket"
    assert result["steps"][3]["action"] is None
    assert "BK123456" in result["steps"][3]["final_answer"]
    
    # Verify token accumulation
    assert result["metrics"]["prompt_tokens"] == 150 * 4
    assert result["metrics"]["completion_tokens"] == 50 * 4
    assert result["metrics"]["total_tokens"] == 200 * 4


def test_react_agent_error_handling_unknown_tool():
    """
    Test that the ReActAgent handles an unknown tool name returned by the LLM.
    """
    responses = [
        # Step 1: LLM tries to call a non-existent tool
        "Thought: Tôi sẽ kiểm tra lịch chiếu bằng cách sử dụng một công cụ không tồn tại.\n"
        "Action: get_weather_forecast\n"
        "Action Input: {\"location\": \"Hanoi\"}",
        
        # Step 2: Agent responds with error observation, LLM corrects itself
        "Thought: Ồ, công cụ get_weather_forecast không tồn tại. Tôi phải sử dụng check_movie_schedule.\n"
        "Action: check_movie_schedule\n"
        "Action Input: {\"movie_name\": \"doraemon\", \"cinema_name\": \"Beta\", \"date\": \"2026-06-01\"}",
        
        # Step 3: Final Answer
        "Thought: Có lịch chiếu rồi, tôi sẽ báo lại luôn cho khách hàng.\n"
        "Final Answer: Lịch chiếu Doraemon hôm nay có các suất: 09:00, 11:30, 14:00, 16:30. Giá vé là 75,000 VND."
    ]
    
    mock_llm = MockLLMProvider(responses)
    agent = ReActAgent(llm=mock_llm, max_steps=5)
    
    result = agent.run_with_trace("Xem lịch Doraemon.")
    
    assert len(result["steps"]) == 3
    assert result["steps"][0]["action"] == "get_weather_forecast"
    assert "ERROR: Unknown tool" in result["steps"][0]["observation"]
    assert result["steps"][1]["action"] == "check_movie_schedule"
    assert "success" in result["steps"][1]["observation"]


def test_react_agent_error_handling_invalid_json():
    """
    Test that the ReActAgent handles invalid JSON in Action Input correctly.
    """
    responses = [
        # Step 1: LLM outputs broken JSON
        "Thought: Tôi sẽ gọi check_movie_schedule nhưng quên dấu ngoặc đóng JSON.\n"
        "Action: check_movie_schedule\n"
        "Action Input: {\"movie_name\": \"doraemon\", \"cinema_name\": \"Beta\"",
        
        # Step 2: LLM receives warning and corrects JSON
        "Thought: Lỗi JSON rồi. Tôi sẽ viết lại JSON chuẩn.\n"
        "Action: check_movie_schedule\n"
        "Action Input: {\"movie_name\": \"doraemon\", \"cinema_name\": \"Beta\", \"date\": \"2026-06-01\"}",
        
        # Step 3: Final Answer
        "Final Answer: Doraemon chiếu lúc 09:00 hôm nay."
    ]
    
    mock_llm = MockLLMProvider(responses)
    agent = ReActAgent(llm=mock_llm, max_steps=5)
    
    result = agent.run_with_trace("Xem lịch Doraemon.")
    
    assert len(result["steps"]) == 3
    assert result["steps"][0]["action"] == "check_movie_schedule"
    assert result["steps"][0]["action_input"] is None  # Broken JSON results in None params
    assert "ERROR: Could not parse Action Input as valid JSON" in result["steps"][0]["observation"]
    
    assert result["steps"][1]["action"] == "check_movie_schedule"
    assert result["steps"][1]["action_input"] == {"movie_name": "doraemon", "cinema_name": "Beta", "date": "2026-06-01"}


if __name__ == "__main__":
    print("Running pytest on tests/test_agent.py...")
    import subprocess
    subprocess.run(["pytest", "-v", __file__])
