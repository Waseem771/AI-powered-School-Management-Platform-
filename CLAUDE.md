# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Area-specific detail lives in [backend/CLAUDE.md](backend/CLAUDE.md) and [frontend/CLAUDE.md](frontend/CLAUDE.md). This file covers the whole project.

## Project

EduCore AI is an AI-powered school management platform for one seeded demo school, Al-Noor Academy (Islamabad, Pakistan; Grades 6-10, sections A/B). It replaces Excel and paper administration with one system for enrollment, fees, exam results, analytics, and AI features. It began as a 2-day hackathon build (`implementation-plan .txt`, `EduCore_AI_Implementation_Plan.pdf`).

| Part | Stack | Deployed to |
|------|-------|-------------|
| `backend/` | FastAPI, SQLModel, SQLite, ReportLab, scikit-learn, SHAP, FAISS, sentence-transformers, Groq | Modal (serverless) |
| `frontend/` | React 18, Vite 5, Tailwind 3, React Router 6, Axios, Recharts, lucide-react (plain JS, no TypeScript) | Vercel (root directory `frontend`) |

They have separate dependencies and are deployed separately. See `DEPLOYMENT_GUIDE.md`.

## Main features (and where they live)

| Feature | Backend | Frontend page |
|---------|---------|---------------|
| JWT admin login | `routers/auth.py` | `pages/Login.jsx` |
| Executive dashboard (KPIs, charts) | `routers/dashboard.py` | `pages/Dashboard.jsx` |
| Student CRUD, search, grade filter | `routers/students.py` | `pages/Students.jsx` |
| Fee invoices, payments, 2-part challan PDF | `routers/fees.py`, `services/pdf_service.py` | `pages/Fees.jsx` |
| Marks entry, grades, report card PDF | `routers/results.py`, `services/pdf_service.py` | `pages/Results.jsx` |
| AI at-risk prediction with SHAP reasons, interventions, risk simulator | `routers/ai.py`, `services/ai_service.py` | `pages/AtRisk.jsx` |
| Chatbot: live data tools + policy RAG, with memory | `routers/chatbot.py`, `services/school_assistant_service.py`, `data_assistant_service.py`, `rag_service.py` | `pages/Chatbot.jsx` |
| AI admissions (optional, CrewAI) | `routers/admissions_crew.py`, `school_crew/` | `pages/Admissions.jsx` |

## Repo map

```
backend/            FastAPI app (run commands from here)
  main.py           app, CORS, router registration, lifespan (creates tables + admin user)
  config.py         .env loading, SCHOOL_*, auth settings, GRADES/SECTIONS/SUBJECTS, fee amounts
  database.py       engine, get_session, create_db_and_tables
  seed_data.py      seeds 50 students, invoices, results (skips if 50+ students exist)
  modal_app.py      Modal deployment (installs from the requirements files)
  requirements*.txt exact versions: runtime, optional admissions, dev/test
  conftest.py       test isolation: temporary database, no real keys
  models/           SQLModel tables: user, student, fee, result
  routers/          auth, students, fees, results, dashboard, ai, chatbot, admissions_crew
  school_crew/      CrewAI agents for admissions (imported only when used)
  services/         ai_service, pdf_service, rag_service, data_assistant_service, school_assistant_service,
                    fee_ledger (all fee calculations), admin_setup, login_throttle, risk_features
  migrate_db.py     reports on and upgrades an existing database, with a backup
  knowledge_base/   5 policy .txt files used by the RAG chatbot
  test_*.py         pytest tests; test_modal.py is a manual script, not collected
frontend/           React app (run commands from here)
  src/api/client.js axios instance + the `api` object (every endpoint)
  src/pages/        one file per route
  src/components/   Layout, DataTable, StatCard, ErrorBoundary
  src/lib/session.js, session.test.js
start_all.bat, run_backend*.bat, run_frontend*.bat   Windows launchers
```

## Commands

Run backend commands from `backend/`, because modules import each other by top-level name (`from config import ...`).

```bash
python -m pip install -r requirements-dev.txt   # add requirements-admissions.txt for AI admissions
python seed_data.py                      # safe to re-run: skips if 50+ students exist
python -m uvicorn main:app --reload      # http://localhost:8000, Swagger at /docs
python check_imports.py                  # diagnose missing or broken dependencies
```

Run frontend commands from `frontend/`:

```bash
npm install
npm run dev      # http://localhost:5173
npm run build
```

`start_all.bat` in the repo root opens both servers on Windows. No linter or formatter is configured for either side. Local runs need `APP_ENV=development` in `backend/.env` (see `.env.example`). With no admin account and no `ADMIN_PASSWORD`, development prints a one-time password to the console.

### Tests

```bash
python -m pytest                 # from backend/; all backend tests
python -m pytest test_backend.py # from backend/; one file
npm test                         # from frontend/
```

`backend/conftest.py` gives every test run a temporary seeded database and blank keys, so tests cannot touch `school.db` or call Groq. Running a test file directly (`python test_backend.py`) also goes through pytest and stays isolated.

