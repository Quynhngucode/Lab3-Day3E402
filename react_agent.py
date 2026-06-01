"""
ReAct Agent - Cinema Ticket Booking
=====================================
Powered by Phi-3-mini-4k-instruct-q4.gguf via llama-cpp-python.

Architecture:
  Thought  →  Action / Action Input  →  [Tool execution]  →  Observation  →  (repeat)
  Final Answer  →  stop

Usage:
  python react_agent.py
"""

import sys
import io
import json

# Force UTF-8 output on Windows so Vietnamese text and symbols render correctly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
import re
import random
import string
from datetime import datetime
from llama_cpp import Llama

# ─────────────────────────────────────────────────────────────────────────────
# 1.  MODEL INITIALISATION
# ─────────────────────────────────────────────────────────────────────────────

MODEL_PATH = "./models/Phi-3-mini-4k-instruct-q4.gguf"

print("[*] Loading model ...  (first run may take ~30 s)")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,
    n_threads=4,
    verbose=False,          # set True to see llama.cpp debug output
)
print("[OK] Model loaded.\n")


# ─────────────────────────────────────────────────────────────────────────────
# 2.  TOOL DEFINITIONS  (mock implementations)
# ─────────────────────────────────────────────────────────────────────────────

def check_movie_schedule(movie_name: str, cinema_name: str, date: str) -> dict:
    """
    Returns available showtimes and a base ticket price for the requested
    movie / cinema / date combination.
    """
    # ── mock data ──────────────────────────────────────────────────────────
    movies = {
        "default": {
            "showtimes": ["10:00", "13:00", "16:30", "19:45", "22:00"],
            "base_price": 85_000,          # VND
        },
        "avengers": {
            "showtimes": ["11:00", "14:30", "18:00", "21:30"],
            "base_price": 90_000,
        },
        "doraemon": {
            "showtimes": ["09:00", "11:30", "14:00", "16:30"],
            "base_price": 75_000,
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
) -> dict:
    """
    Computes the final ticket cost.
    Seat multipliers: VIP × 1.5, Premium × 1.3, Standard × 1.0
    Discount codes  : SUMMER20 → 20 %, STUDENT10 → 10 %
    """
    multipliers = {
        "vip": 1.5,
        "premium": 1.3,
        "standard": 1.0,
    }
    discounts = {
        "SUMMER20": 0.20,
        "STUDENT10": 0.10,
        "AI20K": 0.15,
    }

    seat_key = seat_type.lower()
    multiplier = multipliers.get(seat_key, 1.0)

    subtotal = base_price * multiplier * quantity
    discount_rate = discounts.get(discount_code.upper(), 0.0)
    discount_amount = subtotal * discount_rate
    total = subtotal - discount_amount

    return {
        "status": "success",
        "base_price": base_price,
        "seat_type": seat_type,
        "seat_multiplier": multiplier,
        "quantity": quantity,
        "subtotal": subtotal,
        "discount_code": discount_code or "none",
        "discount_rate": f"{int(discount_rate * 100)}%",
        "discount_amount": discount_amount,
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


# ─────────────────────────────────────────────────────────────────────────────
# 3.  TOOL REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

TOOLS: dict[str, callable] = {
    "check_movie_schedule": check_movie_schedule,
    "calculate_total_price": calculate_total_price,
    "book_movie_ticket": book_movie_ticket,
}

TOOL_DESCRIPTIONS = """
You have access to these tools:

1. check_movie_schedule(movie_name, cinema_name, date)
   - Retrieves available showtimes and base ticket price.
   - movie_name: string  |  cinema_name: string  |  date: string (e.g. "2026-06-01")

2. calculate_total_price(base_price, quantity, seat_type, discount_code="")
   - Computes the final total cost.
   - base_price: number  |  quantity: integer  |  seat_type: "standard"|"vip"|"premium"
   - discount_code: optional string

3. book_movie_ticket(movie_name, cinema_name, showtime, seat_type, quantity, total_price)
   - Completes the booking and returns a confirmation code.
   - All fields are required.
"""

# ─────────────────────────────────────────────────────────────────────────────
# 4.  SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are a cinema ticket booking assistant. Your goal is to help users through selecting a movie and showtime, calculating total price, and confirming the reservation.
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
{TOOL_DESCRIPTIONS}
"""


# ─────────────────────────────────────────────────────────────────────────────
# 5.  PARSING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _drop_hallucinated_obs(text: str) -> str:
    """Cut text at the first hallucinated Observation block."""
    return re.split(r"<\s*[Oo]bservation\s*>", text)[0]


def _normalise_closed_tags(text: str) -> str:
    """
    Convert **closed** XML tags to plain ReAct colon format.
    e.g.  <Action>foo</Action>  =>  Action: foo
    """
    pairs = [
        (r"<\s*Thought\s*>(.*?)<\s*/\s*Thought\s*>",            r"Thought: \1"),
        (r"<\s*Action Input\s*>(.*?)<\s*/\s*Action Input\s*>",  r"Action Input: \1"),
        (r"<\s*Action\s*>(.*?)<\s*/\s*Action\s*>",              r"Action: \1"),
        (r"<\s*Final Answer\s*>(.*?)<\s*/\s*Final Answer\s*>",  r"Final Answer: \1"),
    ]
    for pat, repl in pairs:
        text = re.sub(pat, repl, text, flags=re.DOTALL | re.IGNORECASE)
    return text


def _try_parse_json(raw: str):
    """Best-effort JSON parse with repair. Returns dict or None."""
    for candidate in (raw, raw.replace("'", '"')):
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)  # trailing commas
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None


def _extract_action(raw_text: str):
    """
    Returns (action_name, params_dict) or (None, None).

    Handles three formats Phi-3-mini produces:
      A) Unclosed XML:  <Action>foo</Action>\n<Action Input>\n{...}
      B) Closed XML:    <Action>foo</Action>\n<Action Input>{...}</Action Input>
      C) Plain text:    Action: foo\nAction Input: {...}
    """
    text = _drop_hallucinated_obs(raw_text)

    # ---- Path A/B: any <Action> opening tag (closed or unclosed) -----------
    xml_action_m = re.search(r"<\s*Action\s*>\s*([\w_]+)", text, re.IGNORECASE)
    # Capture JSON that follows <Action Input> regardless of closing tag
    xml_input_m  = re.search(
        r"<\s*Action Input\s*>\s*(\{.*?\})",
        text, re.DOTALL | re.IGNORECASE
    )

    if xml_action_m:
        action_name = xml_action_m.group(1).strip()
        if xml_input_m:
            params = _try_parse_json(xml_input_m.group(1).strip())
            return action_name, params   # params may be None => caller retries
        return action_name, None

    # ---- Path C: plain text (normalise closed tags first) ------------------
    text = _normalise_closed_tags(text)

    plain_action_m = re.search(r"Action\s*:\s*(.+)", text)
    plain_input_m  = re.search(r"Action Input\s*:\s*(\{.*?\})", text, re.DOTALL)

    if not plain_action_m:
        return None, None

    action_name = plain_action_m.group(1).strip().split()[0]
    action_name = re.sub(r"[<>/]", "", action_name).strip()

    if not plain_input_m:
        return action_name, None

    params = _try_parse_json(plain_input_m.group(1).strip())
    return action_name, params


def _extract_final_answer(raw_text: str):
    text = _drop_hallucinated_obs(raw_text)
    text = _normalise_closed_tags(text)
    # Remove any remaining XML tags around the answer text
    text = re.sub(r"<[^>]+>", "", text)
    match = re.search(r"Final Answer\s*:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    answer = match.group(1).strip()
    # Trim appended Thought/Action boilerplate
    answer = re.split(r"\nThought\s*:", answer)[0].strip()
    answer = re.split(r"\nAction\s*:",  answer)[0].strip()
    return answer if answer else None


# ─────────────────────────────────────────────────────────────────────────────
# 6.  AGENT LOOP
# ─────────────────────────────────────────────────────────────────────────────

MAX_STEPS = 5

def run_agent(user_query: str) -> str:
    """
    Runs the ReAct agent for `user_query`.
    Returns the Final Answer string.
    """
    print("=" * 70)
    print(f"[QUERY] {user_query}")
    print("=" * 70)

    # Build an initial prompt in Phi-3 chat format
    # <|system|> … <|end|><|user|> … <|end|><|assistant|>
    conversation = (
        f"<|system|>\n{SYSTEM_PROMPT}<|end|>\n"
        f"<|user|>\n{user_query}<|end|>\n"
        f"<|assistant|>\n"
    )

    for step in range(1, MAX_STEPS + 1):
        print(f"\n-- Step {step} -------------------------------------------------------")

        # ── call the LLM ────────────────────────────────────────────────────
        response = llm(
            conversation,
            max_tokens=512,
            stop=["Observation:", "<Observation>", "<observation>", "<|end|>", "<|user|>"],
            echo=False,
        )
        assistant_text = response["choices"][0]["text"].strip()
        print(f"[MODEL]:\n{assistant_text}\n")

        # ── check for Final Answer ─────────────────────────────────────────
        final_answer = _extract_final_answer(assistant_text)
        if final_answer:
            print("[DONE] Final Answer detected - stopping loop.")
            print("=" * 70)
            return final_answer

        # ── extract Action / Action Input ──────────────────────────────────
        action_name, params = _extract_action(assistant_text)

        if action_name is None:
            # Model produced no action and no final answer – nudge it
            observation = (
                "ERROR: No Action or Final Answer found in your response. "
                "Please follow the ReAct format exactly:\n"
                "Thought: ...\nAction: <tool_name>\nAction Input: {\"key\": \"value\"}"
            )
            print(f"[WARN] Observation (format error): {observation}")
        elif params is None:
            # Action found but JSON is broken
            observation = (
                f"ERROR: Could not parse Action Input as valid JSON. "
                f"Please output a single raw JSON object after 'Action Input:'. "
                f"Example: {{\"movie_name\": \"Doraemon\", \"cinema_name\": \"Beta\", \"date\": \"2026-06-01\"}}"
            )
            print(f"[WARN] Observation (JSON error): {observation}")
        elif action_name not in TOOLS:
            observation = (
                f"ERROR: Unknown tool '{action_name}'. "
                f"Available tools: {', '.join(TOOLS.keys())}"
            )
            print(f"[WARN] Observation (unknown tool): {observation}")
        else:
            # ── execute tool ───────────────────────────────────────────────
            tool_fn = TOOLS[action_name]
            try:
                result = tool_fn(**params)
                observation = json.dumps(result, ensure_ascii=False, indent=2)
                print(f"[TOOL] '{action_name}' executed.")
                print(f"[RESULT] {observation[:300]}{'...' if len(observation) > 300 else ''}")
            except TypeError as e:
                observation = f"ERROR calling {action_name}: {e}. Params received: {params}"
                print(f"[WARN] Tool call error: {observation}")
            except Exception as e:
                observation = f"UNEXPECTED ERROR in {action_name}: {e}"
                print(f"[WARN] Unexpected error: {observation}")

        # ── append assistant turn + observation, continue ──────────────────
        conversation += assistant_text + f"\nObservation: {observation}\n"

    # Exceeded MAX_STEPS
    print("\n[WARN] Maximum steps reached. Asking model for a final summary ...")
    conversation += (
        "\nYou have used all available steps. "
        "Please now provide a Final Answer summarising what you found:\n"
        "Final Answer:"
    )
    response = llm(conversation, max_tokens=300, stop=["<|end|>", "<|user|>"], echo=False)
    fallback = response["choices"][0]["text"].strip()
    print(f"[MODEL] Fallback output:\n{fallback}")
    print("=" * 70)
    return fallback


# ─────────────────────────────────────────────────────────────────────────────
# 7.  ENTRY POINT / DEMO
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")

    query = (
        f"Tìm lịch chiếu phim tại Beta Cinemas hôm nay ({today}). "
        "Sau đó tính tổng tiền mua 2 vé ghế VIP."
    )

    answer = run_agent(query)

    print("\n" + "=" * 70)
    print("FINAL ANSWER:")
    print("=" * 70)
    print(answer)
    print("=" * 70)
