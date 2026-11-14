"""Adds one academic session to a database, never as the current one. Reports only unless --apply.

    python add_academic_session.py path/to/school.db 2026-2027           # report
    python add_academic_session.py path/to/school.db 2026-2027 --apply   # back up, then add

It adds one row to academic_years with is_current = 0. It never changes an existing row, so the
current session stays as it is. It stops if the label already exists or is not like 2026-2027.
Rollback: delete that one row (nothing refers to it until an application is saved against it).
This reads no application secrets.
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

from services.backup_service import create_consistent_backup


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("label")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    match = re.fullmatch(r"(\d{4})-(\d{4})", args.label)
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        print(f"'{args.label}' is not a session label like 2026-2027.")
        return 2
    if not args.database.exists():
        print(f"{args.database} does not exist.")
        return 2

    connection = sqlite3.connect(args.database)
    try:
        before = connection.execute("SELECT id, label, is_current FROM academic_years ORDER BY id").fetchall()
        print("Sessions now:", before)
        if any(row[1] == args.label for row in before):
            print(f"{args.label} already exists. Nothing to do.")
            return 0
        if not args.apply:
            print(f"Report only. --apply would add {args.label} with is_current = 0.")
            return 0

        backup = args.database.with_name(args.database.name + ".backup-before-session-" + args.label)
        if not create_consistent_backup(args.database, backup):
            print("The backup failed, so nothing was changed.")
            return 1
        print("Backed up to", backup.name)

        with connection:
            connection.execute("INSERT INTO academic_years (label, is_current) VALUES (?, 0)", (args.label,))
        after = connection.execute("SELECT id, label, is_current FROM academic_years ORDER BY id").fetchall()
        print("Sessions after:", after)
        unchanged = [row for row in after if row[1] != args.label] == before
        added = [row for row in after if row[1] == args.label]
        if not unchanged or len(added) != 1 or added[0][2] != 0:
            print("CHECK FAILED: existing sessions changed or the new one is wrong. Restore the backup.")
            return 1
        print("Done. The current session is unchanged.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
