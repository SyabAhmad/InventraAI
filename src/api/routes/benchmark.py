"""Benchmark endpoints — live model list, 20 prompts, and run progress.

Flow:
  GET  /api/benchmark/config  -> models from .env + prompt list
  POST /api/benchmark/run     -> starts a background job, returns job_id
  GET  /api/benchmark/jobs/{job_id} -> poll for progress + rows (live)
  GET  /api/benchmark/results/latest -> last saved run file
  GET  /api/benchmark/export/latest  -> .xlsx for the latest saved run (Excel!)
  GET  /api/benchmark/export/{job_id} -> .xlsx for a finished/in-memory job
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from src.api.schemas import BenchmarkConfig, BenchmarkPrompt, BenchmarkRunRequest, ClefCheckRequest
from src.benchmark.clef import run_clef_decision
from src.benchmark.dataset import BENCHMARK_PROMPTS
from src.benchmark.export import build_xlsx
from src.benchmark.runner import get_job, latest_saved_result, start_benchmark
from src.config import BENCHMARK_REPEATS, LLM_BASE_URL, LLM_BENCHMARK_MODELS, LLM_MODEL, LLM_PROVIDER, build_run_metadata

router = APIRouter(prefix="/api", tags=["benchmark"])


@router.get("/benchmark/config", response_model=BenchmarkConfig)
def benchmark_config() -> BenchmarkConfig:
    return BenchmarkConfig(
        models=LLM_BENCHMARK_MODELS,
        default_model=LLM_MODEL,
        provider=LLM_PROVIDER,
        base_url=LLM_BASE_URL,
        prompts=[BenchmarkPrompt(**p) for p in BENCHMARK_PROMPTS],
        repeats_default=BENCHMARK_REPEATS,
        metadata=build_run_metadata(),
    )


@router.post("/benchmark/run")
def run_benchmark(payload: BenchmarkRunRequest) -> dict:
    selected = [m.strip() for m in (payload.models or LLM_BENCHMARK_MODELS) if m.strip()]
    if not selected:
        raise HTTPException(status_code=400, detail="Select at least one model (check .env LLM_BENCHMARK_MODELS).")
    job = start_benchmark(models=selected, prompt_ids=payload.prompt_ids, repeats=payload.repeats, mode=payload.mode)
    return {"job_id": job["id"], "status": job["status"], "models": selected, "mode": job["mode"], "total": "computed on first poll"}


@router.get("/benchmark/jobs/{job_id}")
def benchmark_job(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Benchmark job not found (server may have restarted).")
    return job


@router.get("/benchmark/results/latest")
def benchmark_latest() -> dict:
    data = latest_saved_result()
    if not data:
        return {"status": "empty", "message": "No benchmark results saved yet. Run a benchmark first."}
    return {"status": "ok", **data}


@router.get("/benchmark/export/latest")
def benchmark_export_latest() -> Response:
    """Download the .xlsx for the most recently saved evidence file."""
    data = latest_saved_result()
    if not data:
        raise HTTPException(status_code=404, detail="No benchmark results saved yet. Run a benchmark first.")
    return _xlsx_response(data, "InventraAI_benchmark_latest.xlsx")


@router.get("/benchmark/export/{job_id}")
def benchmark_export(job_id: str) -> Response:
    """Download the .xlsx for one live/finished job (in-memory)."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found (server may have restarted). Use /benchmark/export/latest.")
    return _xlsx_response(job, f"InventraAI_benchmark_{job_id}.xlsx")


def _xlsx_response(job: dict, filename: str) -> Response:
    try:
        payload = build_xlsx(job, file_name=filename)
    except Exception as exc:  # noqa: BLE001 — export must never 500 silently
        raise HTTPException(status_code=500, detail=f"Excel export failed: {exc}") from exc
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/benchmark/clef/check")
def clef_check(payload: ClefCheckRequest) -> dict:
    """One-off Clef decision check via /v1/systemone (NOT part of chat benchmark).

    Example: {"state": "SKU-0001 has 0 stock, min 50", "questions":
      {"need_reorder": {"type": "noul", "instructions": "Decide if reorder is needed."}}}
    """
    try:
        return run_clef_decision(payload.state, payload.questions)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
