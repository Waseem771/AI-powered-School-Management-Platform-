"""Tests for services/backup_job.py.

Everything here runs against temporary directories under pytest's `tmp_path`, standing in for
the real educore-data file and the educore-backups Volume's mount point. None of this imports
Modal, creates any Modal resource, or touches school.db -- see services/backup_job.py's
docstring for why that separation is possible.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from services.backup_job import KARACHI, run_daily_backup_job

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
    connection.execute("INSERT INTO invoices (amount) VALUES (3500)")
    connection.execute("INSERT INTO payments (amount_paid) VALUES (3500)")
    connection.execute("INSERT INTO results (marks_obtained) VALUES (78)")
    connection.commit()
    connection.close()


def _tuesday_noon() -> datetime:
    # 2026-11-17 is a Tuesday: neither a weekly (Monday) nor monthly (1st) promotion day.
    return datetime(2026, 11, 17, 12, 0, tzinfo=KARACHI)


def _monday() -> datetime:
    # 2026-11-16 is a Monday, not the 1st of the month.
    return datetime(2026, 11, 16, 2, 0, tzinfo=KARACHI)


def _first_of_month_not_monday() -> datetime:
    # 2026-12-01 is a Tuesday: the 1st of the month, but not a Monday.
    return datetime(2026, 12, 1, 2, 0, tzinfo=KARACHI)


def test_an_ordinary_day_writes_only_a_daily_backup(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    backups = tmp_path / "backups"

    result = run_daily_backup_job(source, backups, now=_tuesday_noon())

    assert result.ok is True
    assert result.daily_path.is_file()
    assert result.promoted == []
    assert list((backups / "weekly").glob("*.db")) == []
    assert list((backups / "monthly").glob("*.db")) == []


def test_a_monday_also_promotes_to_weekly(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    backups = tmp_path / "backups"

    result = run_daily_backup_job(source, backups, now=_monday())

    assert result.ok is True
    assert len(result.promoted) == 1
    weekly_files = list((backups / "weekly").glob("*.db"))
    assert len(weekly_files) == 1
    assert weekly_files[0].read_bytes() == result.daily_path.read_bytes()
    assert list((backups / "monthly").glob("*.db")) == []


def test_the_first_of_the_month_also_promotes_to_monthly(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    backups = tmp_path / "backups"

    result = run_daily_backup_job(source, backups, now=_first_of_month_not_monday())

    assert result.ok is True
    assert len(result.promoted) == 1
    assert list((backups / "weekly").glob("*.db")) == []
    monthly_files = list((backups / "monthly").glob("*.db"))
    assert len(monthly_files) == 1


def test_a_monday_that_is_also_the_first_promotes_to_both_tiers(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    backups = tmp_path / "backups"
    monday_the_first = datetime(2026, 6, 1, 2, 0, tzinfo=KARACHI)
    assert monday_the_first.weekday() == 0 and monday_the_first.day == 1

    result = run_daily_backup_job(source, backups, now=monday_the_first)

    assert result.ok is True
    assert len(result.promoted) == 2
    assert len(list((backups / "weekly").glob("*.db"))) == 1
    assert len(list((backups / "monthly").glob("*.db"))) == 1


def test_a_missing_source_fails_the_run_and_writes_nothing(tmp_path):
    source = tmp_path / "does-not-exist.db"
    backups = tmp_path / "backups"

    result = run_daily_backup_job(source, backups, now=_monday())

    assert result.ok is False
    assert result.reason is not None
    # Tier directories may be created, but no backup file exists in any of them.
    for tier in ("daily", "weekly", "monthly"):
        tier_dir = backups / tier
        assert not tier_dir.exists() or list(tier_dir.glob("*.db")) == []


def test_a_failed_run_never_touches_an_existing_good_backup_in_any_tier(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    backups = tmp_path / "backups"

    good_run = run_daily_backup_job(source, backups, now=_monday())
    assert good_run.ok is True
    daily_before = good_run.daily_path.read_bytes()
    weekly_before = list((backups / "weekly").glob("*.db"))[0].read_bytes()

    # Now the source disappears (simulating a corrupted/missing mount on a later run).
    source.unlink()
    failed_run = run_daily_backup_job(source, backups, now=_tuesday_noon())

    assert failed_run.ok is False
    assert good_run.daily_path.read_bytes() == daily_before
    assert list((backups / "weekly").glob("*.db"))[0].read_bytes() == weekly_before


def test_daily_retention_keeps_14_and_prunes_the_rest(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    backups = tmp_path / "backups"

    for day in range(1, 21):  # 20 consecutive days, none a Monday or the 1st on purpose
        day_dt = datetime(2026, 3, day, 2, 0, tzinfo=KARACHI)
        if day_dt.weekday() == 0 or day_dt.day == 1:
            continue
        run_daily_backup_job(source, backups, now=day_dt)

    daily_files = list((backups / "daily").glob("*.db"))
    assert len(daily_files) <= 14
    assert len(daily_files) >= 1


def test_the_newest_backup_in_a_tier_is_never_pruned(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    backups = tmp_path / "backups"

    last_result = None
    for day in range(1, 31):
        day_dt = datetime(2026, 4, day, 2, 0, tzinfo=KARACHI)
        if day_dt.weekday() == 0 or day_dt.day == 1:
            continue
        last_result = run_daily_backup_job(source, backups, now=day_dt)

    assert last_result is not None
    assert last_result.daily_path.is_file(), "the most recent backup must survive pruning"


def test_weekly_and_monthly_retention_are_independent_of_the_daily_tier(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    backups = tmp_path / "backups"

    for month in range(1, 13):
        run_daily_backup_job(source, backups, now=datetime(2026, month, 1, 2, 0, tzinfo=KARACHI))

    monthly_files = list((backups / "monthly").glob("*.db"))
    assert len(monthly_files) == 12  # exactly at MONTHLY_KEEP, nothing pruned yet
    assert all(f.is_file() for f in monthly_files)


def test_a_naive_or_differently_zoned_datetime_is_converted_to_karachi_before_any_date_decision(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    backups = tmp_path / "backups"

    # 2026-11-15 23:30 UTC is 2026-11-16 04:30 in Karachi (UTC+5) -- a Monday there, even
    # though the UTC calendar date is still Sunday. If the job used the UTC date directly,
    # this would wrongly skip the weekly promotion.
    utc_instant = datetime(2026, 11, 15, 23, 30, tzinfo=ZoneInfo("UTC"))
    assert utc_instant.astimezone(KARACHI).weekday() == 0

    result = run_daily_backup_job(source, backups, now=utc_instant)

    assert result.ok is True
    assert len(result.promoted) == 1
    assert list((backups / "weekly").glob("*.db"))


def test_source_is_never_written_to(tmp_path):
    source = tmp_path / "school.db"
    _seeded_database(source)
    before = source.read_bytes()
    backups = tmp_path / "backups"

    run_daily_backup_job(source, backups, now=_monday())

    assert source.read_bytes() == before
