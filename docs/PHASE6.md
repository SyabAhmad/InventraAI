# Phase 6 — Benchmarking & Optimization (FYP Roadmap §5)

> **Branch:** `phase-6-benchmark`
> **Status:** Complete — dashboard page + CLI + evidence files
> **Owner:** Arzo Naveed (inventory workstream T08–T11, shared T15–T18)
> **Maps to:** Roadmap 5 Oct – 27 Nov 2026 · 5 model candidates · 60% checkpoint

This phase turns the agent into a **measurable system**. It does not add new
inventory features — it proves which model + prompt is most cost-efficient,
with evidence you can show in a viva.

---

## The idea in one paragraph (viva answer)

> "We froze 20 inventory tasks, ran them on 5 Ollama Cloud models in two
> modes — **Baseline** (original prompt) and **Optimized** (shorter context) —
> using the same cases, settings, and success rules. For each run we logged
> task success, tool accuracy, forecast error, latency (median/p95), LLM
> steps, and a token proxy, plus the date, model tag, hardware, and settings.
> A model is 'better' only if it is faster/cheaper **without** losing accuracy."

That is exactly the PDF method (Roadmap p.9, T15–T18).

---

## What was built

| File | Purpose |
|---|---|
| `src/benchmark/dataset.py` | 20 **frozen** prompts `p01..p20` with category + expected tools. Never edit between Baseline/Optimized runs. |
| `src/benchmark/runner.py` | The experiment engine. Background thread, live polling, evidence files. |
| `src/agent/graph.py` | `BASELINE_PROMPT` (original) + `OPTIMIZED_PROMPT` (shorter). `create_inventory_agent(model, mode)` picks one. |
| `src/config.py` | `build_run_metadata()` — hardware + settings snapshot saved per run. |
| `src/api/routes/benchmark.py` | `GET /config`, `POST /run`, `GET /jobs/{id}`, `GET /results/latest` |
| `frontend/js/benchmark.js` | Benchmarking page: models, prompts, mode, live rows, summary |
| `scripts/run_benchmark.py` | CLI twin of the page (`--mode`, `--smoke`) |
| `tests/test_benchmark.py` | Offline unit tests (scoring + aggregation, no network) |

### 1 — Candidate selection (T03/T15)

Five tags from `.env → LLM_BENCHMARK_MODELS` (verified live at
ollama.com/library on 2026-11-05 — API names below, CLI uses `-cloud`):

```ini
LLM_BENCHMARK_MODELS=gpt-oss:20b,gemma4:31b,nemotron-3-nano:30b,qwen3.5:35b,deepseek-v4.1-flash
```

**Verification verdict:**
| Tag you wanted | On Ollama? | Verdict |
|---|---|---|
| `gpt-oss:20b-cloud` | ✅ exists (`gpt-oss:20b-cloud`) | Use API name `gpt-oss:20b` with `https://ollama.com/v1` |
| `gemma4:31b-cloud` | ✅ exists (`gemma4:31b-cloud`) | Use API name `gemma4:31b` |
| `nemotron-3-nano:30b-cloud` | ✅ exists | Use API name `nemotron-3-nano:30b` |
| `qwen3.5:35b-cloud` | ❌ **404 — does not exist** | `qwen3.5:35b` is local-only (22 GB); true cloud Qwen 3.5 is `qwen3.5:cloud` (397B) |
| `clef:27b-cloud` | ✅ exists but **decision-only** | Uses `/v1/systemone`, NOT chat/tool-calling — moved to separate `clef` check. Replaced in chat list by `deepseek-v4.1-flash` (cloud chat: tools+thinking, 1M ctx) |
| `deepseek-v4.1-flash` | ✅ exists (cloud-only) | Use API name `deepseek-v4.1-flash`, CLI `deepseek-v4.1-flash:cloud` |

Clef is still usable, but correctly: `python scripts/check_clef.py` or
`POST /api/benchmark/clef/check` (System One). It is **not** in the
20-prompt chat benchmark.

**Verify the exact tag** at `ollama.com/models` before a demo. If a tag is
wrong, its rows come back as `error` and the rest still run — the report
must disclose which runs were feasible (PDF: "Start with a smoke set").

Why cloud? Roadmap Risk #1 is "model downloads/inference exceed hardware
capacity". Cloud removes RAM/VRAM as a blocker, at the cost of network
latency being included. Record it in the final report (hardware is still
logged per run via `build_run_metadata()`).

### 2 — Repeatable cases (frozen)

`dataset.py` covers every workstream the PDF asks for:

