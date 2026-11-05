# CLAUDE.md (backend)

Backend guidance for Claude Code. Project-wide context is in [../CLAUDE.md](../CLAUDE.md).

## Run

Always run from `backend/` (imports are top-level: `from config import ...`).

```bash
python -m pip install -r requirements-dev.txt
python seed_data.py                     # development data; seed_demo.py builds the demo school
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
- Chatbot data tools stay read-only and allowlisted. A new tool needs: definition in `services/assistant_tools.py`, `execute_tool` branch, local path in `school_assistant_service.py`, `_STRUCTURED_DATA_KEYS` entry, a card in the frontend, and a question in `test_chatbot_questions.py`. It must work with no `GROQ_API_KEY`. New contact fields must be added to `_NOT_SENT_TO_MODEL`.
- Keep secrets in `.env` only. Never log or echo `GROQ_API_KEY` or `SECRET_KEY`.

## Gotchas

- `ai_service` trains on synthetic data at import time, seeded so that every process gives the same scores. It takes marks only: never add a fee input.
- Risk estimates for real students go through `services/risk_assessment.py`; `dashboard.py`, `ai.py`, and the chatbot all call it.
- `delete_student` refuses a student with any invoice or result; everyone else is archived. If you add a table that references students, add it to that check. A query listing current students must filter on `archived_at`.
