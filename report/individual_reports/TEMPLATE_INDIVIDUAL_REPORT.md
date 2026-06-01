# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Vu Nhat Anh
- **Student ID**: 2A202600894
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

I focused on developing the automated testing suite, integrating the dynamic multi-prompt configuration for the Agent, and conducting a comprehensive performance comparison between the Chatbot Baseline and the ReAct Agent.

### 1. Modules Implemented
- **[agent.py]**: Upgraded the `ReActAgent` class to support the `prompt_version` parameter, allowing dynamic switching between Prompt v1 (Batch) and Prompt v2 (Conversational HITL).
- **[test_agent.py]**: Developed an automated unit testing suite for the ReAct Agent using a Mock LLM, validating happy path booking, unknown tool errors, and broken JSON formatting.
- **[test_chatbot.py]**: Created a baseline comparison testing suite for the Chatbot Baseline to evaluate its functional limitations and compare token efficiency.
- **[test_prompt_comparison.py]**: Established an automated testing script to compare the behavioral differences between Prompt v1 and Prompt v2.

### 2. Code Highlights
* **Dynamic Multi-Prompt Configuration**:
  ```python
  def __init__(self, llm: LLMProvider, tools: Optional[List[Dict[str, Any]]] = None, max_steps: int = 5, prompt_version: str = "v1"):
      self.llm = llm
      self.max_steps = max_steps
      self.history = []
      self.prompt_version = prompt_version
  ```
* **JSON Formatting Error Test Case**: Refer to the verified testing implementation in [test_agent.py]

### 3. Documentation
The testing implementation closely interacts with the Agent's ReAct loop by providing a `MockLLMProvider` class inheriting from `LLMProvider`. This class intercepts prompts generated during each reasoning step, verifies the accuracy of the `Action` and `Action Input`, and returns pre-designed ReAct response strings, enabling the Agent to execute the entire loop efficiently without invoking any paid external APIs.

---

## II. Debugging Case Study (10 Points)

I conducted a diagnostic analysis and designed an automated test case to isolate raw JSON syntax errors during LLM generation.

- **Problem Description**: The LLM attempted to invoke the correct tool (`check_movie_schedule`), but the `Action Input` omitted the closing brace `}` at the end of the raw JSON string:
  `Action Input: {"movie_name": "doraemon", "cinema_name": "Beta"`
- **Log Source**: The detailed simulated and successfully caught error trace is documented in [test_agent.py].
- **Diagnosis**: Large Language Models (LLMs), particularly smaller local models like Phi-3, generate strings word-by-word based on probability, which results in low formatting stability when outputting structured raw JSON. Without strict JSON Mode enforcement at the API level, the model frequently drops essential syntax characters like closing brackets.
- **Solution**: 
  1. Optimized the `_try_parse_json` processing function in `agent.py` to automatically correct minor syntax errors (such as replacing single quotes with double quotes).
  2. Caught exceptions upon parsing failures, returning an `Observation` containing clear error feedback and a standard JSON example. This lets the model learn dynamically and correct its formatting in the subsequent ReAct turn.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning
The `Thought` block acts as the Agent's scratchpad. For complex tasks composed of multiple interdependent steps (querying schedules -> calculating prices -> completing bookings), `Thought` allows the model to decompose the goal and plan sequentially before executing. Conversely, a standard Chatbot attempts to satisfy all requests in a single-turn generation without structured planning, which results in either hallucinating wrong data or declining the task due to the absence of real-time tools.

### 2. Reliability
Although the ReAct Agent is highly superior in resolving complex transactions via tools, it is significantly less efficient than a standard Chatbot for simple Q&A queries (such as *'Doctor Strange showtimes?'*). For this request, the Chatbot Baseline responds politely and instantly in exactly **one single turn (1.0 step)** and consumes **~315 tokens**. Meanwhile, the ReAct Agent takes **1,646 ms**, consumes **2,226 tokens**, and runs through **3.2 steps** only to discover that the movie is not showing and output an identical answer. This highlights a critical industry trade-off regarding operational costs and response latency.

### 3. Observation
The environment's feedback (`Observation`) is the source of real-time data guiding the Agent's subsequent steps. Without `Observation`, the model remains entirely 'blind' to the real world and can only formulate answers based on static pre-training data. Tool feedback (such as specific showtimes, actual base prices, or formatting error messages) directly impacts the `Thought` in the next step, allowing the LLM to make more precise tool invocation (`Action`) decisions dynamically.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Deploy an **Asynchronous Task Queue** architecture. Instead of synchronous processing that forces the user to wait on-screen while the LLM executes multiple ReAct loops, the ticket booking request will be pushed to a background worker queue, and the system will automatically notify the customer upon successful completion. This prevents server bottlenecks when handling tens of thousands of concurrent users.
- **Safety**: 
  1. *Human-in-the-loop (Two-step confirmation)*: Integrate a manual confirmation step from the user before executing high-risk, paid actions like booking (as successfully tested and proven in the Prompt v2 conversational flow).
  2. *Supervisor LLM (Guardrails/Audit)*: Deploy an independent secondary LLM acting as a Gatekeeper. This LLM will scan the arguments generated by the Agent, auditing them for business logic and safety (preventing Prompt Injection attacks trying to manipulate base prices to 0 or request excessive tickets) before allowing the request to hit production APIs.
- **Performance**: Implement **Retrieval-Augmented Tool Selection** by storing the descriptions of hundreds of different cinema business tools (popcorn ordering, loyalty lookup, point exchanges, ticket returns...) in a Vector Database. When a query is received, the system executes a similarity search to retrieve only the 2-3 most relevant tools and injects only their specs into the prompt. This reduces token consumption by up to 90%, dramatically speeds up response times, and prevents model confusion as the tool library grows.
