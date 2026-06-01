import logging
import json
import os
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """
    Ensures that every log line written to file is a valid JSON object.
    """
    def format(self, record):
        try:
            # If the log message is already a valid JSON string, use it
            json.loads(record.msg)
            return record.msg
        except Exception:
            # Otherwise, wrap it in a structured JSON schema
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": record.levelname,
                "data": {
                    "message": record.getMessage()
                }
            }
            if record.exc_info:
                payload["data"]["exception"] = self.formatException(record.exc_info)
            return json.dumps(payload, ensure_ascii=False)

class TerminalFormatter(logging.Formatter):
    """
    Colorizes and formats structured event logs on the terminal.
    Unstructured/raw logs are printed as-is.
    """
    def format(self, record):
        msg = record.getMessage()
        try:
            payload = json.loads(msg)
            event = payload.get("event")
            data = payload.get("data", {})
            
            # Format according to event type using ANSI codes
            if event == "AGENT_START":
                model_info = f"\033[1;36m{data.get('model')}\033[0m"
                user_msg = f"\"\033[33m{data.get('input')}\033[0m\""
                return f"\n\033[1;35m🚀 [AGENT START]\033[0m Model: {model_info} | Input: {user_msg}"
                
            elif event == "AGENT_THOUGHT":
                step_prefix = f"\033[1;30m[Step {data.get('step')}]\033[0m"
                thought_text = f"\033[1;34m🤔 [THOUGHT]\033[0m {data.get('thought')}"
                return f"{step_prefix} {thought_text}"
                
            elif event == "TOOL_CALL":
                args_str = json.dumps(data.get("args"), ensure_ascii=False)
                return f"  \033[1;36m⚙️ [ACTION]\033[0m Calling tool \033[1;32m{data.get('tool')}\033[0m with arguments: \033[36m{args_str}\033[0m"
                
            elif event == "TOOL_RESPONSE":
                res_str = str(data.get("result"))
                if len(res_str) > 400:
                    res_str = res_str[:400] + "... (truncated)"
                return f"  \033[1;33m👁️ [OBSERVATION]\033[0m Result: \033[32m{res_str}\033[0m"
                
            elif event == "AGENT_ERROR":
                err_type = data.get("error_type", "ERROR")
                err_msg = data.get("message", "")
                return f"  \033[1;31m⚠️ [{err_type}]\033[0m \033[31m{err_msg}\033[0m"
                
            elif event == "AGENT_END":
                return f"\033[1;32m🎯 [AGENT END]\033[0m Steps: \033[1;36m{data.get('steps')}\033[0m\n  Final Answer: \033[1;37m{data.get('final_answer')}\033[0m\n"
                
            elif event == "LLM_METRIC":
                cost = data.get("cost_estimate", 0.0)
                total_t = data.get("total_tokens", 0)
                prompt_t = data.get("prompt_tokens", 0)
                comp_t = data.get("completion_tokens", 0)
                ratio = (comp_t / prompt_t) if prompt_t > 0 else 0.0
                latency = data.get("latency_ms", 0)
                return (f"  \033[1;30m📊 [METRIC]\033[0m "
                        f"Tokens: \033[36m{total_t}\033[0m (Prompt: {prompt_t}, Completion: {comp_t}, Ratio: {ratio:.2f}) | "
                        f"Latency: \033[36m{latency}ms\033[0m | "
                        f"Cost: \033[1;32m${cost:.5f}\033[0m")
                
            elif event == "CHATBOT_START":
                model_info = f"\033[1;36m{data.get('model')}\033[0m"
                user_msg = f"\"\033[33m{data.get('input')}\033[0m\""
                return f"\n\033[1;35m💬 [CHATBOT START]\033[0m Model: {model_info} | Input: {user_msg}"
                
            elif event == "CHATBOT_END":
                return f"\033[1;32m💬 [CHATBOT END]\033[0m Response: \033[1;37m{data.get('response')}\033[0m\n"
                
            return f"\033[1;30m[{event}]\033[0m {json.dumps(data, ensure_ascii=False)}"
            
        except Exception:
            if record.levelname == "ERROR":
                return f"\033[1;31m⚠️ [ERROR]\033[0m {msg}"
            elif record.levelname == "WARNING":
                return f"\033[1;33m⚠️ [WARNING]\033[0m {msg}"
            return msg

class IndustryLogger:
    """
    Structured logger that simulates industry practices.
    Logs to both console and a file in JSON format.
    """
    def __init__(self, name: str = "AI-Lab-Agent", log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # File Handler (JSON)
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(JSONFormatter())
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(TerminalFormatter())
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs an event with a timestamp and type."""
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "data": data
        }
        self.logger.info(json.dumps(payload))

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str, exc_info=True):
        self.logger.error(msg, exc_info=exc_info)

# Global logger instance
logger = IndustryLogger()
