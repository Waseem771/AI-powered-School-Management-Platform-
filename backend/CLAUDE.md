# CLAUDE.md (backend)

Backend guidance for Claude Code. Project-wide context is in [../CLAUDE.md](../CLAUDE.md).

## Run

Always run from `backend/` (imports are top-level: `from config import ...`).

```bash
python -m pip install -r requirements.txt
python seed_data.py
python -m uvicorn main:app --reload     # :8000, docs at /docs
python check_imports.py
```

Tests are scripts: `python test_data_assistant.py`, `python test_school_assistant.py`, `python test_backend.py` (the last uses the real `school.db`).

## Layout

- `main.py`: FastAPI app, CORS, router registration, lifespan (creates tables, default `admin` / `admin123`).
- `config.py`: env loading, `GRADES`, `SECTIONS`, `SUBJECTS`, fee amounts, JWT settings.
- `database.py`: SQLite engine and `get_session` dependency.
- `models/`: `user.py`, `student.py` (Base/Create/Update/Read schemas), `fee.py` (Invoice, Payment, FeeStructure, AcademicYear), `result.py` (`calculate_grade`).
- `routers/`: one file per resource; every route except login uses `_user = Depends(get_current_user)`.
- `services/`: business logic; routers stay thin.
- `knowledge_base/*.txt`: policy source for RAG. Editing these changes chatbot answers; restart so chunks reload.

## Conventions

- New endpoint: add the router function, register it in `main.py` if it is a new router, then add the matching method to `frontend/src/api/client.js`.
- Model change: no migrations exist. Delete `school.db`, reseed, and apply the same care to the Modal volume.
- New dependency: add to both `requirements.txt` and the pip list in `modal_app.py`.
- Heavy imports (sentence-transformers, FAISS) must stay lazy so startup stays fast; the RAG model initializes on first use.
- Chatbot data tools stay read-only and allowlisted. A new tool needs: definition, `execute_tool` branch, local keyword fallback, structured-data mapping, and a test in `test_data_assistant.py` / `test_school_assistant.py`. It must work with no `GROQ_API_KEY`.
- Keep secrets in `.env` only. Never log or echo `GROQ_API_KEY` or `SECRET_KEY`.

## Gotchas

- `ai_service` trains on synthetic data at import time; its output differs by process, not by school data.
- Risk features live only in `services/risk_features.py`; `dashboard.py` and `ai.py` both call it.
- Student delete cascades manually (results, invoices, payments) because there are no DB-level cascades; extend `delete_student` if you add tables that reference students.
