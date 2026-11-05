"""Production settings. The app is started in a separate process, because config is read at import."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from config import allowed_cors_origins, resolve_secret_key

BACKEND_DIR = Path(__file__).resolve().parent
STRONG_KEY = "k" * 48
SITE = "https://school-demo.example.com"
PUBLISHED_OLD_KEY = "educore_super_secret_jwt" + "_key_2026_al_noor"

PROBE = """
import json
from fastapi.testclient import TestClient
from main import app

with TestClient(app, raise_server_exceptions=False) as client:
    root = client.get("/")
    allowed = client.options("/students", headers={"Origin": "%(site)s", "Access-Control-Request-Method": "GET"})
    vercel = client.options("/students", headers={"Origin": "https://attacker.vercel.app", "Access-Control-Request-Method": "GET"})
    local = client.options("/students", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    login = client.post("/auth/login", json={"username": "admin", "password": "a-strong-admin-password"})
    print("PROBE" + json.dumps({
        "docs": client.get("/docs").status_code,
        "redoc": client.get("/redoc").status_code,
        "openapi": client.get("/openapi.json").status_code,
        "root_body": root.json(),
        "headers": dict(root.headers),
        "cors_site": allowed.headers.get("access-control-allow-origin"),
        "cors_site_credentials": allowed.headers.get("access-control-allow-credentials"),
        "cors_vercel": vercel.headers.get("access-control-allow-origin"),
        "cors_local": local.headers.get("access-control-allow-origin"),
        "login": login.status_code,
    }))
"""


def _run(code, tmp_path, **overrides):
    env = {
        **os.environ,
        "APP_ENV": "production",
        "SECRET_KEY": STRONG_KEY,
        "ADMIN_PASSWORD": "a-strong-admin-password",
        "ADMIN_PASSWORD_RESET": "",
        "FRONTEND_URL": SITE,
        "DATABASE_URL": f"sqlite:///{(tmp_path / 'prod.db').as_posix()}",
        "GROQ_API_KEY": "",
        **overrides,
    }
    return subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=180
    )


@pytest.fixture(scope="module")
def production(tmp_path_factory):
    result = _run(PROBE % {"site": SITE}, tmp_path_factory.mktemp("prod"))
    assert result.returncode == 0, result.stderr[-1500:]
    line = next(item for item in result.stdout.splitlines() if item.startswith("PROBE"))
    return json.loads(line[len("PROBE"):])


# ── Signing key ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_key", ["", "short-key", PUBLISHED_OLD_KEY], ids=["missing", "short", "published"])
def test_production_rejects_unsafe_signing_keys(bad_key):
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        resolve_secret_key(bad_key, is_production=True)


def test_production_accepts_a_strong_signing_key():
    assert resolve_secret_key(STRONG_KEY, is_production=True) == STRONG_KEY


@pytest.mark.parametrize("bad_key", ["", PUBLISHED_OLD_KEY], ids=["missing", "published"])
def test_development_swaps_unsafe_keys_for_a_random_one(bad_key):
    first, second = resolve_secret_key(bad_key, False), resolve_secret_key(bad_key, False)

    assert first != bad_key and first != second
    assert len(first) >= 32


def test_app_refuses_to_start_without_a_signing_key_and_does_not_print_values(tmp_path):
    result = _run("import config", tmp_path, SECRET_KEY="")

    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr


def test_app_treats_a_missing_app_env_as_production(tmp_path):
    env_overrides = {"SECRET_KEY": "", "APP_ENV": ""}

    result = _run("import config", tmp_path, **env_overrides)

    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr


# ── CORS ────────────────────────────────────────────────────────────────────

def test_production_allows_only_the_configured_origins():
    origins = allowed_cors_origins(True, f"{SITE}/, https://www.example.com")

    assert origins == [SITE, "https://www.example.com"]


def test_development_also_allows_local_ports():
    assert "http://localhost:5173" in allowed_cors_origins(False, "")


def test_running_production_cors(production):
    assert production["cors_site"] == SITE
    assert production["cors_vercel"] is None
    assert production["cors_local"] is None
    assert production["cors_site_credentials"] is None


# ── Running in production ───────────────────────────────────────────────────

def test_api_docs_are_hidden(production):
    assert production["docs"] == production["redoc"] == production["openapi"] == 404
    assert "docs_url" not in production["root_body"]


def test_security_headers_are_sent(production):
    headers = production["headers"]

    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert "max-age" in headers["strict-transport-security"]
    assert "default-src 'none'" in headers["content-security-policy"]
    assert headers["cache-control"] == "no-store"


def test_configured_admin_can_log_in(production):
    assert production["login"] == 200


def test_startup_refuses_a_database_still_on_the_old_default_password(tmp_path):
    seed_old_default = (
        "from sqlmodel import Session\n"
        "from database import create_db_and_tables, engine\n"
        "from models.user import User\n"
        "import hashlib\n"
        "create_db_and_tables()\n"
        "legacy = hashlib.sha256(('alnoor_salt_2026' + 'admin' + '123').encode()).hexdigest()\n"
        "session = Session(engine); session.add(User(username='admin', password_hash=legacy)); session.commit()\n"
    )
    assert _run(seed_old_default, tmp_path).returncode == 0

    start = "from fastapi.testclient import TestClient\nfrom main import app\nTestClient(app).__enter__()\n"
    result = _run(start, tmp_path, ADMIN_PASSWORD="")

    assert result.returncode != 0
    assert "default password" in result.stderr


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
