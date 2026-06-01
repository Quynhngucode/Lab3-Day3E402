# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Bùi Tuấn Minh
- **Student ID**: 2A202600728
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

Trong buổi thực hành Lab 3, tôi đã đóng góp các cải tiến kỹ thuật quan trọng nhằm nâng cao tính tin cậy của ReAct Agent và giải quyết các lỗi tích hợp nghiêm trọng trên hệ thống CineBot:

- **Modules Implementated**: 
  - [static/index.html] (Khắc phục lỗi tự động điền đè API Key)
  - [react_agent.py] (Nâng cấp hệ thống System Prompt lên phiên bản v2)
  - [src/agent/agent.py] (Đảm bảo đồng bộ hóa logic ReAct Agent)

- **Code Highlights**:
  1. *Ngăn ngừa Browser Autofill ghi đè API Key trong `static/index.html`*:
     ```html
     <input type="password" id="mimoApiKeyInput" placeholder="Nhập MiMo API Key..." autocomplete="new-password" />
     <input type="password" id="apiKeyInput" placeholder="Nhập Gemini API Key..." autocomplete="new-password" />
     ```
  2. *Nâng cấp Prompt v2 cho ReAct Loop trong `react_agent.py`*:
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
  - Khai báo `autocomplete="new-password"` giúp ngăn các trình quản lý mật khẩu tự động chèn thông tin nhạy cảm vào ô nhập khóa API, tránh việc gửi khóa rác lên backend làm gián đoạn vòng lặp ReAct của Agent.
  - Việc cấu trúc lại prompt v2 tuân thủ nghiêm ngặt mô hình Thought-Action-Observation giúp mô hình ngôn ngữ (cả cloud như MiMo/Gemini lẫn local Phi-3) hiểu rõ các ràng buộc nghiệp vụ, gọi đúng tool theo đúng thứ tự logic (không được book vé trước khi tính toán tổng tiền, và không được tính tiền nếu không có lịch chiếu).

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: 
  - Hệ thống ReAct Agent bị lỗi khi chuyển sang nhà cung cấp mô hình `MiMo-v2.5-Pro` với thông báo lỗi: `Error code: 401 - {'error': {'message': 'Invalid API Key', 'param': 'Please provide valid API Key', 'code': '401', 'type': 'invalid_key'}}`. Mặc dù file `.env` đã được điền API Key hoàn chỉnh.

- **Log Source**: 
  - Log từ terminal chạy backend `app.py`:
    ```text
    [*] Processing message via MIMO provider in AGENT mode...
    [ERROR] OpenAI API call failed: Error code: 401 - {'error': {'message': 'Invalid API Key', 'param': 'Please provide valid API Key', 'code': '401', 'type': 'invalid_key'}}
    ```

- **Diagnosis**: 
  - Qua kiểm tra kỹ thuật (sử dụng curl/python kiểm tra độc lập API Key trong `.env` trực tiếp tới endpoint `https://token-plan-sgp.xiaomimimo.com/v1`), kết quả trả về `200 OK` chứng minh API Key của hệ thống cấu hình là hoàn toàn chính xác.
  - Vấn đề nằm ở cơ chế truyền khóa: Giao diện sidebar của CineBot sử dụng input ẩn mật khẩu (`type="password"`) cho ô nhập key. Trình duyệt (Chrome/Edge) tự hiểu lầm đây là form đăng nhập nên tự động điền thông tin tài khoản/mật khẩu đang lưu vào ô này.
  - Đoạn mã trong `static/index.js` lấy giá trị bị tự điền này gửi lên backend qua biến `apiKey`. Backend ưu tiên lấy `apiKey` tùy chỉnh từ giao diện trước rồi mới fallback về `.env`:
    ```python
    api_key = custom_api_key.strip() if custom_api_key else os.getenv("OPENAI_API_KEY", "")
    ```
    Hệ quả là khóa rác bị tự điền từ trình duyệt đã ghi đè lên khóa hợp lệ trong `.env`, dẫn tới lỗi xác thực 401 từ máy chủ.

