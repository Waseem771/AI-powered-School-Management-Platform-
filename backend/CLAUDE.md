# CLAUDE.md (backend)

Backend guidance for Claude Code. Project-wide context is in [../CLAUDE.md](../CLAUDE.md).

## Run

Always run from `backend/` (imports are top-level: `from config import ...`).

```bash
python -m pip install -r requirements-dev.txt
python seed_data.py
python -m uvicorn main:app --reload     # :8000, docs at /docs
python check_imports.py
```

Tests: `python -m pytest`. `conftest.py` provides a temporary seeded database, so tests never touch `school.db`.

## Layout

- `main.py`: FastAPI app, CORS, router registration, lifespan (creates tables, sets up the admin account through `services/admin_setup.py`).
- `config.py`: env loading, `GRADES`, `SECTIONS`, `SUBJECTS`, fee amounts, JWT settings.
- `database.py`: SQLite engine and `get_session` dependency.
- `models/`: `user.py`, `student.py` (Base/Create/Update/Read schemas), `fee.py` (Invoice, Payment, FeeStructure, AcademicYear), `result.py` (`calculate_grade`).
- `routers/`: one file per resource; every route except login uses `_user = Depends(get_current_user)`.
- `services/`: business logic; routers stay thin.
- `knowledge_base/*.txt`: policy source for RAG. Editing these changes chatbot answers; restart so chunks reload.

## Conventions

- New endpoint: add the router function, register it in `main.py` if it is a new router, then add the matching method to `frontend/src/api/client.js`.
- Model change: new tables are created automatically. Changes to existing tables go in `migrate_db.py`, additive and tested on a copy. Never delete a database to apply a change.
- New dependency: add an exact version to `requirements.txt` (or `requirements-admissions.txt`). `modal_app.py` installs from these files. It must also resolve for Python 3.11.
- Heavy imports (sentence-transformers, FAISS) must stay lazy so startup stays fast; the RAG model initializes on first use.
- Chatbot data tools stay read-only and allowlisted. A new tool needs: definition, `execute_tool` branch, local keyword fallback, structured-data mapping, and a test in `test_data_assistant.py` / `test_school_assistant.py`. It must work with no `GROQ_API_KEY`.
- Keep secrets in `.env` only. Never log or echo `GROQ_API_KEY` or `SECRET_KEY`.

## Gotchas

- `ai_service` trains on synthetic data at import time; its output differs by process, not by school data.
- Risk features live only in `services/risk_features.py`; `dashboard.py` and `ai.py` both call it.
- `delete_student` refuses a student with any invoice or result; everyone else is archived. If you add a table that references students, add it to that check. A query listing current students must filter on `archived_at`.
