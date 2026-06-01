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
    A Mock LLM Provider that keeps track of the prompt and returns a response
    appropriate to the active Prompt Version (v1 or v2).
    """
    def __init__(self, prompt_version: str):
        super().__init__(model_name="mock-phi-3", api_key="mock_key")
        self.prompt_version = prompt_version
        self.call_count = 0

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        self.call_count += 1
        
        # Responses for Prompt v1 (Batch Execution)
        if self.prompt_version == "v1":
            if self.call_count == 1:
                # Step 1: LLM decides to check the schedule
                response_text = (
                    "Thought: Tôi cần kiểm tra lịch chiếu phim Avengers tại rạp Beta hôm nay để biết suất chiếu.\n"
                    "Action: check_movie_schedule\n"
                    "Action Input: {\"movie_name\": \"avengers\", \"cinema_name\": \"Beta\", \"date\": \"2026-06-01\"}"
                )
            elif self.call_count == 2:
                # Step 2: LLM computes price
                response_text = (
                    "Thought: Suất chiếu khả dụng là 11:00, 14:30... Vé cơ bản là 90k. Bây giờ tính tiền cho 2 vé VIP.\n"
                    "Action: calculate_total_price\n"
                    "Action Input: {\"base_price\": 90000, \"quantity\": 2, \"seat_type\": \"vip\"}"
                )
            elif self.call_count == 3:
                # Step 3: LLM automatically books ticket without user confirmation
                response_text = (
                    "Thought: Tổng chi phí là 270k. Tôi tiến hành đặt vé luôn mà không cần hỏi lại user.\n"
                    "Action: book_movie_ticket\n"
                    "Action Input: {\"movie_name\": \"avengers\", \"cinema_name\": \"Beta\", \"showtime\": \"18:00\", \"seat_type\": \"vip\", \"quantity\": 2, \"total_price\": 270000}"
                )
            else:
                # Final Answer
                response_text = (
                    "Final Answer: Đặt thành công 2 vé VIP phim Avengers tại rạp Beta. Mã vé: BK99999. Tổng tiền: 270.000 VND."
                )
                
        # Responses for Prompt v2 (Conversational / HITL)
        else:
            if self.call_count == 1:
                # Step 1: LLM decides to check the schedule first
                response_text = (
                    "Thought: Tôi cần kiểm tra lịch chiếu của phim Avengers tại cụm rạp Beta hôm nay trước.\n"
                    "Action: check_movie_schedule\n"
                    "Action Input: {\"movie_name\": \"avengers\", \"cinema_name\": \"Beta\", \"date\": \"2026-06-01\"}"
                )
            elif self.call_count == 2:
                # Step 2: Observation has returned multiple showtimes: ["11:00", "14:30", "18:00", "21:30"].
                # According to Prompt v2 rules: "If multiple showtimes are returned, ask the user to choose one."
                # Therefore, the LLM stops here to ask the user instead of booking or calculating.
                response_text = (
                    "Thought: Theo quy tắc ứng xử của Prompt v2, vì có nhiều suất chiếu trả về từ check_movie_schedule, "
                    "tôi phải yêu cầu người dùng chọn suất chiếu mong muốn trước khi tiếp tục.\n"
                    "Final Answer: Phim Avengers hôm nay tại Beta có các suất chiếu: 11:00, 14:30, 18:00, và 21:30. "
                    "Bạn muốn chọn xem vào khung giờ nào?"
                )
            else:
                response_text = "Final Answer: Đang chờ phản hồi của bạn."

        return {
            "content": response_text,
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 80,
                "total_tokens": 200
            },
            "latency_ms": 100,
            "provider": "mock"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield "Mock stream not implemented"


def test_prompt_v1_batch_execution():
    """
    Test Prompt v1 behavior.
    Under Prompt v1, the agent should perform all steps (check schedule, calculate price, and book)
    in a single conversational turn automatically.
    """
    mock_llm = MockLLMProvider(prompt_version="v1")
    agent = ReActAgent(llm=mock_llm, prompt_version="v1", max_steps=5)
    
    query = "Đặt giúp mình 2 vé VIP phim Avengers tại rạp Beta hôm nay."
    result = agent.run_with_trace(query)
    
    # Assertions
    assert result["final_answer"] is not None
    assert "Đặt thành công 2 vé VIP" in result["final_answer"]
    assert "BK99999" in result["final_answer"]
    
    # Steps: 1. check_movie_schedule, 2. calculate_total_price, 3. book_movie_ticket, 4. Final Answer
    assert len(result["steps"]) == 4
    assert result["steps"][0]["action"] == "check_movie_schedule"
    assert result["steps"][1]["action"] == "calculate_total_price"
    assert result["steps"][2]["action"] == "book_movie_ticket"
    assert result["steps"][3]["action"] is None


def test_prompt_v2_conversational_safety_execution():
    """
    Test Prompt v2 behavior.
    Under Prompt v2, when multiple showtimes are found, the agent must ask the user
    to select one instead of booking or calculating directly, enforcing conversational HITL safety.
    """
    mock_llm = MockLLMProvider(prompt_version="v2")
    agent = ReActAgent(llm=mock_llm, prompt_version="v2", max_steps=5)
    
    query = "Đặt giúp mình 2 vé VIP phim Avengers tại rạp Beta hôm nay."
    result = agent.run_with_trace(query)
    
    # Assertions
    assert result["final_answer"] is not None
    assert "Bạn muốn chọn xem vào khung giờ nào?" in result["final_answer"]
    assert "BK99999" not in result["final_answer"]  # It should NOT have booked the ticket yet
    
    # Steps: 1. check_movie_schedule, 2. Final Answer asking for choice
    assert len(result["steps"]) == 2
    assert result["steps"][0]["action"] == "check_movie_schedule"
    assert result["steps"][1]["action"] is None
    assert "Bạn muốn chọn xem vào khung giờ nào?" in result["steps"][1]["final_answer"]


if __name__ == "__main__":
    import subprocess
    subprocess.run(["pytest", "-v", __file__])
