"""Daily backup job logic, decoupled from Modal so it can be tested with plain directories.

Implements the algorithm specified in EDUCORE_AI_PHASE_1_DATABASE_PROTECTION_PLAN.md section
7a.3: one verified daily backup, then weekly/monthly promotion and per-tier retention, all gated
on that day's backup having passed `create_verified_backup` first.

This module only ever sees local `Path`s. `modal_app.py`'s scheduled function passes it the real
mount points (`/data/school.db`, read-only; `/backups`, the educore-backups Volume) when it runs
on Modal; tests pass temporary directories instead. Neither this module nor its tests create,
read, or write anything on Modal itself -- see modal_app.py for the wiring (live on Modal since 2026-11-13).
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from zoneinfo import ZoneInfo

from .backup_service import create_verified_backup, select_files_to_prune

KARACHI = ZoneInfo("Asia/Karachi")
DAILY_KEEP, WEEKLY_KEEP, MONTHLY_KEEP = 14, 8, 12
TIERS = ("daily", "weekly", "monthly")


@dataclass
class BackupJobResult:
    """What happened on one run. `reason` is only meaningful when `ok` is False."""

    ok: bool
    reason: Optional[str] = None
    daily_path: Optional[Path] = None
    promoted: List[str] = field(default_factory=list)
    pruned: List[str] = field(default_factory=list)


def run_daily_backup_job(source_db: Path, backups_root: Path, now: Optional[datetime] = None) -> BackupJobResult:
    """Runs one backup cycle.

    `source_db` is read-only from this function's point of view -- `create_verified_backup`
    (see backup_service.py) opens it through SQLite's `mode=ro` URI flag, so this function
    cannot write to it even by mistake. Every write this function makes lands under
    `backups_root`, in one of `daily/`, `weekly/`, or `monthly/`.

    A failed or unverified backup stops here, before any tier promotion or pruning runs, so an
    existing good backup in any tier is never at risk because today's run went wrong.
    """
    now = (now or datetime.now(KARACHI)).astimezone(KARACHI)
    for tier in TIERS:
        (backups_root / tier).mkdir(parents=True, exist_ok=True)

    stamp = now.strftime("%Y-%m-%d-%H%M")
    daily_path = backups_root / "daily" / f"school-{stamp}.db"
    result = create_verified_backup(source_db, daily_path)
    if not result.ok:
        return BackupJobResult(ok=False, reason=result.reason)

    promoted: List[str] = []
    if now.weekday() == 0:  # Monday, Karachi-local date
        iso_year, iso_week, _ = now.isocalendar()
        weekly_path = backups_root / "weekly" / f"school-{iso_year}-week{iso_week:02d}.db"
        shutil.copyfile(daily_path, weekly_path)
        promoted.append(str(weekly_path))

    if now.day == 1:  # first of the month, Karachi-local date
        monthly_path = backups_root / "monthly" / f"school-{now.strftime('%Y-%m')}.db"
        shutil.copyfile(daily_path, monthly_path)
        promoted.append(str(monthly_path))

    pruned: List[str] = _prune_tier(backups_root / "daily", DAILY_KEEP)
    if now.weekday() == 0:
        pruned += _prune_tier(backups_root / "weekly", WEEKLY_KEEP)
    if now.day == 1:
        pruned += _prune_tier(backups_root / "monthly", MONTHLY_KEEP)

    return BackupJobResult(ok=True, daily_path=daily_path, promoted=promoted, pruned=pruned)


def _prune_tier(tier_dir: Path, keep: int) -> List[str]:
    names = [p.name for p in tier_dir.glob("*.db")]
    to_delete = select_files_to_prune(names, keep)
    for name in to_delete:
        (tier_dir / name).unlink()
    return to_delete
