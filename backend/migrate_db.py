"""Upgrades an existing database, safely. Reports only, unless --apply is given.

    python migrate_db.py                   # report on the database DATABASE_URL points to
    python migrate_db.py path/to/school.db --apply

What --apply does: backs up the file next to itself, then makes these additive changes, all or
nothing. No existing rows change.
  - students.archived_at: a new empty column. Empty means the student is active.
  - One challan per student per month, enforced by a unique index.
  - One mark per student, subject, exam, and year, enforced by a unique index.

It stops, changing nothing, if duplicates already exist, because deciding which record is right
takes a person.

Run this BEFORE deploying code that needs it. The app refuses to start on a database without the
new column. Older code ignores all three changes, so upgrading first is safe.

Rollback: restore the backup file. Or run:
    DROP INDEX uq_invoices_student_month;
    DROP INDEX uq_results_student_subject_exam_year;
    (The empty column can stay. Older code ignores it.)

This reads no application secrets, so it can run without the app's settings.
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from models.fee import INVOICE_STUDENT_MONTH_INDEX
from models.result import ExamType, RESULT_UNIQUE_INDEX
from services.fee_ledger import parse_due_date

ROW_LIMIT = 50
ARCHIVE_COLUMN = "archived_at"
VALID_EXAM_TYPES = ExamType.__args__


def _default_database() -> Path:
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("sqlite:///"):
        return Path(url.removeprefix("sqlite:///"))
    return Path(__file__).resolve().parent / "school.db"


def _print_section(title: str, rows: List[Tuple]) -> None:
    print(f"\n{title}: {len(rows)}")
    for row in rows[:ROW_LIMIT]:
        print("   ", " | ".join(str(value) for value in row))
    if len(rows) > ROW_LIMIT:
        print(f"    ...and {len(rows) - ROW_LIMIT} more")


def _duplicate_challans(connection: sqlite3.Connection) -> List[Tuple]:
    return connection.execute(
        """
        SELECT student_id, month, count(*), group_concat(challan_number, ', ')
        FROM invoices GROUP BY student_id, month HAVING count(*) > 1
        """
    ).fetchall()


def _duplicate_marks(connection: sqlite3.Connection) -> List[Tuple]:
    return connection.execute(
        """
        SELECT student_id, subject, exam_type, academic_year_id, count(*)
        FROM results GROUP BY student_id, subject, exam_type, academic_year_id HAVING count(*) > 1
        """
    ).fetchall()


def _report_fees(connection: sqlite3.Connection) -> None:
    paid_sums = "SELECT invoice_id, sum(amount_paid) AS paid FROM payments GROUP BY invoice_id"
    _print_section(
        "Students with two challans for one month (student, month, count, challans)",
        _duplicate_challans(connection),
    )
    _print_section(
        "Invoices marked paid with no payment recorded (challan, amount)",
        connection.execute(
            f"""
            SELECT i.challan_number, i.amount FROM invoices i
            LEFT JOIN ({paid_sums}) p ON p.invoice_id = i.id
            WHERE i.status = 'paid' AND p.paid IS NULL
            """
        ).fetchall(),
    )
    _print_section(
        "Invoices paid more than invoiced (challan, amount, recorded)",
        connection.execute(
            f"""
            SELECT i.challan_number, i.amount, p.paid FROM invoices i
            JOIN ({paid_sums}) p ON p.invoice_id = i.id WHERE p.paid > i.amount
            """
        ).fetchall(),
    )
    _print_section(
        "Invoices marked paid but not fully paid (challan, amount, recorded)",
        connection.execute(
            f"""
            SELECT i.challan_number, i.amount, p.paid FROM invoices i
            JOIN ({paid_sums}) p ON p.invoice_id = i.id WHERE i.status = 'paid' AND p.paid < i.amount
            """
        ).fetchall(),
    )
    _print_section(
        "Invoices with an unreadable due date, never shown as overdue (challan, due date)",
        [
            (challan, due_date)
            for challan, due_date in connection.execute("SELECT challan_number, due_date FROM invoices")
            if parse_due_date(due_date) is None
        ],
    )


def _report_marks(connection: sqlite3.Connection) -> None:
    _print_section(
        "Marks entered twice for one exam (student, subject, exam, year, count)",
        _duplicate_marks(connection),
    )
    _print_section(
        "Marks that cannot be right (student, subject, obtained, total)",
        connection.execute(
            """
            SELECT student_id, subject, marks_obtained, total_marks FROM results
            WHERE total_marks <= 0 OR marks_obtained < 0 OR marks_obtained > total_marks
            """
        ).fetchall(),
    )
    _print_section(
        "Marks with an unknown exam type, shown only under that name (student, subject, exam)",
        [row for row in connection.execute("SELECT student_id, subject, exam_type FROM results")
         if row[2] not in VALID_EXAM_TYPES],
    )


def _index_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone()
        is not None
    )


def _column_exists(connection: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in connection.execute(f"PRAGMA table_info({table})"))


def _pending_changes(connection: sqlite3.Connection) -> List[str]:
    """The SQL still needed, in the order to run it."""
    changes = []
    if not _column_exists(connection, "students", ARCHIVE_COLUMN):
        changes.append(f"ALTER TABLE students ADD COLUMN {ARCHIVE_COLUMN} DATETIME")
    if not _index_exists(connection, INVOICE_STUDENT_MONTH_INDEX):
        changes.append(f"CREATE UNIQUE INDEX {INVOICE_STUDENT_MONTH_INDEX} ON invoices (student_id, month)")
    if not _index_exists(connection, RESULT_UNIQUE_INDEX):
        changes.append(
            f"CREATE UNIQUE INDEX {RESULT_UNIQUE_INDEX} ON results (student_id, subject, exam_type, academic_year_id)"
        )
    return changes


def _totals(connection: sqlite3.Connection) -> Tuple:
    return connection.execute(
        """
        SELECT (SELECT count(*) FROM students), (SELECT count(*) FROM invoices), (SELECT count(*) FROM payments),
               (SELECT count(*) FROM results), (SELECT sum(amount) FROM invoices),
               (SELECT sum(amount_paid) FROM payments), (SELECT sum(marks_obtained) FROM results)
        """
    ).fetchone()


def _backup(connection: sqlite3.Connection, database: Path) -> Path:
    target = database.with_name(f"{database.name}.backup-{datetime.now():%Y%m%d-%H%M%S}")
    with sqlite3.connect(target) as backup_connection:
        connection.backup(backup_connection)
    backup_connection.close()
    return target


def _apply(database: Path) -> int:
    connection = sqlite3.connect(database, isolation_level=None)
    try:
        changes = _pending_changes(connection)
        if not changes:
            print("\nAlready upgraded. Nothing to do.")
            return 0
        if _duplicate_challans(connection) or _duplicate_marks(connection):
            print("\nStopped: resolve the duplicates listed above. Nothing was changed.")
            return 1

        before = _totals(connection)
        backup_path = _backup(connection, database)
        print(f"\nBackup written: {backup_path}")

        connection.execute("BEGIN IMMEDIATE")
        try:
            for change in changes:
                connection.execute(change)
            connection.execute("COMMIT")
        except sqlite3.Error as error:
            connection.execute("ROLLBACK")
            print(f"\nERROR: {error}. Nothing was changed.")
            return 1

        if _totals(connection) != before:
            print(f"\nERROR: totals changed. Restore {backup_path}.")
            return 1
        print(f"Upgrade complete. Record counts and totals are unchanged: {before}")
        return 0
    finally:
        connection.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Report on and upgrade an EduCore database.")
    parser.add_argument("database", nargs="?", type=Path, default=None)
    parser.add_argument("--apply", action="store_true", help="back up, then make the additive changes")
    arguments = parser.parse_args(argv)

    database = arguments.database or _default_database()
    if not database.is_file():
        print(f"Database not found: {database}")
        return 1

    print(f"Database: {database}")
    read_only = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    try:
        _report_fees(read_only)
        _report_marks(read_only)
        pending = _pending_changes(read_only)
    finally:
        read_only.close()

    if arguments.apply:
        return _apply(database)
    if pending:
        print(f"\nReport only. Nothing was changed. {len(pending)} change(s) waiting. Add --apply to upgrade.")
    else:
        print("\nReport only. Nothing was changed. This database is already upgraded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
