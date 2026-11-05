"""Upgrades an existing database, safely. Reports only, unless --apply is given.

    python migrate_db.py                   # report on the database DATABASE_URL points to
    python migrate_db.py path/to/school.db --apply

What --apply does: backs up the file next to itself, then adds a unique index so a student
cannot have two challans for one month. No rows and no columns change. It stops, changing
nothing, if duplicates already exist, because deciding which challan is right takes a person.

Rollback: restore the backup file, or run  DROP INDEX uq_invoices_student_month;
Older code ignores the index.

This reads no application secrets, so it can run without the app's settings.
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from models.fee import INVOICE_STUDENT_MONTH_INDEX as INDEX_NAME
from services.fee_ledger import parse_due_date

ROW_LIMIT = 50


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


def _duplicates(connection: sqlite3.Connection) -> List[Tuple]:
    return connection.execute(
        """
        SELECT student_id, month, count(*), group_concat(challan_number, ', ')
        FROM invoices GROUP BY student_id, month HAVING count(*) > 1
        """
    ).fetchall()


def _report(connection: sqlite3.Connection) -> List[Tuple]:
    """Prints what a person should know about. Only duplicates block the upgrade."""
    paid_sums = "SELECT invoice_id, sum(amount_paid) AS paid FROM payments GROUP BY invoice_id"
    duplicates = _duplicates(connection)
    _print_section("Students with two challans for one month (student, month, count, challans)", duplicates)
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
    return duplicates


def _index_exists(connection: sqlite3.Connection) -> bool:
    return (
        connection.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (INDEX_NAME,)).fetchone()
        is not None
    )


def _totals(connection: sqlite3.Connection) -> Tuple:
    return connection.execute(
        """
        SELECT (SELECT count(*) FROM invoices), (SELECT count(*) FROM payments),
               (SELECT sum(amount) FROM invoices), (SELECT sum(amount_paid) FROM payments)
        """
    ).fetchone()


def _backup(connection: sqlite3.Connection, database: Path) -> Path:
    target = database.with_name(f"{database.name}.backup-{datetime.now():%Y%m%d-%H%M%S}")
    with sqlite3.connect(target) as backup_connection:
        connection.backup(backup_connection)
    backup_connection.close()
    return target


def _apply(database: Path) -> int:
    connection = sqlite3.connect(database)
    try:
        if _index_exists(connection):
            print("\nAlready upgraded. Nothing to do.")
            return 0
        if _duplicates(connection):
            print("\nStopped: resolve the duplicate challans listed above. Nothing was changed.")
            return 1

        before = _totals(connection)
        backup_path = _backup(connection, database)
        print(f"\nBackup written: {backup_path}")

        connection.execute(f"CREATE UNIQUE INDEX {INDEX_NAME} ON invoices (student_id, month)")
        connection.commit()

        if _totals(connection) != before:
            print(f"\nERROR: totals changed. Restore {backup_path}.")
            return 1
        print(f"Upgrade complete. Invoices, payments and money totals are unchanged: {before}")
        return 0
    finally:
        connection.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Report on and upgrade an EduCore database.")
    parser.add_argument("database", nargs="?", type=Path, default=None)
    parser.add_argument("--apply", action="store_true", help="back up, then add the index")
    arguments = parser.parse_args(argv)

    database = arguments.database or _default_database()
    if not database.is_file():
        print(f"Database not found: {database}")
        return 1

    print(f"Database: {database}")
    read_only = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    try:
        _report(read_only)
    finally:
        read_only.close()

    if arguments.apply:
        return _apply(database)
    print("\nReport only. Nothing was changed. Add --apply to upgrade.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
