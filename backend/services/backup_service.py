"""Reusable SQLite backup helper, built on the Online Backup API.

`migrate_db.py` already did this correctly, once, for its own pre-migration safety copy. This
module is that same technique (`sqlite3.Connection.backup()`, not a raw file copy), shared so a
later caller (a scheduled backup job) uses one tested implementation instead of a second copy of
the logic. See EDUCORE_AI_PHASE_1_DATABASE_PROTECTION_PLAN.md for the design this implements.

Safety, proved rather than assumed:
  - The source is opened through SQLite's own `mode=ro` URI flag. A `mode=ro` connection refuses
    any write at the SQLite driver level ("attempt to write a readonly database") -- this module
    cannot modify the source database even if a bug in it tried to. Confirmed directly: see
    `test_backup_service.py::test_the_read_only_source_connection_cannot_write`.
  - The Online Backup API only ever copies committed data. A transaction left open and
    uncommitted on another connection to the same file is invisible to the backup, proved the same
    way: `test_backup_service.py::test_an_uncommitted_change_on_another_connection_is_not_copied`.
  - Retention deletion is a separate function (`select_files_to_prune`) that knows nothing about
    whether "today's" backup succeeded. The only caller-side rule that keeps a failed run from
    deleting anything is: never call it unless `create_verified_backup(...).ok` is True. This
    module enforces the first half (a failed or unverified backup is never left on disk to be
    retained or counted -- see `create_verified_backup`); the caller enforces the second half by
    construction, which `test_backup_service.py` demonstrates end to end.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence

# The tables this project actually has. No "attendance" table exists anywhere in this codebase
# (confirmed in EDUCORE_AI_SECOND_LEVEL_VERIFICATION.md and the protection plan) -- listing it
# here would silently always report a zero count rather than flag that the table does not exist.
TABLES_TO_COUNT: Sequence[str] = ("students", "invoices", "payments", "results")


@dataclass
class BackupResult:
    """What happened when trying to create one verified backup.

    `path` and `counts` are only meaningful when `ok` is True. A caller must never treat a
    failed result's `path` as something to keep, retain, or count towards a tier's history --
    `create_verified_backup` already deletes the partial/invalid file before returning, so in
    practice there is nothing left at `path` to mistakenly keep.
    """

    ok: bool
    path: Path | None = None
    reason: str | None = None
    counts: Dict[str, int] = field(default_factory=dict)


def _read_only_uri(path: Path) -> str:
    return f"{path.resolve().as_uri()}?mode=ro"


def create_consistent_backup(source_path: Path, dest_path: Path) -> bool:
    """Copies source_path to dest_path with SQLite's Online Backup API.

    The source connection is opened read-only (`mode=ro`), so this call cannot write to
    source_path under any circumstance -- SQLite's own driver refuses the write, not just this
    function's own discipline. Safe to call while another connection holds the source file open
    for writing, including mid-transaction: the backup only ever sees that connection's last
    committed state, never an in-progress write.

    Returns True on success. On any failure, removes whatever partial file may have been left at
    dest_path and returns False -- a failed attempt never leaves a half-written file behind for
    something else to mistake for a real backup.
    """
    # sqlite3.Connection's context manager only commits/rolls back a transaction -- it does NOT
    # close the connection (that is Python's own documented behavior, not an oversight here).
    # Every connection this module opens is therefore closed explicitly, in `finally`, so no
    # open file handle is ever left on a read-only source or a just-written backup. Besides
    # being a plain resource leak, an open handle left on `educore-data` is exactly what would
    # make a later `Volume.reload()` fail with "volume busy", per Modal's own documented
    # behavior (quoted in EDUCORE_AI_PHASE_1_DATABASE_PROTECTION_PLAN.md section 6) -- so this
    # is not a style preference, it is required for this module to be safe to use on a Volume.
    source = None
    dest = None
    succeeded = False
    try:
        source = sqlite3.connect(_read_only_uri(source_path), uri=True)
        dest = sqlite3.connect(dest_path)
        source.backup(dest)
        succeeded = True
        return True
    except sqlite3.Error:
        return False
    finally:
        if dest is not None:
            dest.close()
        if source is not None:
            source.close()
        if not succeeded:
            dest_path.unlink(missing_ok=True)


def verify_backup(path: Path) -> bool:
    """True only if SQLite's own `PRAGMA integrity_check` reports exactly `ok`.

    Opens the file read-only: verifying a backup never needs, and must never risk, a write to it.
    The connection is always closed, including on error -- see the note in
    `create_consistent_backup` about why a leaked handle is not just a style issue here.
    """
    connection = None
    try:
        connection = sqlite3.connect(_read_only_uri(path), uri=True)
        row = connection.execute("PRAGMA integrity_check").fetchone()
        return row is not None and row[0] == "ok"
    except sqlite3.Error:
        return False
    finally:
        if connection is not None:
            connection.close()


def record_counts(path: Path, tables: Sequence[str] = TABLES_TO_COUNT) -> Dict[str, int]:
    """Row counts for the given tables, read-only. A table that does not exist is left out,
    never reported as zero -- a missing table and an empty table are different facts."""
    counts: Dict[str, int] = {}
    connection = sqlite3.connect(_read_only_uri(path), uri=True)
    try:
        existing = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for table in tables:
            if table in existing:
                counts[table] = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]  # noqa: S608
    finally:
        connection.close()
    return counts


def create_verified_backup(source_path: Path, dest_path: Path) -> BackupResult:
    """Creates a backup and only calls it good once integrity_check and record counts agree.

    Never leaves an unverified or partial file at dest_path: any failure here, at any step,
    removes whatever was written and returns ok=False with a plain-language reason. A caller is
    expected to treat `ok=False` as "stop here, touch nothing else, alert" -- see
    EDUCORE_AI_PHASE_1_DATABASE_PROTECTION_PLAN.md section 7a.3 for the full job this backs.
    """
    if not source_path.is_file():
        return BackupResult(ok=False, reason=f"source database not found: {source_path}")

    if not create_consistent_backup(source_path, dest_path):
        return BackupResult(ok=False, reason="backup creation failed")

    if not verify_backup(dest_path):
        dest_path.unlink(missing_ok=True)
        return BackupResult(ok=False, reason="backup failed integrity_check")

    source_counts = record_counts(source_path)
    backup_counts = record_counts(dest_path)
    if source_counts != backup_counts:
        dest_path.unlink(missing_ok=True)
        return BackupResult(
            ok=False,
            reason=f"record counts do not match: source={source_counts} backup={backup_counts}",
        )

    return BackupResult(ok=True, path=dest_path, counts=backup_counts)


def select_files_to_prune(filenames: List[str], keep: int) -> List[str]:
    """Which of these backup filenames to delete, oldest first -- never all of them.

    `filenames` are plain names, not full paths, and are expected to sort correctly in date order
    as plain strings (this project's naming scheme, `school-YYYY-MM-DD-HHMM.db`, does, by
    construction -- no date parsing is needed or attempted here, which is one less way this
    function's idea of "oldest" could disagree with whatever wrote the names).

    Always leaves at least one file behind, regardless of `keep`, even if `keep` is 0 or
    negative: the deletable slice is explicitly capped at `len(filenames) - 1`. This function has
    no notion of "today's run failed" -- that is enforced by the caller never calling this at
    all unless the run that just finished was a verified success (see `create_verified_backup`
    and this module's docstring).
    """
    ordered = sorted(filenames)
    excess = len(ordered) - max(keep, 0)
    if excess <= 0:
        return []
    return ordered[: min(excess, len(ordered) - 1)]
