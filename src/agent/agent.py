import os
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

import os
import re
import json
import random
import string
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

# ─────────────────────────────────────────────────────────────────────────────
# MOCK TOOLS (Cinema Ticket Booking - Unified Database)
# ─────────────────────────────────────────────────────────────────────────────

def check_movie_schedule(movie_name: str, cinema_name: str, date: str) -> dict:
    """
    Retrieves available showtimes and a base ticket price for the requested
    movie / cinema / date combination.
    """
    movies = {
        "doraemon": {
            "showtimes": ["09:00", "11:30", "14:00", "16:30"],
            "base_price": 75_000,
        },
        "avengers": {
            "showtimes": ["11:00", "14:30", "18:00", "21:30"],
            "base_price": 90_000,
        },
        "dune": {
            "showtimes": ["14:00", "17:30", "20:30"],
            "base_price": 100_000,
        },
        "batman": {
            "showtimes": ["13:00", "16:00", "19:00", "22:00"],
            "base_price": 80_000,
        },
        "spider": {
            "showtimes": ["10:30", "15:00", "18:00"],
            "base_price": 110_000,
        },
        "default": {
            "showtimes": ["10:00", "13:00", "16:30", "19:45", "22:00"],
            "base_price": 85_000,
        },
    }

    key = "default"
    for k in movies:
        if k.lower() in movie_name.lower():
            key = k
            break

    info = movies[key]
    return {
        "status": "success",
        "movie_name": movie_name,
        "cinema_name": cinema_name,
        "date": date,
        "available_showtimes": info["showtimes"],
        "base_price": info["base_price"],
        "currency": "VND",
        "note": "Giá vé cơ bản chưa bao gồm phụ thu ghế VIP.",
    }


def calculate_total_price(
    base_price: float,
    quantity: int,
    seat_type: str,
    discount_code: str = "",
    concession: str = "",
) -> dict:
    """
    Computes the final ticket cost.
    Seat multipliers: VIP × 1.5, Premium × 1.3, Standard × 1.0
    Discount codes: SUMMER20 → 20%, STUDENT10 → 10%, AI20K → 15%, CGV30 → 30%, STUDENT → 15%
    Fixed discount: HELLOSUMMER → -20,000 VND
    Concessions: popcorn_combo_1 → 50,000 VND, popcorn_combo_2 → 80,000 VND
    """
    multipliers = {
        "vip": 1.5,
        "premium": 1.3,
        "standard": 1.0,
    }
    
    # Percentage discounts
    discounts = {
        "SUMMER20": 0.20,
        "STUDENT10": 0.10,
        "AI20K": 0.15,
        "CGV30": 0.30,
        "STUDENT": 0.15,
    }
    
    # Concessions
    concessions_map = {
        "popcorn_combo_1": 50_000,
        "popcorn_combo_2": 80_000,
    }

    seat_key = seat_type.lower()
    multiplier = multipliers.get(seat_key, 1.0)

    subtotal = base_price * multiplier * quantity
    
    # Calculate discount
    discount_rate = 0.0
    discount_amount = 0.0
    fixed_discount = 0.0
    
    discount_code_upper = discount_code.upper()
    if discount_code_upper in discounts:
        discount_rate = discounts[discount_code_upper]
        discount_amount = subtotal * discount_rate
    elif discount_code_upper == "HELLOSUMMER":
        fixed_discount = 20_000
        discount_amount = fixed_discount
        
    concession_cost = 0.0
    if concession:
        concession_cost = concessions_map.get(concession.lower(), 0.0)

    total = subtotal - discount_amount + concession_cost

    return {
        "status": "success",
        "base_price": base_price,
        "seat_type": seat_type,
        "seat_multiplier": multiplier,
        "quantity": quantity,
        "subtotal": subtotal,
        "discount_code": discount_code or "none",
        "discount_rate": f"{int(discount_rate * 100)}%" if discount_rate > 0 else "0%",
        "discount_amount": discount_amount,
        "concession": concession or "none",
        "concession_cost": concession_cost,
        "total_price": total,
        "currency": "VND",
        "formatted_total": f"{total:,.0f} VND",
    }


