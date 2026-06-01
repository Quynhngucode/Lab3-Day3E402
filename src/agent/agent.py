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
        
        return f"""You are a helpful and polite Movie Booking Agent. You assist users in finding movie showtimes, pricing, seat availability, applying vouchers, and booking tickets.

### USER PROFILE (LONG-TERM MEMORY):
{long_term_summary}

### AVAILABLE TOOLS:
{tool_descriptions}

### PROTOCOL FOR MULTI-STEP REASONING (ReAct):
To resolve the user's query, follow this precise loop:

Thought: Write a sentence explaining what information you need and which tool you will call.
Action: tool_name(arguments_as_valid_json)
Observation: [The system will run the tool and return the output here]

... (Repeat Thought -> Action -> Observation as many times as needed)

Final Answer: [Write your final response to the user. Explain pricing details, seat numbers, booking ID, or showtimes clearly. Keep it friendly and concise.]

#### FORMAT RULES:
- The Action arguments MUST be valid JSON.
- Example Action format:
  Thought: I need to check the seat availability for Dune 2.
  Action: check_seat_availability({{"movie_name": "dune 2", "showtime": "17:30"}})
- Do NOT output "Observation:". The system will provide it.
- Stop generating content immediately after the Action block.

#### BOOKING RULES:
1. ALWAYS use get_movie_info to find correct showtimes and prices.
2. ALWAYS use check_seat_availability to find seats that are marked "Available".
3. ALWAYS check the user's preferred seat class (e.g. VIP vs Standard) in the User Profile above and prioritize it.
4. ALWAYS call calculate_total_price first to check the cost, discounts, and vouchers before booking.
5. Apply vouchers (like CGV30 or STUDENT) if the user has them in their Profile or requests them.
6. Once seats and pricing are confirmed, call book_ticket to complete the transaction. Report the booking ID, seats, and final price in your Final Answer.
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
        final_answer = "Sorry, I could not complete the request within the step limit."

        # Include short term history in current prompt to keep session context
        short_term_history = self.short_term_memory.get_history_as_string()
        current_prompt = f"Short-term conversation history:\n{short_term_history}\n\nNew message to answer:\nUser: {user_input}"

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
                logger.log_event("TOOL_RESPONSE", {"tool": tool_name, "result": observation})
                
                # Update observation in trace
                self.current_trace[-1]["observation"] = observation
                
                # Append Observation to ReAct trace
                react_trace += f"Observation: {observation}\n"
            else:
                # If no Action and no Final Answer, LLM might have returned a thought only or got confused.
                self.current_trace.append({
                    "step": steps,
                    "thought": thought or content,
                    "error": "No valid ReAct Action format found."
                })
                react_trace += "Observation: Error - No action format found. Please write 'Action: tool_name(arguments)' or 'Final Answer: ...'\n"
                
            steps += 1
            
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
            web_search
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
                quantity = int(args_dict.get("quantity") or 1)
                popcorn_combo_type = int(args_dict.get("popcorn_combo_type") or 0)
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
                popcorn_combo_type = int(args_dict.get("popcorn_combo_type") or 0)
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
                
            else:
                return f"Tool {tool_name} not found."
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Execution error: {str(e)}"}, ensure_ascii=False)
