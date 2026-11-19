"""Teacher-class assignments, daily attendance, corrections, and the administrator's reports."""
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from database import engine
from main import app
from models.attendance import AttendanceChangeHistory, StudentAttendance, TeacherClassAssignment
from models.fee import AcademicYear
from models.student import Student
from models.user import User
from services.fee_ledger import school_today

PASSWORD = "teacher-test-password-1"


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_up():
    yield
    with Session(engine) as session:
        for model in (AttendanceChangeHistory, StudentAttendance, TeacherClassAssignment):
            session.exec(delete(model))
        for user in session.exec(select(User).where(User.role == "teacher")).all():
            session.delete(user)
        session.commit()


@pytest.fixture()
def admin(client, admin_password):
    token = client.post("/auth/login", json={"username": "admin", "password": admin_password}).json()["access_token"]
    return _bearer(token)


def make_teacher(client, admin, username):
    created = client.post("/teachers", headers=admin, json={
        "username": username, "full_name": username.title(), "password": PASSWORD})
    assert created.status_code == 201, created.text
    token = client.post("/auth/login", json={"username": username, "password": PASSWORD}).json()["access_token"]
    return {"id": created.json()["id"], "headers": _bearer(token)}


def assign(client, admin, teacher, grade="Grade 8", section="A", **extra):
    return client.post("/teacher-assignments", headers=admin,
                       json={"teacher_id": teacher["id"], "grade": grade, "section": section, **extra})


@pytest.fixture()
def sara(client, admin):
    return make_teacher(client, admin, "sara")


@pytest.fixture()
def omar(client, admin):
    return make_teacher(client, admin, "omar")


@pytest.fixture()
def class_8a(client, admin, sara):
    """Sara teaches Grade 8-A. Returns the assignment id and the class roster."""
    assignment = assign(client, admin, sara)
    assert assignment.status_code == 201, assignment.text
    assignment_id = assignment.json()["id"]
    roster = client.get(f"/teacher/classes/{assignment_id}", headers=sara["headers"]).json()["students"]
    assert len(roster) >= 3
    return assignment_id, roster


def mark(client, teacher, assignment_id, entries, day=None, reason=None):
    body = {"date": (day or school_today()).isoformat(),
            "entries": [{"student_id": student_id, "status": status} for student_id, status in entries]}
    if reason:
        body["reason"] = reason
    return client.put(f"/teacher/classes/{assignment_id}/attendance", headers=teacher["headers"], json=body)


# ── Assigning teachers ──────────────────────────────────────────────────────

def test_admin_assigns_a_teacher_and_lists_options(client, admin, sara):
    options = client.get("/teacher-assignments/options", headers=admin).json()
    assert "sara" in [t["username"] for t in options["teachers"]]
    assert len(options["classes"]) == 10 and options["academic_years"][0]["is_current"] is True

    response = assign(client, admin, sara)

    assert response.status_code == 201
    body = response.json()
    assert (body["teacher_name"], body["grade"], body["section"]) == ("Sara", "Grade 8", "A")
    assert body["academic_year"] == options["academic_years"][0]["label"] and body["enrolled"] > 0


def test_a_duplicate_assignment_is_refused_but_other_combinations_work(client, admin, sara, omar):
    assert assign(client, admin, sara).status_code == 201

    assert assign(client, admin, sara).status_code == 409
    # One teacher, several classes; several teachers, one class.
    assert assign(client, admin, sara, section="B").status_code == 201
    assert assign(client, admin, sara, grade="Grade 9").status_code == 201
    assert assign(client, admin, omar).status_code == 201
    assert len(client.get("/teacher-assignments", headers=admin).json()) == 4
    assert len(client.get("/teacher-assignments", params={"teacher_id": sara["id"]}, headers=admin).json()) == 3


