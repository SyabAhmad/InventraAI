"""InventraAI FastAPI application.

One command starts everything:

    uvicorn src.api.main:app --reload

Serves:
  - the dashboard frontend at /            (frontend/)
  - live data endpoints at /api/...        (SQLite through the service layer)
  - the LangGraph agent at POST /api/chat  (real tool-calling, no fallback)
  - interactive API docs at /docs
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import chat, dashboard
from src.config import API_HOST, API_PORT, PROJECT_ROOT

FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(
    title="InventraAI API",
    version="0.5.0",
    description="AI inventory management agent for e-commerce - live data and agent endpoints.",
)

# Local-first app: allow the dashboard to call the API even when it is opened
# as a static file (file:// sends an opaque Origin).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(chat.router)


@app.middleware("http")
async def no_cache_frontend(request, call_next):
    """Always serve fresh UI assets so a normal reload picks up new JS.

    Without this a browser can keep running a cached chat.js (and thus an
    older feature set) even after the server has new code.
    """
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith(("/js/", "/css/", "/vendor/", "/ms/")):
        response.headers["Cache-Control"] = "no-store"
    return response


# Static dashboard (mounted last so /api routes take precedence).
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


def main() -> None:
    import uvicorn

    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()
