import time
import json
from typing import Dict, Any, Generator, Optional
from src.core.llm_provider import LLMProvider

class MockProvider(LLMProvider):
    """
    Mock LLM Provider that simulates movie booking agent behaviors for testing without API keys.
    """
    def __init__(self, model_name: str = "mock-gpt-4o"):
        super().__init__(model_name, api_key="mock_key")
        self.step_counts = {}

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        time.sleep(0.5)  # Simulate network latency
        
        prompt_lower = prompt.lower()
        content = ""
        
        # Determine if we are running the chatbot baseline or ReAct agent
        is_react = "thought:" in system_prompt.lower() if system_prompt else False
        
        if is_react:
            # ReAct Agent simulation logic
            # Track how many turns this prompt has gone through in the ReAct loop
            # We can detect this by counting how many Observations are in the prompt
            obs_count = prompt.count("Observation:")
            
            # Isolate the latest message to avoid matching history
            query_part = prompt_lower
            if "new message to answer:" in prompt_lower:
                query_part = prompt_lower.split("new message to answer:")[-1]
            
            if "doctor strange" in query_part:
                # Case 1: Doctor Strange showtimes
                if obs_count == 0:
                    content = "Thought: I need to check the details and showtimes for Doctor Strange.\nAction: get_movie_info({\"movie_name\": \"Doctor Strange\"})"
                elif obs_count == 1:
                    content = "Thought: The search returned that Doctor Strange is not in our mock database but found search results. I will show the user what we found.\nFinal Answer: Phim Doctor Strange hiện tại không có trong hệ thống rạp của chúng tôi. Tuy nhiên, thông tin tìm kiếm cho biết vé VIP có giá từ 120k VND và Standard là 80k VND."
            
            elif "lịch chiếu và giá vé vip" in query_part or "dune 2" in query_part and "vip" in query_part and "đặt" not in query_part:
                # Case 2: Dune 2 VIP showtimes & pricing
                if obs_count == 0:
                    content = "Thought: I need to query movie information for Dune 2.\nAction: get_movie_info({\"movie_name\": \"dune 2\"})"
                elif obs_count == 1:
                    content = "Thought: I have the movie info now, showing Dune: Part Two showtimes (14:00, 17:30, 20:30) and VIP ticket price (120,000 VND). I can answer the user.\nFinal Answer: Lịch chiếu phim Dune: Part Two là 14:00, 17:30 và 20:30. Giá vé VIP là 120.000 VND, còn vé Standard là 80.000 VND."
                    
            elif "batman lúc 19:00" in query_part and "đặt giúp" in query_part:
                # Case 3: Batman 19:00 seats and booking 2 seats
                if obs_count == 0:
                    content = "Thought: I need to check the available seats for Batman at 19:00.\nAction: check_seat_availability({\"movie_name\": \"batman\", \"showtime\": \"19:00\"})"
                elif obs_count == 1:
                    # Parse available seats from mock response (we know B2, B3, C1, etc. will be returned)
                    content = "Thought: Seats B2 and B3 are available. I will first calculate the total price for 2 Standard tickets.\nAction: calculate_total_price({\"ticket_type\": \"Standard\", \"quantity\": 2})"
                elif obs_count == 2:
                    content = "Thought: Total price is 160,000 VND. Now I will book seats B2 and B3 for Batman at 19:00.\nAction: book_ticket({\"movie_name\": \"batman\", \"showtime\": \"19:00\", \"seats\": [\"B2\", \"B3\"], \"ticket_type\": \"Standard\"})"
                elif obs_count == 3:
                    content = "Thought: Booking was successful. I will present the booking ID and seats to the user.\nFinal Answer: Tôi đã đặt thành công 2 vé Standard cho phim The Batman lúc 19:00. Mã ghế của bạn là B2, B3. Tổng tiền là 160.000 VND. Mã đặt vé của bạn là BK-123456."
                    
            elif "1 vé vip cho phim dune 2 lúc 17:30" in query_part or "hồ sơ" in query_part:
                # Case 4: Long term memory and voucher
                if obs_count == 0:
                    # User profile says VIP seat preference, voucher CGV30 is in profile wallet
                    content = "Thought: I should find showtimes for Dune 2.\nAction: get_movie_info({\"movie_name\": \"dune 2\"})"
                elif obs_count == 1:
                    content = "Thought: Now check available VIP seats (row A) for Dune 2 at 17:30.\nAction: check_seat_availability({\"movie_name\": \"dune 2\", \"showtime\": \"17:30\"})"
                elif obs_count == 2:
                    content = "Thought: VIP seat A1 is available. Let's calculate total price for 1 VIP ticket applying voucher CGV30.\nAction: calculate_total_price({\"ticket_type\": \"VIP\", \"quantity\": 1, \"voucher_code\": \"CGV30\"})"
                elif obs_count == 3:
                    content = "Thought: Total price is 84,000 VND (30% discount applied to 120,000 VND). I will now book seat A1.\nAction: book_ticket({\"movie_name\": \"dune 2\", \"showtime\": \"17:30\", \"seats\": [\"A1\"], \"ticket_type\": \"VIP\", \"voucher_code\": \"CGV30\"})"
                elif obs_count == 4:
                    content = "Thought: Booking completed. I will inform the user.\nFinal Answer: Vé VIP của bạn đã được đặt thành công cho phim Dune: Part Two lúc 17:30. Ghế được chọn là A1. Nhờ áp dụng mã giảm giá CGV30 (30%), tổng số tiền thanh toán là 84.000 VND (giá gốc 120.000 VND). Mã đặt vé: BK-777888."
            
            elif "trailer" in query_part or "xem trailer" in query_part:
                if obs_count == 0:
                    movie = "dune 2"
                    if "batman" in query_part:
                        movie = "batman"
                    elif "spider" in query_part:
                        movie = "spider-man"
                    content = f"Thought: I need to search for the trailer of {movie}.\nAction: search_youtube_trailer({{\"movie_name\": \"{movie}\"}})"
                elif obs_count == 1:
                    embed_url = "https://www.youtube.com/embed/U2Qp5pL3yTo"
                    title = "Dune: Part Two"
                    if "batman" in query_part:
                        embed_url = "https://www.youtube.com/embed/mqqft2x_Aa4"
                        title = "The Batman"
                    elif "spider" in query_part:
                        embed_url = "https://www.youtube.com/embed/cqGjhVJWtEg"
                        title = "Spider-Man: Across the Spider-Verse"
                    content = f"Thought: I have the trailer embed link. I will show it to the user.\nFinal Answer: Chắc chắn rồi! Dưới đây là trailer chính thức của phim {title}. Chúc bạn xem trailer vui vẻ!\n\n{embed_url}"

            else:
                # Catch-all ReAct response
                content = "Thought: I will perform a search to answer the query.\nAction: web_search({\"query\": \"" + prompt[:30] + "\"})" if obs_count == 0 else "Thought: Ready to reply.\nFinal Answer: Xin chào, tôi có thể giúp gì cho bạn về thông tin lịch chiếu và đặt vé xem phim?"
        
        else:
            # Chatbot Baseline simulation logic (no tool calls, direct output)
            query_part = prompt_lower
            if "new message to answer:" in prompt_lower:
                query_part = prompt_lower.split("new message to answer:")[-1]
                
            if "doctor strange" in query_part:
                content = "Phim Doctor Strange hiện tại không chiếu rạp, giá vé có thể là 80.000 VND cho Standard và 120.000 VND cho VIP. Bạn có muốn đặt phim khác không?"
            elif "lịch chiếu và giá vé vip" in query_part or "dune 2" in query_part and "vip" in query_part and "đặt" not in query_part:
                content = "Lịch chiếu phim Dune 2 là các khung giờ trong ngày, vé VIP giá khoảng 120.000 VND. Vui lòng cho tôi biết bạn muốn đặt mấy vé."
            elif "batman lúc 19:00" in query_part and "đặt giúp" in query_part:
                content = "Tôi không thể kiểm tra ghế trống hay đặt vé trực tiếp cho bạn được vì tôi là chatbot thông thường. Tuy nhiên, giá vé Standard phim Batman lúc 19:00 là 80.000 VND. Bạn nên tự lên website để đặt vé."
            elif "1 vé vip cho phim dune 2 lúc 17:30" in query_part or "hồ sơ" in query_part:
                content = "Chào bạn, tôi nhớ bạn thích ngồi ghế VIP và có voucher CGV30. Tuy nhiên tôi không thể tự động tra cứu ghế hay áp dụng mã đặt vé cho bạn. Bạn có thể tự đặt trên web của rạp."
            elif "trailer" in query_part or "xem trailer" in query_part:
                title = "Dune: Part Two"
                embed_url = "https://www.youtube.com/embed/U2Qp5pL3yTo"
                if "batman" in query_part:
                    title = "The Batman"
                    embed_url = "https://www.youtube.com/embed/mqqft2x_Aa4"
                elif "spider" in query_part:
                    title = "Spider-Man: Across the Spider-Verse"
                    embed_url = "https://www.youtube.com/embed/cqGjhVJWtEg"
                content = f"Chào bạn! Dưới đây là trailer phim {title} để bạn tham khảo. Để đặt vé trực tiếp, hãy chuyển sang chế độ ReAct Agent nhé!\n\n{embed_url}"
            else:
                content = "Chào bạn! Tôi có thể hỗ trợ bạn tìm kiếm thông tin phim ảnh và tư vấn đặt vé xem phim."

        usage = {
            "prompt_tokens": len(prompt.split()) * 4,
            "completion_tokens": len(content.split()) * 4,
            "total_tokens": (len(prompt.split()) + len(content.split())) * 4
        }
        
        return {
            "content": content,
            "usage": usage,
            "latency_ms": 150 + len(content.split()) * 5,
            "provider": "mock"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        res = self.generate(prompt, system_prompt)
        yield res["content"]
