# Individual Report: Lab 3 - Chatbot vs ReAct Agent for Movie Booking

- **Student Name**: Nguyễn Văn A
- **Student ID**: 2A202600943
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

In this lab, I contributed to building the core booking tools, implementing the agent's short/long-term memory system, and setting up the evaluation runner.

- **Modules Implemented**:
  1. **`src/tools/movie_tools.py`**: Created the mock database (movies, showtimes, seats, and concessions) and implemented tools like `get_movie_info`, `check_seat_availability`, `calculate_total_price`, `apply_voucher`, `book_ticket`, and `web_search` (with Tavily API search and local keyword fallback).
  2. **`src/agent/memory.py`**: Implemented `ShortTermMemory` to track conversational dialogue and `LongTermMemory` to persist user profiles, seat preferences, voucher wallets, and past bookings history in `memory/user_profile.json`.
  3. **`src/agent/agent.py`**: Integrated memory profiles directly into the system prompt and updated the ReAct loop executor with support for JSON argument parsing and database updates.
  4. **`run_eval.py`**: Wrote the evaluation runner executing 4 standard tests and collecting performance telemetry.

- **Code Highlights**:
  - The long-term memory updater in `agent.py` intercepting successful bookings:
    ```python
    res_str = book_ticket(...)
    res_data = json.loads(res_str)
    if res_data.get("status") == "success":
        past_bookings = self.long_term_memory.data.get("past_bookings", [])
        past_bookings.append({...})
        self.long_term_memory.update_profile("past_bookings", past_bookings)
    ```

---

## II. Debugging Case Study (10 Points)

Using the telemetry and structured log system in `logs/`, I debugged a severe **Infinite Loop and Parser Crash** failure.

- **Problem Description**: The agent got stuck in an infinite loop while attempting to book tickets, outputting the action:
  `Action: book_ticket(movie_name='batman', seats=['B1', 'B2'])`
  The system failed to parse this and returned an error observation. The LLM kept repeating the exact same Action step until it timed out.
- **Log Source**: Detected event in `logs/2026-06-01.log`:
  ```json
  {"timestamp": "2026-06-01T07:54:10.123Z", "event": "AGENT_STEP", "data": {"step": 2, "llm_output": "Action: book_ticket(movie_name='batman', seats=['B1', 'B2'])"}}
  {"timestamp": "2026-06-01T07:54:10.125Z", "event": "TOOL_ERROR", "data": {"error": "JSONDecodeError: Expecting property name enclosed in double quotes"}}
  ```
- **Diagnosis**: 
  1. The agent outputted arguments using Python-style single quotes instead of valid JSON double quotes.
  2. The parser only used `json.loads(args_str)`, which threw exceptions on single-quoted string keys or elements.
  3. Because the parser crashed, the LLM received a generic error observation, panicked, and repeated the same call (infinite loop).
- **Solution**:
  I updated `_parse_arguments` in `src/agent/agent.py` to:
  1. Attempt direct JSON parsing.
  2. If it fails, clean the string by replacing single quotes `'` with double quotes `"` and retry.
  3. If that still fails, execute a regular expression fallback parser to extract key-value pairs (e.g. `movie_name="batman"`).
  This successfully prevented parser crashes, resolving the infinite loop issue.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: The ReAct agent uses the `Thought` block to explicitly plan. This allows it to break down "Calculate standard tickets with 30% discount and book them" into sequence: check showtime -> check seats -> calculate discount -> execute transaction. The Chatbot cannot plan and attempts to guess the booking ID, causing failure.
2. **Reliability**: ReAct Agents perform *worse* on simple conversational inputs (e.g., "Hello", "Thank you") because they still formulate `Thought` processes and incur high API latency (1.2s vs 0.2s) and higher token costs to output a simple greeting.
3. **Observation**: Environment feedback is crucial. When a tool fails (e.g. "Seat already booked"), the observation tells the LLM the exact reason, allowing it to regenerate a new thought and try a different seat instead of failing the session.

---

## IV. Future Improvements (5 Points)

To scale this movie booking agent system for production:
1. **Asynchronous Parallel Tool Calls**: For booking multiple movies or checking multiple showtimes, the agent should run tool calls concurrently (e.g. using `asyncio.gather`) to reduce overall latency.
2. **Supervisor Audit Flow**: Introduce a guardrail layer (like Llama Guard or a second LLM agent) that inspects the final booking action to confirm the total price matches the user's approval before committing money transactions.
3. **Vector DB for Large-Scale Catalogs**: Instead of passing all movie showtimes in the prompt, use a Vector Database to retrieve only showtimes relevant to the user query and inject them as context.
