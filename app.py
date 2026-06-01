import os
import sys
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingTCPServer
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run_eval import init_provider, TOOL_SPECS
from src.agent.agent import ReActAgent
from src.chatbot import BaselineChatbot
from src.tools.movie_tools import MOCK_MOVIES, MOCK_SEATS, MOCK_VOUCHERS, MOCK_CONCESSIONS
from src.telemetry.metrics import tracker

load_dotenv()

# Cache providers and agents by provider name to avoid re-loading models on every request
_PROVIDER_CACHE = {}

def get_agent_for_provider(provider_name: str):
    """
    Lazily initialise and cache a (ReActAgent, BaselineChatbot) pair per provider.
    Supported values: "openai" | "google" | "local"
    Falls back to the value in .env if provider_name is empty / unknown.
    """
    global _PROVIDER_CACHE

    key = provider_name.strip().lower() if provider_name else os.getenv("DEFAULT_PROVIDER", "google").lower()

    if key not in _PROVIDER_CACHE:
        print(f"[server] Initialising provider '{key}' ...")
        # Temporarily override DEFAULT_PROVIDER so init_provider() picks the right one
        original = os.environ.get("DEFAULT_PROVIDER")
        os.environ["DEFAULT_PROVIDER"] = key
        provider = init_provider()
        if original is not None:
            os.environ["DEFAULT_PROVIDER"] = original
        else:
            del os.environ["DEFAULT_PROVIDER"]

        agent   = ReActAgent(llm=provider, tools=TOOL_SPECS, max_steps=6)
        chatbot = BaselineChatbot(llm=provider, tools=TOOL_SPECS)
        # Share a single LongTermMemory so both modes see the same booking history
        chatbot.long_term_memory = agent.long_term_memory

        _PROVIDER_CACHE[key] = (agent, chatbot)
        print(f"[server] Provider loaded: {provider.__class__.__name__} ({provider.model_name})")

    return _PROVIDER_CACHE[key]


# ─── Default provider (pre-warm on startup) ──────────────────────────────────
DEFAULT_PROVIDER_NAME = os.getenv("DEFAULT_PROVIDER", "google").lower()


class MovieBookingHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Silence default terminal logs to keep output clean
        pass

    def send_json(self, data, status=200):
        response_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', len(response_bytes))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        # 1. API: Get Profile (Long-Term Memory) — use default provider
        if self.path == "/api/profile":
            agent, _ = get_agent_for_provider(DEFAULT_PROVIDER_NAME)
            self.send_json(agent.long_term_memory.get_profile())
            return

        # 2. API: Get Database state (Movies, showtimes, seats)
        elif self.path == "/api/database":
            seats_data = {}
            for k, seats in MOCK_SEATS.items():
                seats_data[k] = seats

            self.send_json({
                "movies": MOCK_MOVIES,
                "seats": seats_data,
                "vouchers": MOCK_VOUCHERS,
                "concessions": MOCK_CONCESSIONS
            })
            return

        # 3. Serve Frontend Static files
        else:
            filename = self.path.lstrip('/')
            if not filename or filename == "index.html":
                filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "static", "index.html")
            else:
                filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "static", filename)

            if os.path.exists(filepath) and os.path.isfile(filepath):
                content_type = "text/html"
                if filepath.endswith(".css"):
                    content_type = "text/css"
                elif filepath.endswith(".js"):
                    content_type = "application/javascript"
                elif filepath.endswith(".png"):
                    content_type = "image/png"
                elif filepath.endswith(".json"):
                    content_type = "application/json"

                try:
                    with open(filepath, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", len(content))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    self.send_error(500, f"Error reading file: {e}")
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 - Not Found")

    def do_POST(self):
        content_length = int(self.headers['Content-Length'] or 0)
        post_data = self.rfile.read(content_length)

        try:
            req_data = json.loads(post_data.decode('utf-8'))
        except Exception:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        # 1. API: Reset session memory
        if self.path == "/api/reset":
            # Reset all cached agents
            for key, (agent, chatbot) in _PROVIDER_CACHE.items():
                agent.short_term_memory.clear()
                chatbot.short_term_memory.clear()

            # Optionally reset profile
            reset_all = req_data.get("reset_profile", False)
            if reset_all and _PROVIDER_CACHE:
                first_agent = next(iter(_PROVIDER_CACHE.values()))[0]
                first_agent.long_term_memory.data["past_bookings"] = []
                first_agent.long_term_memory.data["user_name"] = "Khách hàng"
                first_agent.long_term_memory.save()

            self.send_json({"status": "success", "message": "Memory cleared."})
            return

        # 2. API: Chat endpoint
        elif self.path == "/api/chat":
            user_message = req_data.get("message", "")
            use_chatbot  = req_data.get("use_chatbot", False)
            # ── NEW: accept provider choice from UI ─────────────────────────
            provider_name = req_data.get("provider", DEFAULT_PROVIDER_NAME)

            if not user_message:
                self.send_json({"error": "Message is empty"}, 400)
                return

            try:
                agent, chatbot = get_agent_for_provider(provider_name)
            except Exception as e:
                self.send_json({"error": f"Failed to load provider '{provider_name}': {e}"}, 500)
                return

            tracker.reset_session()
            start_time = time.time()

            if use_chatbot:
                response_text = chatbot.run(user_message)
                trace = []
            else:
                response_text = agent.run(user_message)
                trace = agent.current_trace

            latency = int((time.time() - start_time) * 1000)

            # Guard: filter only dict entries (logger may append strings in some setups)
            metrics_dicts = [m for m in tracker.session_metrics if isinstance(m, dict)]

            total_tokens      = sum(m.get("total_tokens", 0)      for m in metrics_dicts)
            prompt_tokens     = sum(m.get("prompt_tokens", 0)     for m in metrics_dicts)
            completion_tokens = sum(m.get("completion_tokens", 0) for m in metrics_dicts)
            cost              = sum(m.get("cost_estimate", 0.0)   for m in metrics_dicts)
            steps             = len(metrics_dicts) if not use_chatbot else 1

            self.send_json({
                "response": response_text,
                "trace":    trace,
                "provider": provider_name,
                "metrics": {
                    "latency_ms":        latency,
                    "total_tokens":      total_tokens,
                    "prompt_tokens":     prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cost":              cost,
                    "steps":             steps
                }
            })
            return

        else:
            self.send_response(404)
            self.end_headers()


class ThreadingHTTPServer(ThreadingTCPServer, HTTPServer):
    pass


def start_server(port=5000):
    print("Starting backend services & loading default LLM provider...")
    get_agent_for_provider(DEFAULT_PROVIDER_NAME)

    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, MovieBookingHandler)
    print(f"Movie Booking Dashboard running on: http://localhost:{port}")
    print(f"Default provider: {DEFAULT_PROVIDER_NAME.upper()} (can be switched from UI)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server...")
        httpd.server_close()


if __name__ == "__main__":
    start_server(5000)
