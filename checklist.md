# Checklist hoàn thành GROUP REPORT – Movie Ticket Booking Agent

## 0. Thông tin đầu report

- [ ] Điền **Team Name**
- [ ] Điền **Team Members**
- [ ] Điền **Deployment Date**
- [ ] Đổi tên file cuối cùng thành `GROUP_REPORT_[TEAM_NAME].md`

---

## 1. Executive Summary

- [ ] Viết tên hệ thống: **Movie Ticket Booking Agent** hoặc **Cinema Ticket Booking Agent**
- [ ] Mô tả mục tiêu agent: hỗ trợ người dùng đặt vé xem phim
- [ ] Nêu workflow chính:
  - Check lịch chiếu / giá vé cơ bản
  - Tính tổng tiền
  - Xác nhận đặt vé
- [ ] Ghi tổng số test cases
- [ ] Ghi số case thành công
- [ ] Tính **Success Rate**
- [ ] So sánh ngắn với chatbot baseline
- [ ] Nêu key outcome: agent đáng tin cậy hơn chatbot vì dùng tool thay vì tự bịa thông tin

Ví dụ cần điền:

```md
Success Rate: 16/20 test cases = 80%

Key Outcome:
Our agent performs better than the chatbot baseline in multi-step booking tasks because it uses tools to check showtimes, calculate prices, and confirm reservations.
```

---

## 2. System Architecture & Tooling

## 2.1 ReAct Loop Implementation

- [ ] Vẽ sơ đồ ReAct loop:
  - User Query
  - Thought
  - Action
  - Observation
  - Final Answer
- [ ] Mô tả flow chính của agent

Flow đề xuất:

```text
User asks to book movie tickets
        ↓
Agent extracts required information:
movie_name, cinema_name, date, quantity, seat_type, discount_code
        ↓
Tool 1: check_movie_schedule
        ↓
Observation: available showtimes + base ticket price
        ↓
Tool 2: calculate_total_price
        ↓
Observation: total price
        ↓
Tool 3: book_movie_ticket
        ↓
Observation: booking confirmation code + reservation status
        ↓
Final Answer
```

- [ ] Ghi rõ điều kiện dừng:
  - Nếu thiếu thông tin → hỏi lại user
  - Nếu không có lịch chiếu → trả final answer, không tính tiền
  - Nếu chưa có `base_price` → không gọi `calculate_total_price`
  - Nếu chưa có `total_price` → không gọi `book_movie_ticket`
  - Nếu booking thành công → trả mã xác nhận

---

## 2.2 Tool Definitions

## Tool 1: `check_movie_schedule`

- [ ] Ghi description:
  - Tool dùng để lấy danh sách suất chiếu và giá vé cơ bản
- [ ] Ghi input parameters:
  - `movie_name`
  - `cinema_name`
  - `date`
- [ ] Ghi output:
  - danh sách showtimes
  - base price per ticket
- [ ] Viết ví dụ input JSON
- [ ] Viết ví dụ output JSON

Ví dụ:

```json
{
  "movie_name": "Mai",
  "cinema_name": "CGV Vincom Ba Trieu",
  "date": "2026-06-02"
}
```

---

## Tool 2: `calculate_total_price`

- [ ] Ghi description:
  - Tool dùng để tính tổng tiền vé
- [ ] Ghi input parameters:
  - `base_price`
  - `quantity`
  - `seat_type`
  - `discount_code`
- [ ] Ghi output:
  - total price
- [ ] Viết ví dụ input JSON
- [ ] Viết ví dụ output JSON
- [ ] Kiểm tra tool có xử lý:
  - standard seat
  - VIP seat
  - discount code hợp lệ
  - discount code không hợp lệ

Ví dụ:

```json
{
  "base_price": 90000,
  "quantity": 2,
  "seat_type": "VIP",
  "discount_code": "STUDENT10"
}
```

---

## Tool 3: `book_movie_ticket`

- [ ] Ghi description:
  - Tool dùng để xác nhận đặt vé
- [ ] Ghi input parameters:
  - `movie_name`
  - `cinema_name`
  - `showtime`
  - `seat_type`
  - `quantity`
  - `total_price`
- [ ] Ghi output:
  - booking confirmation code
  - reservation status
- [ ] Viết ví dụ input JSON
- [ ] Viết ví dụ output JSON
- [ ] Đảm bảo tool chỉ được gọi sau khi đã có `total_price`

Ví dụ:

```json
{
  "movie_name": "Mai",
  "cinema_name": "CGV Vincom Ba Trieu",
  "showtime": "19:30",
  "seat_type": "VIP",
  "quantity": 2,
  "total_price": 198000
}
```

---

## 2.3 LLM Providers Used

