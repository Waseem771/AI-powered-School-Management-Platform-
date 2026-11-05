"""Test isolation. Runs before any test module, so config.py sees these values first.

Tests must never touch the real school.db, read real keys, or call external AI services.
"""
import os
import random
import tempfile
from pathlib import Path

import pytest

_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="educore-test-"))
TEST_DB_PATH = _TEST_DB_DIR / "test.db"
TEST_ADMIN_PASSWORD = "test-admin-password-1"

# load_dotenv() does not override variables that are already set.
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["GROQ_API_KEY"] = ""
os.environ["SECRET_KEY"] = "test-only-signing-key-not-used-outside-the-test-suite"
os.environ["ADMIN_PASSWORD"] = TEST_ADMIN_PASSWORD
os.environ["ADMIN_PASSWORD_RESET"] = ""
os.environ["FRONTEND_URL"] = ""

# Manual connectivity script, not a test: it calls a real endpoint when run.
collect_ignore = ["test_modal.py"]


@pytest.fixture(scope="session", autouse=True)
def seeded_test_database():
    """Create and seed a throwaway database shared by the end-to-end tests."""
    from database import engine
    from seed_data import seed_database

    # The seed draws random challan numbers; a fixed seed keeps them collision-free.
    random.seed(20261104)
    seed_database()
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_login_throttle():
    """Failed logins in one test must not lock out the next."""
    from routers.auth import address_throttle, login_throttle

    login_throttle.clear()
    address_throttle.clear()
    yield
    login_throttle.clear()
    address_throttle.clear()


@pytest.fixture()
def admin_password():
    return TEST_ADMIN_PASSWORD
