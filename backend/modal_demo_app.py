"""The fictional demo school online: a Modal app of its own, never the production one.

It has its own app (educore-demo), storage (educore-demo-data) and secret (educore-demo-secrets), and
always opens /data/demo.db, a file built by seed_demo.py holding only made-up records. It never mounts
educore-data or reads educore-secrets, so nothing in it can reach the school's real records.

    python -m modal volume create educore-demo-data
    python -m modal volume put educore-demo-data <path to a built demo.db> demo.db
    python -m modal deploy modal_demo_app.py      # from a clean `git archive` export, as for production

There is no backup schedule here on purpose: the data is made up, and rebuilding it is the reset.
See DEPLOYMENT_GUIDE.md, "Showing the demo school online".
"""
import os
from pathlib import Path

import modal

app = modal.App("educore-demo")
# Not create_if_missing: a missing volume must fail the deploy, never start an empty demo.
demo_volume = modal.Volume.from_name("educore-demo-data")
DEMO_DATABASE = "/data/demo.db"

backend_dir = Path(__file__).parent
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements(str(backend_dir / "requirements.txt"))
    .pip_install_from_requirements(str(backend_dir / "requirements-admissions.txt"))
    .add_local_dir(
        backend_dir,
        remote_path="/root/backend",
        ignore=["venv_312", "**/__pycache__", "**/*.pyc", "*.db", "*.backup-*", "*.env", ".env", "dev_outbox"],
        copy=True,
    )
)


@app.function(
    image=image,
    volumes={"/data": demo_volume},
    secrets=[modal.Secret.from_name("educore-demo-secrets")],
    timeout=300,
    max_containers=1,  # SQLite on a Volume: one writer, as in production
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def fastapi_app():
    """The same FastAPI app as production, on the demo database only."""
    import sys
    sys.path.insert(0, "/root/backend")
    os.chdir("/root/backend")

    # Set here, not from the secret, so no setting can point the demo at another database.
    os.environ["DATABASE_URL"] = f"sqlite:///{DEMO_DATABASE}"
    os.environ["DEMO_MODE"] = "true"
    os.environ["DEMO_FULL_ACCESS"] = "true"  # the demo login manages this made-up school (routers/auth.py)
    if not Path(DEMO_DATABASE).is_file():
        raise RuntimeError(f"{DEMO_DATABASE} is missing. Upload a demo.db built by seed_demo.py first.")

    from main import app as web_app
    return web_app