- [ ] Ghi model chính nhóm dùng
- [ ] Ghi model backup nếu có
- [ ] Ghi lý do chọn model
- [ ] Ghi giới hạn của model nếu có:
  - latency
  - quota
  - function calling error
  - JSON format error

Ví dụ:

```md
Primary: Gemini 2.0 Flash  
Secondary: None  
Reason: The model supports function calling and is suitable for a lightweight ReAct agent.
```

---

## 3. Telemetry & Performance Dashboard

## 3.1 Metrics cần đo

- [ ] Total test cases
- [ ] Successful cases
- [ ] Failed cases
- [ ] Success rate
- [ ] Average latency
- [ ] Max latency hoặc P99 latency
- [ ] Average token count
- [ ] Average loop count
- [ ] Total tool calls
- [ ] Tool call success rate
- [ ] JSON parser errors
- [ ] Hallucinated tool errors
- [ ] Timeout errors
- [ ] Wrong tool order errors

Bảng mẫu:

| Metric | Value |
|---|---:|
| Total Test Cases | 20 |
| Success Rate | 16/20 = 80% |
| Average Latency | 1.5s |
| Max Latency | 4.2s |
| Average Loop Count | 3.1 |
| Average Tokens per Task | 350 |
| Tool Call Success Rate | 90% |
| JSON Parser Errors | 1 |
| Timeout Errors | 0 |
| Hallucinated Tool Errors | 1 |

---

## 3.2 Logs cần lưu

- [ ] Lưu input user
- [ ] Lưu từng Thought
- [ ] Lưu từng Action
- [ ] Lưu từng Observation
- [ ] Lưu Final Answer
- [ ] Lưu latency
- [ ] Lưu token count
- [ ] Lưu loop count
- [ ] Lưu error type nếu có

---

## 4. Root Cause Analysis – Failure Traces

Chọn ít nhất 2–3 case lỗi để phân tích.

## Case 1: Thiếu thông tin nhưng agent vẫn gọi tool

- [ ] Ghi input user
- [ ] Ghi tool call sai
- [ ] Ghi observation hoặc lỗi
- [ ] Ghi root cause
- [ ] Ghi cách sửa

Ví dụ:

```md
Input:
"Tôi muốn đặt vé xem phim."

Expected:
Agent should ask for missing information such as movie name, cinema name, date, and quantity.

Failure:
Agent hallucinated missing parameters and called check_movie_schedule.

Root Cause:
The prompt did not clearly instruct the agent to ask clarification questions when required parameters are missing.

Fix:
Add a rule: If required booking information is missing, ask the user before calling any tool.
```

---

## Case 2: Không có lịch chiếu nhưng agent vẫn tính tiền

- [ ] Ghi input user
- [ ] Ghi output từ `check_movie_schedule`
- [ ] Ghi tool call sai tiếp theo
- [ ] Ghi root cause
- [ ] Ghi cách sửa

Ví dụ:

```md
Input:
"Đặt 2 vé phim Doraemon ở CGV Hà Nội ngày 2026-06-05."

Observation:
No showtimes found.

Failure:
Agent still called calculate_total_price.

Root Cause:
The agent did not treat an empty schedule result as a stopping condition.

Fix:
If check_movie_schedule returns no showtimes, stop and ask the user to choose another movie, cinema, or date.
```

---

## Case 3: Gọi `book_movie_ticket` trước khi tính tiền

- [ ] Ghi input user
- [ ] Ghi thứ tự tool call sai
- [ ] Ghi root cause
- [ ] Ghi cách sửa

Ví dụ:

```md
Failure:
Agent called book_movie_ticket before calculate_total_price.

Root Cause:
The system prompt did not strictly define the required tool order.

Fix:
Add a strict workflow order:
check_movie_schedule → calculate_total_price → book_movie_ticket.
```

---

## 5. Ablation Studies & Experiments

## Experiment 1: Prompt v1 vs Prompt v2

- [ ] Viết prompt v1
- [ ] Chạy toàn bộ test suite với prompt v1
- [ ] Ghi success rate của prompt v1
- [ ] Ghi lỗi chính của prompt v1
- [ ] Sửa thành prompt v2
- [ ] Chạy lại cùng test suite
- [ ] Ghi success rate của prompt v2
- [ ] So sánh kết quả

Bảng mẫu:

| Version | Success Rate | Main Errors |
|---|---:|---|
| Prompt v1 | 65% | Missing parameters, wrong tool order |
| Prompt v2 | 85% | Some unclear user inputs still failed |

Prompt v2 nên có rule:

```text
Always call tools in this order:
1. check_movie_schedule
2. calculate_total_price
3. book_movie_ticket

Do not calculate price if no showtime is available.
Do not book tickets before calculating total price.
If required information is missing, ask the user a clarification question.
```

---

## Experiment 2: Chatbot vs Agent

