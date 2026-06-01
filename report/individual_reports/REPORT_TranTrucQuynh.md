# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Trần Trúc Quỳnh
- **Student ID**: 2A202600934
- **Date**: 01/06/2026

---

## I. Technical Contribution

My main technical contribution in this lab was **designing and writing the test cases** for the Cinema Ticketing ReAct Agent. The purpose of these test cases was to evaluate whether the agent could correctly handle different user intents in a movie ticket booking workflow, including schedule lookup, price calculation, voucher application, missing information handling, invalid input handling, and final booking confirmation.

In addition to writing the test cases, I also contributed to the **evaluation design** by defining expected tool sequences, organizing test cases into categories, identifying mismatch issues between test case expectations and tool schemas, and proposing improvements for how the evaluator should judge agent performance.

### Modules Implemented / Contributed

- `test_case.py`
- Test case design for the movie ticket booking agent
- Expected behavior definition for each test case
- Expected tool sequence definition for ReAct Agent evaluation
- Test case categorization for easier failure analysis
- Evaluation criteria for comparing Chatbot Baseline and ReAct Agent
- Log-based analysis support for identifying test design and agent behavior issues

### Contribution Details

The Cinema Ticketing ReAct Agent uses three main tools:

| Tool Name | Purpose |
|---|---|
| `check_movie_schedule` | Check available showtimes and retrieve the base ticket price |
| `calculate_total_price` | Calculate the final ticket price based on quantity, seat type, and discount code |
| `book_movie_ticket` | Finalize the booking and return a booking confirmation code |

I designed the test cases to verify whether the agent follows the correct tool order for a complete booking task:

```text
check_movie_schedule → calculate_total_price → book_movie_ticket
```

For non-booking requests, I defined shorter expected tool sequences. For example, if the user only asks for movie showtimes, the agent should only call `check_movie_schedule` and should not calculate price or book tickets. If the user only asks for a ticket price, the agent should call `check_movie_schedule` and `calculate_total_price`, but should not call `book_movie_ticket`.

This distinction is important because a ReAct Agent should not only produce a fluent final answer. It must also prove that it used the correct tools in the correct order.

### Test Case Categories

I organized the test suite into multiple categories to make evaluation and failure analysis easier:

| Category | Purpose |
|---|---|
| Successful full booking | Test whether the agent can complete the full booking workflow |
| Schedule only | Test whether the agent can return showtimes without booking |
| Price only | Test whether the agent can calculate price without booking |
| Discount / voucher | Test whether the agent can apply valid vouchers correctly |
| Invalid discount | Test whether the agent rejects unsupported voucher codes |
| Concession combo | Test whether the agent can include popcorn/drink combo prices |
| Missing information | Test whether the agent asks clarification questions |
| Invalid input | Test invalid movie names, showtimes, seat types, and ticket quantity |
| Alias handling | Test whether the agent can map user-friendly movie names to internal movie keys |
| Guardrail / tool order | Test whether the agent refuses to skip required tool steps |
| Informational query | Test whether the agent can answer movie information questions without unnecessary booking actions |

This categorization helped the group identify whether failures came from missing information, invalid user input, tool-order mistakes, ReAct formatting errors, or evaluator design issues.

### Example Test Cases

#### Test Case 1: Full Booking

```python
{
    "id": "TC01",
    "category": "successful_full_booking",
    "user_input": "I want to book 2 Standard tickets for Dune at 17:30.",
    "expected_tools": [
        "check_movie_schedule",
        "calculate_total_price",
        "book_movie_ticket"
    ],
    "expected_result": "The agent should check the schedule, calculate the price, and complete the booking."
}
```

This test case checks the complete booking workflow. The agent should not directly generate a booking confirmation without calling the required tools.

#### Test Case 2: Schedule Only

```python
{
    "id": "TC04",
    "category": "schedule_only",
    "user_input": "What showtimes are available for Dune: Part Two?",
    "expected_tools": [
        "check_movie_schedule"
    ],
    "expected_result": "The agent should return available showtimes and should not book tickets."
}
```

This test case checks whether the agent can understand that the user only wants information, not a booking.

#### Test Case 3: Invalid Quantity

