"""The online demo can never reach production's storage, secret or database."""
from pathlib import Path

SOURCE = (Path(__file__).parent / "modal_demo_app.py").read_text(encoding="utf-8")


def test_the_demo_app_uses_only_its_own_resources():
    assert 'modal.App("educore-demo")' in SOURCE
    assert 'Volume.from_name("educore-demo-data")' in SOURCE
    assert 'Secret.from_name("educore-demo-secrets")' in SOURCE
    for production in ('"educore-data"', '"educore-secrets"', '"educore-backups"', "school.db", "educore-ai-school-platform"):
        assert production not in SOURCE


def test_the_demo_app_forces_its_database_and_demo_mode():
    assert 'os.environ["DATABASE_URL"] = f"sqlite:///{DEMO_DATABASE}"' in SOURCE
    assert 'DEMO_DATABASE = "/data/demo.db"' in SOURCE
    assert 'os.environ["DEMO_MODE"] = "true"' in SOURCE
    assert 'os.environ["DEMO_FULL_ACCESS"] = "true"' in SOURCE
    # Production must never turn full access on.
    assert "DEMO_FULL_ACCESS" not in (Path(__file__).parent / "modal_app.py").read_text(encoding="utf-8")
