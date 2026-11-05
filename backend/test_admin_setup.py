"""The admin account is created safely, and production never runs on a known default password."""
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from models.user import User, hash_password, verify_password
from services.admin_setup import ensure_admin_account

STRONG = "a-strong-admin-password"
OLD_DEFAULT = "admin" + "123"


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def _add_admin(session, password):
    session.add(User(username="admin", password_hash=hash_password(password), role="admin"))
    session.commit()


def _admin(session):
    return session.exec(select(User).where(User.username == "admin")).first()


def test_production_refuses_to_start_with_no_admin_and_no_password(session):
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        ensure_admin_account(session, is_production=True, admin_password="")


def test_production_creates_admin_from_the_configured_password(session):
    ensure_admin_account(session, is_production=True, admin_password=STRONG)

    assert verify_password(STRONG, _admin(session).password_hash)
    assert _admin(session).password_hash.startswith("$2")


def test_production_refuses_to_keep_the_old_default_password(session):
    _add_admin(session, OLD_DEFAULT)

    with pytest.raises(RuntimeError, match="default password"):
        ensure_admin_account(session, is_production=True, admin_password="")


def test_production_replaces_the_old_default_with_the_configured_password(session):
    _add_admin(session, OLD_DEFAULT)

    ensure_admin_account(session, is_production=True, admin_password=STRONG)

    assert verify_password(STRONG, _admin(session).password_hash)
    assert not verify_password(OLD_DEFAULT, _admin(session).password_hash)


@pytest.mark.parametrize("weak", [OLD_DEFAULT, "short"])
def test_production_refuses_a_weak_configured_password(session, weak):
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        ensure_admin_account(session, is_production=True, admin_password=weak)


def test_configured_password_does_not_overwrite_one_changed_in_the_app(session):
    _add_admin(session, "changed-in-the-app-1")

    ensure_admin_account(session, is_production=True, admin_password=STRONG)

    assert verify_password("changed-in-the-app-1", _admin(session).password_hash)


def test_forced_reset_applies_the_configured_password(session):
    _add_admin(session, "forgotten-password-1")

    ensure_admin_account(session, is_production=True, admin_password=STRONG, force_reset=True)

    assert verify_password(STRONG, _admin(session).password_hash)


def test_forced_reset_without_a_password_fails_clearly(session):
    _add_admin(session, "forgotten-password-1")

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        ensure_admin_account(session, is_production=True, admin_password="", force_reset=True)


def test_development_generates_a_one_time_password_and_shows_it_once(session, capsys):
    ensure_admin_account(session, is_production=False, admin_password="")

    output = capsys.readouterr().out
    generated = output.split("password:")[1].split()[0]
    assert verify_password(generated, _admin(session).password_hash)

    ensure_admin_account(session, is_production=False, admin_password="")
    assert "password:" not in capsys.readouterr().out


def test_development_leaves_an_existing_admin_alone(session):
    _add_admin(session, OLD_DEFAULT)

    ensure_admin_account(session, is_production=False, admin_password="")

    assert verify_password(OLD_DEFAULT, _admin(session).password_hash)


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