## Environment variables

Backend, set in `backend/.env` (template: `.env.example`) or the Modal secret `educore-secrets`:

| Variable | Purpose |
|----------|---------|
| `SCHOOL_NAME`, `SCHOOL_TAGLINE`, `SCHOOL_ADDRESS`, `SCHOOL_PHONE`, `SCHOOL_EMAIL`, `CURRENCY` | Branding used in PDFs and the chatbot |
| `APP_ENV` | `development` for local work. Unset or anything else means production safeguards |
| `SECRET_KEY` | JWT signing key (HS256, 8h tokens). Production refuses to start if it is missing, short, or a key once published in this repo |
| `ADMIN_PASSWORD` | Sets the admin password when the account is created or still on a known default. Required then in production. Does not overwrite a password changed in the app |
| `ADMIN_PASSWORD_RESET` | `true` forces `ADMIN_PASSWORD` to apply, for a forgotten password. Remove afterwards |
| `GROQ_API_KEY`, `GROQ_MODEL` | Optional. Without a key, everything falls back to local logic |
| `MODAL_PROXY_TOKEN_ID`, `MODAL_PROXY_TOKEN_SECRET` | Optional. AI admissions only; without them that feature returns 503 |
| `DATABASE_URL` | Defaults to local SQLite; Modal sets `sqlite:////data/school.db` |
| `FRONTEND_URL` | Allowed CORS origins, exact and comma-separated. Required for browsers in production |

Frontend: `VITE_API_URL` (no trailing slash). `frontend/.env.production` holds the production value.

`backend/.env` is for secrets and must never be committed or pasted into docs. Credentials are read from the environment only, never written in code; `test_environment.py` fails if a known credential pattern appears in project files.

## Architecture

### Backend layout

`main.py` wires up the routers in `routers/`, which call `services/` and use the SQLModel tables in `models/`. Startup creates missing tables and runs `services/admin_setup.py:ensure_admin_account`, which also refuses to run production on a known default password.

- **Schema changes.** `SQLModel.metadata.create_all` adds new tables but never alters existing ones. Changes to existing tables go through `migrate_db.py`, which backs up first, reports problems, and only changes anything with `--apply`. Keep changes additive, and never delete a database to apply one.
- **Config:** `config.py` loads `.env` and also holds the fixed school structure (`GRADES`, `SECTIONS`, `SUBJECTS`) and fee amounts.
- **Dependencies:** every package is pinned to an exact version that works on Python 3.13 (local) and resolves for 3.11 (Modal). `modal_app.py` installs from the requirements files, so there is one list. Check any change with a clean install and `python -m pytest`.
- **Optional AI admissions:** CrewAI is imported inside the request handler. The app must start and work without it, returning 503 for that feature only.

### Data model

- `students`: name, unique `roll_number`, grade, section, guardian_name, phone, dob (string).
- `invoices`: student_id, amount, month (`November 2026`), due_date (`10-Nov-2026`), unique `challan_number`, `status` (`pending`, `partial`, or `paid`), one per student per month. `payments`: invoice_id, amount_paid, `payment_mode` (cash/bank/online). Payment rows are the source of truth for money received. `fee_structures` and `academic_years` exist but are barely used.
- `results`: student_id, subject, marks_obtained, total_marks, exam_type. Grades come from `calculate_grade` in `models/result.py`: A+ at 90%, A 80, B 70, C 60, D 50, otherwise F.
- `users`: username, bcrypt password hash (older SHA-256 hashes upgrade at next login), role.
- `revoked_tokens`: tokens ended by logout, kept until they expire.

### API surface

All routes require auth except `/auth/login`, `/auth/logout`, and the root status route.

| Prefix | Routes |
|--------|--------|
| `/auth` | `POST /login`, `POST /logout`, `POST /change-password`, `GET /me` |
| `/students` | `GET` (search, grade), `POST`, `GET/PUT/DELETE /{id}` |
| `/fees` | `GET` (status, grade, student_id), `GET /summary`, `POST /generate`, `POST /{id}/pay`, `GET /{id}/payments`, `GET /{id}/pdf` |
| `/results` | `GET /{student_id}`, `POST` (upsert marks), `GET /{student_id}/report-card/pdf` |
| `/dashboard` | `GET /stats` |
| `/ai` | `GET /at-risk` (grade, risk_level), `GET /at-risk/{student_id}` |
| `/chatbot` | `POST /ask`, `GET/DELETE /history/{session_id}`, `GET /topics` |

### Auth

`routers/auth.py:get_current_user` accepts a bearer token only; there are no auth cookies. The frontend stores the token in `localStorage` and attaches it in an axios interceptor in `src/api/client.js`. Protected routes declare `_user = Depends(get_current_user)`.

Tokens carry a `jti`, which logout adds to `revoked_tokens`, and a fingerprint of the password hash, so changing a password ends all older sessions. Failed logins are limited per username and per address by `services/login_throttle.py`. That throttle is in memory, which relies on the single Modal container.

