"""
Modal deployment definition for EduCore AI Backend (FastAPI).

Deployment Quickstart:
----------------------
1. Install modal:
       pip install modal

2. Authenticate modal account:
       modal setup

3. Create your secret on the Modal dashboard. See DEPLOYMENT_GUIDE.md for each value:
       SECRET_KEY, ADMIN_PASSWORD, FRONTEND_URL, and optionally GROQ_API_KEY,
       MODAL_PROXY_TOKEN_ID, MODAL_PROXY_TOKEN_SECRET

4. Seed the database on the Modal persistent volume:
       modal run modal_app.py::seed_database_volume

5. Deploy the backend:
       modal deploy modal_app.py
"""

import os
from pathlib import Path
import modal

# 1. Define the Modal App
app = modal.App("educore-ai-school-platform")

# 2. Persistent volume for SQLite database (/data/school.db)
data_volume = modal.Volume.from_name("educore-data", create_if_missing=True)

# 3. Define the container image. Versions come only from the requirements files.
backend_dir = Path(__file__).parent
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements(str(backend_dir / "requirements.txt"))
    .pip_install_from_requirements(str(backend_dir / "requirements-admissions.txt"))
    .add_local_dir(
        Path(__file__).parent, 
        remote_path="/root/backend", 
        ignore=["venv_312", "**/__pycache__", "**/*.pyc", "school.db", "local_dev.db", "demo.db", "*.backup-*", ".env", "local_dev_credentials.env"],
        copy=True
    )
)


@app.function(
    image=image,
    volumes={"/data": data_volume},
    secrets=[modal.Secret.from_name("educore-secrets")],
    timeout=300,
    # SQLite on a Volume is safe with one writer only, and the login throttle lives in memory.
    max_containers=1,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def fastapi_app():
    """Serverless ASGI entrypoint for FastAPI on Modal."""
    import sys
    sys.path.insert(0, "/root/backend")
    os.chdir("/root/backend")

    # Use the persistent volume for SQLite if not using an external PostgreSQL URL
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "sqlite:////data/school.db"

    from main import app as web_app
    return web_app


@app.function(
    image=image,
    volumes={"/data": data_volume},
    secrets=[modal.Secret.from_name("educore-secrets")],
    timeout=300,
)
def seed_database_volume():
    """Initializes and seeds 50 students into the Modal persistent volume."""
    import sys
    sys.path.insert(0, "/root/backend")
    os.chdir("/root/backend")

    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "sqlite:////data/school.db"

    from seed_data import seed_database
    seed_database()
    data_volume.commit()
    print("✅ Database successfully seeded into Modal Volume (/data/school.db)!")


@app.function(image=image, volumes={"/data": data_volume}, timeout=300)
def upgrade_database(apply: bool = False):
    """Reports on the volume's database; with --apply, backs it up and upgrades it. See DEPLOYMENT_GUIDE.md."""
    import sys
    sys.path.insert(0, "/root/backend")
    os.chdir("/root/backend")
    # This job has no access to the app's secrets, and needs none: it signs nothing and serves
    # nobody. Without this, loading the settings stops it for lacking a signing key.
    os.environ["APP_ENV"] = "development"

    from migrate_db import main as migrate

    exit_code = migrate(["/data/school.db", "--apply"] if apply else ["/data/school.db"])
    if apply:
        data_volume.commit()
    if exit_code != 0:
        raise SystemExit(exit_code)


@app.function(image=image, volumes={"/data": data_volume}, timeout=300)
def add_academic_session(label: str, apply: bool = False):
    """Adds a session (never as the current one). Reports only unless apply. See add_academic_session.py."""
    import sys
    sys.path.insert(0, "/root/backend")
    os.chdir("/root/backend")

    from add_academic_session import main as add_session

    code = add_session(["/data/school.db", label] + (["--apply"] if apply else []))
    if apply:
        data_volume.commit()
    if code != 0:
        raise SystemExit(code)


# Phase 1b (see EDUCORE_AI_PHASE_1_DATABASE_PROTECTION_PLAN.md section 7a.3): a dedicated,
# separate volume for backups. This is live: the educore-backups volume exists on Modal and the
# schedule below has been firing since 2026-11-13. Because it lives in this file, every
# `modal deploy modal_app.py` redeploys it along with the web app.
backup_volume = modal.Volume.from_name("educore-backups", create_if_missing=True)


@app.function(
    image=image,
    volumes={
        # Read-only: the backup job must never become a second writer to educore-data. See
        # plan section 6.4 -- this makes an accidental write fail at the OS level, not just by
        # convention.
        "/data": data_volume.with_mount_options(read_only=True),
        "/backups": backup_volume,
    },
    timeout=600,
    schedule=modal.Cron("0 2 * * *", timezone="Asia/Karachi"),
)
def run_scheduled_backup():
    """Daily verified backup of /data/school.db into educore-backups, with retention.

    Live since 2026-11-13 (see DEPLOYMENT_GUIDE.md, "Backups and restoring").
    The actual backup/retention algorithm is in services/backup_job.py, tested there against
    temporary directories -- this function only wires it to the real Modal mount points.
    """
    import sys
    sys.path.insert(0, "/root/backend")
    os.chdir("/root/backend")

    from pathlib import Path as _Path
    from services.backup_job import run_daily_backup_job

    # Defensive: pick up the latest committed state rather than trust a possibly-reused
    # container's view from an earlier mount. See plan section 6.1.
    data_volume.reload()
    result = run_daily_backup_job(_Path("/data/school.db"), _Path("/backups"))
    backup_volume.commit()
    if not result.ok:
        raise RuntimeError(f"scheduled backup failed: {result.reason}")
    print(f"backup ok: {result.daily_path} promoted={result.promoted} pruned={result.pruned}")
