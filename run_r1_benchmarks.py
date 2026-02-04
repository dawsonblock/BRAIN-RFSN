# run_r1_benchmarks.py
import os
import sys
from benchmarks.swebench_runner import run_swebench_lite
from benchmarks.gaia_runner import run_gaia_benchmark

# Set API Key from environment
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    print("❌ Error: DEEPSEEK_API_KEY not set in environment.")
    sys.exit(1)

def main():
    print("🚀 Starting RFSN Benchmark with DeepSeek R1 (deepseek-reasoner)\n")
    print("-" * 60)
    
    # 1. SWE-bench Lite
    print("\n🛠️ Running SWE-bench Lite (Simplified)...")
    swe_run = run_swebench_lite(api_key=DEEPSEEK_API_KEY)
    print(f"✅ Run ID: {swe_run.run_id}")
    print(f"📊 Resolve Rate: {swe_run.resolve_rate:.1%} ({swe_run.tasks_resolved}/{swe_run.tasks_total})")
    
    # 2. GAIA Benchmark
    print("\n🌍 Running GAIA Benchmark (Sample)...")
    gaia_run = run_gaia_benchmark(api_key=DEEPSEEK_API_KEY)
    print(f"✅ Run ID: {gaia_run.run_id}")
    print(f"📊 Accuracy: {gaia_run.accuracy:.1%} ({gaia_run.tasks_correct}/{gaia_run.tasks_total})")
    
    print("-" * 60)
    print("\n🏁 All benchmarks complete. Detailed results saved in ./swebench_results and ./gaia_results")

if __name__ == "__main__":
    main()
