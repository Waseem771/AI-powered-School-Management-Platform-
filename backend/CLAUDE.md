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
- `routers/teachers.py`: teacher account management (admin only) and the teacher portal endpoint. Auth dependencies live in `routers/auth.py`: `get_authenticated_user` (any active account), `get_current_user` (staff; refuses portal-only roles such as teacher, so new routes are closed to teachers by default) and `require_roles(...)`. `test_teachers.py` audits every route in the OpenAPI schema for this.
- `routers/assignments.py`, `routers/attendance.py`, `services/attendance.py`, `models/attendance.py`: teacher-class assignments and daily attendance (see the root CLAUDE.md for the rules). Reports count recorded rows only. `test_attendance.py` covers them.
- `routers/parents.py`, `services/parent_portal.py`, `models/parent.py`: parent accounts (admin), result publishing (admin) and the parent's own portal. Every portal route starts from `linked_student`, so a child that is not linked is a 404 and never loaded. Marks are read through `published_marks`, so an unreleased exam cannot reach a parent. PDFs reuse the existing challan, receipt and report card functions after those checks. `services/password_reset.py` and `test_parent_password_reset.py` and `test_teacher_password_reset.py`: an administrator's reset of a parent or teacher password (`apply_admin_reset`: policy check, new hash, audit row in `password_reset_events`, forced change at next sign-in). `test_parents.py` audits every route in the OpenAPI schema, as `test_teachers.py` does.
- `services/self_service_reset.py`, `services/email_service.py`, `PasswordResetToken` in `models/user.py`, and the `/auth/forgot-password`, `/auth/reset-password[/check]` routes: a teacher or parent resets their own password from an emailed link (single use, 60 minutes, hashed in the database, link in the URL fragment). The answer to a request is always identical and takes the same time (no account or email enumeration): the route only queues the address, and the lookup, the new link and the email happen afterwards on one worker thread (`send_reset_link_if_eligible`; tests call `drain_background_work()`, which `conftest.py` also does around every test). A link is claimed with one conditional UPDATE, so it cannot be spent twice even by simultaneous submissions, and every password change (the emailed link, `/auth/change-password`, an administrator's reset) and every email change ends the account's unused links (`invalidate_tokens`). Limits are per email and per address (in memory, like the login throttle), and nothing logs a token, link or address. `test_email_service.py` runs the real SMTP path against a fake local server. `services/email_address.py` is the one rule for an address (exactly one plain ASCII mailbox: no commas, lists, display names, quotes, brackets, spaces or line breaks), used by account creation, email changes and the forgot-password request; `send_email` also refuses anything that is not one mailbox. `python check_registered_emails.py [db]` lists existing accounts whose address breaks the rule or is shared, read-only, changing nothing. Administrators are not eligible. Administrators change a teacher's or parent's email with `PUT /teachers|parents/{id}/email` (their own password required; `change_account_email` in `routers/teachers.py`). `test_self_service_reset.py` covers it; `conftest.py` sets `EMAIL_BACKEND=memory`.
- `config.py`: env loading, `GRADES`, `SECTIONS`, `SUBJECTS`, fee amounts, JWT settings.
- `database.py`: SQLite engine and `get_session` dependency.
- `models/`: `user.py`, `student.py` (Base/Create/Update/Read schemas), `fee.py` (Invoice, Payment, FeeStructure, AcademicYear), `result.py` (`calculate_grade`).
- `routers/`: one file per resource; every route except login uses `_user = Depends(get_current_user)`.
- `services/`: business logic; routers stay thin.
- `services/backup_service.py`: shared SQLite backup helper (`create_consistent_backup`, `verify_backup`, `record_counts`, `create_verified_backup`, `select_files_to_prune`), built on the Online Backup API. `migrate_db.py`'s pre-migration backup uses it.
- `services/backup_job.py`: the daily backup/promotion/retention algorithm (`run_daily_backup_job`) from `EDUCORE_AI_PHASE_1_DATABASE_PROTECTION_PLAN.md` section 7a.3, built on `backup_service.py`. Takes plain `Path`s, so it is tested entirely against temporary directories (`test_backup_job.py`) with no Modal involved. `modal_app.py`'s `run_scheduled_backup` wires it to the real `/data` (read-only) and `/backups` mounts, scheduled for 02:00 `Asia/Karachi` via `modal.Cron` and it is live: the `educore-backups` Volume exists and the schedule has been firing since 2026-11-13 (daily backups seen on 2026-11-13 20:32 and 2026-11-14 02:00). It is in the same file as the web app, so every `modal deploy modal_app.py` redeploys it too. Backup and restore steps are in `DEPLOYMENT_GUIDE.md`, "Backups and restoring".
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