def test_the_same_class_can_be_assigned_again_in_another_session(client, admin, sara):
    with Session(engine) as session:
        other = AcademicYear(label="2026-2027-test", is_current=False)
        session.add(other)
        session.commit()
        other_id = other.id
    try:
        assert assign(client, admin, sara).status_code == 201
        assert assign(client, admin, sara, academic_year_id=other_id).status_code == 201
        assert assign(client, admin, sara, academic_year_id=other_id).status_code == 409
    finally:
        with Session(engine) as session:
            session.exec(delete(TeacherClassAssignment))
            session.exec(delete(AcademicYear).where(AcademicYear.id == other_id))
            session.commit()


def test_assignment_input_is_checked(client, admin, sara):
    assert assign(client, admin, sara, grade="Grade 99").status_code == 422
    assert assign(client, admin, sara, section="Z").status_code == 422
    assert assign(client, admin, sara, academic_year_id=9999).status_code == 422
    assert client.post("/teacher-assignments", headers=admin,
                       json={"teacher_id": 99999, "grade": "Grade 8", "section": "A"}).status_code == 404
    with Session(engine) as session:
        admin_id = session.exec(select(User).where(User.username == "admin")).one().id
    # Only teacher accounts can be assigned to a class.
    assert client.post("/teacher-assignments", headers=admin,
                       json={"teacher_id": admin_id, "grade": "Grade 8", "section": "A"}).status_code == 404


def test_a_deactivated_teacher_cannot_be_assigned(client, admin, sara):
    client.post(f"/teachers/{sara['id']}/deactivate", headers=admin)

    assert assign(client, admin, sara).status_code == 422


def test_assignments_can_be_edited_and_removed_without_touching_attendance(client, admin, sara, omar, class_8a):
    assignment_id, roster = class_8a
    assert mark(client, sara, assignment_id, [(roster[0]["id"], "present")]).status_code == 200

    moved = client.put(f"/teacher-assignments/{assignment_id}", headers=admin,
                       json={"teacher_id": omar["id"], "grade": "Grade 8", "section": "B"})
    assert moved.status_code == 200 and moved.json()["teacher_username"] == "omar"
    assert client.get("/teacher/classes", headers=sara["headers"]).json()["classes"] == []

    second = assign(client, admin, omar).json()["id"]
    clash = client.put(f"/teacher-assignments/{second}", headers=admin,
                       json={"teacher_id": omar["id"], "grade": "Grade 8", "section": "B"})
    assert clash.status_code == 409

    assert client.delete(f"/teacher-assignments/{assignment_id}", headers=admin).status_code == 204
    assert client.delete(f"/teacher-assignments/{assignment_id}", headers=admin).status_code == 404
    with Session(engine) as session:
        assert len(session.exec(select(StudentAttendance)).all()) == 1


def test_only_administrators_manage_assignments(client, admin, sara):
    assert client.get("/teacher-assignments", headers=sara["headers"]).status_code == 403
    assert assign(client, {"Authorization": sara["headers"]["Authorization"]}, sara).status_code == 403
    assert client.get("/teacher-assignments").status_code == 401


# ── A teacher's classes ─────────────────────────────────────────────────────

def test_a_teacher_sees_only_their_own_classes_and_students(client, admin, sara, omar, class_8a):
    assignment_id, roster = class_8a
    other = assign(client, admin, omar, grade="Grade 9", section="B").json()["id"]

    mine = client.get("/teacher/classes", headers=sara["headers"]).json()
    assert [c["id"] for c in mine["classes"]] == [assignment_id]
    card = mine["classes"][0]
    assert (card["grade"], card["section"], card["is_current_session"]) == ("Grade 8", "A", True)
    assert card["enrolled"] == len(roster) and card["today_attendance"]["state"] == "not_submitted"
    assert card["academic_year"]

    for path in ("", "/attendance", "/history"):
        assert client.get(f"/teacher/classes/{other}{path}", headers=sara["headers"]).status_code == 403
    assert client.get("/teacher/classes/987654", headers=sara["headers"]).status_code == 403
    assert mark(client, sara, other, [(1, "present")]).status_code == 403