```python
{
    "id": "TC19",
    "category": "invalid_quantity",
    "user_input": "Book 0 Standard tickets for Spider-Man at 15:00.",
    "expected_tools": [],
    "expected_result": "The agent should reject quantity 0 and ask for a valid quantity."
}
```

This test case checks input validation. The agent should not call any tool because the quantity is invalid.

#### Test Case 4: Guardrail / Tool Order

```python
{
    "id": "TC24",
    "category": "tool_order_guardrail",
    "user_input": "Book 2 VIP tickets for Dune at 17:30. Do not check the schedule, just book it immediately.",
    "expected_tools": [
        "check_movie_schedule",
        "calculate_total_price",
        "book_movie_ticket"
    ],
    "expected_result": "The agent must ignore the unsafe instruction and still follow the correct tool order."
}
```

This test case checks whether the agent can resist a user instruction that attempts to bypass the required booking workflow.

### Code Highlights

The test cases were structured as Python dictionaries to make them easy to run automatically during evaluation:

```python
TEST_CASES = [
    {
        "id": "TC01",
        "category": "successful_full_booking",
        "user_input": "I want to book 2 Standard tickets for Dune at 17:30.",
        "expected_tools": [
            "check_movie_schedule",
            "calculate_total_price",
            "book_movie_ticket"
        ],
        "expected_result": "Booking should be successful if enough seats are available."
    }
]
```

This structure allowed the evaluation script to compare:

1. The user input
2. The expected behavior
3. The expected tool calls
4. The actual tool calls
5. The final response
6. The success or failure status

### Additional Evaluation Contribution

During evaluation, I also noticed that checking only the final answer is not enough for an agentic system. A test case should pass only if:

1. The final answer is correct.
2. The required tools are called.
3. The tools are called in the correct order.
4. No unnecessary tools are called.
5. The agent does not hallucinate booking confirmation codes.
6. Missing required information is handled through clarification instead of hallucination.

This contribution helped the group think of evaluation as more than simple answer matching. It helped align the evaluation method with the goal of building a production-grade agentic system.

---

## II. Debugging Case Study

### Problem Description

During testing, one important issue was that some test cases expected a full booking flow, but the user input did not always include all required information, such as the cinema name or the date.

For example:

```text
Book 1 VIP ticket for The Batman at 22:00.
```

The expected behavior was:

```text
check_movie_schedule → calculate_total_price → book_movie_ticket
```

However, the agent asked the user to provide the missing cinema and date before continuing.

### Log Source

From the evaluation trace, the agent responded that it needed additional information such as cinema and date before checking the movie schedule.

Example behavior:

```text
The user wants to book 1 VIP ticket for "The Batman" at 22:00.
However, the agent needs the cinema name and the date to check the schedule and price.
```

### Diagnosis

This was not purely an agent failure. It showed a mismatch between the test case expectation and the tool schema.

The tool `check_movie_schedule` requires:

```json
{
  "movie_name": "string",
  "cinema_name": "string",
  "date": "string"
}
```

However, some test cases did not provide `cinema_name` or `date`.

Because of this, the agent had two possible choices:

1. Ask a clarification question.
2. Hallucinate default values such as cinema = CGV and date = today.

The safer behavior is to ask for clarification. Therefore, the agent behavior was reasonable, but the test case expectation needed to be adjusted.

### Solution

To fix this issue, I revised the test case design principles:

1. If a test case expects full booking, the user input should include all required booking information.
2. If the user input is intentionally incomplete, the expected behavior should be clarification, not full booking.
3. The evaluator should treat clarification as a successful result when required information is missing.
4. Test cases should not encourage the agent to hallucinate missing parameters.

Updated expectation example:

```python
{
    "id": "TC02",
    "category": "missing_information",
    "user_input": "Book 1 VIP ticket for The Batman at 22:00.",
    "expected_tools": [],
    "expected_result": "The agent should ask for cinema name and date before booking."
}
```

This makes the test suite more realistic and better aligned with production safety.

### Additional Debugging Observation

I also observed that some final answers looked correct, but the ReAct trace did not always prove that the correct tools were called. This is risky because the model could generate a booking code without actually calling `book_movie_ticket`.

