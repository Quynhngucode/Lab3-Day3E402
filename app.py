import os
import io
import sys
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Force UTF-8 output on Windows for clean log messages
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Load environment variables
load_dotenv()

# Add current workspace to path to allow import of src modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent

# Cache for the heavy local Phi-3 model
LOCAL_PROVIDER_CACHE = None

def get_local_provider():
    global LOCAL_PROVIDER_CACHE
    if LOCAL_PROVIDER_CACHE is None:
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file not found at {model_path}. "
                "Please download Phi-3-mini-4k-instruct-q4.gguf and place it in the models/ folder."
            )
        
        print("[*] Loading local model into cache (this first run will take ~15-30s)...")
        from src.core.local_provider import LocalProvider
        # n_ctx=4096, n_threads=4 as defined in react_agent.py
        LOCAL_PROVIDER_CACHE = LocalProvider(model_path=model_path, n_ctx=4096, n_threads=4)
        print("[OK] Local model loaded and cached successfully.")
    
    return LOCAL_PROVIDER_CACHE


def execute_agent_chat(message: str, provider_type: str, custom_api_key: str = "", mode: str = "agent") -> dict:
    """
    Initializes the requested provider, sets up ReActAgent, and runs the agent loop or chatbot baseline,
    capturing full traces and metrics.
    """
    try:
        if provider_type == "local":
            # Use local Phi-3
            provider = get_local_provider()
        elif provider_type == "openai" or provider_type == "mimo":
            # Use OpenAI/Mimo API
            api_key = custom_api_key.strip() if custom_api_key else os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                return {
                    "final_answer": "Lỗi: Không tìm thấy OpenAI/Mimo API Key. Vui lòng kiểm tra file .env hoặc bảng điều khiển.",
                    "steps": [],
                    "metrics": {"total_steps": 0, "latency_ms": 0, "total_tokens": 0},
                    "success": False
                }
            model_name = os.getenv("DEFAULT_MODEL", "mimo-v2.5-pro")
            from src.core.openai_provider import OpenAIProvider
            provider = OpenAIProvider(model_name=model_name, api_key=api_key)
        else:
            # Use Gemini Cloud API
            # Priority: 1. Custom key entered in UI, 2. Env variable
            api_key = custom_api_key.strip() if custom_api_key else os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                return {
                    "final_answer": "Lỗi: Không tìm thấy Gemini API Key. Vui lòng nhập API Key trong bảng điều khiển ở góc trái UI.",
                    "steps": [],
                    "metrics": {"total_steps": 0, "latency_ms": 0, "total_tokens": 0},
                    "success": False
                }
            
            # Initialize Gemini provider dynamically using the configured model in env
            model_name = os.getenv("DEFAULT_MODEL", "gemini-3-flash-preview")
            provider = GeminiProvider(model_name=model_name, api_key=api_key)
        
        if mode == "chatbot":
            CHATBOT_SYSTEM_PROMPT = """You are a helpful cinema booking customer assistant. 
You do not have access to any external databases or ticket booking tools. 
Answer customer inquiries in friendly Vietnamese to the best of your ability. 
If they ask to book tickets or check showtimes, you must explain that you are a standard chatbot 
and do not have access to tools, so you cannot check schedules, calculate prices, or book tickets."""
            
            start_time = time.time()
            res = provider.generate(message, system_prompt=CHATBOT_SYSTEM_PROMPT)
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "final_answer": res["content"],
                "steps": [],
                "error_metrics": {
                    "JSON_PARSER_ERROR": 0,
                    "HALLUCINATED_TOOL_ERROR": 0,
                    "WRONG_TOOL_ORDER_ERROR": 0,
                    "MISSING_PARAMETERS_ERROR": 0
                },
                "metrics": {
                    "total_steps": 0,
                    "latency_ms": latency_ms,
                    "prompt_tokens": res.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": res.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": res.get("usage", {}).get("total_tokens", 0)
                },
                "success": True
            }

        # Instantiate ReActAgent with the loaded provider
        agent = ReActAgent(llm=provider, max_steps=5)
        
        # Run agent and get trace details
        result = agent.run_with_trace(message)
        result["success"] = True
        return result

    except FileNotFoundError as e:
        print(f"[ERROR] File error: {e}")
        return {
            "final_answer": f"Lỗi: Không tìm thấy tệp mô hình cục bộ. Chi tiết: {str(e)}",
            "steps": [],
            "metrics": {"total_steps": 0, "latency_ms": 0, "total_tokens": 0},
            "success": False
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "final_answer": f"Đã xảy ra lỗi hệ thống: {str(e)}",
            "steps": [],
            "metrics": {"total_steps": 0, "latency_ms": 0, "total_tokens": 0},
            "success": False
        }


class ChatbotHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    Lightweight, high-performance HTTP server handler. Serves frontend files
    from /static directory and handles chat/status APIs.
    """
    
    def do_GET(self):
        # Serve index.html or other static files
        path = self.path
        if path == '/' or path == '/index.html':
            self.serve_static_file('static/index.html', 'text/html')
        elif path == '/index.css':
            self.serve_static_file('static/index.css', 'text/css')
        elif path == '/index.js':
            self.serve_static_file('static/index.js', 'application/javascript')
        elif path == '/api/status':
            self.handle_api_status()
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        if self.path == '/api/chat':
            self.handle_api_chat()
        else:
            self.send_error(404, "Endpoint Not Found")

    def serve_static_file(self, filepath: str, content_type: str):
        """Helper to read and serve static assets."""
        try:
            if not os.path.exists(filepath):
                self.send_error(404, f"File {filepath} not found")
                return

            with open(filepath, 'rb') as f:
                content = f.read()
                
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")

    def handle_api_status(self):
        """Returns the readiness status of the backend providers."""
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        local_model_downloaded = os.path.exists(model_path)
        gemini_key_configured = bool(os.getenv("GEMINI_API_KEY"))
        
        status_data = {
            "local_model": {
                "downloaded": local_model_downloaded,
                "cached": LOCAL_PROVIDER_CACHE is not None,
                "path": model_path
            },
            "gemini_api": {
                "env_configured": gemini_key_configured
            },
            "status": "ready"
        }
        
        response_bytes = json.dumps(status_data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(response_bytes)

    def handle_api_chat(self):
        """Processes user chat request by running the ReAct agent."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
            message = payload.get('message', '')
            provider = payload.get('provider', 'google')  # 'google', 'local', or 'mimo'
            api_key = payload.get('apiKey', '')
            mode = payload.get('mode', 'agent')           # 'agent' or 'chatbot'
            
            print(f"\n[*] Processing message via {provider.upper()} provider in {mode.upper()} mode...")
            response_data = execute_agent_chat(message, provider, api_key, mode)
            
            response_bytes = json.dumps(response_data, ensure_ascii=False).encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_bytes)
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            error_data = {
                "final_answer": f"Lỗi xử lý yêu cầu: {str(e)}",
                "steps": [],
                "metrics": {"total_steps": 0, "latency_ms": 0, "total_tokens": 0},
                "success": False
            }
            self.wfile.write(json.dumps(error_data, ensure_ascii=False).encode('utf-8'))


def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, ChatbotHTTPRequestHandler)
    print(f"\n" + "="*60)
    print(f"🚀 Cinema Ticket Booking ReAct Chatbot Server started at:")
    print(f"👉 http://localhost:{port}")
    print(f"Press Ctrl+C to terminate.")
    print("="*60 + "\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopping...")
        httpd.server_close()
        print("[OK] Server stopped.")


if __name__ == '__main__':
    # Default port is 8000
    run_server(port=8000)
