import os
import sys
import json
import time
import argparse
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run_eval import init_provider, TOOL_SPECS
from src.agent.agent import ReActAgent
from src.telemetry.metrics import tracker
from src.telemetry.logger import logger
from tests.test_case import TEST_CASES

def run_backend_eval(provider, log_file, results):
    print("\n" + "="*50)
    print("RUNNING IN BACKEND MODE (Gemini / active provider)")
    print(f"Model: {provider.model_name}")
    print("="*50 + "\n")
    
    log_file.write(f"=== BACKEND AGENT EVALUATION (Model: {provider.model_name}) ===\n\n")

    # Mapping of tool names for status evaluation
    # tests/test_case.py expects: check_movie_schedule, calculate_total_price, book_movie_ticket
    # Backend agent uses: get_movie_info, check_seat_availability, calculate_total_price, book_ticket
    tool_mappings = {
        "check_movie_schedule": "get_movie_info",
        "book_movie_ticket": "book_ticket"
    }

    for idx, case in enumerate(TEST_CASES):
        tc_id = case["id"]
        category = case["category"]
        user_input = case["user_input"]
        expected_tools = case["expected_tools"]
        
        print(f"[{idx+1}/{len(TEST_CASES)}] Running {tc_id} ({category}): {user_input[:50]}...")
        log_file.write(f"[{tc_id}] Category: {category}\n")
        log_file.write(f"Input: {user_input}\n")
        log_file.write(f"Expected Tools (CLI): {expected_tools}\n")
        log_file.write("-" * 50 + "\n")

        agent = ReActAgent(llm=provider, tools=TOOL_SPECS, max_steps=6)
        tracker.reset_session()
        start_time = time.time()
        
        # Hook agent._execute_tool to record tool calls
        actual_tools_called = []
        original_execute = agent._execute_tool
        
        def hooked_execute(tool_name, args_dict):
            actual_tools_called.append(tool_name)
            log_file.write(f"   [Tool Call] {tool_name}({json.dumps(args_dict, ensure_ascii=False)})\n")
            res = original_execute(tool_name, args_dict)
            log_file.write(f"   [Observation] {res[:500]}...\n")
            return res
            
        agent._execute_tool = hooked_execute

        try:
            response = agent.run(user_input)
        except Exception as e:
            response = f"ERROR during execution: {e}"
            log_file.write(f"   [Exception Error] {e}\n")
            
        latency = int((time.time() - start_time) * 1000)
        
        # Log trace steps
        log_file.write(f"   [Trace Steps]\n")
        for step in agent.current_trace:
            if "thought" in step and step["thought"]:
                log_file.write(f"      Thought: {step['thought']}\n")
            if "tool" in step:
                log_file.write(f"      Action: {step['tool']}({json.dumps(step.get('arguments', {}), ensure_ascii=False)})\n")
            if "observation" in step and step["observation"]:
                log_file.write(f"      Observation: {step['observation'][:300]}...\n")
                
        log_file.write(f"   [Final Answer] {response}\n")
        log_file.write(f"   [Latency] {latency}ms\n")
        
        # Validate tool usage
        # Map expected tools to backend tool names
        mapped_expected = []
        for t in expected_tools:
            mapped_expected.append(tool_mappings.get(t, t))
            
        # We check if all mapped expected tools were called
        passed = True
        for met in mapped_expected:
            if met not in actual_tools_called:
                passed = False
                break
                
        status = "PASS" if passed else "FAIL"
        log_file.write(f"   [Status] {status} (Actual calls: {actual_tools_called})\n")
        log_file.write("="*80 + "\n\n")
        log_file.flush()

        results.append({
            "id": tc_id,
            "category": category,
            "user_input": user_input,
            "expected_tools": expected_tools,
            "actual_tools": actual_tools_called,
            "response": response,
            "latency_ms": latency,
            "status": status
        })


