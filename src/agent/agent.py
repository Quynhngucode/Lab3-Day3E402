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
    
    def __init__(self, llm: LLMProvider, tools: Optional[List[Dict[str, Any]]] = None, max_steps: int = 5):
        self.llm = llm
        self.max_steps = max_steps
        self.history = []
        
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
        
        return f"""You are a cinema booking assistant that uses tools to help customers.
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
                observation = (
                    "ERROR: No Action or Final Answer found in your response. "
                    "Please follow the ReAct format exactly:\n"
                    "Thought: ...\nAction: <tool_name>\nAction Input: {\"key\": \"value\"}"
                )
            elif params is None:
                observation = (
                    "ERROR: Could not parse Action Input as valid JSON. "
                    "Please output a single raw JSON object after 'Action Input:'. "
                    "Example: {\"movie_name\": \"Doraemon\", \"cinema_name\": \"Beta\", \"date\": \"2026-06-01\"}"
                )
            elif action_name not in MOCK_TOOLS_MAP:
                observation = (
                    f"ERROR: Unknown tool '{action_name}'. "
                    f"Available tools: {', '.join(MOCK_TOOLS_MAP.keys())}"
                )
            else:
                # Execute tool
                tool_fn = MOCK_TOOLS_MAP[action_name]
                try:
                    result_data = tool_fn(**params)
                    observation = json.dumps(result_data, ensure_ascii=False, indent=2)
                    logger.log_event("TOOL_EXECUTION", {"tool": action_name, "params": params, "status": "success"})
                except TypeError as e:
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
            
        latency_ms = int((time.time() - start_time) * 1000)
        logger.log_event("AGENT_END", {"steps": len(steps_trace), "latency_ms": latency_ms})
        
        return {
            "final_answer": final_answer,
            "steps": steps_trace,
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

