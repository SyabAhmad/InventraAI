"""Excel export for benchmark evidence files.

Produces a single .xlsx with 4 sheets:
  1. Summary   — per-model metrics + bar charts + line chart
  2. Results   — every row (one model × one case × one repeat)
  3. By Case   — per-case view for Baseline vs Optimized compare
  4. Metadata  — hardware/settings snapshot (date, python, platform, models, mode)

Works on the JSON evidence dicts produced by runner.py (same shape whether
still running in memory or loaded from benchmark_results/*.json).
No formulas beyond simple cell references — keeps the file portable and
printable for the viva.
"""
from __future__ import annotations

from io import BytesIO
from datetime import datetime, timezone
from typing import Any
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, column_index_from_string

_HDR_FILL = PatternFill("solid", fgColor="8B6F47")
_HDR_FONT = Font(color="FFFFFF", bold=True, size=11, name="Segoe UI")
_SUBHDR_FILL = PatternFill("solid", fgColor="F5F1E8")
_ZEBRA = PatternFill("solid", fgColor="FAF7F2")
_OK_FILL = PatternFill("solid", fgColor="E9F3EA")
_WARN_FILL = PatternFill("solid", fgColor="FDF6E3")
_BAD_FILL = PatternFill("solid", fgColor="FCE9E7")
_THIN = Side(style="thin", color="E3DDD1")
_BOX = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _apply_header(ws, row: int, headers: list[str], start_col: int = 1) -> None:
    for i, h in enumerate(headers, start=start_col):
        c = ws.cell(row=row, column=i, value=h)
        c.fill = _HDR_FILL
        c.font = _HDR_FONT
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = _BOX
    ws.row_dimensions[row].height = 22


def _auto_width(ws, widths: dict[int, float]) -> None:
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w


def _zebra(ws, start_row: int, end_row: int, cols: list[int]) -> None:
    for r in range(start_row, end_row + 1):
        if r % 2 == 0:
            for c in cols:
                ws.cell(row=r, column=c).fill = _ZEBRA


def _fmt_title(ws, cell: str, text: str, size: int = 14) -> None:
    ws[cell] = text
    ws[cell].font = Font(bold=True, size=size, color="2B2B2B", name="Segoe UI")


def _write_summary(wb: Workbook, mode: str, metadata: dict, models: list[str], summary: dict[str, dict]) -> None:
    ws = wb.create_sheet("Summary")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A5"

    _fmt_title(ws, "A1", "InventraAI — Benchmark Summary")
    ws["A2"] = f"Mode: {mode}   |   Provider: {metadata.get('provider', '?')}   |   Base URL: {metadata.get('base_url', '?')}"
    ws["A2"].font = Font(size=10, italic=True, color="6B6B6B", name="Segoe UI")

    headers = ["Model", "Total runs", "Success %", "Tool accuracy %", "Median latency (ms)", "p95 latency (ms)",
               "Avg steps", "Avg tokens*", "Forecast MAE", "Forecast MAPE"]
    _apply_header(ws, 4, headers)
    rows: list[list[Any]] = []
    for model in models:
        s = summary.get(model, {}) or {}
        rows.append([
            model,
            s.get("total", 0),
            s.get("success_rate", 0.0),
            s.get("tool_accuracy", 0.0),
            s.get("median_latency_ms", s.get("avg_latency_ms", 0.0)),
            s.get("p95_latency_ms", 0.0),
            s.get("avg_steps", 0.0),
            s.get("avg_tokens", 0.0),
            s.get("forecast_mae"),
            s.get("forecast_mape"),
        ])
    for i, row in enumerate(rows, start=5):
        for j, val in enumerate(row, start=1):
            c = ws.cell(row=i, column=j, value=val)
            c.border = _BOX
            if j == 1:
                c.font = Font(bold=True, name="Consolas")
            elif j >= 2:
                c.alignment = Alignment(horizontal="center")
                if j in (3, 4):
                    c.number_format = '0.0"%"'
                elif j == 9:
                    c.number_format = "0.000"
                elif j == 10:
                    c.number_format = '0.000"%"'
    end = 4 + len(rows)

    # Conditional highlight by tool accuracy (green >= 90, amber >= 60, red otherwise)
    for i in range(5, end + 1):
        acc = ws.cell(row=i, column=4).value or 0
        fill = _OK_FILL if acc >= 90 else (_WARN_FILL if acc >= 60 else _BAD_FILL)
        ws.cell(row=i, column=4).fill = fill
    _zebra(ws, 5, end, list(range(1, 11)))

    _auto_width(ws, {1: 24, 2: 12, 3: 13, 4: 17, 5: 18, 6: 17, 7: 11, 8: 13, 9: 15, 10: 16})
    ws.auto_filter.ref = f"A4:J{end}"

    # ---- Embedded charts ----
    chart_row = end + 2
    bar_latency = BarChart()
    bar_latency.type = "col"
    bar_latency.style = 10
    bar_latency.y_axis.title = "ms"
    bar_latency.x_axis.title = "Model"
    bar_latency.title = "Median latency per model"
    bar_latency.y_axis.delete = False
    bar_latency.x_axis.delete = False
    data = Reference(ws, min_col=5, max_col=5, min_row=4, max_row=end)
    cats = Reference(ws, min_col=1, min_row=5, max_row=end)
    bar_latency.add_data(data, titles_from_data=True)
    bar_latency.set_categories(cats)
    bar_latency.legend = None
    bar_latency.dLbls = DataLabelList()
    bar_latency.dLbls.showVal = True
    bar_latency.dLbls.numFmt = '#,##0" ms"'
    bar_latency.height, bar_latency.width = 8, 16
    ws.add_chart(bar_latency, f"A{chart_row}")

    bar_success = BarChart()
    bar_success.type = "col"
    bar_success.style = 10
    bar_success.y_axis.title = "%"
    bar_success.x_axis.title = "Model"
    bar_success.title = "Task success vs Tool accuracy (%)"
    data2 = Reference(ws, min_col=3, max_col=4, min_row=4, max_row=end)
    bar_success.add_data(data2, titles_from_data=True)
    bar_success.set_categories(cats)
    bar_success.height, bar_success.width = 8, 16
    bar_success.y_axis.scaling.min = 0
    bar_success.y_axis.scaling.max = 100
    ws.add_chart(bar_success, f"F{chart_row}")

    ws[f"A{chart_row + 18}"] = "* tokens = chars ÷ 4 proxy (provider usage counts are not always returned). Formatted for viva printout."
    ws[f"A{chart_row + 18}"].font = Font(size=9, italic=True, color="6B6B6B")


