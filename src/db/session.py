"""
Database session setup (PostgreSQL).
"""

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@lru_cache
def _db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


@lru_cache
def _engine():
    return create_engine(_db_url(), pool_pre_ping=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
Database session/engine setup (PostgreSQL).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@lru_cache
def _db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        # Expected format: postgresql+psycopg2://user:pass@host:port/dbname
        raise RuntimeError("DATABASE_URL not set")
    return url


@lru_cache
def _engine():
    return create_engine(_db_url(), pool_pre_ping=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine())


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