def book_movie_ticket(
    movie_name: str,
    cinema_name: str,
    showtime: str,
    seat_type: str,
    quantity: int,
    total_price: float,
) -> dict:
    """
    Finalises the booking and returns a confirmation code.
    """
    booking_id = "BK" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    return {
        "status": "success",
        "booking_confirmed": True,
        "booking_id": booking_id,
        "movie_name": movie_name,
        "cinema_name": cinema_name,
        "showtime": showtime,
        "seat_type": seat_type,
        "quantity": quantity,
        "total_price": total_price,
        "currency": "VND",
        "booking_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": (
            f"Đặt vé thành công! Mã đặt chỗ của bạn là {booking_id}. "
            "Vui lòng đến quầy 15 phút trước giờ chiếu."
        ),
    }


# Tool Registry Map
MOCK_TOOLS_MAP = {
    "check_movie_schedule": check_movie_schedule,
    "calculate_total_price": calculate_total_price,
    "book_movie_ticket": book_movie_ticket,
}


class ReActAgent:
    """
    A robust ReAct Agent following the Thought-Action-Observation loop.
    Supports dynamic execution of cinema booking tools, tracks detailed step-by-step
    traces, handles formatting/parsing corner-cases, and works with any LLMProvider.
    """
    
    def __init__(self, llm: LLMProvider, tools: Optional[List[Dict[str, Any]]] = None, max_steps: int = 5, prompt_version: str = "v1"):
        self.llm = llm
        self.max_steps = max_steps
        self.history = []
        self.prompt_version = prompt_version
        
        # Default tools if none are provided
        if tools is None:
            self.tools = [
                {
                    "name": "check_movie_schedule",
                    "description": "Retrieves available showtimes and base ticket price.\nParameters:\n  - movie_name (string)\n  - cinema_name (string)\n  - date (string, e.g. '2026-06-01')"
                },
                {
                    "name": "calculate_total_price",
                    "description": "Computes the final total cost.\nParameters:\n  - base_price (number)\n  - quantity (integer)\n  - seat_type (string: 'standard'|'vip'|'premium')\n  - discount_code (optional string)"
                },
                {
                    "name": "book_movie_ticket",
                    "description": "Completes the booking and returns a confirmation code.\nParameters:\n  - movie_name (string)\n  - cinema_name (string)\n  - showtime (string)\n  - seat_type (string)\n  - quantity (integer)\n  - total_price (number)"
                }
            ]
        else:
            self.tools = tools

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n\n".join([
            f"{i+1}. {t['name']}\n   - Description: {t['description']}" 
            for i, t in enumerate(self.tools)
        ])
        
        if self.prompt_version == "v2":
            return f"""## System Prompt (Detailed)

You are a cinema ticket booking assistant. Your goal is to help users through selecting a movie and showtime, calculating total price, and confirming the reservation. You must use the tools in the correct order and only after collecting required details.

### Tool order (mandatory)

1) check_movie_schedule
	- Purpose: fetch showtimes and base price for a movie at a cinema and date.
	- Required inputs: movie_name, cinema_name, date

2) calculate_total_price
	- Purpose: compute final cost based on base price, quantity, seat type, and discount.
	- Required inputs: base_price, quantity, seat_type, discount_code (optional)

3) book_movie_ticket
	- Purpose: finalize booking after user confirmation.
	- Required inputs: movie_name, cinema_name, showtime, seat_type, quantity, total_price

### Behavior rules

- Ask for missing details before calling a tool.
- If multiple showtimes are returned, ask the user to choose one.
- If seat type or quantity is missing, ask for it.
- If discount code is not provided, pass an empty string or null.
- After calculating the price, ask for confirmation before booking.
- If there is no availability, propose another date or cinema.
- Keep responses concise and focused on booking.

### Required slots

- movie_name
- cinema_name
- date
- showtime
- seat_type
- quantity
- discount_code (optional)

### Example flow

User: "Book 2 VIP tickets for Dune at Galaxy Cinema tomorrow."

Assistant: "Sure. Let me check available showtimes."

Tool call: check_movie_schedule(movie_name="Dune", cinema_name="Galaxy Cinema", date="tomorrow")

Assistant: "Available showtimes: 6:30 PM, 8:45 PM. Base price is $10. Which showtime do you prefer?"

User: "8:45 PM."

Assistant: "Got it. Any discount code?"

User: "No."

Assistant: "Let me calculate the total."

Tool call: calculate_total_price(base_price=10, quantity=2, seat_type="VIP", discount_code="")

Assistant: "Total is $24. Would you like me to confirm the booking?"

User: "Yes."

Tool call: book_movie_ticket(movie_name="Dune", cinema_name="Galaxy Cinema", showtime="8:45 PM", seat_type="VIP", quantity=2, total_price=24)

Assistant: "Booked. Your confirmation code is ABC123."

### Failure handling

- If check_movie_schedule returns empty, ask the user to try a different date.
- If calculate_total_price fails, restate inputs and ask the user to verify.
- If booking fails, apologize and offer to retry or adjust details.

---

### ReAct Format Guidelines (Mandatory)
You MUST follow this exact ReAct loop format for EVERY step:

Thought: <your reasoning about what to do next>
Action: <exact tool name from the list>
Action Input: <strictly valid JSON object with the required parameters>

After receiving an Observation you continue with another Thought/Action pair,
OR you finish with:

Final Answer: <your complete, friendly answer in Vietnamese>

Rules:
- NEVER skip the Action Input.
- Action Input MUST be a single raw JSON object, no markdown fences, no extra text.
- Use only the exact tool names listed below.
- Do NOT invent data; use only what was returned in Observations.
- Respond in Vietnamese for the Final Answer.

You have access to these tools:
{tool_descriptions}
"""
        
        # Default Prompt v1
        return f"""You are a cinema booking assistant that uses tools to help customers.
You MUST follow this exact ReAct loop format for EVERY step:

Thought: <your reasoning about what to do next>
Action: <exact tool name from the list>
Action Input: <strictly valid JSON object with the required parameters>

After receiving an Observation you continue with another Thought/Action pair,
OR you finish with:

Final Answer: <your complete, friendly answer in Vietnamese>

CRITICAL RULES:

1. MANDATORY TOOL ORDER:
   You must call the tools in this exact order:
   - Tool 1: check_movie_schedule
     * Purpose: fetch showtimes and base price for a movie at a cinema and date.
     * Required inputs: movie_name, cinema_name, date
   - Tool 2: calculate_total_price
     * Purpose: compute final cost based on base price, quantity, seat type, and discount.
     * Required inputs: base_price, quantity, seat_type, discount_code (optional)
   - Tool 3: book_movie_ticket
     * Purpose: finalize booking after user confirmation.
     * Required inputs: movie_name, cinema_name, showtime, seat_type, quantity, total_price

2. BEHAVIOR RULES & GUARDRAILS:
   - Ask for missing details before calling a tool. If any slot (movie_name, cinema_name, date, showtime, seat_type, quantity) is missing, ask the user for it.
   - If multiple showtimes are returned by check_movie_schedule, ask the user to choose one.
   - If discount code is not provided by the user, pass an empty string "" or "none". Do NOT hallucinate vouchers.
   - After calculating the price, you MUST ask for confirmation before booking (e.g. "Tổng tiền là X, bạn có đồng ý xác nhận đặt vé không?").
   - If there is no availability (empty showtimes), propose another date or cinema and stop.
   - Keep responses concise and focused on booking.
   - You must NEVER invent booking confirmation codes (like BK...) or mock prices. Always query them via tools.

3. REQUIRED SLOTS:
   - movie_name
   - cinema_name
   - date
   - showtime
   - seat_type
   - quantity
   - discount_code (optional)

4. FAILURE HANDLING:
   - If check_movie_schedule returns empty, ask the user to try a different date or cinema.
   - If calculate_total_price fails, restate inputs and ask the user to verify.
   - If booking fails, apologize and offer to retry or adjust details.

5. VIETNAMESE RESPONSE:
   - The Final Answer must always be written in a warm, polite, and helpful Vietnamese.

You have access to these tools:
{tool_descriptions}

EXAMPLE FLOW (ReAct Multi-turn Execution):

Turn 1:
User: "Book 2 VIP tickets for Dune at Galaxy Cinema tomorrow."
Thought: The user wants to book 2 VIP tickets for Dune at Galaxy Cinema tomorrow. I have the movie_name ("Dune"), cinema_name ("Galaxy Cinema"), date ("tomorrow"), seat_type ("VIP"), and quantity (2). However, showtime is missing. According to the rules, I should check the schedule first to see what showtimes are available before asking.
Action: check_movie_schedule
Action Input: {{"movie_name": "Dune", "cinema_name": "Galaxy Cinema", "date": "2026-06-02"}}
Observation: {{"status": "success", "movie_name": "Dune", "cinema_name": "Galaxy Cinema", "date": "2026-06-02", "available_showtimes": ["18:30", "20:45"], "base_price": 80000, "currency": "VND"}}
Thought: Available showtimes are 18:30 and 20:45. I need the user to select one showtime before calculating price or booking.
Final Answer: Rạp Galaxy Cinema ngày mai có các suất chiếu phim Dune lúc 18:30 và 20:45. Giá vé cơ bản là 80.000 VNĐ. Bạn vui lòng chọn suất chiếu muốn đặt nhé!

Turn 2:
User: "Chọn suất chiếu 20:45 nhé."
Thought: The user selected 20:45. I now have the showtime ("20:45"). I can calculate the price. Let me ask if they have a discount code or proceed to calculation directly.
Action: calculate_total_price
Action Input: {{"base_price": 80000, "quantity": 2, "seat_type": "VIP", "discount_code": ""}}
Observation: {{"status": "success", "base_price": 80000, "quantity": 2, "seat_type": "VIP", "total_price": 240000, "formatted_total": "240,000 VND"}}
Thought: Total price is 240,000 VND. According to Behavior Rules, I must ask for user confirmation before executing book_movie_ticket.
Final Answer: Tổng chi phí cho 2 vé VIP phim Dune lúc 20:45 tại Galaxy Cinema là 240.000 VNĐ. Bạn có xác nhận muốn đặt vé không?

Turn 3:
User: "Đồng ý đặt vé."
Thought: The user confirmed booking. I can proceed to finalize booking.
Action: book_movie_ticket
Action Input: {{"movie_name": "Dune", "cinema_name": "Galaxy Cinema", "showtime": "20:45", "seat_type": "VIP", "quantity": 2, "total_price": 240000}}
Observation: {{"status": "success", "booking_confirmed": true, "booking_id": "BK90827364", "message": "Đặt vé thành công!"}}
Thought: Booking is confirmed. I can present the final answer with booking code BK90827364.
Final Answer: Đặt vé thành công! Mã đặt chỗ của bạn là BK90827364. Vui lòng đến rạp trước 15 phút để nhận vé. Chúc bạn có một buổi xem phim tuyệt vời!
"""

    def run(self, user_input: str) -> str:
        """Runs the agent and returns the final string answer (satisfies base signature)."""
        result = self.run_with_trace(user_input)
        return result.get("final_answer", "Xin lỗi, đã xảy ra lỗi trong quá trình xử lý.")

    def run_with_trace(self, user_input: str) -> Dict[str, Any]:
        """
        Runs the ReAct loop and records all details including thought steps,
        tool logs, latency, and tokens.
        """
        start_time = time.time()
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        system_prompt = self.get_system_prompt()
        current_prompt = user_input
        steps_trace = []
        final_answer = None
        
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        # Telemetry Structured Error Metrics
        error_metrics = {
            "JSON_PARSER_ERROR": 0,
            "HALLUCINATED_TOOL_ERROR": 0,
            "WRONG_TOOL_ORDER_ERROR": 0,
            "MISSING_PARAMETERS_ERROR": 0
        }
        
        tools_called = []
        
        for step in range(1, self.max_steps + 1):
            # Call the LLM provider
            result = self.llm.generate(current_prompt, system_prompt=system_prompt)
            assistant_text = result.get("content", "").strip()
            
            # Aggregate token usage if available
            usage = result.get("usage", {})
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)
            
            # Check for Final Answer
            final_ans_text = self._extract_final_answer(assistant_text)
            if final_ans_text:
                final_answer = final_ans_text
                steps_trace.append({
                    "step": step,
                    "thought": self._extract_thought(assistant_text) or "Đã tìm thấy câu trả lời cuối cùng.",
                    "action": None,
                    "action_input": None,
                    "observation": None,
                    "final_answer": final_answer
                })
                break
            
            # Extract Action / Action Input
            action_name, params = self._extract_action(assistant_text)
            thought_text = self._extract_thought(assistant_text) or "Đang tiến hành gọi công cụ để lấy thông tin."
            
            step_record = {
                "step": step,
                "thought": thought_text,
                "action": action_name,
                "action_input": params,
                "observation": None,
                "final_answer": None
            }
            
            if action_name is None:
                error_metrics["JSON_PARSER_ERROR"] += 1
                observation = (
                    "ERROR: No Action or Final Answer found in your response. "
                    "Please follow the ReAct format exactly:\n"
                    "Thought: ...\nAction: <tool_name>\nAction Input: {\"key\": \"value\"}"
                )
            elif params is None:
                error_metrics["JSON_PARSER_ERROR"] += 1
                observation = (
                    "ERROR: Could not parse Action Input as valid JSON. "
                    "Please output a single raw JSON object after 'Action Input:'. "
                    "Example: {\"movie_name\": \"Doraemon\", \"cinema_name\": \"Beta\", \"date\": \"2026-06-01\"}"
                )
            elif action_name not in MOCK_TOOLS_MAP:
                error_metrics["HALLUCINATED_TOOL_ERROR"] += 1
                observation = (
                    f"ERROR: Unknown tool '{action_name}'. "
                    f"Available tools: {', '.join(MOCK_TOOLS_MAP.keys())}"
                )
            else:
                # Sequence verification guard checking
                wrong_order = False
                if action_name == "calculate_total_price" and "check_movie_schedule" not in tools_called:
                    wrong_order = True
                elif action_name == "book_movie_ticket" and "calculate_total_price" not in tools_called:
                    wrong_order = True
                
                if wrong_order:
                    error_metrics["WRONG_TOOL_ORDER_ERROR"] += 1
                    observation = (
                        f"ERROR: Cannot execute {action_name} due to incorrect tool order sequence constraint. "
                        f"You must run check_movie_schedule before calculate_total_price, and calculate_total_price before book_movie_ticket."
                    )
                    print(f"[WARN] Sequence violation detected in LLM Action: {action_name}")
                else:
                    # Execute tool
                    tool_fn = MOCK_TOOLS_MAP[action_name]
                    try:
                        result_data = tool_fn(**params)
                        observation = json.dumps(result_data, ensure_ascii=False, indent=2)
                        tools_called.append(action_name)
                        logger.log_event("TOOL_EXECUTION", {"tool": action_name, "params": params, "status": "success"})
                    except TypeError as e:
                        error_metrics["MISSING_PARAMETERS_ERROR"] += 1
                        observation = f"ERROR calling {action_name}: {e}. Params received: {params}"
                        logger.log_event("TOOL_EXECUTION", {"tool": action_name, "params": params, "status": "type_error", "error": str(e)})
                    except Exception as e:
                        observation = f"UNEXPECTED ERROR in {action_name}: {e}"
                        logger.log_event("TOOL_EXECUTION", {"tool": action_name, "params": params, "status": "error", "error": str(e)})
            
            step_record["observation"] = observation
            steps_trace.append(step_record)
            
            # Append turn and observation to prompt
            current_prompt += "\n" + assistant_text + f"\nObservation: {observation}\n"
        
        # Fallback if max steps exceeded
        if final_answer is None:
            fallback_prompt = current_prompt + "\nYou have used all available steps. Please now provide a Final Answer summarising what you found:\nFinal Answer:"
            result = self.llm.generate(fallback_prompt, system_prompt=system_prompt)
            fallback_text = result.get("content", "").strip()
            final_answer = self._extract_final_answer(fallback_text) or fallback_text
            steps_trace.append({
                "step": len(steps_trace) + 1,
                "thought": "Đã đạt số bước tối đa. Tóm tắt kết quả.",
                "action": None,
                "action_input": None,
                "observation": None,
                "final_answer": final_answer
            })
            
            usage = result.get("usage", {})
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)
            
        # Component 4: Runtime verify guard to prevent hallucinating booking confirmations
        # If the final answer contains booking success terms, but book_movie_ticket was not called, override it
        fake_success = False
        success_terms = ["đặt thành công", "mã đặt chỗ", "mã xác nhận", "mã vé", "booking_id", "booking id", "đã đặt chỗ", "đã đặt vé"]
        final_answer_lower = final_answer.lower()
        if any(term in final_answer_lower for term in success_terms):
            if "book_movie_ticket" not in tools_called:
                fake_success = True
                
        if fake_success:
            print("[WARN] Overriding hallucinated booking final answer!")
            final_answer = "Xin lỗi, tôi không thể hoàn tất đặt vé do thiếu thông tin rạp chiếu, suất chiếu hoặc quá trình gọi công cụ đặt vé gặp lỗi. Vui lòng cung cấp đầy đủ thông tin hoặc thực hiện lại yêu cầu."
            steps_trace.append({
                "step": len(steps_trace) + 1,
                "thought": "CẢNH BÁO CODE-LEVEL: Model đã tự ý bịa thông tin đặt vé khi chưa gọi book_movie_ticket. Ghi đè câu trả lời an toàn.",
                "action": None,
                "action_input": None,
                "observation": None,
                "final_answer": final_answer
            })
            error_metrics["WRONG_TOOL_ORDER_ERROR"] += 1
            
        latency_ms = int((time.time() - start_time) * 1000)
        logger.log_event("AGENT_END", {"steps": len(steps_trace), "latency_ms": latency_ms})
        
        return {
            "final_answer": final_answer,
            "steps": steps_trace,
            "error_metrics": error_metrics,
            "metrics": {
                "total_steps": len(steps_trace),
                "latency_ms": latency_ms,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens
            }
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # PARSING HELPERS (adapted from react_agent.py)
    # ─────────────────────────────────────────────────────────────────────────────
    
    def _drop_hallucinated_obs(self, text: str) -> str:
        return re.split(r"<\s*[Oo]bservation\s*>", text)[0]

    def _normalise_closed_tags(self, text: str) -> str:
        pairs = [
            (r"<\s*Thought\s*>(.*?)<\s*/\s*Thought\s*>",            r"Thought: \1"),
            (r"<\s*Action Input\s*>(.*?)<\s*/\s*Action Input\s*>",  r"Action Input: \1"),
            (r"<\s*Action\s*>(.*?)<\s*/\s*Action\s*>",              r"Action: \1"),
            (r"<\s*Final Answer\s*>(.*?)<\s*/\s*Final Answer\s*>",  r"Final Answer: \1"),
        ]
        for pat, repl in pairs:
            text = re.sub(pat, repl, text, flags=re.DOTALL | re.IGNORECASE)
        return text

    def _try_parse_json(self, raw: str):
        for candidate in (raw, raw.replace("'", '"')):
            candidate = re.sub(r",\s*([}\]])", r"\1", candidate)  # trailing commas
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        return None

    def _extract_thought(self, raw_text: str) -> Optional[str]:
        text = self._drop_hallucinated_obs(raw_text)
        text = self._normalise_closed_tags(text)
        text = re.sub(r"<[^>]+>", "", text)
        match = re.search(r"Thought\s*:\s*(.*)", text, re.IGNORECASE)
        if not match:
            return None
        thought = match.group(1).strip()
        # Trim off other ReAct block patterns
        thought = re.split(r"\nAction\s*:", thought, flags=re.IGNORECASE)[0].strip()
        thought = re.split(r"\nFinal Answer\s*:", thought, flags=re.IGNORECASE)[0].strip()
        return thought if thought else None

    def _extract_action(self, raw_text: str):
        text = self._drop_hallucinated_obs(raw_text)
        
        # Path A/B: opening tags
        xml_action_m = re.search(r"<\s*Action\s*>\s*([\w_]+)", text, re.IGNORECASE)
        xml_input_m  = re.search(r"<\s*Action Input\s*>\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)

        if xml_action_m:
            action_name = xml_action_m.group(1).strip()
            if xml_input_m:
                params = self._try_parse_json(xml_input_m.group(1).strip())
                return action_name, params
            return action_name, None

        # Path C: plain ReAct
        text = self._normalise_closed_tags(text)
        plain_action_m = re.search(r"Action\s*:\s*(.+)", text, re.IGNORECASE)
        plain_input_m  = re.search(r"Action Input\s*:\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)

        if not plain_action_m:
            return None, None

        action_name = plain_action_m.group(1).strip().split()[0]
        action_name = re.sub(r"[<>/]", "", action_name).strip()

        if not plain_input_m:
            return action_name, None

        params = self._try_parse_json(plain_input_m.group(1).strip())
        return action_name, params

    def _extract_final_answer(self, raw_text: str) -> Optional[str]:
        text = self._drop_hallucinated_obs(raw_text)
        text = self._normalise_closed_tags(text)
        text = re.sub(r"<[^>]+>", "", text)
        match = re.search(r"Final Answer\s*:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        answer = match.group(1).strip()
        answer = re.split(r"\nThought\s*:", answer, flags=re.IGNORECASE)[0].strip()
        answer = re.split(r"\nAction\s*:",  answer, flags=re.IGNORECASE)[0].strip()
        return answer if answer else None