def _write_results(wb: Workbook, rows: list[dict]) -> None:
    ws = wb.create_sheet("Results")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A5"
    _fmt_title(ws, "A1", "Benchmark — Every Row (evidence)")
    ws["A2"] = f"{len(rows)} rows · one row = one case × one model × one repeat"
    ws["A2"].font = Font(size=10, italic=True, color="6B6B6B")

    headers = ["#", "Model", "Mode", "Case", "Question", "Category", "Status", "Success",
               "Tool accuracy", "Tools called", "Steps", "Latency (ms)", "Tokens*", "Repeat", "Answer preview"]
    _apply_header(ws, 4, headers)
    for i, r in enumerate(rows, start=5):
        vals = [
            i - 4, r.get("model"), r.get("mode", "baseline"), r.get("id"), r.get("question"),
            r.get("category"), r.get("status"), "Yes" if r.get("success") else "No",
            "Yes" if r.get("tool_accuracy") else "No",
            ", ".join(r.get("tools_called", []) or []),
            r.get("steps", 0), r.get("latency_ms", 0.0), r.get("tokens_proxy", 0), r.get("repeat", 1),
            (r.get("answer_preview") or r.get("error") or "")[:300],
        ]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.border = _BOX
            if j == 2:
                c.font = Font(bold=True, name="Consolas")
            elif j == 4:
                c.font = Font(bold=True)
            if j in (10, 13):
                c.alignment = Alignment(wrap_text=True, vertical="center")
            else:
                c.alignment = Alignment(vertical="center", wrap_text=(j >= 14))
            if j == 12:
                c.number_format = "#,##0.0"
            if j == 11:
                c.alignment = Alignment(horizontal="center", vertical="center")
            if j == 7:
                status = str(v or "").lower()
                c.alignment = Alignment(horizontal="center", vertical="center")
                c.fill = _OK_FILL if status == "passed" else (_WARN_FILL if status == "success" else _BAD_FILL)
        ws.row_dimensions[i].height = 30
    end = 4 + len(rows)
    _auto_width(ws, {1: 5, 2: 22, 3: 10, 4: 8, 5: 42, 6: 12, 7: 11, 8: 9, 9: 14, 10: 38, 11: 8, 12: 12, 13: 10, 14: 8, 15: 90})
    ws.auto_filter.ref = f"A4:O{end}"
    _zebra(ws, 5, end, list(range(1, 16)))


