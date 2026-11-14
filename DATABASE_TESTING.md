# Database Backup — Testing Summary (Phase 1a / 1b)

Covers the work done against `EDUCORE_AI_PHASE_1_DATABASE_PROTECTION_PLAN.md` so far: the shared
backup helper (Phase 1a) and the scheduled-backup algorithm plus its (undeployed) Modal wiring
(Phase 1b). Nothing below has touched a real Modal resource, deployed anything, or activated any
schedule — both phases were explicitly approved as code-and-local-tests only.

## Scope approved vs. done

| Stage | Work | Status |
|---|---|---|
| 1a | Shared backup helper + temporary-database tests | Done, approved |
| 1b | Scheduled function + new backup Volume (code only, no real resource) | Done, approved as code+tests only |
| 1c | Deploy and observe the backup job on Modal | Not started — needs separate approval |
| 1d | Isolated restore drill | Not started — needs separate approval, after 1c |

## Files

| File | Phase | What it is |
|---|---|---|
| `backend/services/backup_service.py` | 1a | `create_consistent_backup`, `verify_backup`, `record_counts`, `create_verified_backup`, `select_files_to_prune`. Built on SQLite's Online Backup API; source always opened `mode=ro`. |
| `backend/test_backup_service.py` | 1a | 17 tests, including the read-only-cannot-write proof and the failed-backup-cannot-be-retained proof the owner asked to see before anything else. |
| `backend/migrate_db.py` | 1a | Refactored to call `backup_service.create_consistent_backup` instead of its own inline copy. Behavior unchanged — its own 14 tests pass unmodified. |
| `backend/services/backup_job.py` | 1b | `run_daily_backup_job`: one verified daily backup, then weekly (Monday)/monthly (1st) promotion, then per-tier retention (14 daily / 8 weekly / 12 monthly). Pure `Path`-based, no Modal import. |
| `backend/test_backup_job.py` | 1b | 11 tests: ordinary day, weekly promotion, monthly promotion, both at once, missing-source failure, a failed run never touching an existing good backup, retention caps per tier, newest-never-pruned, and a UTC-vs-Asia/Karachi timezone edge case. |
| `backend/modal_app.py` | 1b | Added `backup_volume = modal.Volume.from_name("educore-backups", create_if_missing=True)` and `run_scheduled_backup` (`/data` mounted **read-only**, `/backups` mounted, `schedule=modal.Cron("0 2 * * *", timezone="Asia/Karachi")`). Deployed on 2026-11-13: the Volume exists, and daily backups were seen on 2026-11-13 20:32 and 2026-11-14 02:00 (Asia/Karachi). |
| `backend/CLAUDE.md`, `CLAUDE.md` | 1a/1b | Repo-map and layout notes updated to describe the above. |

## Key design points, carried from the approved plan

- **Read-only source, proved not assumed**: the source connection is opened through SQLite's
  `mode=ro` URI flag; `test_backup_service.py` reproduces the OS-level write refusal directly
  rather than trusting the module's own discipline.
- **A failed/incomplete backup can never trigger retention deletion**: `create_verified_backup`
  deletes any partial/invalid file before returning `ok=False`, and `run_daily_backup_job`
  returns before any promotion or pruning runs on failure — proved end-to-end in both test files.
- **Connection-leak bug found and fixed during 1a**: an early version used
  `with sqlite3.connect(...) as conn:` for read-only connections, which only commits/rolls back —
  it does not close the connection (confirmed against `sqlite3.Connection.__exit__`'s own
  docstring). Caught by the test suite itself (`PermissionError` on cleanup), fixed by opening
  plain connections and closing them in `finally`. Relevant beyond this machine: Modal's own docs
  say `Volume.reload()` fails on open files, so this exact leak would have broken the real
  scheduled job.
- **Volume concurrency**: per plan §6, safety against `fastapi_app()` comes from three stacked,
  independently-verified guarantees — Modal's per-container mount isolation, the read-only mount
  flag (`with_mount_options(read_only=True)`), and the SQLite Online Backup API — not from the
  Online Backup API alone, and not from `max_containers=1` (verified to apply only to the
  function it's set on, not Volume-wide).
- **Timezone handling**: `datetime.now(ZoneInfo("Asia/Karachi"))` computed once per run and used
  for every date decision (stamp, weekly/monthly triggers), never a bare/naive `datetime.now()`.
  Tested directly with a UTC instant that is already Monday in Karachi.

## Test results

```
backend/test_backup_service.py   17 passed
backend/test_backup_job.py       11 passed
backend/test_migrate_db.py       14 passed   (unchanged, refactor only)

Full suite (python -m pytest -q):
  before any Phase 1 work:  468 passed, 17 failed, 4 errors
  after Phase 1a:           485 passed, 17 failed, 4 errors   (+17 = new backup_service tests)
  after Phase 1b:           496 passed, 17 failed, 4 errors   (+11 = new backup_job tests)
```

Zero regressions across both phases — the failing/error count never moved.

## The pre-existing 17 failed + 4 errors — not part of this work

All 21 trace to one cause, unrelated to backups: `from sklearn.ensemble import
RandomForestClassifier` fails on this machine with `DLL load failed while importing _criterion:
An Application Control policy has blocked this file`, which sets `ai_service.ML_AVAILABLE =
False`. Every test needing a real risk score or a SHAP explanation then fails
(`test_risk.py` — 11 failed + 4 errors, `test_demo_seed.py` — 5 failed,
`test_chatbot_questions.py` — 1 failed).

**Attempted fix, not just diagnosis**: installed scikit-learn 1.6.1 and 1.7.2 (binary wheels, in
an isolated scratch directory, not the real environment) to test whether a different build
dodges the block, the same way this project's `uharfbuzz` pin (0.50.2, after 0.57.0 was blocked)
did. Both still hit the identical Application Control error — this is not one flagged release,
it is this machine's policy blocking scikit-learn's compiled extension itself. Fixing it means
changing a Windows Application Control allow-list, which is a security-policy decision for the
machine's owner/admin, not something to change unilaterally.

**Why it doesn't matter for production**: Modal's containers run Debian Linux, not Windows, so
this block does not exist there. `EDUCORE_AI_SECOND_LEVEL_VERIFICATION.md` already confirmed the
live `/ai/at-risk` endpoint works against production. This is a local-dev-only gap.

## Confirmed untouched throughout 1a and 1b

No Modal resource created, no `modal deploy`, no `modal run`, no Cron activated, no production
database or secrets read or changed, no Vercel deployment.

## Next

1c (deploy and observe the backup job on Modal) and 1d (isolated restore drill) remain separate,
not-yet-approved steps per the owner's staged plan.
