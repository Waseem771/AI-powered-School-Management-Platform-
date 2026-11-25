from sqlmodel import Session, SQLModel, create_engine, select

from add_admin_account import add_admin
from models.user import User, hash_password, verify_password


def _users(path):
    engine = create_engine(f"sqlite:///{path}")
    with Session(engine) as session:
        users = session.exec(select(User).order_by(User.id)).all()
    engine.dispose()
    return users


def test_reports_then_adds_once_with_a_backup(tmp_path):
    database = tmp_path / "school.db"
    engine = create_engine(f"sqlite:///{database}")
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    password_hash = hash_password("a-test-only-password")

    assert add_admin(database, "admin1") == 0
    assert _users(database) == []

    assert add_admin(database, "admin1", password_hash) == 0
    (user,) = _users(database)
    assert (user.username, user.role, user.is_active) == ("admin1", "admin", True)
    assert verify_password("a-test-only-password", user.password_hash)
    assert (tmp_path / "school.db.backup-before-admin-admin1").exists()

    assert add_admin(database, "ADMIN1", password_hash) == 1
    assert len(_users(database)) == 1
