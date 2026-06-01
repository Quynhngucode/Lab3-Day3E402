# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: Team E402
- **Team Members**: Vu Nhat Anh, Bui Tuan Minh, Nguyen Hoai Ngoc, Tran Truc Quynh
- **Deployment Date**: 2026-06-01

---

## 1. Executive Summary

The system was built to solve the automated movie ticket booking problem at cinema branches (Beta Cinemas) using a ReAct Agent mechanism, and to directly compare its performance with a baseline chatbot (Chatbot Baseline).

- **Success Rate**: 
  - Chatbot Baseline: **50%** (Successful on 2/4 test cases).
  - ReAct Agent: **100%** (Successful on 4/4 test cases).
- **Key Outcome**: The ReAct Agent successfully resolved booking, seat-checking, and voucher application tasks by accurately invoking mock real-time data tools. In contrast, the Chatbot Baseline failed completely on complex booking tasks due to physical constraints preventing it from retrieving dynamic data or performing computations.

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation
The system implements the ReAct (Reasoning and Acting) inference loop with the following structure:
1. **Thought**: The LLM analyzes the current request to formulate a plan.
2. **Action**: The LLM selects precisely one tool from the provided list.
3. **Action Input**: The LLM formats the tool invocation arguments as a strictly valid JSON object.
4. **Observation**: The Agent executes the Python code of the tool, retrieves the returned data, and appends it to the conversation history for the LLM to proceed with the next reasoning step.
5. The loop terminates when the LLM outputs a **Final Answer** tag containing the ultimate, friendly answer in Vietnamese.

### 2.2 Tool Definitions (Inventory)
| Tool Name | Input Format | Use Case |
| :--- | :--- | :--- |
| `check_movie_schedule` | `{"movie_name": string, "cinema_name": string, "date": string}` | Retrieves available showtimes and the standard base ticket price at the designated cinema. |
| `calculate_total_price` | `{"base_price": number, "quantity": integer, "seat_type": string, "discount_code": string}` | Computes the final ticket cost based on quantity, seat type multipliers (VIP x1.5, Premium x1.3, Standard x1.0), and promotional discount codes. |
| `book_movie_ticket` | `{"movie_name": string, "cinema_name": string, "showtime": string, "seat_type": string, "quantity": integer, "total_price": number}` | Finalizes the booking transaction and generates a random booking confirmation code. |

### 2.3 LLM Providers Used
- **Primary**: Gemini Cloud API (Uses the model configured in the `.env` file, default is `gemini-3-flash-preview`).
- **Secondary (Backup)**: Local CPU Model (`Phi-3-mini-4k-instruct-q4.gguf` running on CPU via `llama-cpp-python`).
- **Development/Testing**: MockLLMProvider (Simulates deterministic responses for fast Unit Testing).

---

## 3. Telemetry & Performance Dashboard

Analysis of actual data collected during the final evaluation run (`logs/eval_results.json`):

- **Average Latency (P50)**:
  - Chatbot Baseline: **506.0 ms**
  - ReAct Agent: **1,519.0 ms** (Median computed from the runs: 1012ms, 1017ms, 2021ms, 2534ms)
- **Max Latency (P99)**:
  - Chatbot Baseline: **506.0 ms**
  - ReAct Agent: **2,534.0 ms**
- **Average Tokens per Task**:
  - Chatbot Baseline: **315.0 tokens** (Total of 1,260 tokens / 4 cases)
  - ReAct Agent: **2,226.0 tokens** (Total of 8,904 tokens / 4 cases)
- **Total Cost of Test Suite**: **$0.00** (Due to running via Mock Provider and free Gemini testing API).

---

## 4. Root Cause Analysis (RCA) - Failure Traces

To ensure robustness and real-world operational quality of the Agentic system, a Root Cause Analysis (RCA) was conducted on two Failure Traces of the ReAct Agent encountered during testing, which were subsequently packaged into automated regression test cases in the `tests/test_agent.py` file.

### Case Study 1: Lỗi Sai Định Dạng Cú Pháp Action Input (Broken JSON Syntax)
- **Input**: *"Xem lịch chiếu phim Doraemon hôm nay tại Beta."*
- **Observation**: The LLM generated the correct tool action (`check_movie_schedule`), but the `Action Input` had broken syntax due to a missing closing brace:
  `Action Input: {"movie_name": "doraemon", "cinema_name": "Beta"`
  The parsing system intercepted the error and threw: `ERROR: Could not parse Action Input as valid JSON. Please output a single raw JSON object...`
