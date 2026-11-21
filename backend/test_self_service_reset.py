"""Self-service "forgot password" for teachers and parents, and the administrator's control of their email.

Synthetic accounts only, removed after each test. Emails are kept in memory (conftest sets EMAIL_BACKEND=memory),
so nothing is ever sent."""
import logging
import re
import threading
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import config
import routers.auth as auth_router
from database import engine
from main import app
from models.parent import ParentStudentLink
from models.student import Student
from models.user import PasswordResetEvent, PasswordResetToken, RevokedToken, User
from services import email_service
from services.self_service_reset import _now, clear_throttles, drain_background_work, send_reset_link_if_eligible

ORIGINAL = "original-password-for-tests-1"
CHOSEN = "freshly-chosen-password-7"
TEMPORARY = "temporary-by-admin-pw-3"
TEACHER_EMAIL = "sara.selfservice@example.test"
PARENT_EMAIL = "pa.selfservice@example.test"
GENERIC = "reset link is on its way"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _login(client, username, password):
    return client.post("/auth/login", json={"username": username, "password": password})


@pytest.fixture(autouse=True)
def clean_up():
    yield
    drain_background_work()
    with Session(engine) as session:
        for model in (PasswordResetToken, PasswordResetEvent, ParentStudentLink, RevokedToken):
            for row in session.exec(select(model)).all():
                session.delete(row)
        for user in session.exec(select(User).where(User.role.in_(["teacher", "parent", "registrar"]))).all():
            session.delete(user)
        admin = session.exec(select(User).where(User.username == "admin")).first()
        admin.email = None
        session.add(admin)
        session.commit()


@pytest.fixture()
def admin_token(client, admin_password):
    return _login(client, "admin", admin_password).json()["access_token"]


def _make_teacher(client, admin_token, username="sara.self", email=TEACHER_EMAIL):
    response = client.post("/teachers", headers=_bearer(admin_token), json={
        "username": username, "full_name": "Sara Self", "email": email, "password": ORIGINAL})
    assert response.status_code == 201, response.text
    return response.json()


def _make_parent(client, admin_token, username="pa.self", email=PARENT_EMAIL):
    with Session(engine) as session:
        student_id = session.exec(select(Student).where(Student.roll_number == "045")).one().id
    response = client.post("/parents", headers=_bearer(admin_token), json={
        "username": username, "full_name": "Pa Self", "email": email, "password": ORIGINAL,
        "student_ids": [student_id], "relationship": "Father"})
    assert response.status_code == 201, response.text
    return response.json()


def _ask(client, email):
    response = client.post("/auth/forgot-password", json={"email": email})
    drain_background_work()  # the lookup, the new link and the email all happen after the reply
    return response


def _token_from(message):
    found = re.search(r"/reset-password#token=([A-Za-z0-9_-]+)", message.body)
    assert found, "the email has no reset link"
    return found.group(1)


def _latest_token(to):
    return _token_from([m for m in email_service.outbox if m.to == to][-1])


# ── Requesting a link ───────────────────────────────────────────────────────

@pytest.mark.parametrize("make,email", [(_make_teacher, TEACHER_EMAIL), (_make_parent, PARENT_EMAIL)])
def test_a_registered_teacher_or_parent_gets_one_link_by_email_only(client, admin_token, make, email):
    make(client, admin_token)
    response = _ask(client, email)
    assert response.status_code == 202
    assert GENERIC in response.json()["message"]
    assert [m.to for m in email_service.outbox] == [email]
    token = _token_from(email_service.outbox[0])
    assert token not in response.text  # the link is never in an API response
    assert email_service.outbox[0].body.count("60 minutes") == 1
    assert "#token=" in email_service.outbox[0].body  # in the fragment, so it is not sent to servers or Referer


def test_the_email_is_matched_ignoring_case_and_spaces(client, admin_token):
    _make_teacher(client, admin_token)
    _ask(client, f"  {TEACHER_EMAIL.upper()} ")
    assert len(email_service.outbox) == 1


