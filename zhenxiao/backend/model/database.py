from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from config import settings

_connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}

engine = create_engine(
    settings.db_url,
    poolclass=NullPool,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
