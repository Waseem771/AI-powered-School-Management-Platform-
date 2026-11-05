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
        ignore=["venv_312", "**/__pycache__", "**/*.pyc", "school.db", "*.backup-*", ".env"],
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

    from migrate_db import main as migrate

    exit_code = migrate(["/data/school.db", "--apply"] if apply else ["/data/school.db"])
    if apply:
        data_volume.commit()
    if exit_code != 0:
        raise SystemExit(exit_code)