def test_a_class_reports_the_school_date_and_its_attendance_status_separately(client, class_8a, sara):
    assignment_id, _ = class_8a

    detail = client.get(f"/teacher/classes/{assignment_id}", headers=sara["headers"]).json()

    assert detail["today"] == school_today().isoformat()
    assert detail["today_attendance"]["state"] == "not_submitted" and detail["edit_window_days"] == 7
    listing = client.get("/teacher/classes", headers=sara["headers"]).json()
    assert listing["today"] == school_today().isoformat()


def test_the_roster_shows_only_what_a_teacher_needs(client, class_8a, sara):
    assignment_id, roster = class_8a

    assert set(roster[0]) == {"id", "name", "roll_number", "grade", "section"}
    assert all(student["grade"] == "Grade 8" and student["section"] == "A" for student in roster)
    with Session(engine) as session:
        archived = session.exec(select(Student).where(Student.id == roster[0]["id"])).one()
        archived.archived_at = datetime.now(timezone.utc)
        session.add(archived)
        session.commit()
    try:
        fresh = client.get(f"/teacher/classes/{assignment_id}", headers=sara["headers"]).json()["students"]
        assert roster[0]["id"] not in [student["id"] for student in fresh]
    finally:
        with Session(engine) as session:
            student = session.get(Student, roster[0]["id"])
            student.archived_at = None
            session.add(student)
            session.commit()


# ── Marking attendance ──────────────────────────────────────────────────────

def test_a_teacher_submits_attendance_and_reviews_it(client, sara, class_8a):
    assignment_id, roster = class_8a
    statuses = ["present", "absent", "late", "leave"]
    entries = [(student["id"], statuses[index % 4]) for index, student in enumerate(roster)]

    saved = mark(client, sara, assignment_id, entries)

    assert saved.status_code == 200
    body = saved.json()
    assert (body["created"], body["corrected"], body["unchanged"]) == (len(roster), 0, 0)
    assert body["state"] == "complete" and body["recorded"] == len(roster)
    shown = client.get(f"/teacher/classes/{assignment_id}/attendance", headers=sara["headers"]).json()
    assert [s["status"] for s in shown["students"]] == [statuses[i % 4] for i in range(len(roster))]
    assert shown["students"][0]["marked_by"] == "Sara"
    assert client.get("/teacher/classes", headers=sara["headers"]).json()["classes"][0]["today_attendance"]["state"] == "complete"


def test_saving_again_never_duplicates_records(client, sara, class_8a):
    assignment_id, roster = class_8a
    entries = [(student["id"], "present") for student in roster]
    mark(client, sara, assignment_id, entries)

    again = mark(client, sara, assignment_id, entries)

    assert again.status_code == 200 and again.json()["unchanged"] == len(roster) and again.json()["created"] == 0
    with Session(engine) as session:
        assert len(session.exec(select(StudentAttendance)).all()) == len(roster)
        assert session.exec(select(AttendanceChangeHistory)).all() == []


def test_unmarked_students_are_never_counted_absent(client, admin, sara, class_8a):
    assignment_id, roster = class_8a

    mark(client, sara, assignment_id, [(roster[0]["id"], "present")])

    day = client.get(f"/teacher/classes/{assignment_id}/attendance", headers=sara["headers"]).json()
    assert day["state"] == "partial" and day["recorded"] == 1
    assert [s["status"] for s in day["students"]][1:] == [None] * (len(roster) - 1)
    row = next(c for c in client.get("/attendance/overview", headers=admin).json()["classes"]
               if (c["grade"], c["section"]) == ("Grade 8", "A"))
    assert row["absent"] == 0 and row["not_recorded"] == len(roster) - 1


@pytest.mark.parametrize("bad_date", ["2026-13-45", "yesterday", "", "05/11/2026"])
def test_invalid_dates_are_rejected(client, sara, class_8a, bad_date):
    assignment_id, roster = class_8a
    body = {"date": bad_date, "entries": [{"student_id": roster[0]["id"], "status": "present"}]}

    assert client.put(f"/teacher/classes/{assignment_id}/attendance", headers=sara["headers"], json=body).status_code == 422