def _write_by_case(wb: Workbook, rows: list[dict], models: list[str]) -> None:
    ws = wb.create_sheet("By Case")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "B5"
    _fmt_title(ws, "A1", "Benchmark — Per Case × Per Model")

    headers = ["Case"] + [m for m in models] + ["Winner (accuracy)", "Notes"]
    _apply_header(ws, 4, headers)
    store: dict[str, dict[str, dict]] = {}
    for r in rows:
        store.setdefault(r.get("id", "?"), {})[r.get("model", "?")] = r
    case_ids = sorted(store.keys())
    for i, cid in enumerate(case_ids, start=5):
        row = [cid]
        accs = []
        for m in models:
            r = store[cid].get(m)
            if r:
                row.append("P" if (r.get("tool_accuracy") and r.get("success")) else ("✓" if r.get("success") else "✗"))
                accs.append(r.get("tool_accuracy", False))
            else:
                row.append("—")
        best = ""
        if accs:
            best = "all" if all(accs) else ("none" if not any(accs) else "partial")
        row.append(best)
        q = next(iter(store[cid].values())).get("question", "")
        row.append(q)
        for j, v in enumerate(row, start=1):
            c = ws.cell(row=i, column=j, value=v)
            c.border = _BOX
            if j == 1:
                c.font = Font(bold=True)
            if 2 <= j <= 1 + len(models):
                c.alignment = Alignment(horizontal="center", vertical="center")
                if v == "P":
                    c.fill = _OK_FILL
                elif v == "✓":
                    c.fill = _WARN_FILL
                elif v == "✗":
                    c.fill = _BAD_FILL
        ws.row_dimensions[i].height = 18
    end = 4 + len(case_ids)
    _auto_width(ws, {1: 8, **{i + 2: 18 for i in range(len(models))}, len(models) + 2: 18, len(models) + 3: 70})
    ws.auto_filter.ref = f"A4:{get_column_letter(len(models) + 3)}{end}"


def _write_metadata(wb: Workbook, mode: str, metadata: dict, models: list[str], started: str, finished: str, file_name: str | None) -> None:
    ws = wb.create_sheet("Metadata")
    ws.sheet_view.showGridLines = False
    _fmt_title(ws, "A1", "Benchmark — Provenance & Settings")
    ws["A2"] = "Recorded automatically per run (see docs/PHASE6.md §5). Share this sheet with your report."
    ws["A2"].font = Font(size=9, italic=True, color="6B6B6B")
    rows = [
        ("Mode", mode),
        ("Provider", metadata.get("provider", "")),
        ("Base URL", metadata.get("base_url", "")),
        ("Models", ", ".join(models)),
        ("Default model", metadata.get("default_model", "")),
        ("Temperature", metadata.get("temperature", "")),
        ("Python", metadata.get("python", "")),
        ("Platform", metadata.get("platform", "")),
        ("Processor", metadata.get("processor", "")),
        ("Forecast horizon (days)", metadata.get("forecast_horizon_days", "")),
        ("Database path", metadata.get("database_path", "")),
        ("Run started", started or datetime.now(timezone.utc).isoformat()),
        ("Run finished", finished or ""),
        ("Source file", file_name or ""),
        ("Exported at", datetime.now(timezone.utc).isoformat()),
        ("Token proxy", "chars ÷ 4 (consistent proxy — no provider usage counts assumed)"),
        ("Experiment", "Baseline = original prompt · Optimized = shorter context (same cases/tools/success rules)"),
    ]
    row = 4
    for k, v in rows:
        ws.cell(row=row, column=1, value=k).font = Font(bold=True)
        ws.cell(row=row, column=1).border = _BOX
        c = ws.cell(row=row, column=2, value=str(v) if v is not None else "")
        c.border = _BOX
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[row].height = 18
        row += 1
    _auto_width(ws, {1: 26, 2: 90})


def build_xlsx(job: dict[str, Any], file_name: str | None = None) -> bytes:
    """Build the .xlsx bytes for one benchmark job/run dict."""
    mode = job.get("mode", "baseline")
    models = job.get("models", [])
    summary = job.get("summary", {})
    results = job.get("results", []) or []
    metadata = job.get("metadata") or {}
    started = job.get("started_at", "")
    finished = job.get("finished_at", "")

    wb = Workbook()
    wb.remove(wb["Sheet"])  # start clean
    _write_summary(wb, mode, metadata, models, summary)
    _write_results(wb, results)
    _write_by_case(wb, results, models)
    _write_metadata(wb, mode, metadata, models, started, finished, file_name)

    # Page setup for printout
    for ws in wb.worksheets:
        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = 5  # legal
        ws.page_margins.left = ws.page_margins.right = 0.4
        ws.page_margins.top = ws.page_margins.bottom = 0.35
        ws.oddFooter.left.text = "&D &T · InventraAI · Arzo Naveed"
        ws.oddFooter.left.size = 9
        ws.oddFooter.left.color = "6B6B6B"
        ws.oddFooter.center.text = "InventraAI — Benchmark"
        ws.oddFooter.center.size = 9
        ws.oddFooter.center.color = "6B6B6B"
        ws.oddFooter.right.text = "Page &P of &N"
        ws.oddFooter.right.size = 9
        ws.oddFooter.right.color = "6B6B6B"

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


__all__ = ["build_xlsx"]