def test_only_a_hash_of_the_token_is_stored(client, admin_token):
    _make_teacher(client, admin_token)
    _ask(client, TEACHER_EMAIL)
    token = _latest_token(TEACHER_EMAIL)
    with Session(engine) as session:
        rows = session.exec(select(PasswordResetToken)).all()
    assert len(rows) == 1 and token not in rows[0].token_hash and len(rows[0].token_hash) == 64
    assert rows[0].expires_at - rows[0].created_at == timedelta(minutes=60)


def test_every_kind_of_unknown_address_gets_the_same_answer_and_no_email(client, admin_token):
    """No way to tell which addresses belong to accounts."""
    teacher = _make_teacher(client, admin_token)
    _make_parent(client, admin_token, email=None)
    _make_teacher(client, admin_token, username="dup.one", email="shared@example.test")
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
        admin.email = "admin.office@example.test"
        session.add(admin)
        session.commit()
    client.post(f"/teachers/{teacher['id']}/deactivate", headers=_bearer(admin_token))
    # A second account with the same email: the link would not say whose account it is.
    with Session(engine) as session:
        other = session.exec(select(User).where(User.username == "dup.one")).one()
        session.add(User(username="dup.two", password_hash=other.password_hash, role="parent", email="shared@example.test"))
        session.commit()

    answers = []
    for address in ["nobody@example.test", TEACHER_EMAIL, "admin.office@example.test", "shared@example.test"]:
        response = _ask(client, address)
        answers.append((response.status_code, response.json()))
    assert len(set(str(a) for a in answers)) == 1 and answers[0][0] == 202
    assert email_service.outbox == []
    with Session(engine) as session:
        assert session.exec(select(PasswordResetToken)).all() == []


def test_nothing_is_sent_when_no_email_delivery_is_configured(client, admin_token, monkeypatch):
    _make_teacher(client, admin_token)
    monkeypatch.setattr(config, "EMAIL_BACKEND", "")
    response = _ask(client, TEACHER_EMAIL)
    assert response.status_code == 202 and GENERIC in response.json()["message"]
    with Session(engine) as session:
        assert session.exec(select(PasswordResetToken)).all() == []


def test_a_new_request_replaces_the_earlier_link(client, admin_token):
    _make_teacher(client, admin_token)
    _ask(client, TEACHER_EMAIL)
    first = _latest_token(TEACHER_EMAIL)
    _ask(client, TEACHER_EMAIL)
    second = _latest_token(TEACHER_EMAIL)
    assert first != second
    assert client.post("/auth/reset-password/check", json={"token": first}).status_code == 400
    assert client.post("/auth/reset-password/check", json={"token": second}).status_code == 200


def test_the_development_file_backend_writes_an_eml_and_production_refuses_it(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EMAIL_BACKEND", "file")
    monkeypatch.setattr(config, "EMAIL_OUTBOX_DIR", tmp_path)
    assert email_service.send_email("someone@example.test", "Hello", "Body") is True
    files = list(tmp_path.glob("*.eml"))
    assert len(files) == 1 and "someone@example.test" not in files[0].name
    monkeypatch.setattr(config, "IS_PRODUCTION", True)
    assert email_service.email_enabled() is False
    assert email_service.send_email("someone@example.test", "Hello", "Body") is False
    assert len(list(tmp_path.glob("*.eml"))) == 1


# ── Using the link ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("make,username,email", [
    (_make_teacher, "sara.self", TEACHER_EMAIL), (_make_parent, "pa.self", PARENT_EMAIL)])
def test_choosing_a_new_password_works_once_and_ends_old_sessions(client, admin_token, make, username, email):
    make(client, admin_token)
    old_session = _login(client, username, ORIGINAL).json()["access_token"]
    _ask(client, email)
    token = _latest_token(email)

    response = client.post("/auth/reset-password", json={"token": token, "new_password": CHOSEN})
    assert response.status_code == 200
    assert CHOSEN not in response.text and token not in response.text
    assert client.get("/auth/me", headers=_bearer(old_session)).status_code == 401
    assert _login(client, username, ORIGINAL).status_code == 401
    assert _login(client, username, CHOSEN).status_code == 200
    # The link is spent, and the owner is told their password changed.
    assert client.post("/auth/reset-password", json={"token": token, "new_password": "another-password-88"}).status_code == 400
    assert _login(client, username, "another-password-88").status_code == 401
    assert "was changed" in email_service.outbox[-1].subject and "#token" not in email_service.outbox[-1].body


