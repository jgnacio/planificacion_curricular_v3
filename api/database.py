import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./ebi.db"

_is_sqlite = DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_pool_kwargs = {} if _is_sqlite else {
    "pool_pre_ping": True,   # descarta conexiones muertas antes de usarlas
    "pool_recycle": 300,     # recicla conexiones cada 5 min (Supabase cierra idle ~10 min)
    "pool_size": 5,
    "max_overflow": 10,
}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
