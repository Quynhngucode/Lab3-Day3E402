# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Bui Tuan Minh
- **Student ID**: 2A202600728
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

During Lab 3, I made significant technical contributions aimed at enhancing the reliability of the ReAct Agent and resolving critical integration issues on the CineBot system:

- **Modules Implemented**: 
  - [static/index.html] (Resolved browser autofill overriding the API Key)
  - [react_agent.py] (Upgraded the System Prompt to Prompt v2)
  - [src/agent/agent.py] (Ensured synchronization of ReAct Agent logic)

- **Code Highlights**:
  1. *Preventing Browser Autofill from overriding the API Key in `static/index.html`*:
     ```html
     <input type="password" id="mimoApiKeyInput" placeholder="Nhập MiMo API Key..." autocomplete="new-password" />
     <input type="password" id="apiKeyInput" placeholder="Nhập Gemini API Key..." autocomplete="new-password" />
     ```
  2. *Upgrading to Prompt v2 for the ReAct Loop in `react_agent.py`*:
     ```python
     SYSTEM_PROMPT = f"""You are a cinema ticket booking assistant. Your goal is to help users through selecting a movie and showtime, calculating total price, and confirming the reservation.
     You MUST follow this exact ReAct loop format for EVERY step:

     Thought: <your reasoning about what to do next>
     Action: <exact tool name from the list>
     Action Input: <strictly valid JSON object with the required parameters>
     
     ...
     CRITICAL RULES:
     1. MANDATORY TOOL ORDER:
        check_movie_schedule -> calculate_total_price -> book_movie_ticket
     ...
     """
     ```

- **Documentation**: 
  - Declaring `autocomplete="new-password"` prevents browser password managers from automatically inserting stored credentials or mismatched passwords into the API Key input fields. This ensures that the frontend does not send invalid keys to the backend, which previously caused ReAct loop authentication failures.
  - Structuring Prompt v2 in a strict Thought-Action-Observation format guides the language models (both cloud-based like MiMo/Gemini and local like Phi-3) to respect cinema ticketing business rules. This enforces a mandatory tool sequence (`check_movie_schedule` -> `calculate_total_price` -> `book_movie_ticket`) and prevents calculation or booking when required slots or showtimes are missing.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: 
  - The ReAct Agent failed when switching to the `MiMo-v2.5-Pro` provider, returning the following system error: `Error code: 401 - {'error': {'message': 'Invalid API Key', 'param': 'Please provide valid API Key', 'code': '401', 'type': 'invalid_key'}}`, despite having a fully configured API Key in the `.env` file.

- **Log Source**: 
  - Log from backend `app.py` terminal:
    ```text
    [*] Processing message via MIMO provider in AGENT mode...
    [ERROR] OpenAI API call failed: Error code: 401 - {'error': {'message': 'Invalid API Key', 'param': 'Please provide valid API Key', 'code': '401', 'type': 'invalid_key'}}
    ```

- **Diagnosis**: 
  - A standalone verification (using python/requests to the endpoint `https://token-plan-sgp.xiaomimimo.com/v1` with the key in `.env`) succeeded with an HTTP `200 OK` status, proving the environment-configured key was completely valid and active.
  - The issue originated from credential autofill: The CineBot sidebar UI used hidden password inputs (`type="password"`) for API Key fields. Web browsers (e.g., Chrome/Edge) mistook these for standard login forms and automatically filled them with stored user passwords or outdated API keys.
  - The frontend script `static/index.js` read this autofilled value and sent it to the backend. The backend preferred this custom API Key over the environment variable, overriding the valid key with the incorrect autofilled one, resulting in a 401 authentication error.

- **Solution**: 
  - Modified `static/index.html` by adding the `autocomplete="new-password"` attribute to both API Key password inputs to completely disable browser autofill.
  - Instructed the user to clear the UI key fields to let the backend safely fall back to the `.env` variables. Following this fix, the agent connected successfully and never encountered the 401 error again.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: 
    - The `Thought` block acts as a highly effective Chain of Thought scratchpad for the ReAct Agent. Unlike a standard chatbot (which generates text directly based on probability), the `Thought` block enables the agent to decompose the request step-by-step: checking which parameters are missing, identifying the correct tool to call, and outlining intermediate goals. This makes the Agent significantly superior in handling multi-step cinema booking tasks.
2.  **Reliability**: 
    - The ReAct Agent can perform worse than a standard Chatbot if it encounters JSON/XML formatting errors (JSON Parser Errors), especially when smaller local models (like Phi-3) fail to adhere strictly to the ReAct output structure, hallucinate tool names, or output incomplete payloads. A standard chatbot is faster and never fails due to syntax parsing issues, although it is prone to hallucinating fictional transaction codes and showtimes.
3.  **Observation**: 
    - Environment feedback (`Observation`) is the bridge that determines the Agent's next actions. For example, if `check_movie_schedule` returns an empty list of showtimes, the Agent reads this from the observation, treats it as a stopping condition, and suggests alternative showtimes or cinemas in the `Final Answer` instead of wasting tokens calling price calculation or booking tools.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: 
  - To scale this cinema ticket booking agent system to production, we should transition synchronous tool calls to an asynchronous task queue (e.g., Celery with Redis/RabbitMQ). This prevents the web server from blocking during high-concurrency external database or payment queries.
- **Safety**: 
  - Implement a supervisor LLM or framework (such as NeMo Guardrails) to audit and validate agent actions before execution. Additionally, a user verification step (like OTP or transaction tokens) must be enforced for actual payment or reservation confirmations to mitigate Prompt Injection attacks.
- **Performance**: 
  - As the number of tools grows (e.g., detail seat selection, concession selection, food ordering, emailing, refunds), we should integrate a Vector Database (like ChromaDB or Milvus) to perform Dynamic Tool Retrieval. This will keep the system prompt clean, reduce token consumption, and avoid exceeding the context window of local models.

---