def test_the_existing_password_policy_applies_and_a_weak_choice_does_not_spend_the_link(client, admin_token):
    _make_teacher(client, admin_token)
    _ask(client, TEACHER_EMAIL)
    token = _latest_token(TEACHER_EMAIL)
    for weak, reason in [("short", "at least 10"), ("password123", "too common"), ("x" * 80, "at most 72")]:
        response = client.post("/auth/reset-password", json={"token": token, "new_password": weak})
        assert response.status_code == 422 and reason in response.json()["detail"]
    assert _login(client, "sara.self", ORIGINAL).status_code == 200
    assert client.post("/auth/reset-password", json={"token": token, "new_password": CHOSEN}).status_code == 200


def test_an_expired_link_is_refused(client, admin_token):
    _make_teacher(client, admin_token)
    _ask(client, TEACHER_EMAIL)
    token = _latest_token(TEACHER_EMAIL)
    with Session(engine) as session:
        row = session.exec(select(PasswordResetToken)).one()
        row.expires_at = _now() - timedelta(seconds=1)
        session.add(row)
        session.commit()
    assert client.post("/auth/reset-password/check", json={"token": token}).status_code == 400
    response = client.post("/auth/reset-password", json={"token": token, "new_password": CHOSEN})
    assert response.status_code == 400 and "not valid any more" in response.json()["detail"]
    assert _login(client, "sara.self", ORIGINAL).status_code == 200


def test_garbage_and_cross_account_tokens_get_one_generic_error(client, admin_token):
    _make_teacher(client, admin_token)
    for token in ["nonsense", "a" * 43, " "]:
        response = client.post("/auth/reset-password", json={"token": token, "new_password": CHOSEN})
        assert response.status_code == 400 and response.json()["detail"].startswith("This reset link is not valid")


def test_a_link_stops_working_if_the_account_is_deactivated_or_its_email_changes(client, admin_token, admin_password):
    teacher = _make_teacher(client, admin_token)
    _ask(client, TEACHER_EMAIL)
    token = _latest_token(TEACHER_EMAIL)
    client.post(f"/teachers/{teacher['id']}/deactivate", headers=_bearer(admin_token))
    assert client.post("/auth/reset-password/check", json={"token": token}).status_code == 400
    client.post(f"/teachers/{teacher['id']}/activate", headers=_bearer(admin_token))
    assert client.post("/auth/reset-password/check", json={"token": token}).status_code == 200

    changed = client.put(f"/teachers/{teacher['id']}/email", headers=_bearer(admin_token),
                         json={"email": "new.sara@example.test", "admin_password": admin_password})
    assert changed.status_code == 200
    assert client.post("/auth/reset-password/check", json={"token": token}).status_code == 400


def test_it_completes_a_forced_change_left_by_an_administrator_reset(client, admin_token):
    teacher = _make_teacher(client, admin_token)
    client.post(f"/teachers/{teacher['id']}/reset-password", headers=_bearer(admin_token), json={"new_password": TEMPORARY})
    assert _login(client, "sara.self", TEMPORARY).json()["must_change_password"] is True
    _ask(client, TEACHER_EMAIL)
    client.post("/auth/reset-password", json={"token": _latest_token(TEACHER_EMAIL), "new_password": CHOSEN})
    signed_in = _login(client, "sara.self", CHOSEN).json()
    assert signed_in["must_change_password"] is False
    assert client.get("/teacher/profile", headers=_bearer(signed_in["access_token"])).status_code == 200


def test_the_administrator_assisted_reset_still_works(client, admin_token):
    parent = _make_parent(client, admin_token)
    response = client.post(f"/parents/{parent['id']}/reset-password", headers=_bearer(admin_token), json={"new_password": TEMPORARY})
    assert response.status_code == 200
    assert _login(client, "pa.self", TEMPORARY).json()["must_change_password"] is True


# ── Rate limits ─────────────────────────────────────────────────────────────

def test_one_address_gets_three_links_an_hour_and_the_answer_never_changes(client, admin_token):
    _make_teacher(client, admin_token)
    answers = {str(_ask(client, TEACHER_EMAIL).json()) for _ in range(6)}
    assert len(answers) == 1
    assert len(email_service.outbox) == 3