def test_future_dates_and_dates_beyond_the_teacher_window_are_refused(client, sara, class_8a):
    assignment_id, roster = class_8a
    entry = [(roster[0]["id"], "present")]
    today = school_today()

    assert mark(client, sara, assignment_id, entry, day=today + timedelta(days=1)).status_code == 422
    assert mark(client, sara, assignment_id, entry, day=today - timedelta(days=8)).status_code == 403
    assert mark(client, sara, assignment_id, entry, day=today - timedelta(days=7)).status_code == 200
    assert client.get(f"/teacher/classes/{assignment_id}/attendance", headers=sara["headers"],
                      params={"date": (today + timedelta(days=2)).isoformat()}).status_code == 422


def test_invalid_entries_are_refused_and_nothing_is_saved(client, sara, class_8a):
    assignment_id, roster = class_8a
    good = (roster[0]["id"], "present")

    assert mark(client, sara, assignment_id, [good, (roster[1]["id"], "sleeping")]).status_code == 422
    assert mark(client, sara, assignment_id, [good, (roster[1]["id"], "absent"), (roster[1]["id"], "late")]).status_code == 422
    assert mark(client, sara, assignment_id, []).status_code == 422
    with Session(engine) as session:
        outsider = session.exec(select(Student).where(Student.grade == "Grade 9")).first().id
    assert mark(client, sara, assignment_id, [good, (outsider, "present")]).status_code == 403
    with Session(engine) as session:
        assert session.exec(select(StudentAttendance)).all() == []


def test_a_correction_needs_a_reason_and_is_written_to_the_history(client, admin, sara, class_8a):
    assignment_id, roster = class_8a
    student = roster[0]["id"]
    mark(client, sara, assignment_id, [(student, "absent"), (roster[1]["id"], "present")])

    assert mark(client, sara, assignment_id, [(student, "present")]).status_code == 422
    fixed = mark(client, sara, assignment_id, [(student, "present"), (roster[1]["id"], "present")],
                 reason="Parent confirmed arrival")

    assert fixed.status_code == 200
    assert (fixed.json()["corrected"], fixed.json()["unchanged"]) == (1, 1)
    change = fixed.json()["changes"][0]
    assert (change["old_status"], change["new_status"], change["reason"], change["changed_by"]) == (
        "absent", "present", "Parent confirmed arrival", "Sara")
    assert fixed.json()["students"][0]["status"] == "present"
    trail = client.get(f"/attendance/students/{student}/history", headers=admin).json()
    assert trail["changes"][0]["reason"] == "Parent confirmed arrival" and trail["present"] == 1
    assert client.get("/attendance/changes", headers=admin).json()["changes"][0]["student"] == roster[0]["name"]


def test_a_teacher_reads_the_class_history_including_corrected_days(client, sara, class_8a):
    assignment_id, roster = class_8a
    today = school_today()
    mark(client, sara, assignment_id, [(s["id"], "present") for s in roster], day=today - timedelta(days=1))
    mark(client, sara, assignment_id, [(roster[0]["id"], "absent"), (roster[1]["id"], "late")], day=today)
    mark(client, sara, assignment_id, [(roster[0]["id"], "present")], day=today, reason="Arrived late")

    history = client.get(f"/teacher/classes/{assignment_id}/history", headers=sara["headers"])

    assert history.status_code == 200, history.text
    days = history.json()["days"]
    assert [d["date"] for d in days] == [today.isoformat(), (today - timedelta(days=1)).isoformat()]
    newest, older = days
    assert (newest["present"], newest["late"], newest["absent"], newest["recorded"]) == (1, 1, 0, 2)
    assert newest["state"] == "partial" and newest["corrected"] is True
    assert older["state"] == "complete" and older["corrected"] is False and older["present"] == len(roster)
    narrow = client.get(f"/teacher/classes/{assignment_id}/history", headers=sara["headers"],
                        params={"start": today.isoformat(), "end": today.isoformat()}).json()["days"]
    assert [d["date"] for d in narrow] == [today.isoformat()]