- [ ] Chạy cùng test cases trên chatbot baseline
- [ ] Chạy cùng test cases trên agent
- [ ] So sánh kết quả
- [ ] Chỉ ra case agent thắng
- [ ] Chỉ ra case chatbot và agent hòa

Bảng mẫu:

| Case | Chatbot Result | Agent Result | Winner |
|---|---|---|---|
| Ask available showtimes | May hallucinate | Uses check_movie_schedule | Agent |
| Calculate VIP ticket price | May estimate price | Uses calculate_total_price | Agent |
| Full booking request | Cannot really book | Uses all 3 tools | Agent |
| General question | Correct | Correct | Draw |

---

## 6. Production Readiness Review

## 6.1 Security

- [ ] Validate input trước khi gọi tool
- [ ] Không để prompt injection thay đổi workflow
- [ ] Không log thông tin cá nhân nhạy cảm
- [ ] Không báo booking thành công nếu tool không trả success
- [ ] Không tự bịa booking code

---

## 6.2 Guardrails

- [ ] Có `max_steps` để tránh infinite loop
- [ ] Có timeout cho mỗi tool
- [ ] Có retry hoặc fallback khi tool lỗi
- [ ] Có rule hỏi lại khi thiếu thông tin
- [ ] Có rule dừng nếu không có lịch chiếu
- [ ] Có rule không tính tiền nếu chưa có `base_price`
- [ ] Có rule không đặt vé nếu chưa có `total_price`

---

## 6.3 Reliability

- [ ] Nếu tool trả empty result, agent phải báo rõ
- [ ] Nếu discount code không hợp lệ, agent phải xử lý hợp lý
- [ ] Nếu booking fail, agent phải báo thất bại
- [ ] Nếu user nhập ngày sai format, agent phải hỏi lại
- [ ] Nếu user nhập số lượng vé không hợp lệ, agent phải hỏi lại

---

## 6.4 Scaling

- [ ] Có thể thay mock data bằng database thật
- [ ] Có thể thêm payment tool
- [ ] Có thể thêm seat selection tool
- [ ] Có thể thêm email/SMS confirmation tool
- [ ] Có thể thêm cancellation/refund tool
- [ ] Có thể chuyển sang LangGraph nếu workflow phức tạp hơn

---

## 7. Test Suite cần chuẩn bị

Chuẩn bị khoảng 15–20 test cases.

| Type | Example Input | Expected Behavior |
|---|---|---|
| Successful booking | "Đặt 2 vé phim Mai ở CGV lúc 19:30" | Check schedule → calculate price → book ticket |
| Missing movie name | "Tôi muốn đặt 2 vé xem phim" | Ask clarification |
| Missing date | "Đặt vé phim Mai ở CGV" | Ask clarification |
| No showtime | "Đặt phim không có lịch chiếu" | Stop and inform user |
| VIP seat | "Đặt 2 vé VIP phim Mai" | Apply seat multiplier |
| Discount code | "Đặt 2 vé dùng mã STUDENT10" | Apply discount |
| Invalid discount | "Dùng mã ABCXYZ" | Handle invalid code |
| Large quantity | "Đặt 100 vé" | Check availability / reject |
| Invalid date | "Đặt vé ngày 40/13" | Ask user to correct date |
| Full booking | "Đặt 2 vé VIP phim Mai ở CGV ngày mai lúc 19:30" | Use all 3 tools |

---

## 8. Thứ tự làm report đề xuất

1. [ ] Hoàn thiện TOOL.md với input/output JSON rõ ràng
2. [ ] Viết system prompt có strict tool order
3. [ ] Tạo mock data phim, rạp, lịch chiếu, giá vé
4. [ ] Tạo 15–20 test cases
5. [ ] Chạy chatbot baseline
6. [ ] Chạy agent v1
7. [ ] Thu logs: latency, token, loop count, tool calls, errors
8. [ ] Phân tích 2–3 failure traces
9. [ ] Sửa prompt/tool description thành agent v2
10. [ ] Chạy lại test suite
11. [ ] So sánh v1 vs v2
12. [ ] So sánh chatbot vs agent
13. [ ] Viết Production Readiness Review
14. [ ] Hoàn thiện report theo template
15. [ ] Đổi tên file thành `GROUP_REPORT_[TEAM_NAME].md`

---

## 9. Điều quan trọng cần chứng minh trong report

- [ ] Agent biết dùng tool thay vì tự bịa thông tin
- [ ] Agent gọi tool đúng thứ tự
- [ ] Agent biết dừng khi không có lịch chiếu
- [ ] Agent biết hỏi lại khi thiếu thông tin
- [ ] Agent có logs để phân tích lỗi
- [ ] Agent v2 tốt hơn agent v1 sau khi sửa prompt/tool description
- [ ] Agent tốt hơn chatbot baseline ở các task multi-step
