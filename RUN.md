# Run the Project — from scratch

Complete, copy-paste instructions for the **full build** (Phase 5: dashboard + API + agent chat).
Works on Windows (PowerShell) and macOS/Linux (bash).

---

## 0. What you need

| Requirement | Notes |
|---|---|
| Python 3.9+ | Tested on 3.9–3.12 |
| pip | Comes with Python |
| git | To clone the repo |
| LLM API key | Any OpenAI-compatible provider (Ollama Cloud recommended). Local Ollama needs no key. |

---

## 1. Clone and open the project

```bash
git clone https://github.com/SyabAhmad/InventraAI.git
cd InventraAI
git checkout phase-5-dashboard
```

> Use `phase-5-dashboard` for the full app. Earlier phase branches only contain the
> parts built up to that phase.

---

## 2. Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If activation is blocked by the execution policy, run this once for the current
terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Configure the LLM (`.env`)

```powershell
# Windows
copy .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

Open `.env` and set at least these:

```ini
LLM_BASE_URL=https://ollama.com/v1
LLM_API_KEY=your-key-here
LLM_MODEL=gemma4:31b
```

| Provider | `LLM_BASE_URL` | `LLM_API_KEY` |
|---|---|---|
| Ollama Cloud | `https://ollama.com/v1` | your Ollama key |
| Groq | `https://api.groq.com/openai/v1` | your Groq key |
| OpenAI | `https://api.openai.com/v1` | your OpenAI key |
| Local Ollama | `http://localhost:11434/v1` | `ollama` (any non-empty text) |

The old `OLLAMA_*` variable names still work (they are aliases).

---

## 5. Create and seed the database

```bash
python scripts/init_db.py
```

Expected output:

```text
{'status': 'seeded', 'products': 100, 'inventory': 100, 'sales': 8745}
DB path: ...\data\inventory.db
```

To wipe and re-seed from zero:

```bash
python scripts/init_db.py --reset --products 100 --days 90
```

---

## 6. Start the server (backend + dashboard)

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

You should see:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

## 7. Open the app

| URL | What it is |
|---|---|
| http://127.0.0.1:8000 | Dashboard + chat UI |
| http://127.0.0.1:8000/docs | Interactive API docs |
| http://127.0.0.1:8000/api/health | Health check (should return `{"status":"ok",...}`) |

> `GET /health` returns 404 on purpose — the endpoint is `/api/health`.

---

## 8. Use the chat (MenteE)

Open the chat panel and try:

- `Show inventory summary`
- `Which products are low in stock?`
- `Make a bar chart of the top sellers`
- `find me last 3 days of most selling book` → then `chart the above book`

Notes:

- Charts (bar / line / pie) render **inline in the chat**.
- The last 12 turns of the conversation are sent with each question, so follow-ups
  like "chart the above book" work.
- Small "used: …" chips show which tools the agent called.
- Answers come only from real database data — there is no fabricated fallback.

---

## 9. Stop the server

Press `Ctrl+C` in the terminal.

---

## 10. Optional: chat from the terminal

```bash
python scripts/chat_cli.py
```

Type a question, or `exit` to quit.

---

## 11. Optional: static / snapshot mode (no server)

Open `frontend/index.html` directly in a browser. It uses the bundled
`frontend/js/data.js`.

Regenerate the bundle after re-seeding the database:

```bash
python scripts/generate_products_html.py
```

In snapshot mode the chat uses the local intent engine (no LLM), so it works offline.

---

## 12. Run the tests

```bash
python -m pytest -q
```

Expected on `phase-5-dashboard`: `44 passed`.

---

## 13. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: src` | Run the command from the project root (where `src/` lives). |
| venv activation blocked (Windows) | Use `.venv\Scripts\python.exe -m uvicorn ...`, or set the process execution policy (step 2). |
| Chat returns HTTP 502 / 401 | Check `LLM_API_KEY`, `LLM_BASE_URL`, and that the model is available on your account. |
| Database not found | Run `python scripts/init_db.py`; check `DATABASE_PATH` in `.env`. |
| Port 8000 already in use | Stop the old process, or start with `--port 8001`. |
| Changes to JS not showing | The server sends `Cache-Control: no-store`, so press `Ctrl+F5` once. |
