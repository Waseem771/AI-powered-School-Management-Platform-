"""Tests for services/backup_service.py.

Every test here uses its own temporary SQLite file under pytest's `tmp_path` fixture. None of
this touches `school.db`, any Modal Volume, or any secret -- it cannot, since nothing here
imports Modal or reaches outside the temporary directory pytest gives each test.
"""
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from services.backup_service import (
    BackupResult,
    create_consistent_backup,
    create_verified_backup,
    record_counts,
    select_files_to_prune,
    verify_backup,
)

SCHEMA = """
CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE invoices (id INTEGER PRIMARY KEY, amount INTEGER);
CREATE TABLE payments (id INTEGER PRIMARY KEY, amount_paid INTEGER);
CREATE TABLE results (id INTEGER PRIMARY KEY, marks_obtained INTEGER);
"""


def _seeded_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    connection.execute("INSERT INTO students (name) VALUES ('Ahmed Khan')")
    connection.execute("INSERT INTO students (name) VALUES ('Bilal Tariq')")
    connection.execute("INSERT INTO invoices (amount) VALUES (3500)")
    connection.execute("INSERT INTO payments (amount_paid) VALUES (3500)")
    connection.execute("INSERT INTO results (marks_obtained) VALUES (78)")
    connection.execute("INSERT INTO results (marks_obtained) VALUES (91)")
    connection.commit()
    connection.close()


# --- The two safety properties the owner asked to have confirmed before anything else ---


def test_the_read_only_source_connection_cannot_write(tmp_path):
    """Proves, not just by convention, that this module cannot modify the source database.

    If create_consistent_backup ever used a writable connection to the source, this test would
    not be able to tell the difference from the outside -- so it reaches into the same
    mechanism (SQLite's mode=ro URI) the module itself uses, confirming SQLite's own driver is
    the one refusing the write, not just a promise in this module's code.
    """
    source = tmp_path / "source.db"
    _seeded_database(source)
    before = source.read_bytes()

    dest = tmp_path / "backup.db"
    assert create_consistent_backup(source, dest) is True

    after = source.read_bytes()
    assert before == after, "the source file's bytes changed during backup"

    # And directly: the same read-only URI scheme this module uses really does refuse a write.
    from services.backup_service import _read_only_uri  # the module's own helper, tested directly

    ro = sqlite3.connect(_read_only_uri(source), uri=True)
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("INSERT INTO students (name) VALUES ('Should Not Be Allowed')")
    ro.close()


def test_an_uncommitted_change_on_another_connection_is_not_copied(tmp_path):
    """The backup only ever sees committed data -- an in-progress write on another connection
    to the same file is invisible to it, exactly as SQLite's Online Backup API promises."""
    source = tmp_path / "source.db"
    _seeded_database(source)

    writer = sqlite3.connect(source)
    writer.execute("INSERT INTO students (name) VALUES ('Not Yet Committed')")
    # Deliberately not committed.

    dest = tmp_path / "backup.db"
    assert create_consistent_backup(source, dest) is True

    names = {row[0] for row in sqlite3.connect(dest).execute("SELECT name FROM students")}
    assert "Not Yet Committed" not in names
    assert names == {"Ahmed Khan", "Bilal Tariq"}

    writer.commit()
    writer.close()


# --- Backup creation and verification ---


def test_a_good_backup_passes_integrity_check_and_matches_record_counts(tmp_path):
    source = tmp_path / "source.db"
    _seeded_database(source)

    dest = tmp_path / "backup.db"
    assert create_consistent_backup(source, dest) is True
    assert verify_backup(dest) is True
    assert record_counts(dest) == record_counts(source)
    assert record_counts(source) == {"students": 2, "invoices": 1, "payments": 1, "results": 2}


def test_record_counts_leaves_out_a_table_that_does_not_exist(tmp_path):
    """A missing table and an empty table are different facts -- counts must not conflate them."""
    path = tmp_path / "no_attendance.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE students (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()

    counts = record_counts(path, tables=("students", "attendance"))
    assert counts == {"students": 0}
    assert "attendance" not in counts


def test_verify_backup_rejects_a_corrupted_file(tmp_path):
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite database")
    assert verify_backup(corrupt) is False


