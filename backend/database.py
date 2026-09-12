from sqlmodel import SQLModel, create_engine, Session
from config import DATABASE_URL

# SQLite requires check_same_thread=False for multithreaded access
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