def test_one_client_is_limited_overall_and_the_limit_is_the_same_for_real_and_unknown_addresses(client, admin_token):
    _make_teacher(client, admin_token)
    statuses = [_ask(client, f"person{n}@example.test").status_code for n in range(12)]
    assert statuses[:10] == [202] * 10 and statuses[10:] == [429, 429]
    assert _ask(client, TEACHER_EMAIL).status_code == 429 and email_service.outbox == []


def test_repeated_wrong_links_are_limited(client):
    codes = [client.post("/auth/reset-password", json={"token": f"wrong-{n}", "new_password": CHOSEN}).status_code
             for n in range(12)]
    assert codes[:10] == [400] * 10 and codes[10:] == [429, 429]


# ── Nothing sensitive in logs ───────────────────────────────────────────────

def test_no_token_link_or_password_reaches_the_logs(client, admin_token, caplog):
    _make_teacher(client, admin_token)
    with caplog.at_level(logging.DEBUG):
        _ask(client, TEACHER_EMAIL)
        token = _latest_token(TEACHER_EMAIL)
        client.post("/auth/reset-password", json={"token": token, "new_password": CHOSEN})
    text = caplog.text
    assert token not in text and CHOSEN not in text and TEACHER_EMAIL not in text


def test_a_failing_mail_server_neither_breaks_the_request_nor_leaks(client, admin_token, monkeypatch, caplog):
    _make_teacher(client, admin_token)
    monkeypatch.setattr(config, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.invalid")
    monkeypatch.setattr(config, "SMTP_PORT", 1)
    with caplog.at_level(logging.DEBUG):
        assert _ask(client, TEACHER_EMAIL).status_code == 202
    assert TEACHER_EMAIL not in caplog.text


# ── Administrator: registered email addresses ───────────────────────────────

def test_an_administrator_changes_an_email_after_confirming_their_password(client, admin_token, admin_password):
    teacher = _make_teacher(client, admin_token)
    url = f"/teachers/{teacher['id']}/email"
    wrong = client.put(url, headers=_bearer(admin_token), json={"email": "x@example.test", "admin_password": "not-my-password"})
    assert wrong.status_code == 400
    assert client.get("/teachers", headers=_bearer(admin_token)).json()[0]["email"] == TEACHER_EMAIL

    done = client.put(url, headers=_bearer(admin_token), json={"email": " New.Sara@Example.test ", "admin_password": admin_password})
    assert done.status_code == 200 and done.json()["email"] == "new.sara@example.test"
    assert admin_password not in done.text
    # The old address is told, and can no longer be used to reset.
    assert [m.to for m in email_service.outbox] == [TEACHER_EMAIL]
    assert "changed" in email_service.outbox[0].subject
    email_service.outbox.clear()
    _ask(client, TEACHER_EMAIL)
    assert email_service.outbox == []
    _ask(client, "new.sara@example.test")
    assert len(email_service.outbox) == 1

    cleared = client.put(url, headers=_bearer(admin_token), json={"email": None, "admin_password": admin_password})
    assert cleared.status_code == 200 and cleared.json()["email"] is None


def test_the_same_works_for_parents_and_refuses_an_address_another_account_uses(client, admin_token, admin_password):
    parent = _make_parent(client, admin_token)
    _make_teacher(client, admin_token)
    url = f"/parents/{parent['id']}/email"
    taken = client.put(url, headers=_bearer(admin_token), json={"email": TEACHER_EMAIL, "admin_password": admin_password})
    assert taken.status_code == 409
    bad = client.put(url, headers=_bearer(admin_token), json={"email": "not an email", "admin_password": admin_password})
    assert bad.status_code == 422
    same = client.put(url, headers=_bearer(admin_token), json={"email": PARENT_EMAIL, "admin_password": admin_password})
    assert same.status_code == 200 and email_service.outbox == []  # nothing changed, nobody is notified
    done = client.put(url, headers=_bearer(admin_token), json={"email": "new.pa@example.test", "admin_password": admin_password})
    assert done.status_code == 200 and done.json()["email"] == "new.pa@example.test" and done.json()["children"]


def test_the_email_routes_are_for_administrators_and_only_for_teacher_and_parent_accounts(client, admin_token, admin_password):
    teacher = _make_teacher(client, admin_token)
    parent = _make_parent(client, admin_token)
    body = {"email": "z@example.test", "admin_password": admin_password}
    assert client.put(f"/teachers/{teacher['id']}/email", json=body).status_code == 401
    teacher_token = _login(client, "sara.self", ORIGINAL).json()["access_token"]
    parent_token = _login(client, "pa.self", ORIGINAL).json()["access_token"]
    for token in (teacher_token, parent_token):
        assert client.put(f"/teachers/{teacher['id']}/email", headers=_bearer(token), json=body).status_code == 403
        assert client.put(f"/parents/{parent['id']}/email", headers=_bearer(token), json=body).status_code == 403
    with Session(engine) as session:
        admin_id = session.exec(select(User).where(User.username == "admin")).one().id
    assert client.put(f"/teachers/{admin_id}/email", headers=_bearer(admin_token), json=body).status_code == 404
    assert client.put(f"/parents/{teacher['id']}/email", headers=_bearer(admin_token), json=body).status_code == 404


def test_wrong_administrator_passwords_are_limited(client, admin_token):
    teacher = _make_teacher(client, admin_token)
    codes = [client.put(f"/teachers/{teacher['id']}/email", headers=_bearer(admin_token),
                        json={"email": "z@example.test", "admin_password": f"guess-{n}"}).status_code for n in range(12)]
    assert codes[:10] == [400] * 10 and 429 in codes[10:]


def test_an_administrator_account_cannot_be_reset_by_email(client, admin_token):
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
        admin.email = "admin.only@example.test"
        session.add(admin)
        session.commit()
    assert _ask(client, "admin.only@example.test").status_code == 202
    assert email_service.outbox == []


# ── Found in the final security review ──────────────────────────────────────

def test_the_reply_does_no_work_that_depends_on_the_address(client, admin_token, monkeypatch):
    """Whether an address is registered decides how long the lookup, a new link and an email take (a link is a
    database write). None of it may happen before the reply, or the reply's timing tells anyone with a stopwatch
    which addresses have an account."""
    _make_teacher(client, admin_token)
    queued = []
    monkeypatch.setattr(auth_router, "run_in_background", lambda function, *args: queued.append((function, args)))
    for address in (TEACHER_EMAIL, "nobody@example.test"):
        clear_throttles()
        response = client.post("/auth/forgot-password", json={"email": address})
        assert response.status_code == 202 and GENERIC in response.json()["message"]
    # Both requests did exactly the same thing themselves: queue the address. No link and no email exist yet.
    assert queued == [(send_reset_link_if_eligible, (TEACHER_EMAIL,)), (send_reset_link_if_eligible, ("nobody@example.test",))]
    with Session(engine) as session:
        assert session.exec(select(PasswordResetToken)).all() == []
    assert email_service.outbox == []
    # The queued work then does the rest, and only the registered address gets anything.
    for function, args in queued:
        function(*args)
    assert [m.to for m in email_service.outbox] == [TEACHER_EMAIL]


def test_a_link_cannot_be_spent_twice_even_when_submitted_at_the_same_moment(client, admin_token):
    """Single use must hold under concurrency: before the fix both submissions succeeded and the later one won."""
    _make_teacher(client, admin_token)
    for trial in range(2):
        clear_throttles()
        _ask(client, TEACHER_EMAIL)
        token = _latest_token(TEACHER_EMAIL)
        passwords = [f"race-password-{trial}-a", f"race-password-{trial}-b"]
        barrier, codes = threading.Barrier(2), [None, None]

        def submit(index):
            barrier.wait()
            codes[index] = TestClient(app).post(
                "/auth/reset-password", json={"token": token, "new_password": passwords[index]}).status_code

        threads = [threading.Thread(target=submit, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert sorted(codes) == [200, 400]
        assert _login(client, "sara.self", passwords[codes.index(200)]).status_code == 200
        assert _login(client, "sara.self", passwords[codes.index(400)]).status_code == 401


def test_a_link_requested_earlier_cannot_undo_a_password_change_made_another_way(client, admin_token):
    teacher = _make_teacher(client, admin_token)
    _ask(client, TEACHER_EMAIL)
    token = _latest_token(TEACHER_EMAIL)
    signed_in = _login(client, "sara.self", ORIGINAL).json()["access_token"]
    changed = client.post("/auth/change-password", headers=_bearer(signed_in),
                          json={"current_password": ORIGINAL, "new_password": CHOSEN})
    assert changed.status_code == 200
    assert client.post("/auth/reset-password/check", json={"token": token}).status_code == 400

    # The same after an administrator's reset, which is what the office does for an account it distrusts.
    clear_throttles()
    _ask(client, TEACHER_EMAIL)
    token = _latest_token(TEACHER_EMAIL)
    reset = client.post(f"/teachers/{teacher['id']}/reset-password", headers=_bearer(admin_token),
                        json={"new_password": TEMPORARY})
    assert reset.status_code == 200
    assert client.post("/auth/reset-password/check", json={"token": token}).status_code == 400
    assert _login(client, "sara.self", TEMPORARY).status_code == 200


# ── One mailbox per registered address ──────────────────────────────────────

BAD_ADDRESSES = ["local,mallory@example.test", "a@b.test\nBcc: x@y.test", "a@b.test\r\nBcc: x@y.test", "not-an-email",
                 "a@@b.test", "a b@example.test", "@example.test", "a@", "a@example", "a@-bad.test", "a@exa_mple.test",
                 "a..b@example.test", ".a@example.test", "a@example.t", "é@example.test", "x" * 70 + "@example.test", "a;b@example.test", "x<y@example.test", '"a"@example.test',
                 "a(b)@example.test", "a\b@example.test", "a:b@example.test", "a@b.c\x00d", "a@[1.2.3].test"]


@pytest.mark.parametrize("address", BAD_ADDRESSES)
def test_an_address_that_a_mail_header_could_read_as_several_is_refused(client, admin_token, admin_password, address):
    created = client.post("/teachers", headers=_bearer(admin_token), json={
        "username": "bad.address", "full_name": "Bad Address", "email": address, "password": ORIGINAL})
    assert created.status_code == 422
    teacher = _make_teacher(client, admin_token)
    changed = client.put(f"/teachers/{teacher['id']}/email", headers=_bearer(admin_token),
                         json={"email": address, "admin_password": admin_password})
    assert changed.status_code == 422


def test_the_mail_service_refuses_a_recipient_that_is_not_exactly_one_mailbox():
    for address in ("a,b@example.test", "x<y@example.test", "a@b.test, c@d.test"):
        assert email_service.send_email(address, "Subject", "Body") is False
    assert email_service.outbox == []
    assert email_service.send_email("ok@example.test", "Subject", "Body") is True


def test_the_forgot_password_form_applies_the_same_rule(client, admin_token):
    """A malformed address is a 422 (it says nothing about who has an account); a well-formed unknown one is 202."""
    _make_teacher(client, admin_token)
    for address in BAD_ADDRESSES:
        clear_throttles()
        response = client.post("/auth/forgot-password", json={"email": address})
        assert response.status_code == 422, address
    drain_background_work()
    assert email_service.outbox == []
    for address in ("nobody@example.test", TEACHER_EMAIL):
        clear_throttles()
        assert client.post("/auth/forgot-password", json={"email": address}).status_code == 202


def test_parent_accounts_use_the_same_rule(client, admin_token, admin_password):
    parent = _make_parent(client, admin_token)
    with Session(engine) as session:
        student_id = session.exec(select(Student).where(Student.roll_number == "045")).one().id
    for address in ("a,b@example.test", "a@b.test\nBcc: x@y.test"):
        created = client.post("/parents", headers=_bearer(admin_token), json={
            "username": "bad.parent", "full_name": "Bad Parent", "email": address, "password": ORIGINAL, "student_ids": [student_id]})
        assert created.status_code == 422
        changed = client.put(f"/parents/{parent['id']}/email", headers=_bearer(admin_token),
                             json={"email": address, "admin_password": admin_password})
        assert changed.status_code == 422
    assert client.get("/parents", headers=_bearer(admin_token)).json()[0]["email"] == PARENT_EMAIL