def run_gguf_eval(log_file, results):
    print("\n" + "="*50)
    print("RUNNING IN GGUF MODE (Local Phi-3 model)")
    print("="*50 + "\n")
    
    log_file.write(f"=== GGUF AGENT EVALUATION (Local Phi-3) ===\n\n")

    try:
        import react_agent
    except Exception as e:
        print(f"❌ Error loading react_agent.py: {e}")
        print("Please check if your GGUF model path is configured correctly in .env and llama-cpp-python is installed.")
        log_file.write(f"CRITICAL ERROR: Failed to load react_agent.py: {e}\n")
        return

    for idx, case in enumerate(TEST_CASES):
        tc_id = case["id"]
        category = case["category"]
        user_input = case["user_input"]
        expected_tools = case["expected_tools"]
        
        print(f"[{idx+1}/{len(TEST_CASES)}] Running {tc_id} ({category}): {user_input[:50]}...")
        log_file.write(f"[{tc_id}] Category: {category}\n")
        log_file.write(f"Input: {user_input}\n")
        log_file.write(f"Expected Tools: {expected_tools}\n")
        log_file.write("-" * 50 + "\n")

        # Hook the mock tools to record calls
        actual_tools_called = []
        original_tools = {k: v for k, v in react_agent.TOOLS.items()}

        def hook_tool(name, fn):
            def hooked(*args, **kwargs):
                actual_tools_called.append(name)
                log_file.write(f"   [Tool Call] {name}(args={args}, kwargs={kwargs})\n")
                res = fn(*args, **kwargs)
                log_file.write(f"   [Observation] {json.dumps(res, ensure_ascii=False)}\n")
                return res
            return hooked

        for name, fn in original_tools.items():
            react_agent.TOOLS[name] = hook_tool(name, fn)

        start_time = time.time()
        try:
            response = react_agent.run_agent(user_input)
        except Exception as e:
            response = f"ERROR during execution: {e}"
            log_file.write(f"   [Exception Error] {e}\n")

        latency = int((time.time() - start_time) * 1000)

        log_file.write(f"   [Final Answer] {response}\n")
        log_file.write(f"   [Latency] {latency}ms\n")

        # Validate tool calls
        passed = (actual_tools_called == expected_tools)
        status = "PASS" if passed else "FAIL"
        log_file.write(f"   [Status] {status} (Actual calls: {actual_tools_called})\n")
        log_file.write("="*80 + "\n\n")
        log_file.flush()

        # Restore original tools
        for name, fn in original_tools.items():
            react_agent.TOOLS[name] = fn

        results.append({
            "id": tc_id,
            "category": category,
            "user_input": user_input,
            "expected_tools": expected_tools,
            "actual_tools": actual_tools_called,
            "response": response,
            "latency_ms": latency,
            "status": status
        })


def main():
    parser = argparse.ArgumentParser(description="Cinema Booking Agent Test Suite Runner")
    parser.add_argument("--mode", type=str, choices=["backend", "gguf"], default="backend",
                        help="Evaluation mode: 'backend' (Gemini/cached API, fast) or 'gguf' (local GGUF model, slow)")
    args = parser.parse_args()

    load_dotenv()
    os.makedirs("logs", exist_ok=True)
    
    log_file_path = os.path.join("logs", "test_execution.log")
    results = []

    print("="*80)
    print("STARTING TEST CASE EVALUATION SUITE")
    print(f"Mode: {args.mode.upper()}")
    print(f"Log Output: {log_file_path}")
    print("="*80)

    with open(log_file_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"=== MOVIE BOOKING AGENT - SYSTEM TEST SUITE ===\n")
        log_file.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"Mode: {args.mode.upper()}\n")
        log_file.write("="*80 + "\n\n")

        if args.mode == "backend":
            provider = init_provider()
            run_backend_eval(provider, log_file, results)
        else:
            run_gguf_eval(log_file, results)

        # Print overall statistics
        pass_count = sum(1 for r in results if r["status"] == "PASS")
        fail_count = len(results) - pass_count
        pass_rate = (pass_count / len(results)) * 100 if results else 0
        avg_latency = sum(r["latency_ms"] for r in results) / len(results) if results else 0

        log_file.write(f"=== TEST RUN SUMMARY ===\n")
        log_file.write(f"Total Tests: {len(results)}\n")
        log_file.write(f"Passed: {pass_count} ({pass_rate:.1f}%)\n")
        log_file.write(f"Failed: {fail_count}\n")
        log_file.write(f"Average Latency: {avg_latency:.1f}ms\n")
        log_file.write("="*80 + "\n")

    # Save results as JSON
    with open("logs/test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    # Write Markdown Summary Report
    summary_path = os.path.join("logs", "test_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"# Cinema Booking Agent - Test Suite Execution Summary\n\n")
        f.write(f"- **Execution Mode**: {args.mode.upper()}\n")
        f.write(f"- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"## Metrics Summary\n")
        f.write(f"- **Total Tests Run**: {len(results)}\n")
        f.write(f"- **Passed**: {pass_count} ({pass_rate:.1f}%)\n")
        f.write(f"- **Failed**: {fail_count}\n")
        f.write(f"- **Average Latency**: {avg_latency:.1f} ms\n\n")
        
        f.write(f"## Detailed Test Run Results\n\n")
        f.write(f"| Case ID | Category | Query | Expected Tools | Actual Tools | Status |\n")
        f.write(f"| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in results:
            status_emoji = "✅ PASS" if r["status"] == "PASS" else "❌ FAIL"
            f.write(f"| {r['id']} | {r['category']} | {r['user_input']} | `{r['expected_tools']}` | `{r['actual_tools']}` | {status_emoji} |\n")

    print("\n" + "="*80)
    print("TEST SUITE RUN COMPLETED!")
    print(f"- Total Cases: {len(results)}")
    print(f"- Passed: {pass_count}/{len(results)} ({pass_rate:.1f}%)")
    print(f"- Detailed Log: {log_file_path}")
    print(f"- Markdown Summary Report: {summary_path}")
    print("="*80)


if __name__ == "__main__":
    main()
