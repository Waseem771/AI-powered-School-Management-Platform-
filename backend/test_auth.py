"""Login, tokens, logout, password changes and login throttling."""
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from config import ALGORITHM, SECRET_KEY
from database import engine
from main import app
from models.user import User, hash_password, needs_rehash, verify_password
from services.login_throttle import LoginThrottle

PUBLISHED_OLD_KEY = "educore_super_secret_jwt" + "_key_2026_al_noor"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _login(client, password, username="admin"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _set_stored_hash(new_hash):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "admin")).one()
        user.password_hash = new_hash
        session.add(user)
        session.commit()


def _stored_hash():
    with Session(engine) as session:
        return session.exec(select(User).where(User.username == "admin")).one().password_hash


# ── Password hashing ────────────────────────────────────────────────────────

def test_new_passwords_use_salted_bcrypt():
    first, second = hash_password("a-long-password"), hash_password("a-long-password")

    assert first.startswith("$2")
    assert first != second
    assert verify_password("a-long-password", first)
    assert not verify_password("wrong-password", first)
    assert not needs_rehash(first)


def test_old_sha256_hash_still_verifies_and_is_flagged_for_upgrade():
    legacy = hashlib.sha256("alnoor_salt_2026legacy-password".encode()).hexdigest()

    assert verify_password("legacy-password", legacy)
    assert not verify_password("other-password", legacy)
    assert needs_rehash(legacy)


def test_login_upgrades_an_old_hash_to_bcrypt(client, admin_password):
    original = _stored_hash()
    legacy = hashlib.sha256(f"alnoor_salt_2026{admin_password}".encode()).hexdigest()
    _set_stored_hash(legacy)
    try:
        response = _login(client, admin_password)

        assert response.status_code == 200
        assert _stored_hash().startswith("$2")
    finally:
        _set_stored_hash(original)


def test_verify_handles_a_corrupt_stored_hash_without_crashing():
    assert not verify_password("anything", "$2b$broken")
    assert not verify_password("x" * 200, hash_password("a-long-password"))


# ── Login ───────────────────────────────────────────────────────────────────

def test_login_returns_a_token_and_sets_no_cookie(client, admin_password):
    response = _login(client, admin_password)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert "set-cookie" not in response.headers


def test_wrong_password_and_unknown_user_get_the_same_answer(client):
    wrong = _login(client, "wrong-password")
    unknown = _login(client, "wrong-password", username="nobody")

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_very_long_password_is_rejected_cleanly(client):
    assert _login(client, "x" * 500).status_code == 422


# ── Tokens ──────────────────────────────────────────────────────────────────

def test_token_signed_with_the_published_old_key_is_rejected(client):
    forged = jwt.encode(
        {"sub": "admin", "role": "admin", "exp": datetime.now(timezone.utc) + timedelta(days=365)},
        PUBLISHED_OLD_KEY,
        algorithm=ALGORITHM,
    )

    assert client.get("/students", headers=_bearer(forged)).status_code == 401