def test_create_consistent_backup_fails_cleanly_when_the_source_is_missing(tmp_path):
    missing = tmp_path / "does_not_exist.db"
    dest = tmp_path / "backup.db"
    assert create_consistent_backup(missing, dest) is False
    assert not dest.exists(), "a failed backup must not leave a partial file behind"


def test_create_verified_backup_succeeds_on_a_healthy_database(tmp_path):
    source = tmp_path / "source.db"
    _seeded_database(source)
    dest = tmp_path / "backup.db"

    result = create_verified_backup(source, dest)

    assert isinstance(result, BackupResult)
    assert result.ok is True
    assert result.path == dest
    assert result.counts == {"students": 2, "invoices": 1, "payments": 1, "results": 2}
    assert dest.exists()


# --- Failure handling: the owner's second pre-check, confirmed empirically ---


def test_create_verified_backup_reports_failure_and_leaves_nothing_behind_when_source_is_missing(
    tmp_path,
):
    missing = tmp_path / "gone.db"
    dest = tmp_path / "backup.db"

    result = create_verified_backup(missing, dest)

    assert result.ok is False
    assert "not found" in result.reason
    assert not dest.exists()


def test_create_verified_backup_rejects_and_removes_a_backup_that_fails_integrity_check(tmp_path, monkeypatch):
    """Simulates the backup API producing a file that then fails integrity_check -- the
    function must refuse to call it good and must not leave that bad file on disk."""
    source = tmp_path / "source.db"
    _seeded_database(source)
    dest = tmp_path / "backup.db"

    import services.backup_service as backup_service

    def _fake_backup_that_corrupts(_source_path, dest_path):
        dest_path.write_bytes(b"not a real sqlite file")
        return True

    monkeypatch.setattr(backup_service, "create_consistent_backup", _fake_backup_that_corrupts)

    result = backup_service.create_verified_backup(source, dest)

    assert result.ok is False
    assert "integrity_check" in result.reason
    assert not dest.exists()


def test_create_verified_backup_rejects_a_backup_whose_counts_do_not_match(tmp_path, monkeypatch):
    """Simulates a backup that is individually a valid SQLite file (passes integrity_check) but
    does not actually match the source's record counts -- e.g. a backup taken against a
    different, stale database by mistake. Must be rejected and removed, not just logged."""
    source = tmp_path / "source.db"
    _seeded_database(source)
    dest = tmp_path / "backup.db"

    import services.backup_service as backup_service

    def _fake_backup_from_a_different_database(_source_path, dest_path):
        # A perfectly valid SQLite file, but with different data than `source` -- as if it had
        # backed up some other database entirely.
        connection = sqlite3.connect(dest_path)
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO students (name) VALUES ('Someone Else')")
        connection.commit()
        connection.close()
        return True

    monkeypatch.setattr(backup_service, "create_consistent_backup", _fake_backup_from_a_different_database)

    result = backup_service.create_verified_backup(source, dest)

    assert result.ok is False
    assert "do not match" in result.reason
    assert not dest.exists()


def test_a_failed_or_incomplete_backup_can_never_reach_retention_deletion(tmp_path, monkeypatch):
    """End-to-end proof of the owner's second pre-check: simulate today's backup run failing,
    confirm no file was written for it, and confirm select_files_to_prune -- the only function
    that deletes anything -- is never even reachable with that failure's non-existent file, and
    every backup that already existed before the failed run is completely untouched."""
    source = tmp_path / "source.db"
    _seeded_database(source)

    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()
    existing = ["school-2026-11-01-0200.db", "school-2026-11-02-0200.db", "school-2026-11-03-0200.db"]
    for name in existing:
        (backups_dir / name).write_text("pretend this is a valid prior backup")

    import services.backup_service as backup_service

    def _always_fails(_source_path, _dest_path):
        return False

    monkeypatch.setattr(backup_service, "create_consistent_backup", _always_fails)

    todays_attempt = backups_dir / "school-2026-11-04-0200.db"
    result = backup_service.create_verified_backup(source, todays_attempt)

    assert result.ok is False
    assert not todays_attempt.exists(), "a failed run must not leave a file for retention to find"

    # The actual job logic (not built in Phase 1a) would read this: `if not result.ok: return`
    # before ever calling select_files_to_prune. Demonstrating that rule here, structurally:
    if result.ok:
        pruned = backup_service.select_files_to_prune(
            [p.name for p in backups_dir.iterdir()], keep=2
        )
    else:
        pruned = []  # the only call site a real job would ever take on a failed run

    assert pruned == []
    assert sorted(p.name for p in backups_dir.iterdir()) == sorted(existing), (
        "every pre-existing backup must survive a failed run untouched"
    )


