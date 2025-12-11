"""
SQLAlchemy models.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)


class Series(Base):
    __tablename__ = "series"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(32), default="active")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    chapters = relationship("Chapter", back_populates="series")


class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String(255))
    status = Column(String(32), default="pending")
    page_count = Column(Integer)
    json_path = Column(String(1024))
    json_hash = Column(String(128))
    rendered_zip_path = Column(String(1024))
    rendered_zip_hash = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    series = relationship("Series", back_populates="chapters")
    chapter_json = relationship("ChapterJSON", uselist=False, back_populates="chapter")
    chapter_summary = relationship("ChapterSummary", uselist=False, back_populates="chapter")


class ChapterJSON(Base):
    __tablename__ = "chapter_json"
    chapter_id = Column(Integer, ForeignKey("chapters.id"), primary_key=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chapter = relationship("Chapter", back_populates="chapter_json")


class ChapterSummary(Base):
    __tablename__ = "chapter_summary"
    chapter_id = Column(Integer, ForeignKey("chapters.id"), primary_key=True)
    summary_text = Column(Text)
    character_registry = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chapter = relationship("Chapter", back_populates="chapter_summary")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(64), nullable=False)
    series_id = Column(Integer, ForeignKey("series.id"))
    chapter_id = Column(Integer, ForeignKey("chapters.id"))
    detail = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
"""
SQLAlchemy models for series/chapters and audit.
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)


class Series(Base):
    __tablename__ = "series"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(32), default="active")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    chapters = relationship("Chapter", back_populates="series")


class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String(255))
    status = Column(String(32), default="pending")  # pending|processing|done|failed
    page_count = Column(Integer)
    json_path = Column(String(1024))
    json_hash = Column(String(128))
    rendered_zip_path = Column(String(1024))
    rendered_zip_hash = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    series = relationship("Series", back_populates="chapters")
    chapter_json = relationship("ChapterJSON", uselist=False, back_populates="chapter")
    chapter_summary = relationship("ChapterSummary", uselist=False, back_populates="chapter")


class ChapterJSON(Base):
    __tablename__ = "chapter_json"
    chapter_id = Column(Integer, ForeignKey("chapters.id"), primary_key=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chapter = relationship("Chapter", back_populates="chapter_json")


class ChapterSummary(Base):
    __tablename__ = "chapter_summary"
    chapter_id = Column(Integer, ForeignKey("chapters.id"), primary_key=True)
    summary_text = Column(Text)
    character_registry = Column(JSON)  # list/dict of characters, tone, quirks
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chapter = relationship("Chapter", back_populates="chapter_summary")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(64), nullable=False)
    series_id = Column(Integer, ForeignKey("series.id"))
    chapter_id = Column(Integer, ForeignKey("chapters.id"))
    detail = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

