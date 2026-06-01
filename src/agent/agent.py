import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.agent.memory import ShortTermMemory, LongTermMemory

class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Supports short-term and long-term memory, dynamic tool execution, and telemetry logging.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 6):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.short_term_memory = ShortTermMemory()
        self.long_term_memory = LongTermMemory()
        self.current_trace: List[Dict[str, Any]] = []

    def get_system_prompt(self) -> str:
        """
        Constructs the system prompt that instructs the agent to follow ReAct.
        Includes available tools, short-term history, and long-term profile data.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        
        long_term_summary = self.long_term_memory.get_profile_as_string()
        
        return f"""Bạn là một Movie Booking Agent chuyên nghiệp, thân thiện và đáng tin cậy. Bạn hỗ trợ người dùng tìm lịch chiếu, giá vé, tình trạng ghế, áp mã giảm giá, và đặt vé phim.

### THÔNG TIN NGƯỜI DÙNG (LONG-TERM MEMORY):
{long_term_summary}

### CÁC CÔNG CỤ CÓ SẴN:
{tool_descriptions}

### QUY TRÌNH SUY LUẬN NHIỀU BƯỚC (ReAct):
Để giải quyết yêu cầu của người dùng, lặp lại vòng lặp sau:

Thought: Giải thích bạn cần thông tin gì và sẽ gọi công cụ nào.
Action: tool_name(arguments_as_valid_json)
Observation: [Hệ thống sẽ chạy công cụ và trả kết quả tại đây]

... (Lặp lại Thought → Action → Observation cho đến khi có đủ thông tin)

Final Answer: [Phản hồi cuối cùng cho người dùng. Trình bày rõ ràng chi tiết giá, số ghế, mã đặt vé, hoặc lịch chiếu. Giữ giọng văn thân thiện và súc tích.]

#### QUY TẮC ĐỊNH DẠNG:
- Tham số của Action PHẢI là JSON hợp lệ.
- Ví dụ định dạng Action:
  Thought: Tôi cần kiểm tra ghế trống cho Dune 2.
  Action: check_seat_availability({{"movie_name": "dune 2", "showtime": "17:30"}})
- KHÔNG tự xuất "Observation:". Hệ thống sẽ cung cấp.
- Dừng sinh nội dung ngay sau khối Action.

#### TOOL ORDER (MANDATORY):
1. get_movie_info: Get showtimes, base prices, and details.
2. check_seat_availability: Check available seats for standard/VIP.
3. calculate_total_price: Calculate subtotal, discounts (vouchers), concessions, and total price.
4. book_ticket: Finalize booking transaction.

#### BEHAVIOR RULES:
- Ask for missing details before calling a tool.
- If multiple showtimes are returned, ask the user to choose one.
- If seat type or quantity is missing, ask for it.
- Check user's preferred seat class in the User Profile above and prioritize it.
- Apply vouchers (like CGV30 or STUDENT) if the user has them in their Profile or requests them.
- After calculating the price, ask for confirmation before booking, unless the user explicitly requested automatic booking (e.g., "đặt giúp tôi", "book giúp").
- If the user requests automatic booking, automatically select available seats from the check_seat_availability results and proceed directly to book_ticket. Do not stop to ask the user to choose or confirm seats.
- If there is no availability, propose another date, cinema, or showtime.
- If the user asks to watch a movie trailer, see a preview, or wants to check what a movie is about, call search_youtube_trailer to provide the trailer video embed. Always output the exact trailer embed URL from the tool's output to the user.
- Keep responses concise and focused on booking.

#### REQUIRED SLOTS:
- movie_name
- showtime
- seat_type (or ticket_type)
- quantity