- Inventory: p01 summary, p02 low-stock, p03 out-of-stock, p04 stock lookup
- Search: p05 category search, p20 unknown SKU (hallucination guardrail)
- Sales: p06 summary, p07 top sellers, p08 slow movers, p09 revenue by category
- Forecast: p10 demand, p11 validation, p12 method comparison
- Reorder: p13 single, p14 all, p15 summary
- Chart: p16 bar, p17 line, p18 pie, p19 per-product trend

`p20` is the anti-hallucination case: the answer must say "not found" —
inventing stock is a quality failure even if a tool ran.

### 3 — Baseline vs Optimized (T17)

| Mode | Prompt | What changes |
|---|---|---|
| `baseline` | Original `BASELINE_PROMPT` | Existing context + call pattern |
| `optimized` | `OPTIMIZED_PROMPT` | Shorter context, clearer structure, "no extra tool calls" |

Same models, same 20 cases, same tools, same success rules — only the
prompt differs, so the delta is attributable. Run both modes and compare
**accuracy vs latency**, not just latency alone.

### 4 — Metrics (PDF p.9 table)

Per row (one model × one case × one repeat):

- **Task success** — non-empty answer, no exception
- **Quality** — `tool_accuracy` (expected tools subset) + forecast
  **MAE/MAPE** ground truth for p10–p12 (from `validate_forecast`)
- **Latency/usage** — wall time (mean / **median** / **p95**), `steps`
  (LLM calls), **token proxy** = chars ÷ 4 (consistent proxy)

Per model summary (`_aggregate`): success %, accuracy %, median/p95
latency, avg steps, avg tokens, forecast MAE/MAPE.

### 5 — Evidence files

Every run writes `benchmark_results/run_*.json`:

```json
{
  "id": "...", "mode": "optimized",
  "started_at": "...", "finished_at": "...",
  "metadata": { "python": "...", "platform": "...", "provider": "ollama",
                "base_url": "...", "temperature": 0.2, ... },
  "models": ["..."], "prompt_ids": ["p01", ...], "repeats": 1,
  "summary": { "<model>": { success_rate, tool_accuracy, median_latency_ms,
                            p95_latency_ms, avg_steps, avg_tokens, ... } },
  "results": [ { "id": "p01", "model": "...", "status": "passed",
                 "latency_ms": 1234.5, "steps": 3, "tokens_proxy": 120,
                 "tools_called": ["inventory_summary"],
                 "answer_preview": "...", "error": "" } ]
}
```

Never contains the API key. This file *is* the viva evidence.

---

## How to run

```bash
# 1. Dashboard (live rows + progress)
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
# → http://127.0.0.1:8000 → Benchmarking → pick models/prompts/mode → Start

# 2. CLI (same engine)
python scripts/run_benchmark.py --mode baseline --smoke
python scripts/run_benchmark.py --mode optimized
python scripts/run_benchmark.py --models gemma4:31b-cloud --prompts p01,p13,p16 --repeats 3 --mode baseline

# 3. Offline tests (no network)
python -m pytest tests/test_benchmark.py tests/test_agent.py -q
```

Recommended sequence (PDF):
1. **Smoke** (p01–p05, all models) — confirm tags/keys work.
2. **Baseline** full (20 × 5) — your T16 record.
3. **Optimized** full (20 × 5) — your T17 matched comparison.
4. Write the cost-efficiency report from the two JSON files (T18).

---

## Design rules

- **Frozen cases.** Never retune a prompt in the dataset mid-comparison.
- **One row = one evidence record.** No row, no claim.
- **Errors are data.** A failed model row stays in the file as `error`.
- **Token proxy disclaimer.** Adapters don't always return usage, so we use
  chars÷4 consistently and label it `tokens_proxy` everywhere.
- **Deterministic tools.** All numbers come from SQLite/Python tools;
  the LLM only routes and narrates, so accuracy deltas come from the
  model/prompt, not the data.

## What comes next (W8)

- T18 matched comparison table (Baseline vs Optimized per model).
- Whole-project Cost-Efficiency Report (all 3 agents, shared format).
- Model recommendation grounded in measured rows — no savings claim
  unless the JSON supports it.

---

## Glossary

- **Baseline / Optimized** — the two prompt modes compared head-to-head.
- **Smoke set** — p01–p05 quick run to validate tags/keys before the full run.
- **Tool accuracy** — did the agent call every tool the case expects?
- **p95 latency** — 95% of runs were faster than this; the tail users feel.
- **Token proxy** — estimated tokens (chars ÷ 4) used as a fair cost proxy.
- **Evidence file** — the JSON in `benchmark_results/` with full provenance.
