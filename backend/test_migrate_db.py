"""The database upgrade must never lose data, must back up first, and must be safe to re-run."""
import sqlite3

import pytest

import migrate_db


def _make_old_database(path, duplicate=False):
    """The schema as it exists on deployed databases, without the unique index."""
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE invoices (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, amount FLOAT NOT NULL,
            month VARCHAR NOT NULL, due_date VARCHAR NOT NULL, challan_number VARCHAR NOT NULL,
            status VARCHAR NOT NULL, created_at DATETIME NOT NULL);
        CREATE TABLE payments (id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL, amount_paid FLOAT NOT NULL,
            paid_at DATETIME NOT NULL, payment_mode VARCHAR NOT NULL);
        INSERT INTO invoices VALUES (1, 1, 4000, 'October 2025', '10-Oct-2025', 'CHN-1', 'paid', '2025-10-01');
        INSERT INTO invoices VALUES (2, 2, 4000, 'October 2025', '10-Oct-2025', 'CHN-2', 'pending', '2025-10-01');
        INSERT INTO payments VALUES (1, 1, 4000, '2025-10-02', 'cash');
        """
    )
    if duplicate:
        connection.execute(
            "INSERT INTO invoices VALUES (3, 1, 4000, 'October 2025', '10-Oct-2025', 'CHN-3', 'pending', '2025-10-03')"
        )
    connection.commit()
    connection.close()


def _rows(path, table):
    connection = sqlite3.connect(path)
    rows = connection.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    connection.close()
    return rows


def _has_index(path):
    connection = sqlite3.connect(path)
    found = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (migrate_db.INDEX_NAME,)
    ).fetchone()
    connection.close()
    return found is not None


def _backups(tmp_path):
    return list(tmp_path.glob("*.backup-*"))


def test_check_only_changes_nothing(tmp_path):
    db = tmp_path / "school.db"
    _make_old_database(db)
    before = db.read_bytes()

    exit_code = migrate_db.main([str(db)])

    assert exit_code == 0
    assert db.read_bytes() == before
    assert _backups(tmp_path) == []


def test_apply_backs_up_adds_the_index_and_keeps_all_data(tmp_path):
    db = tmp_path / "school.db"
    _make_old_database(db)
    invoices, payments = _rows(db, "invoices"), _rows(db, "payments")

    exit_code = migrate_db.main([str(db), "--apply"])

    assert exit_code == 0
    assert _has_index(db)
    assert _rows(db, "invoices") == invoices
    assert _rows(db, "payments") == payments
    backups = _backups(tmp_path)
    assert len(backups) == 1
    assert _rows(backups[0], "invoices") == invoices
    assert not _has_index(backups[0])


def test_index_blocks_a_duplicate_month_afterwards(tmp_path):
    db = tmp_path / "school.db"
    _make_old_database(db)
    migrate_db.main([str(db), "--apply"])

    connection = sqlite3.connect(db)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO invoices VALUES (9, 1, 1, 'October 2025', 'x', 'CHN-9', 'pending', '2025-10-01')"
        )
    connection.close()


def test_running_twice_is_harmless(tmp_path):
    db = tmp_path / "school.db"
    _make_old_database(db)
    migrate_db.main([str(db), "--apply"])
    first_backups = _backups(tmp_path)

    assert migrate_db.main([str(db), "--apply"]) == 0
    assert _backups(tmp_path) == first_backups


def test_existing_duplicates_stop_the_upgrade_and_are_listed_without_deleting_anything(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_old_database(db, duplicate=True)
    before = _rows(db, "invoices")

    exit_code = migrate_db.main([str(db), "--apply"])

    assert exit_code == 1
    assert not _has_index(db)
    assert _rows(db, "invoices") == before
    assert _backups(tmp_path) == []
    output = capsys.readouterr().out
    assert "CHN-1" in output and "CHN-3" in output


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


def test_missing_database_fails_clearly(tmp_path, capsys):
    assert migrate_db.main([str(tmp_path / "nope.db")]) == 1
    assert "not found" in capsys.readouterr().out


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
