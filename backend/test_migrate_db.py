"""The database upgrade must never lose data, must back up first, and must be safe to re-run."""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

import migrate_db

INDEXES = (migrate_db.INVOICE_STUDENT_MONTH_INDEX, migrate_db.RESULT_UNIQUE_INDEX)


def _make_old_database(path, duplicate=False, duplicate_mark=False):
    """The schema as it exists on deployed databases, without the column or the indexes."""
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE students (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, roll_number VARCHAR NOT NULL,
            grade VARCHAR NOT NULL, section VARCHAR NOT NULL, guardian_name VARCHAR NOT NULL,
            phone VARCHAR NOT NULL, dob VARCHAR, created_at DATETIME NOT NULL);
        CREATE TABLE invoices (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, amount FLOAT NOT NULL,
            month VARCHAR NOT NULL, due_date VARCHAR NOT NULL, challan_number VARCHAR NOT NULL,
            status VARCHAR NOT NULL, created_at DATETIME NOT NULL);
        CREATE TABLE payments (id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL, amount_paid FLOAT NOT NULL,
            paid_at DATETIME NOT NULL, payment_mode VARCHAR NOT NULL);
        CREATE TABLE results (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, subject VARCHAR NOT NULL,
            marks_obtained FLOAT NOT NULL, total_marks FLOAT NOT NULL, exam_type VARCHAR NOT NULL,
            academic_year_id INTEGER);
        INSERT INTO students VALUES (1, 'Sana Mirza', '001', 'Grade 7', 'A', 'Imran Mirza', '0301-2345678', NULL, '2025-08-01');
        INSERT INTO students VALUES (2, 'Hina Soomro', '002', 'Grade 8', 'B', 'Akbar Soomro', '0301-2345679', NULL, '2025-08-01');
        INSERT INTO invoices VALUES (1, 1, 4000, 'October 2025', '10-Oct-2025', 'CHN-1', 'paid', '2025-10-01');
        INSERT INTO invoices VALUES (2, 2, 4000, 'October 2025', '10-Oct-2025', 'CHN-2', 'pending', '2025-10-01');
        INSERT INTO payments VALUES (1, 1, 4000, '2025-10-02', 'cash');
        INSERT INTO results VALUES (1, 1, 'English', 70, 100, 'Final Term', 1);
        INSERT INTO results VALUES (2, 1, 'English', 60, 100, 'Midterm', 1);
        """
    )
    if duplicate:
        connection.execute(
            "INSERT INTO invoices VALUES (3, 1, 4000, 'October 2025', '10-Oct-2025', 'CHN-3', 'pending', '2025-10-03')"
        )
    if duplicate_mark:
        connection.execute("INSERT INTO results VALUES (3, 1, 'English', 75, 100, 'Final Term', 1)")
    connection.commit()
    connection.close()


def _rows(path, table):
    connection = sqlite3.connect(path)
    rows = connection.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    connection.close()
    return rows


def _student_rows_without_new_column(path):
    connection = sqlite3.connect(path)
    rows = connection.execute(
        "SELECT id, name, roll_number, grade, section, guardian_name, phone, dob, created_at FROM students ORDER BY id"
    ).fetchall()
    connection.close()
    return rows


def _has_index(path, name):
    connection = sqlite3.connect(path)
    found = connection.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone()
    connection.close()
    return found is not None


def _has_archive_column(path):
    connection = sqlite3.connect(path)
    found = any(row[1] == "archived_at" for row in connection.execute("PRAGMA table_info(students)"))
    connection.close()
    return found


def _backups(tmp_path):
    return list(tmp_path.glob("*.backup-*"))


def test_check_only_changes_nothing(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_old_database(db)
    before = db.read_bytes()

    exit_code = migrate_db.main([str(db)])

    assert exit_code == 0
    assert db.read_bytes() == before
    assert _backups(tmp_path) == []
    assert "3 change(s) waiting" in capsys.readouterr().out


def test_apply_backs_up_makes_the_changes_and_keeps_all_data(tmp_path):
    db = tmp_path / "school.db"
    _make_old_database(db)
    students = _student_rows_without_new_column(db)
    invoices, payments, results = _rows(db, "invoices"), _rows(db, "payments"), _rows(db, "results")

    exit_code = migrate_db.main([str(db), "--apply"])

    assert exit_code == 0
    assert _has_archive_column(db)
    assert all(_has_index(db, name) for name in INDEXES)
    assert _student_rows_without_new_column(db) == students
    assert _rows(db, "invoices") == invoices
    assert _rows(db, "payments") == payments
    assert _rows(db, "results") == results
    backups = _backups(tmp_path)
    assert len(backups) == 1
    assert _rows(backups[0], "invoices") == invoices
    assert _rows(backups[0], "results") == results
    assert not _has_archive_column(backups[0])
    assert not any(_has_index(backups[0], name) for name in INDEXES)


def test_every_existing_student_stays_active(tmp_path):
    db = tmp_path / "school.db"
    _make_old_database(db)

    migrate_db.main([str(db), "--apply"])

    connection = sqlite3.connect(db)
    assert connection.execute("SELECT count(*) FROM students WHERE archived_at IS NOT NULL").fetchone() == (0,)
    connection.close()


def test_indexes_block_duplicates_afterwards_but_allow_a_second_exam(tmp_path):
    db = tmp_path / "school.db"
    _make_old_database(db)
    migrate_db.main([str(db), "--apply"])

    connection = sqlite3.connect(db)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO invoices VALUES (9, 1, 1, 'October 2025', 'x', 'CHN-9', 'pending', '2025-10-01')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO results VALUES (9, 1, 'English', 1, 100, 'Final Term', 1)")
    connection.execute("INSERT INTO results VALUES (10, 1, 'English', 1, 100, 'Final Term', 2)")
    connection.close()


def test_running_twice_is_harmless(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_old_database(db)
    migrate_db.main([str(db), "--apply"])
    first_backups = _backups(tmp_path)

    assert migrate_db.main([str(db), "--apply"]) == 0
    assert _backups(tmp_path) == first_backups
    assert "Already upgraded" in capsys.readouterr().out


def test_a_database_with_only_the_earlier_fee_index_gets_the_rest(tmp_path):
    db = tmp_path / "school.db"
    _make_old_database(db)
    connection = sqlite3.connect(db)
    connection.execute(f"CREATE UNIQUE INDEX {migrate_db.INVOICE_STUDENT_MONTH_INDEX} ON invoices (student_id, month)")
    connection.commit()
    connection.close()

    assert migrate_db.main([str(db), "--apply"]) == 0
    assert _has_archive_column(db)
    assert _has_index(db, migrate_db.RESULT_UNIQUE_INDEX)


def test_existing_duplicate_challans_stop_the_upgrade_and_are_listed_without_deleting_anything(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_old_database(db, duplicate=True)
    before = _rows(db, "invoices")

    exit_code = migrate_db.main([str(db), "--apply"])

    assert exit_code == 1
    assert not _has_archive_column(db)
    assert not any(_has_index(db, name) for name in INDEXES)
    assert _rows(db, "invoices") == before
    assert _backups(tmp_path) == []
    output = capsys.readouterr().out
    assert "CHN-1" in output and "CHN-3" in output


def test_existing_duplicate_marks_stop_the_upgrade_without_deleting_anything(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_old_database(db, duplicate_mark=True)
    before = _rows(db, "results")

    assert migrate_db.main([str(db), "--apply"]) == 1
    assert not _has_archive_column(db)
    assert _rows(db, "results") == before
    assert _backups(tmp_path) == []
    assert "Marks entered twice" in capsys.readouterr().out


def test_report_flags_money_records_that_need_a_person_to_review(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_old_database(db)
    connection = sqlite3.connect(db)
    connection.executescript(
        """
        INSERT INTO invoices VALUES (4, 4, 4000, 'May 2026', '??', 'CHN-4', 'paid', '2026-05-01');
        INSERT INTO invoices VALUES (5, 5, 4000, 'May 2026', '10-May-2026', 'CHN-5', 'paid', '2026-05-01');
        INSERT INTO payments VALUES (2, 5, 4000, '2026-05-02', 'cash');
        INSERT INTO payments VALUES (3, 5, 4000, '2026-05-02', 'cash');
        INSERT INTO invoices VALUES (6, 6, 4000, 'May 2026', '10-May-2026', 'CHN-6', 'paid', '2026-05-01');
        INSERT INTO payments VALUES (4, 6, 1, '2026-05-02', 'cash');
        """
    )
    connection.commit()
    connection.close()

    assert migrate_db.main([str(db)]) == 0

    output = capsys.readouterr().out
    assert "marked paid with no payment" in output and "CHN-4" in output
    assert "paid more than invoiced" in output and "CHN-5" in output
    assert "marked paid but not fully paid" in output and "CHN-6" in output
    assert "unreadable due date" in output


def test_report_flags_marks_that_need_a_person_to_review(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_old_database(db)
    connection = sqlite3.connect(db)
    connection.executescript(
        """
        INSERT INTO results VALUES (5, 2, 'Science', 150, 100, 'Final Term', 1);
        INSERT INTO results VALUES (6, 2, 'Urdu', 50, 100, 'Pizza Test', 1);
        """
    )
    connection.commit()
    connection.close()

    assert migrate_db.main([str(db)]) == 0

    output = capsys.readouterr().out
    assert "cannot be right" in output and "150" in output
    assert "unknown exam type" in output and "Pizza Test" in output


def test_missing_database_fails_clearly(tmp_path, capsys):
    assert migrate_db.main([str(tmp_path / "nope.db")]) == 1
    assert "not found" in capsys.readouterr().out


def test_runs_with_no_application_secrets(tmp_path):
    """The Modal upgrade function has no secrets attached, and production settings would refuse to load."""
    db = tmp_path / "school.db"
    _make_old_database(db)
    environment = {key: value for key, value in os.environ.items() if key not in ("SECRET_KEY", "APP_ENV")}
    # Stops load_dotenv from finding a real .env file: the script runs from a folder with none.
    backend = Path(migrate_db.__file__).resolve().parent
    environment["PYTHONPATH"] = str(backend)

    finished = subprocess.run(
        [sys.executable, str(backend / "migrate_db.py"), str(db)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert finished.returncode == 0, finished.stderr


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