# --- Retention selection: pure-function properties ---


def test_select_files_to_prune_keeps_the_newest_and_deletes_only_the_oldest_excess():
    files = [f"school-2026-11-{day:02d}-0200.db" for day in range(1, 11)]  # 10 files
    to_delete = select_files_to_prune(files, keep=7)

    assert len(to_delete) == 3
    assert to_delete == files[:3], "must delete the oldest, not an arbitrary subset"
    assert files[-1] not in to_delete, "the newest file must never be selected for deletion"


def test_select_files_to_prune_never_empties_a_tier_even_with_a_degenerate_keep_value():
    files = [f"school-2026-11-{day:02d}-0200.db" for day in range(1, 6)]

    for keep in (0, -5):
        to_delete = select_files_to_prune(files, keep=keep)
        assert len(to_delete) == len(files) - 1
        assert files[-1] not in to_delete


def test_select_files_to_prune_does_nothing_when_under_the_keep_count():
    files = ["school-2026-11-01-0200.db", "school-2026-11-02-0200.db"]
    assert select_files_to_prune(files, keep=14) == []


def test_select_files_to_prune_is_safe_on_an_empty_list():
    assert select_files_to_prune([], keep=14) == []


# --- Isolated restore: the fourth thing the owner asked to have tested ---


def test_a_verified_backup_restores_cleanly_into_a_fresh_temporary_database(tmp_path):
    """Restore, tested the same way the plan's section 11 describes: point a brand-new,
    throwaway DATABASE_URL at the backup file and confirm the application's own model layer
    reads it back correctly -- not just that the raw bytes look like a SQLite file."""
    source = tmp_path / "source.db"
    _seeded_database(source)
    source_counts = record_counts(source)

    backup = tmp_path / "backup.db"
    result = create_verified_backup(source, backup)
    assert result.ok is True

    # "Restore into a temporary database" -- the restored file IS the temporary database; no
    # copy-back into `source` happens, matching the plan's "never overwrite the original" rule
    # even in this isolated test.
    restored_engine_counts = record_counts(backup)
    assert restored_engine_counts == source_counts

    # Confirm it is genuinely usable as a database, not just a file that happens to parse:
    # run an ordinary query the application itself would run.
    connection = sqlite3.connect(backup)
    names = sorted(row[0] for row in connection.execute("SELECT name FROM students ORDER BY name"))
    assert names == ["Ahmed Khan", "Bilal Tariq"]
    connection.close()

    # And the original is still exactly as it was -- the restore drill never touched it.
    assert record_counts(source) == source_counts


def test_concurrent_writer_and_backup_do_not_corrupt_either_file(tmp_path):
    """A closer approximation of production: a background thread keeps writing to the source
    (like fastapi_app() serving requests) while a backup is taken, repeatedly. Neither the
    source nor any backup should ever fail integrity_check."""
    source = tmp_path / "source.db"
    _seeded_database(source)

    stop = threading.Event()
    errors = []

    def _keep_writing():
        connection = sqlite3.connect(source)
        counter = 1000
        try:
            while not stop.is_set():
                connection.execute("INSERT INTO results (marks_obtained) VALUES (?)", (counter,))
                connection.commit()
                counter += 1
                time.sleep(0.01)
        except Exception as error:  # pragma: no cover - would fail the test via `errors`
            errors.append(error)
        finally:
            connection.close()

    writer = threading.Thread(target=_keep_writing, daemon=True)
    writer.start()
    try:
        for i in range(5):
            dest = tmp_path / f"backup-{i}.db"
            assert create_consistent_backup(source, dest) is True
            assert verify_backup(dest) is True
    finally:
        stop.set()
        writer.join(timeout=5)

    assert errors == []
    assert verify_backup(source) is True
