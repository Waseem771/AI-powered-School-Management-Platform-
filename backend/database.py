from typing import List

from sqlalchemy import inspect
from sqlmodel import SQLModel, create_engine, Session
from config import DATABASE_URL

# SQLite requires check_same_thread=False for multithreaded access
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def schema_problems(target_engine) -> List[str]:
    """Columns the code needs that an existing database does not have yet, as table.column."""
    inspector = inspect(target_engine)
    existing_tables = set(inspector.get_table_names())
    problems = []
    for table in SQLModel.metadata.sorted_tables:
        if table.name in existing_tables:
            present = {column["name"] for column in inspector.get_columns(table.name)}
            problems.extend(f"{table.name}.{column.name}" for column in table.columns if column.name not in present)
    return problems


def create_db_and_tables():
    """create_all adds missing tables but never alters existing ones, so an older database is
    stopped here, untouched, with instructions, rather than failing on every request later."""
    missing = schema_problems(engine)
    if missing:
        raise RuntimeError(
            f"This database needs upgrading (missing: {', '.join(missing)}). Nothing has been changed. "
            "Run: python migrate_db.py --apply  (it backs up first). On Modal, see DEPLOYMENT_GUIDE.md."
        )
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