- **Solution**: 
  - Sửa đổi giao diện `static/index.html` để thêm thuộc tính `autocomplete="new-password"` vào cả hai trường nhập API Key để vô hiệu hóa hoàn toàn cơ chế tự điền của trình duyệt. 
  - Hướng dẫn người dùng xóa sạch trường nhập khóa trên UI để backend tự động fallback một cách an toàn về biến môi trường trong file `.env`. Sau khi áp dụng giải pháp, Agent hoạt động hoàn hảo và không bao giờ gặp lại lỗi 401.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: 
    - Khối `Thought` đóng vai trò là "bảng nháp tư duy" (Chain of Thought) cực kỳ hiệu quả của Agent. So với Chatbot thông thường (chỉ đoán từ tiếp theo trực tiếp dựa trên prompt đầu vào), `Thought` giúp ReAct Agent định hình các bước cần làm một cách logic: phân tích xem yêu cầu của người dùng thiếu những thông tin gì, có cần gọi công cụ nào hỗ trợ hay không. Khả năng "nghĩ trước khi làm" này giúp Agent vượt trội khi thực hiện các tác vụ phức tạp gồm nhiều bước (Multi-step tasks).
2.  **Reliability**: 
    - ReAct Agent có thể hoạt động tệ hơn Chatbot khi gặp các lỗi về định dạng đầu ra (JSON Parser Error), ví dụ khi mô hình nhỏ (Phi-3) không tuân thủ cấu trúc ReAct thô, sinh ra mã XML bị lỗi cú pháp hoặc gọi các công cụ không có thực (Hallucinated Tool). Chatbot thông thường tuy có thể đưa ra thông tin bịa đặt (Hallucination) nhưng luôn có tốc độ phản hồi nhanh hơn và không bao giờ bị đứng (crash) do lỗi phân tích cú pháp code.
3.  **Observation**: 
    - Phản hồi từ môi trường (`Observation`) là cầu nối quyết định hành vi tiếp theo của Agent. Ví dụ, nếu kết quả của `check_movie_schedule` trả về danh sách lịch chiếu trống, Agent sẽ đọc `Observation` đó và tự động dừng tiến trình (Stopping Condition), đưa ra câu trả lời tư vấn đổi ngày chiếu hoặc rạp cho khách hàng thay vì tiếp tục gọi tool `calculate_total_price` hay `book_movie_ticket` một cách vô nghĩa.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**: 
  - Để đưa hệ thống AI Agent này lên quy mô sản xuất thực tế (Production), cần chuyển các lời gọi công cụ đồng bộ (Synchronous Tool Calls) sang mô hình hàng đợi bất đồng bộ (Asynchronous Task Queue) sử dụng Celery kết hợp Redis/RabbitMQ. Điều này giúp hệ thống không bị nghẽn (non-blocking) khi xử lý hàng ngàn yêu cầu cùng lúc.
- **Safety**: 
  - Thiết lập một mô hình ngôn ngữ giám sát (Supervisor/Guardrail LLM) hoặc sử dụng thư viện chuyên dụng như NeMo Guardrails để kiểm duyệt các hành động của Agent trước khi thực thi. Đồng thời áp dụng cơ chế xác thực OTP/Token của người dùng khi gọi công cụ thanh toán hoặc đặt chỗ thực tế nhằm ngăn chặn tấn công Prompt Injection (ví dụ khách hàng lừa Agent bỏ qua bước thanh toán).
- **Performance**: 
  - Khi số lượng công cụ trong tương lai tăng lên hàng chục hoặc hàng trăm (ví dụ: công cụ chọn ghế chi tiết, công cụ chọn đồ ăn đi kèm, gửi email, hoàn tiền...), cần sử dụng một Vector Database (như ChromaDB/Milvus) để thực hiện kỹ thuật truy xuất công cụ động (Dynamic Tool Retrieval) - chỉ đưa các công cụ thực sự liên quan vào system prompt để tối ưu hóa context window và giảm chi phí token.

---