def test_attendance_is_closed_for_a_session_that_is_not_current(client, admin, sara, class_8a):
    assignment_id, roster = class_8a
    with Session(engine) as session:
        year = session.exec(select(AcademicYear).where(AcademicYear.is_current == True)).one()  # noqa: E712
        year_id = year.id
        year.is_current = False
        session.add(year)
        session.commit()
    try:
        assert mark(client, sara, assignment_id, [(roster[0]["id"], "present")]).status_code == 409
    finally:
        with Session(engine) as session:
            year = session.get(AcademicYear, year_id)
            year.is_current = True
            session.add(year)
            session.commit()


def test_a_deactivated_teacher_loses_access_at_once(client, admin, sara, class_8a):
    assignment_id, roster = class_8a
    client.post(f"/teachers/{sara['id']}/deactivate", headers=admin)

    assert client.get("/teacher/classes", headers=sara["headers"]).status_code == 401
    assert mark(client, sara, assignment_id, [(roster[0]["id"], "present")]).status_code == 401


def test_a_teacher_cannot_use_the_administrator_attendance_routes(client, sara, class_8a):
    for path in ("/attendance/overview", "/attendance/monthly", "/attendance/report", "/attendance/export.csv",
                 "/attendance/frequent-absentees", "/attendance/changes", "/attendance/students/1/history"):
        assert client.get(path, headers=sara["headers"]).status_code == 403, path
        assert client.get(path).status_code == 401, path
    body = {"date": school_today().isoformat(), "grade": "Grade 8", "section": "A", "entries": []}
    assert client.put("/attendance/class-day", headers=sara["headers"], json=body).status_code == 403


# ── The administrator's view ────────────────────────────────────────────────

def _record(client, sara, assignment_id, roster, status_for, day):
    return mark(client, sara, assignment_id, [(s["id"], status_for(i)) for i, s in enumerate(roster)], day=day)


def test_the_overview_keeps_missing_submissions_apart_from_absences(client, admin, sara, class_8a):
    assignment_id, roster = class_8a
    _record(client, sara, assignment_id, roster, lambda i: "absent" if i == 0 else "present", school_today())

    overview = client.get("/attendance/overview", headers=admin).json()

    by_class = {(c["grade"], c["section"]): c for c in overview["classes"]}
    submitted = by_class[("Grade 8", "A")]
    assert (submitted["state"], submitted["absent"], submitted["not_recorded"]) == ("complete", 1, 0)
    assert submitted["teachers"] == ["Sara"]
    untouched = by_class[("Grade 6", "A")]
    assert (untouched["state"], untouched["absent"], untouched["recorded"]) == ("not_submitted", 0, 0)
    assert untouched["not_recorded"] == untouched["enrolled"] > 0
    assert overview["classes_not_submitted"] == 9 and overview["totals"]["absent"] == 1
    filtered = client.get("/attendance/overview", params={"grade": "Grade 8", "section": "A"}, headers=admin).json()
    assert len(filtered["classes"]) == 1


def test_monthly_summary_and_frequent_absentees_use_only_recorded_days(client, admin, sara, class_8a):
    assignment_id, roster = class_8a
    today = school_today()
    for back in range(4):
        _record(client, sara, assignment_id, roster, lambda i: "absent" if i == 0 else "present",
                today - timedelta(days=back))

    monthly = client.get("/attendance/monthly", params={"month": today.strftime("%Y-%m")}, headers=admin).json()
    row = next(c for c in monthly["classes"] if (c["grade"], c["section"]) == ("Grade 8", "A"))
    assert row["recorded"] == row["present"] + row["absent"] and row["absent"] >= 1
    assert row["attendance_rate"] == round(row["present"] * 100 / row["recorded"], 1)
    empty = next(c for c in monthly["classes"] if (c["grade"], c["section"]) == ("Grade 6", "A"))
    assert empty["attendance_rate"] is None and empty["recorded"] == 0

    start = (today - timedelta(days=3)).isoformat()
    absentees = client.get("/attendance/frequent-absentees", params={"start": start, "min_absences": 3}, headers=admin).json()
    assert [s["id"] for s in absentees["students"]] == [roster[0]["id"]]
    assert absentees["students"][0]["absent"] == 4 and absentees["students"][0]["absence_rate"] == 100.0
    assert client.get("/attendance/frequent-absentees", params={"start": start, "min_absences": 5},
                      headers=admin).json()["students"] == []
    assert client.get("/attendance/monthly", params={"month": "2026-13"}, headers=admin).status_code == 422


