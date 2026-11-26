"""Adds the shared 'demo' login to the browser tests' throwaway database. Run from backend/."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from add_admin_account import add_admin  # noqa: E402
from models.user import hash_password  # noqa: E402

sys.exit(add_admin(Path(sys.argv[1]), "demo", hash_password(os.environ["DEMO_ADMIN_PASSWORD"]), demo=True))
