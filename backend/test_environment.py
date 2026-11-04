"""Guards for the safety net itself: isolation, pinned versions, and no committed credentials."""
import re
from pathlib import Path

from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

CREDENTIAL_PATTERN = re.compile(
    r"\b(?:wk-[A-Za-z0-9]{12,}|ws-[A-Za-z0-9]{12,}|gsk_[A-Za-z0-9]{12,}|hf_[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{12,})"
)
SCANNED_SUFFIXES = {".py", ".js", ".jsx", ".json", ".md", ".txt", ".bat", ".html", ".example", ".production"}
SKIPPED_DIRS = {"node_modules", "dist", "__pycache__", ".git", "venv", ".venv", "venv_312", ".code-review-graph"}


def _requirement_lines(path: Path) -> list[str]:
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith(("#", "-r"))]


def test_tests_use_a_temporary_database_not_school_db():
    from database import engine

    database_path = Path(make_url(str(engine.url)).database).resolve()

    assert database_path != (BACKEND_DIR / "school.db").resolve()
    assert BACKEND_DIR not in database_path.parents


def test_every_runtime_dependency_is_pinned_to_an_exact_version():
    for filename in ("requirements.txt", "requirements-admissions.txt", "requirements-dev.txt"):
        unpinned = [line for line in _requirement_lines(BACKEND_DIR / filename) if "==" not in line]
        assert unpinned == [], f"{filename} has unpinned packages: {unpinned}"


def test_modal_image_installs_from_requirements_files_not_its_own_list():
    modal_source = (BACKEND_DIR / "modal_app.py").read_text(encoding="utf-8")

    assert "pip_install_from_requirements" in modal_source
    assert '"fastapi' not in modal_source


def test_no_credentials_are_written_in_project_files():
    offenders = []
    for path in PROJECT_DIR.rglob("*"):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        if SKIPPED_DIRS.intersection(path.relative_to(PROJECT_DIR).parts):
            continue
        if CREDENTIAL_PATTERN.search(path.read_text(encoding="utf-8", errors="ignore")):
            offenders.append(str(path.relative_to(PROJECT_DIR)))

    assert offenders == []


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
