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
from src.agent.agent import ReActAgent
from tests.test_case import TEST_CASES, get_minimal_test_cases

def initialize_provider():
    """Initializes the active LLM Provider based on .env config."""
    provider_type = os.getenv("DEFAULT_PROVIDER", "google").lower()
    model_name = os.getenv("DEFAULT_MODEL", "gemini-3-flash-preview")
    
    print(f"[*] Initializing provider: {provider_type.upper()} ({model_name})")
    
    if provider_type == "local":
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Local model GGUF not found at {model_path}")
        from src.core.local_provider import LocalProvider
        return LocalProvider(model_path=model_path, n_ctx=4096, n_threads=4)
    else:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in your .env file!")
        return GeminiProvider(model_name=model_name, api_key=api_key)

def run_evaluation():
    try:
        # 1. Setup provider & agent
        provider = initialize_provider()
        agent = ReActAgent(llm=provider, max_steps=5)
        
        # 2. Select test cases (ask user or run all)
        # For programmatic execution, we run the minimal subset or full set
        # Running all 25 cases via cloud takes ~30s, but offline Phi-3 takes ~6m.
        # We will run all cases if Google Gemini is selected, otherwise minimal subset.
        is_cloud = os.getenv("DEFAULT_PROVIDER", "google").lower() == "google"
        cases_to_run = TEST_CASES if is_cloud else get_minimal_test_cases()
        
        print(f"[*] Selected {len(cases_to_run)} test cases out of {len(TEST_CASES)} to execute.")
        
        results = []
        log_lines = []
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_lines.append("=" * 80)
        log_lines.append(f"CINEMA TICKETING REACT AGENT EVALUATION REPORT - {timestamp}")
        log_lines.append(f"LLM Provider: {provider.model_name}")
        log_lines.append(f"Total test cases selected: {len(cases_to_run)}")
        log_lines.append("=" * 80 + "\n")
        
        start_time_suite = time.time()
        
        for idx, case in enumerate(cases_to_run, 1):
            case_id = case["id"]
            category = case["category"]
            user_input = case["user_input"]
            expected_behavior = case["expected_behavior"]
            
            print(f"\n[{idx}/{len(cases_to_run)}] Running {case_id} ({category})...")
            print(f"Prompt: \"{user_input}\"")
            
            # Spacing delay to avoid hitting the 5 RPM free tier rate limit
            if idx > 1 and is_cloud:
                print("[*] Waiting 12 seconds to be gentle on free-tier rate limits...")
                time.sleep(12)
            
            # Execute agent trace with automatic retry on 429
            max_retries = 3
            retry_attempt = 0
            run_success = False
            
            while retry_attempt < max_retries and not run_success:
                try:
                    res = agent.run_with_trace(user_input)
                    latency = res["metrics"]["latency_ms"]
                    steps_count = res["metrics"]["total_steps"]
                    tokens = res["metrics"]["total_tokens"]
                    final_ans = res["final_answer"]
                    steps_trace = res["steps"]
                    
                    print(f"✔ Completed in {latency/1000:.2f}s | Steps: {steps_count} | Tokens: {tokens}")
                    print(f"Answer: {final_ans[:100]}...")
                    
                    # Append structured log info
                    log_lines.append(f"[{case_id}] Category: {category}")
                    log_lines.append(f"User Prompt: {user_input}")
                    log_lines.append(f"Expected Behavior: {expected_behavior}")
                    log_lines.append(f"Final Answer: {final_ans}")
                    log_lines.append("ReAct Steps Trace:")
                    
                    for step in steps_trace:
                        log_lines.append(f"  Step {step['step']}:")
                        log_lines.append(f"    Thought: {step['thought']}")
                        if step.get("action"):
                            log_lines.append(f"    Action: {step['action']}({json.dumps(step['action_input'], ensure_ascii=False)})")
                        if step.get("observation"):
                            log_lines.append(f"    Observation: {step['observation']}")
                    
                    log_lines.append(f"Metrics: Latency: {latency}ms | Steps: {steps_count} | Tokens: {tokens}")
                    log_lines.append("-" * 80 + "\n")
                    
                    results.append({
                        "id": case_id,
                        "category": category,
                        "prompt": user_input,
                        "answer": final_ans,
                        "steps_count": steps_count,
                        "latency_ms": latency,
                        "tokens": tokens,
                        "status": "success"
                    })
                    run_success = True
                    
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                        retry_attempt += 1
                        wait_time = 25 if retry_attempt == 1 else 35
                        print(f"⚠️ Rate limit hit (429) on attempt {retry_attempt}/{max_retries}. Waiting {wait_time}s before retrying...")
                        time.sleep(wait_time)
                    else:
                        # Non-rate-limit errors are recorded as failures
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
                        run_success = True  # Break retry loop but record as error
            
            if not run_success:
                # Exceeded all retries
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
        
        # 3. Add summary stats to log
        log_lines.append("=" * 80)
        log_lines.append("EVALUATION SUMMARY STATISTICS")
        log_lines.append(f"Total time taken: {total_latency_suite:.2f} seconds")
        log_lines.append(f"Successful cases: {len([r for r in results if r['status'] == 'success'])}/{len(cases_to_run)}")
        
        success_results = [r for r in results if r['status'] == 'success']
        if success_results:
            avg_latency = sum(r['latency_ms'] for r in success_results) / len(success_results)
            avg_steps = sum(r['steps_count'] for r in success_results) / len(success_results)
            avg_tokens = sum(r['tokens'] for r in success_results) / len(success_results)
            log_lines.append(f"Average Latency: {avg_latency:.0f} ms")
            log_lines.append(f"Average Steps: {avg_steps:.1f}")
            log_lines.append(f"Average Tokens: {avg_tokens:.1f}")
        
        log_lines.append("=" * 80)
        
        # 4. Write log file
        log_directory = "logs"
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)
            
        log_filepath = os.path.join(log_directory, "evaluation_run.log")
        with open(log_filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
            
        print(f"\n" + "=" * 60)
        print(f"🎉 Evaluation completed successfully!")
        print(f"📄 Detailed log report saved to: {log_filepath}")
        print(f"=" * 60)
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")

if __name__ == "__main__":
    run_evaluation()