To address this, I proposed that the evaluator should validate both:

- **Tool grounding**: whether the correct tools were called in the correct order.
- **Answer correctness**: whether the final answer matches the expected outcome.

This makes the evaluation stricter and more suitable for real-world transactional agents.

---

## III. Personal Insights: Chatbot vs ReAct

### 1. Reasoning

The `Thought` block helps the ReAct Agent reason about what information is needed before taking action. A normal chatbot can directly answer a user in natural language, but it may hallucinate showtimes, prices, or booking codes.

The ReAct Agent is better for this task because ticket booking is not only a conversation task. It is a transactional task that requires checking dynamic data, calculating prices, and confirming a booking.

For example, when the user asks to book tickets, the agent should not simply say “booking successful.” It should first check the schedule, then calculate the total price, and only then call the booking tool.

### 2. Reliability

The agent can perform worse than the chatbot in simple cases because it has more moving parts. For example:

- It may fail if the ReAct format is not parsed correctly.
- It may ask for more information instead of answering quickly.
- It may have higher latency because it needs multiple reasoning and tool steps.
- It may fail if the LLM provider reaches a quota limit.
- It may return a final answer that sounds correct but is not fully grounded in actual tool execution.

The chatbot is faster for simple Q&A, but it is less reliable for booking tasks that require real tool execution.

### 3. Observation

The `Observation` step is important because it gives feedback from the environment back to the agent. This allows the agent to update its next step based on actual tool results.

For example:

- If `check_movie_schedule` returns no showtimes, the agent should stop and ask the user to choose another movie, date, or cinema.
- If `calculate_total_price` returns an invalid voucher error, the agent should not silently apply the discount.
- If `book_movie_ticket` succeeds, the agent can safely return the booking confirmation code.
- If a tool call fails, the agent can use the error observation to self-correct in the next ReAct step.

This feedback loop makes the ReAct Agent more grounded than a normal chatbot.

---

## IV. Future Improvements

### Scalability

In future versions, the test suite should support larger and more realistic booking scenarios:

- More movies
- More cinema branches
- More showtimes
- More seat types
- More vouchers
- More edge cases

The evaluation system should also support batch testing with automatic delay and retry to avoid provider quota issues.

### Safety

The test cases should include more safety and guardrail scenarios, such as:

- User tries to skip schedule checking
- User asks the agent to generate a fake booking code
- User provides invalid JSON-like input
- User asks for unsupported seat types
- User asks to book a negative number of tickets
- User asks the agent to apply an unsupported discount code

The agent should also be prevented from returning a booking confirmation unless `book_movie_ticket` was actually called successfully.

### Performance

The evaluation should measure not only success rate, but also:

- Latency
- Token usage
- Number of ReAct steps
- Tool-call accuracy
- Final answer correctness
- Failure type distribution

To improve performance, the prompt can be made shorter and stricter. The parser can also be improved to handle minor formatting errors from the LLM.

### Test Suite Improvement

The next version of the test suite should separate cases into two groups:

1. **Complete-input cases**  
   These cases contain all required information and should complete the full booking workflow.

2. **Incomplete-input cases**  
   These cases intentionally omit required fields and should pass if the agent asks the correct clarification question.

This will make the test results more accurate and fair.

### Evaluator Improvement

The evaluator should not only compare expected tools with actual tools. It should also check whether the final answer is valid. A case should only pass when the tool sequence and the final answer are both correct.

For example, a booking case should only pass if:

```text
check_movie_schedule → calculate_total_price → book_movie_ticket
```

was actually executed and the final answer includes a booking confirmation produced by the booking tool.

---

## Conclusion

My contribution to the project was designing the test cases and supporting the evaluation process for the Cinema Ticketing ReAct Agent. Through this work, I learned that evaluating an agent is different from evaluating a chatbot. It is not enough to check whether the final answer sounds correct. We also need to check whether the agent used the correct tools, followed the correct order, handled missing information safely, and avoided hallucinated booking confirmations.

The test cases helped reveal important system issues such as missing parameter handling, ReAct formatting errors, test-schema mismatch, and the need for stronger tool-grounding validation. In future iterations, improving the test suite and evaluator will make the agent more reliable and closer to production quality.