def test_student_history_lists_each_recorded_day(client, admin, sara, class_8a):
    assignment_id, roster = class_8a
    today = school_today()
    mark(client, sara, assignment_id, [(roster[0]["id"], "late")], day=today)
    mark(client, sara, assignment_id, [(roster[0]["id"], "present")], day=today - timedelta(days=2))

    history = client.get(f"/attendance/students/{roster[0]['id']}/history", headers=admin).json()

    assert [(r["date"], r["status"]) for r in history["records"]] == [
        (today.isoformat(), "late"), ((today - timedelta(days=2)).isoformat(), "present")]
    assert history["days_recorded"] == 2 and history["attendance_rate"] == 100.0
    assert client.get("/attendance/students/999999/history", headers=admin).status_code == 404


def test_an_administrator_can_correct_any_past_date_with_a_reason(client, admin, sara, class_8a):
    assignment_id, roster = class_8a
    long_ago = school_today() - timedelta(days=40)
    body = {"date": long_ago.isoformat(), "grade": "Grade 8", "section": "A",
            "entries": [{"student_id": roster[0]["id"], "status": "absent"}]}

    created = client.put("/attendance/class-day", headers=admin, json=body)
    assert created.status_code == 200 and created.json()["created"] == 1
    body["entries"][0]["status"] = "leave"
    assert client.put("/attendance/class-day", headers=admin, json=body).status_code == 422
    body["reason"] = "Leave letter received"
    fixed = client.put("/attendance/class-day", headers=admin, json=body)
    assert fixed.status_code == 200 and fixed.json()["changes"][0]["changed_by"] == "admin"
    shown = client.get("/attendance/class-day", headers=admin,
                       params={"date": long_ago.isoformat(), "grade": "Grade 8", "section": "A"}).json()
    assert shown["students"][0]["status"] == "leave"
    body["date"] = (school_today() + timedelta(days=1)).isoformat()
    assert client.put("/attendance/class-day", headers=admin, json=body).status_code == 422
    body.update(date=long_ago.isoformat(), grade="Grade 99")
    assert client.put("/attendance/class-day", headers=admin, json=body).status_code == 422


def test_csv_export_and_the_printable_report(client, admin, sara, class_8a):
    assignment_id, roster = class_8a
    _record(client, sara, assignment_id, roster, lambda i: "absent" if i == 0 else "present", school_today())
    with Session(engine) as session:
        student = session.get(Student, roster[1]["id"])
        original = student.name
        student.name = "=HYPERLINK(\"http://example.test\")"
        session.add(student)
        session.commit()
    try:
        export = client.get("/attendance/export.csv", headers=admin, params={"grade": "Grade 8", "section": "A"})
    finally:
        with Session(engine) as session:
            student = session.get(Student, roster[1]["id"])
            student.name = original
            session.add(student)
            session.commit()

    assert export.status_code == 200 and export.headers["content-type"].startswith("text/csv")
    assert "attachment" in export.headers["content-disposition"]
    lines = export.text.lstrip("﻿").splitlines()
    assert lines[0] == "Date,Grade,Section,Roll number,Student,Status,Marked by,Corrected"
    assert len(lines) == len(roster) + 1
    assert any(",absent,Sara,No" in line for line in lines)
    assert "'=HYPERLINK" in export.text and ",=HYPERLINK" not in export.text and ',"=HYPERLINK' not in export.text

    report = client.get("/attendance/report", headers=admin).json()
    assert report["totals"]["recorded"] == len(roster) and report["totals"]["absent"] == 1
    assert len(report["classes"]) == 10
    assert client.get("/attendance/report", headers=admin, params={"start": "2026-02-01", "end": "2026-01-01"}).status_code == 422
    assert client.get("/attendance/report", headers=admin,
                      params={"start": "2020-01-01", "end": "2026-01-01"}).status_code == 422


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