#### FAILURE HANDLING:
- If a movie is not found, list available movies (Dune: Part Two, The Batman, Spider-Man: Across the Spider-Verse) and ask the user to choose or search.
- If calculate_total_price fails, restate inputs and ask the user to verify.
- If booking fails, apologize, offer to retry or choose different seats.
"""

    def run(self, user_input: str) -> str:
        """
        Executes the ReAct loop:
        1. Accumulates conversation context and history.
        2. Queries LLM for Thought + Action.
        3. Parses Action, runs Tool, records Observation.
        4. Terminates on Final Answer or max steps.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        # Reset structured trace for this run
        self.current_trace = []
        
        # Add user query to short-term memory
        self.short_term_memory.add_message("user", user_input)
        
        react_trace = ""
        steps = 0
        final_answer = "Xin lỗi, tôi không thể hoàn thành yêu cầu trong giới hạn số bước."

        # Include short term history in current prompt to keep session context
        short_term_history = self.short_term_memory.get_history_as_string()
        current_prompt = f"Lịch sử hội thoại ngắn hạn:\n{short_term_history}\n\nTin nhắn mới từ người dùng:\nUser: {user_input}\nHãy luôn suy nghĩ (Thought) và trả lời (Final Answer) bằng Tiếng Việt!"

        while steps < self.max_steps:
            # 1. Generate LLM Response
            system_prompt = self.get_system_prompt()
            
            # Incorporate the ReAct trace into the generation prompt
            generation_prompt = current_prompt
            if react_trace:
                generation_prompt = f"{current_prompt}\n\n{react_trace}"
                
            response = self.llm.generate(generation_prompt, system_prompt=system_prompt)
            content = response.get("content", "").strip()
            
            # Log metric
            tracker.track_request(
                provider=response.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=response.get("usage", {}),
                latency_ms=response.get("latency_ms", 0)
            )
            
            logger.log_event("AGENT_STEP", {"step": steps, "llm_output": content})
            
            # Append output to ReAct trace
            react_trace += content + "\n"
            
            # Parse Thought
            thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|$)", content, re.DOTALL | re.IGNORECASE)
            thought = thought_match.group(1).strip() if thought_match else ""
            if thought:
                logger.log_event("AGENT_THOUGHT", {"step": steps, "thought": thought})
            
            # 2. Check for Final Answer
            final_match = re.search(r"Final Answer:\s*(.*)", content, re.DOTALL | re.IGNORECASE)
            if final_match:
                final_answer = final_match.group(1).strip()
                self.current_trace.append({
                    "step": steps,
                    "thought": thought,
                    "final_answer": final_answer
                })
                break
                
            # 3. Parse Action
            action_match = re.search(r"Action:\s*(\w+)\((.*)\)", content, re.DOTALL)
            
            # Robust fallback: if no Action and no Final Answer keyword, but we have text outside Thought,
            # treat it as the Final Answer (model forgot prefix).
            is_final_fallback = False
            if not action_match and not final_match:
                text_without_thought = content
                if thought_match:
                    text_without_thought = content.replace(thought_match.group(0), "").strip()
                
                text_without_thought = re.sub(r"^(Action:|Observation:|Final Answer:)\s*", "", text_without_thought, flags=re.IGNORECASE).strip()
                if text_without_thought:
                    final_answer = text_without_thought
                    self.current_trace.append({
                        "step": steps,
                        "thought": thought,
                        "final_answer": final_answer
                    })
                    is_final_fallback = True
            
            if is_final_fallback:
                break
                
            if action_match:
                tool_name = action_match.group(1).strip()
                args_str = action_match.group(2).strip()
                
                # Parse args
                args_dict = self._parse_arguments(args_str)
                logger.log_event("TOOL_CALL", {"tool": tool_name, "args": args_dict})
                
                # Record trace step
                self.current_trace.append({
                    "step": steps,
                    "thought": thought,
                    "tool": tool_name,
                    "arguments": args_dict,
                    "observation": ""
                })
                
                # Execute tool
                observation = self._execute_tool(tool_name, args_dict)
                if observation.startswith(f"Tool {tool_name} not found."):
                    tracker.track_error("HALLUCINATION_ERROR", f"LLM hallucinated non-existent tool '{tool_name}'")
                
                logger.log_event("TOOL_RESPONSE", {"tool": tool_name, "result": observation})
                
                # Update observation in trace
                self.current_trace[-1]["observation"] = observation
                
                # Append Observation to ReAct trace
                react_trace += f"Observation: {observation}\n"
            else:
                # If no Action and no Final Answer, LLM might have returned a thought only or got confused.
                error_msg = "No valid ReAct Action format found."
                tracker.track_error("JSON_PARSER_ERROR", "LLM response did not contain a valid Action or Final Answer block.")
                
                self.current_trace.append({
                    "step": steps,
                    "thought": thought or content,
                    "error": error_msg
                })
                react_trace += f"Observation: Error - {error_msg} Please write 'Action: tool_name(arguments)' or 'Final Answer: ...'\n"
                
            steps += 1
            
        if steps >= self.max_steps and not final_match:
            tracker.track_error("TIMEOUT_ERROR", f"ReAct agent exceeded max_steps ({self.max_steps}) without generating a Final Answer.")
            
        logger.log_event("AGENT_END", {"steps": steps, "final_answer": final_answer})
        
        # Save final answer to short-term memory
        self.short_term_memory.add_message("assistant", final_answer)
        
        return final_answer

    def _parse_arguments(self, args_str: str) -> Dict[str, Any]:
        """
        Parses arguments from string format into a dict. Supports JSON and key=value patterns.
        """
        args_str = args_str.strip()
        if not args_str:
            return {}
            
        # 1. Try parsing as JSON
        try:
            return json.loads(args_str)
        except json.JSONDecodeError:
            pass
            
        # 2. Clean single quotes to double quotes and retry
        try:
            cleaned = args_str.replace("'", '"')
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
            
        # 3. Handle single string (e.g. "dune 2")
        if (args_str.startswith('"') and args_str.endswith('"')) or (args_str.startswith("'") and args_str.endswith("'")):
            return {"raw_arg": args_str[1:-1]}
            
        # 4. Handle key=value string
        parsed = {}
        pattern = r"(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|([^,\s\)]+))"
        matches = re.findall(pattern, args_str)
        for match in matches:
            key = match[0]
            val = match[1] or match[2] or match[3]
            parsed[key] = val
            
        if parsed:
            return parsed
            
        return {"raw_arg": args_str}

    def _execute_tool(self, tool_name: str, args_dict: Dict[str, Any]) -> str:
        """
        Executes the requested tool dynamically and updates long-term memory on successful booking.
        """
        from src.tools.movie_tools import (
            get_movie_info,
            check_seat_availability,
            apply_voucher,
            calculate_total_price,
            book_ticket,
            web_search,
            search_youtube_trailer
        )
        try:
            if tool_name == "get_movie_info":
                movie_name = args_dict.get("movie_name") or args_dict.get("raw_arg") or ""
                return get_movie_info(movie_name=movie_name)
                
            elif tool_name == "check_seat_availability":
                movie_name = args_dict.get("movie_name") or ""
                showtime = args_dict.get("showtime") or ""
                return check_seat_availability(movie_name=movie_name, showtime=showtime)
                
            elif tool_name == "apply_voucher":
                voucher_code = args_dict.get("voucher_code") or args_dict.get("raw_arg") or ""
                return apply_voucher(voucher_code=voucher_code)
                
            elif tool_name == "calculate_total_price":
                ticket_type = args_dict.get("ticket_type") or "Standard"
                try:
                    quantity = int(args_dict.get("quantity") or 1)
                except Exception:
                    quantity = 1
                
                popcorn_val = args_dict.get("popcorn_combo_type")
                if popcorn_val is None or (isinstance(popcorn_val, str) and not popcorn_val.strip().isdigit()):
                    popcorn_combo_type = 0
                else:
                    try:
                        popcorn_combo_type = int(popcorn_val)
                    except Exception:
                        popcorn_combo_type = 0

                voucher_code = args_dict.get("voucher_code") or ""
                return calculate_total_price(
                    ticket_type=ticket_type,
                    quantity=quantity,
                    popcorn_combo_type=popcorn_combo_type,
                    voucher_code=voucher_code
                )
                
            elif tool_name == "book_ticket":
                movie_name = args_dict.get("movie_name") or ""
                showtime = args_dict.get("showtime") or ""
                seats = args_dict.get("seats") or []
                if isinstance(seats, str):
                    # parse string representation of list like "['A1', 'A2']" or "A1, B2"
                    if "[" in seats:
                        seats = seats.replace("[", "").replace("]", "").replace("'", "").replace('"', "").split(",")
                        seats = [s.strip() for s in seats if s.strip()]
                    else:
                        seats = [s.strip() for s in seats.split(",") if s.strip()]
                ticket_type = args_dict.get("ticket_type") or "Standard"
                
                popcorn_val = args_dict.get("popcorn_combo_type")
                if popcorn_val is None or (isinstance(popcorn_val, str) and not popcorn_val.strip().isdigit()):
                    popcorn_combo_type = 0
                else:
                    try:
                        popcorn_combo_type = int(popcorn_val)
                    except Exception:
                        popcorn_combo_type = 0

                voucher_code = args_dict.get("voucher_code") or ""
                
                res_str = book_ticket(
                    movie_name=movie_name,
                    showtime=showtime,
                    seats=seats,
                    ticket_type=ticket_type,
                    popcorn_combo_type=popcorn_combo_type,
                    voucher_code=voucher_code
                )
                
                # Check status and update long-term memory
                try:
                    res_data = json.loads(res_str)
                    if res_data.get("status") == "success":
                        past_bookings = self.long_term_memory.data.get("past_bookings", [])
                        past_bookings.append({
                            "booking_id": res_data.get("booking_id"),
                            "movie": res_data.get("movie"),
                            "showtime": res_data.get("showtime"),
                            "seats": res_data.get("seats"),
                            "ticket_type": res_data.get("ticket_type"),
                            "total_price": res_data.get("total_price")
                        })
                        self.long_term_memory.update_profile("past_bookings", past_bookings)
                except Exception as e:
                    logger.error(f"Error updating booking in memory: {e}")
                    
                return res_str
                
            elif tool_name == "web_search":
                query = args_dict.get("query") or args_dict.get("raw_arg") or ""
                return web_search(query=query)
                
            elif tool_name == "search_youtube_trailer":
                movie_name = args_dict.get("movie_name") or args_dict.get("raw_arg") or ""
                return search_youtube_trailer(movie_name=movie_name)
                
            else:
                return f"Tool {tool_name} not found."
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Execution error: {str(e)}"}, ensure_ascii=False)