The PDF routes use the same dependency. The frontend fetches them as blobs through `src/lib/pdf.js` and `components/PdfButton.jsx`, because plain links cannot send the token.

### Chatbot routing

`POST /chatbot/ask` goes through `SchoolAssistantService.answer` (`services/school_assistant_service.py`), which uses keyword heuristics (`_is_data_question`) to choose one of three paths. The path is returned in the response's `mode` field.

1. **`groq_tool_calling`:** record questions when a Groq key is set. The LLM may only call the read-only tools defined in `SchoolDataAssistant` (`services/data_assistant_service.py`: `tool_definitions` and `execute_tool`). `_build_structured_data` passes tool results to the UI as tables.
2. **`school_data`:** the local fallback when there is no key or Groq fails. `_answer_with_local_tools` calls the same data methods based on keyword matching.
3. **`policy_rag`:** everything else goes to `PolicyRAGService` (`services/rag_service.py`), which searches `knowledge_base/*.txt`. Retrieval falls back from FAISS + sentence-transformers to TF-IDF, and answers can be generated locally without Groq.

Adding a data capability means changing the tool definition, `execute_tool`, the local fallback, and the structured-data mapping. All of this must work without a `GROQ_API_KEY`. The tools are read-only by design; do not add write tools or raw SQL access.

Conversation memory is an in-process dict in `routers/chatbot.py`, capped at 40 messages per session. It is lost on restart and isn't shared between Modal containers.

Single-student questions ("fee dues for Ahmed Khan") must not hit the bulk pending-list path; `_is_pending_list_question` is guarded by `_student_identifier`.

### At-risk model

`AtRiskModelService` (`services/ai_service.py`) trains a Random Forest on synthetic data when the module is imported, which happens at server start because `main.py` imports it. There is no saved model file, and real school records are not training data. Features are `avg_marks_pct`, `fee_defaults`, `failing_subjects`, `grade_trend`. Categories: High above 70%, Medium 40-70%, Low below 40%.

`services/risk_features.py:compute_student_features` builds the features from live records (used by `routers/ai.py` and `routers/dashboard.py`), but `grade_trend` is a heuristic derived from current marks, not historical data. SHAP explains predictions when it can be loaded, with a feature-importance fallback otherwise.

### PDFs

`services/pdf_service.py` (ReportLab) builds a 2-part fee challan (Bank Copy and Student Copy) and an official report card (marks table, colored grades, summary, promotion status, remarks, signature lines).

### Frontend

All API calls go through the `api` object in `src/api/client.js`, which also handles the 401 redirect to `/login`. The base URL is `VITE_API_URL`, falling back to `localhost:8000` in dev and a hardcoded Modal URL in production builds. Pages live in `src/pages/` and are routed in `src/App.jsx` under the shared `Layout`. `ProtectedRoute` only checks that `educore_user` exists in `localStorage`; the backend enforces real access.

The chatbot page keeps its history, session id, and memory toggle in `localStorage` (`educore_chat_history`, `educore_chat_session_id`, `educore_chat_memory_enabled`). The Risk Simulator in `AtRisk.jsx` is a client-side formula, not a call to the real model.

CORS in `main.py` allows exact origins only: `FRONTEND_URL`, plus localhost:5173 and 5174 in development. In production, `/docs` and `/openapi.json` are off and security headers are added.

## Known gotchas

- Risk features for both the dashboard and the At-Risk page come from `services/risk_features.py:compute_student_features`. Change feature logic there only, so the two never drift apart.
- All fee money comes from `services/fee_ledger.py`, which the dashboard, Fees page, and chatbot share. Add fee calculations there only.
- Challan numbers are `CHN-` plus a random number, checked against existing invoices (`_unique_challan_number` in `routers/fees.py`).
- The challan PDF splits the invoice amount into tuition (capped at `TUITION_FEE_MONTHLY` from `config.py`) and the remainder as exam fee.
- Deleting a student also removes their results, invoices, and the invoices' payments.
- Chatbot memory and the at-risk model are per process, so they behave differently across Modal containers.
- `GROQ_MODEL` differs between `.env.example` and the README; trust `.env.example` and `config.py`.
- Seed data is demo data (for example Ahmed Khan #045 and Bilal Tariq #012 are used in demos and tests). Don't change names the tests depend on.

## Deployment

Backend: set `SECRET_KEY`, `ADMIN_PASSWORD`, and `FRONTEND_URL` in the Modal secret `educore-secrets`, then `modal deploy modal_app.py`. It runs one container (`max_containers=1`) because SQLite on a Volume needs a single writer. Frontend: import the repo into Vercel with root directory `frontend` and set `VITE_API_URL` to the Modal URL. Full steps are in `DEPLOYMENT_GUIDE.md`.

## Code graph

This repo may have a code-review-graph knowledge graph (see `AGENTS.md` when present). Use its MCP tools, when available, to narrow scope before reading source. If the graph and the source disagree, trust the source.
