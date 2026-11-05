"""CLI benchmark runner — same engine as the dashboard Benchmarking page.

Usage:
  python scripts/run_benchmark.py [--models a,b] [--prompts p01,p02] [--repeats 1] [--mode baseline|optimized] [--smoke]
Smoke = first 5 prompts only (p01–p05), for the PDF 'smoke set first' step.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.benchmark.runner import start_benchmark, get_job
from src.config import LLM_BENCHMARK_MODELS


def main() -> None:
    ap = argparse.ArgumentParser(description="InventraAI benchmark (Baseline vs Optimized, PDF §5)")
    ap.add_argument("--models", default=",".join(LLM_BENCHMARK_MODELS))
    ap.add_argument("--prompts", default="", help="Comma-separated ids e.g. p01,p02 (default: all)")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--mode", default="baseline", choices=["baseline", "optimized"])
    ap.add_argument("--smoke", action="store_true", help="Run only p01–p05 (smoke set)")
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    prompt_ids = [p.strip() for p in args.prompts.split(",") if p.strip()] or None
    if args.smoke:
        prompt_ids = ["p01", "p02", "p03", "p04", "p05"]

    print(f"Starting benchmark: mode={args.mode} models={models} prompts={prompt_ids} repeats={args.repeats}\n")
    job = start_benchmark(models=models, prompt_ids=prompt_ids, repeats=args.repeats, mode=args.mode)
    job_id = job["id"]

    while True:
        time.sleep(1.5)
        j = get_job(job_id)
        if not j:
            print("job lost")
            break
        print(f"[{j.get('progress_pct', 0)}%] {j.get('done', 0)}/{j.get('total', '?')} — {j.get('current_prompt', j.get('status', ''))}", flush=True)
        if j.get("status") in ("done", "failed"):
            break

    j = get_job(job_id) or {}
    print("\n=== SUMMARY ===")
    print(json.dumps(j.get("summary", {}), indent=2))
    if j.get("file"):
        print(f"\nSaved: {j['file']}")


if __name__ == "__main__":
    main()