def test_correctly_signed_token_without_session_claims_is_rejected(client):
    bare = jwt.encode(
        {"sub": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, SECRET_KEY, algorithm=ALGORITHM
    )

    assert client.get("/auth/me", headers=_bearer(bare)).status_code == 401


def test_expired_token_is_rejected(client, admin_password):
    token = _login(client, admin_password).json()["access_token"]
    claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    claims["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)

    expired = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)

    assert client.get("/auth/me", headers=_bearer(expired)).status_code == 401


def test_a_token_in_a_cookie_is_not_accepted(client, admin_password):
    token = _login(client, admin_password).json()["access_token"]

    response = client.get("/auth/me", cookies={"educore_access_token": token})

    assert response.status_code == 401


def test_pdf_routes_work_with_a_bearer_token_and_reject_without(client, admin_password):
    token = _login(client, admin_password).json()["access_token"]
    student_id = client.get("/students", headers=_bearer(token)).json()[0]["id"]
    url = f"/results/{student_id}/report-card/pdf"

    assert client.get(url).status_code == 401
    with_token = client.get(url, headers=_bearer(token))
    assert with_token.status_code == 200
    assert with_token.headers["content-type"] == "application/pdf"


# ── Logout ──────────────────────────────────────────────────────────────────

def test_logout_revokes_only_that_token(client, admin_password):
    first = _login(client, admin_password).json()["access_token"]
    second = _login(client, admin_password).json()["access_token"]

    assert client.post("/auth/logout", headers=_bearer(first)).status_code == 204

    assert client.get("/auth/me", headers=_bearer(first)).status_code == 401
    assert client.get("/auth/me", headers=_bearer(second)).status_code == 200


def test_logout_without_a_token_is_harmless(client):
    assert client.post("/auth/logout").status_code == 204


# ── Changing password ───────────────────────────────────────────────────────

def _change(client, token, current, new):
    return client.post(
        "/auth/change-password",
        headers=_bearer(token),
        json={"current_password": current, "new_password": new},
    )


def test_change_password_needs_login(client):
    response = client.post("/auth/change-password", json={"current_password": "a", "new_password": "b"})

    assert response.status_code == 401


def test_change_password_rejects_wrong_current_password(client, admin_password):
    token = _login(client, admin_password).json()["access_token"]

    assert _change(client, token, "wrong-password", "brand-new-password-1").status_code == 400


@pytest.mark.parametrize(
    "weak",
    ["short", "admin123", "password123", "x" * 73],
    ids=["too-short", "known-default", "common", "too-long"],
)
def test_change_password_rejects_weak_passwords(client, admin_password, weak):
    token = _login(client, admin_password).json()["access_token"]

    assert _change(client, token, admin_password, weak).status_code == 422


def test_change_password_rejects_reusing_the_current_one(client, admin_password):
    token = _login(client, admin_password).json()["access_token"]

    assert _change(client, token, admin_password, admin_password).status_code == 422


def test_change_password_ends_old_sessions_and_keeps_this_one(client, admin_password):
    original = _stored_hash()
    old_token = _login(client, admin_password).json()["access_token"]
    try:
        response = _change(client, old_token, admin_password, "brand-new-password-1")

        assert response.status_code == 200
        assert client.get("/auth/me", headers=_bearer(old_token)).status_code == 401
        assert client.get("/auth/me", headers=_bearer(response.json()["access_token"])).status_code == 200
        assert _login(client, admin_password).status_code == 401
        assert _login(client, "brand-new-password-1").status_code == 200
    finally:
        _set_stored_hash(original)


# ── Throttling ──────────────────────────────────────────────────────────────

def test_repeated_failures_lock_the_account_even_for_the_right_password(client, admin_password):
    statuses = [_login(client, f"wrong-{attempt}").status_code for attempt in range(10)]
    locked = _login(client, admin_password)

    assert set(statuses) == {401}
    assert locked.status_code == 429
    assert int(locked.headers["retry-after"]) > 0


def test_successful_login_clears_earlier_failures(client, admin_password):
    for attempt in range(9):
        _login(client, f"wrong-{attempt}")

    assert _login(client, admin_password).status_code == 200
    assert _login(client, "wrong-again").status_code == 401


def test_username_lockout_ignores_case(client):
    for attempt in range(10):
        _login(client, f"wrong-{attempt}", username="ADMIN")

    assert _login(client, "anything", username="admin").status_code == 429


def test_throttle_releases_after_the_window():
    now = [1000.0]
    throttle = LoginThrottle(max_failures=2, window_seconds=60, clock=lambda: now[0])

    throttle.record_failure("key")
    assert throttle.retry_after("key") == 0
    throttle.record_failure("key")
    assert 0 < throttle.retry_after("key") <= 60

    now[0] += 61
    assert throttle.retry_after("key") == 0


def test_throttle_forgets_old_keys_so_memory_stays_bounded():
    now = [1000.0]
    throttle = LoginThrottle(max_failures=2, window_seconds=60, clock=lambda: now[0])

    for index in range(1000):
        throttle.record_failure(f"key-{index}")
    now[0] += 61
    throttle.record_failure("fresh")

    assert throttle.tracked_keys() == 1


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
