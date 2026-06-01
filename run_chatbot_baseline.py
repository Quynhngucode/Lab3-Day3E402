import os
import io
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Force UTF-8 output on Windows for clean console rendering of Vietnamese characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Load environment variables
load_dotenv()

# Add current workspace to path to allow importing src modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.gemini_provider import GeminiProvider
from src.core.openai_provider import OpenAIProvider
from tests.test_case import TEST_CASES, get_minimal_test_cases

def initialize_provider():
    """Initializes the active LLM Provider based on .env config."""
    provider_type = os.getenv("DEFAULT_PROVIDER", "google").lower()
    model_name = os.getenv("DEFAULT_MODEL", "gemini-3-flash-preview")
    
    print(f"[*] Initializing Chatbot baseline provider: {provider_type.upper()} ({model_name})")
    
    if provider_type == "local":
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Local model GGUF not found at {model_path}")
        from src.core.local_provider import LocalProvider
        return LocalProvider(model_path=model_path, n_ctx=4096, n_threads=4)
    elif provider_type == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in your .env file!")
        return OpenAIProvider(model_name=model_name, api_key=api_key)
    else:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in your .env file!")
        return GeminiProvider(model_name=model_name, api_key=api_key)

def run_chatbot_baseline():
    try:
        # 1. Setup provider
        provider = initialize_provider()
        
        # 2. Select test cases
        is_cloud = os.getenv("DEFAULT_PROVIDER", "google").lower() == "google"
        cases_to_run = TEST_CASES if is_cloud else get_minimal_test_cases()
        
        print(f"[*] Selected {len(cases_to_run)} test cases for Chatbot Baseline.")
        
        results = []
        log_lines = []
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_lines.append("=" * 80)
        log_lines.append(f"CHATBOT BASELINE EVALUATION REPORT - {timestamp}")
        log_lines.append(f"LLM Provider: {provider.model_name}")
        log_lines.append(f"Total test cases selected: {len(cases_to_run)}")
        log_lines.append("=" * 80 + "\n")
        
        start_time_suite = time.time()
        
        # Baseline Chatbot Prompt (No Tools)
        CHATBOT_SYSTEM_PROMPT = """You are a helpful cinema booking customer assistant. 
You do not have access to any external databases or ticket booking tools. 
Answer customer inquiries in friendly Vietnamese to the best of your ability. 
If they ask to book tickets or check showtimes, you must explain that you are a standard chatbot 
and do not have access to tools, so you cannot check schedules, calculate prices, or book tickets."""

        for idx, case in enumerate(cases_to_run, 1):
            case_id = case["id"]
            category = case["category"]
            user_input = case["user_input"]
            expected_behavior = case["expected_behavior"]
            
            print(f"\n[{idx}/{len(cases_to_run)}] Running Chatbot {case_id} ({category})...")
            print(f"Prompt: \"{user_input}\"")
            
            if idx > 1 and is_cloud:
                print("[*] Waiting 15 seconds to be gentle on free-tier rate limits...")
                time.sleep(15)
            
            max_retries = 3
            retry_attempt = 0
            run_success = False
            
            while retry_attempt < max_retries and not run_success:
                try:
                    start_time = time.time()
                    res = provider.generate(user_input, system_prompt=CHATBOT_SYSTEM_PROMPT)
                    latency = int((time.time() - start_time) * 1000)
                    
                    final_ans = res["content"].strip()
                    usage = res.get("usage", {})
                    tokens = usage.get("total_tokens", 0)
                    
                    print(f"✔ Completed in {latency/1000:.2f}s | Tokens: {tokens}")
                    print(f"Answer: {final_ans[:100]}...")
                    
                    # Chatbots never use tools, so actual_tools is always empty
                    actual_tools = []
                    expected_tools = case.get("expected_tools", [])
                    # Chatbot matches sequence only if no tools are expected (e.g. TC13 or general queries)
                    sequence_matched = (actual_tools == expected_tools)
                    
                    log_lines.append(f"[{case_id}] Category: {category}")
                    log_lines.append(f"User Prompt: {user_input}")
                    log_lines.append(f"Expected Behavior: {expected_behavior}")
                    log_lines.append(f"Final Answer: {final_ans}")
                    log_lines.append(f"Sequence Matched: {sequence_matched} (No Tools Used)")
                    log_lines.append(f"Metrics: Latency: {latency}ms | Tokens: {tokens}")
                    log_lines.append("-" * 80 + "\n")
                    
                    results.append({
                        "id": case_id,
                        "category": category,
                        "prompt": user_input,
                        "answer": final_ans,
                        "latency_ms": latency,
                        "tokens": tokens,
                        "sequence_matched": sequence_matched,
                        "status": "success"
                    })
                    run_success = True
                    
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                        retry_attempt += 1
                        wait_time = 30 if retry_attempt == 1 else 45
                        print(f"⚠️ Rate limit hit (429) on attempt {retry_attempt}/{max_retries}. Waiting {wait_time}s before retrying...")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ Failed: {e}")
                        log_lines.append(f"[{case_id}] Category: {category}")
                        log_lines.append(f"User Prompt: {user_input}")
                        log_lines.append(f"❌ Error during execution: {str(e)}")
                        log_lines.append("-" * 80 + "\n")
                        
                        results.append({
                            "id": case_id,
                            "category": category,
                            "prompt": user_input,
                            "status": "error",
                            "error": str(e)
                        })
                        run_success = True
            
            if not run_success:
                log_lines.append(f"[{case_id}] Category: {category}")
                log_lines.append(f"User Prompt: {user_input}")
                log_lines.append("❌ Failed: Rate limit retries exceeded.")
                log_lines.append("-" * 80 + "\n")
                results.append({
                    "id": case_id,
                    "category": category,
                    "prompt": user_input,
                    "status": "error",
                    "error": "Rate limit retries exceeded"
                })

        total_latency_suite = time.time() - start_time_suite
        success_results = [r for r in results if r['status'] == 'success']
        sequence_matches = [r for r in success_results if r.get('sequence_matched', False)]
        
        # 3. Add summary stats to log
        log_lines.append("=" * 80)
        log_lines.append("CHATBOT BASELINE SUMMARY STATISTICS")
        log_lines.append(f"Total time taken: {total_latency_suite:.2f} seconds")
        log_lines.append(f"Successful runs: {len(success_results)}/{len(cases_to_run)}")
        log_lines.append(f"Strict correctness (Success Rate): {len(sequence_matches)}/{len(cases_to_run)} = {len(sequence_matches)/len(cases_to_run)*100:.1f}%")
        
        if success_results:
            avg_latency = sum(r['latency_ms'] for r in success_results) / len(success_results)
            avg_tokens = sum(r['tokens'] for r in success_results) / len(success_results)
            
            # P50 & P99 latency
            latencies = sorted([r['latency_ms'] for r in success_results])
            n = len(latencies)
            p50 = latencies[int(n * 0.5)] if n > 0 else 0
            p99 = latencies[min(n - 1, max(0, int(n * 0.99)))] if n > 0 else 0
            
            log_lines.append(f"Average Latency: {avg_latency:.0f} ms")
            log_lines.append(f"Latency P50: {p50} ms")
            log_lines.append(f"Latency P99: {p99} ms")
            log_lines.append(f"Average Tokens: {avg_tokens:.1f}")
        
        log_lines.append("=" * 80)
        
        # 4. Write log file
        log_directory = "logs"
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)
            
        log_filepath = os.path.join(log_directory, "chatbot_run.log")
        with open(log_filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
            
        print(f"\n" + "=" * 60)
        print(f"🎉 Chatbot Baseline completed successfully!")
        print(f"📄 Detailed log report saved to: {log_filepath}")
        print(f"=" * 60)
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")

if __name__ == "__main__":
    run_chatbot_baseline()