- **Root Cause**: Large Language Models (LLMs), especially smaller local models like Phi-3, are highly prone to omitting special characters (closing braces `}`, double quotes `"`) when generating raw JSON structures in free-form text mode without strict enforcement mechanisms (such as JSON Mode at the API level).
- **Resolution & Verification**:
  1. *Parser Defense*: Optimized the `_try_parse_json` processing function in `agent.py` to automatically correct minor syntax errors (such as replacing single quotes with double quotes and stripping trailing commas).
  2. *Feedback Loop Guardrail*: Designed an exception handling mechanism that translates syntax errors into an `Observation` containing visual feedback and a standard JSON example. In the next ReAct turn, the LLM reads the error Observation and successfully self-corrects the formatting.
  3. *Automated Regression*: Packaged this failure into the `test_react_agent_error_handling_invalid_json` test case to automatically verify the LLM's self-formatting capability with every update.

### Case Study 2: Ảo Tưởng Công Cụ Không Tồn Tại (Unknown Tool Hallucination)
- **Input**: *"Xem lịch Doraemon."*
- **Observation**: The LLM attempted to call an imaginary tool not in the registered list:
  `Action: get_weather_forecast`
  The Agent intercepted it and returned: `ERROR: Unknown tool 'get_weather_forecast'. Available tools: check_movie_schedule, calculate_total_price, book_movie_ticket`
- **Root Cause**: The LLM suffered from hallucination due to pre-training bias, assuming it had default search or weather tools while ignoring the actual tool list defined in the System Prompt.
- **Resolution & Verification**:
  1. *System Prompt Enforcement*: Tightened tool definition instructions in the System Prompt, explicitly requiring: *"Use only the exact tool names listed below."*
  2. *Self-Correction Loop*: Utilized the real-time error feedback mechanism of ReAct. Upon receiving the unknown tool error from the Observation, the LLM adjusted its reasoning strategy (`Thought`) and decided to call the correct available tool `check_movie_schedule`.
  3. *Automated Regression*: Automated testing via `test_react_agent_error_handling_unknown_tool` to ensure the Agent dynamically redirects to the correct action without crashing the system.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt v1 vs Prompt v2

We conducted an empirical comparison of the system's behavior under two system prompt configurations: Prompt v1 (Batch Execution-oriented) and Prompt v2 (Conversational HITL-oriented):

- **Prompt v1 (Default)**: Highly concise, pushing the LLM to automatically run through all necessary tool loops to output the final answer as quickly as possible.
- **Prompt v2 (Upgraded)**: Adds details on mandatory tool ordering, information slot-filling rules, requiring the user to choose when multiple showtimes are returned, and strictly demanding confirmation before executing booking.

**Analysis of experimental results (`tests/test_prompt_comparison.py`):**
1. **Automation and Response Latency (1-Turn Completion)**:
   - **Prompt v1**: Completes the entire ticket booking workflow (schedule query -> price calculation -> booking and ticket code output) in exactly **one single chat turn** via 4 continuous ReAct steps without communicating with the user.
   - **Prompt v2**: Complies strictly with conversational behavioral rules. Upon executing `check_movie_schedule` and receiving multiple available showtimes, the Agent **immediately halts the loop at step 2** and outputs a question asking the customer to select a specific showtime: *"Avengers showtimes at Beta today are: 11:00, 14:30, 18:00, and 21:30. Which showtime do you prefer?"*. This prevents the Agent from making unauthorized booking decisions when information is incomplete.
2. **Industrial Trade-offs**:
   - **HITL Safety**: Prompt v2 wins decisively. The two-step confirmation eliminates the risk of the Agent hallucinating the amount or purchasing the wrong ticket, causing financial loss to the customer.
   - **Resources and User Experience**: Prompt v1 provides a faster and more seamless experience (single-sentence instruction), but carries high risk. Prompt v2 is significantly safer but requires multi-turn dialogue, increasing overall latency and the system's API call volume.

### Experiment 2: Chatbot vs Agent
| Case ID | Test Case Name | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Simple Query (Doctor Strange Showtimes) | Correct | Correct | **Draw** |
| 2 | Showtimes & Price (Dune 2 VIP) | Correct | Correct | **Draw** |
| 3 | Check seats & Book (Batman) | Incorrect (Decline) | Correct | **Agent** |
| 4 | Memory & Loyalty Voucher (Dune 2) | Incorrect (Decline) | Correct | **Agent** |

---

## 6. Production Readiness Review

- **Security**: Successfully hid API Keys via `.env` environment variables. *[UNRESOLVED: Input Sanitization filtering for malicious parameters in tool calls has not been developed yet]*
- **Guardrails**: Configured and verified the `max_steps=5` parameter in `ReActAgent` to absolutely prevent infinite LLM reasoning loops, avoiding billing surprises.
- **Scaling**: *[UNRESOLVED: Advanced multi-agent orchestration mechanisms (LangGraph) or direct database/production API integration of cinemas have not been developed yet]*
