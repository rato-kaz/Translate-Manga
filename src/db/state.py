"""
SQLite-backed state store for chapter processing (optional).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclass
class ChapterRecord:
    manga: str
    chapter: int
    status: str
    json_path: Optional[str]
    page_count: Optional[int]
    content_hash: Optional[str]
    updated_at: str


class ChapterStateDB:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chapters (
                    manga TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    json_path TEXT,
                    page_count INTEGER,
                    content_hash TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (manga, chapter)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS context_summaries (
                    manga TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    summary TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (manga, chapter)
                );
                """
            )
            conn.commit()

    def mark_chapter(self, manga: str, chapter: int, status: str, json_path: Optional[Path] = None, page_count: Optional[int] = None, content_hash: Optional[str] = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO chapters (manga, chapter, status, json_path, page_count, content_hash, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(manga, chapter) DO UPDATE SET
                    status=excluded.status,
                    json_path=excluded.json_path,
                    page_count=excluded.page_count,
                    content_hash=excluded.content_hash,
                    updated_at=datetime('now');
                """,
                (manga, chapter, status, str(json_path) if json_path else None, page_count, content_hash),
            )
            conn.commit()

    def get_chapter(self, manga: str, chapter: int) -> Optional[ChapterRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT manga, chapter, status, json_path, page_count, content_hash, updated_at
                FROM chapters WHERE manga=? AND chapter=?;
                """,
                (manga, chapter),
            )
            row = cur.fetchone()
            if not row:
                return None
            return ChapterRecord(*row)

    def list_processed(self, manga: str) -> List[ChapterRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT manga, chapter, status, json_path, page_count, content_hash, updated_at
                FROM chapters WHERE manga=? AND status='processed' ORDER BY chapter;
                """,
                (manga,),
            )
            return [ChapterRecord(*row) for row in cur.fetchall()]

    def list_pending(self, manga: str, chapters: Iterable[int]) -> List[int]:
        processed = {rec.chapter for rec in self.list_processed(manga)}
        return [ch for ch in chapters if ch not in processed]

    def upsert_summary(self, manga: str, chapter: int, summary: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO context_summaries (manga, chapter, summary, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(manga, chapter) DO UPDATE SET
                    summary=excluded.summary,
                    updated_at=datetime('now');
                """,
                (manga, chapter, summary),
            )
            conn.commit()

    def get_summaries_upto(self, manga: str, chapter_inclusive: int) -> List[Tuple[int, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT chapter, summary FROM context_summaries
                WHERE manga=? AND chapter<=? ORDER BY chapter;
                """,
                (manga, chapter_inclusive),
            )
            return [(row[0], row[1]) for row in cur.fetchall()]
"""
SQLite-backed state store for chapter processing.

Goals:
- Avoid re-running processed chapters when generating JSON.
- Keep metadata (manga, chapter, json_path, hash, status, timestamps).
- Provide context retrieval for translation (can be expanded to store summaries).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclass
class ChapterRecord:
    manga: str
    chapter: int
    status: str  # processed|pending|failed
    json_path: Optional[str]
    page_count: Optional[int]
    content_hash: Optional[str]
    updated_at: str


class ChapterStateDB:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #
    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chapters (
                    manga TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    json_path TEXT,
                    page_count INTEGER,
                    content_hash TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (manga, chapter)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS context_summaries (
                    manga TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    summary TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (manga, chapter)
                );
                """
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # CRUD for chapters
    # ------------------------------------------------------------------ #
    def mark_chapter(
        self,
        manga: str,
        chapter: int,
        status: str,
        json_path: Optional[Path] = None,
        page_count: Optional[int] = None,
        content_hash: Optional[str] = None,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO chapters (manga, chapter, status, json_path, page_count, content_hash, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(manga, chapter) DO UPDATE SET
                    status=excluded.status,
                    json_path=excluded.json_path,
                    page_count=excluded.page_count,
                    content_hash=excluded.content_hash,
                    updated_at=datetime('now');
                """,
                (
                    manga,
                    chapter,
                    status,
                    str(json_path) if json_path else None,
                    page_count,
                    content_hash,
                ),
            )
            conn.commit()

    def get_chapter(self, manga: str, chapter: int) -> Optional[ChapterRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT manga, chapter, status, json_path, page_count, content_hash, updated_at
                FROM chapters
                WHERE manga=? AND chapter=?;
                """,
                (manga, chapter),
            )
            row = cur.fetchone()
            if not row:
                return None
            return ChapterRecord(*row)

    def list_processed(self, manga: str) -> List[ChapterRecord]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT manga, chapter, status, json_path, page_count, content_hash, updated_at
                FROM chapters
                WHERE manga=? AND status='processed'
                ORDER BY chapter;
                """,
                (manga,),
            )
            return [ChapterRecord(*row) for row in cur.fetchall()]

    def list_pending(self, manga: str, chapters: Iterable[int]) -> List[int]:
        """Return chapters from input list that are not marked processed."""
        chapters_set = set(chapters)
        processed = {rec.chapter for rec in self.list_processed(manga)}
        return [ch for ch in chapters if ch not in processed]

    # ------------------------------------------------------------------ #
    # Context summaries (for translation context reuse)
    # ------------------------------------------------------------------ #
    def upsert_summary(self, manga: str, chapter: int, summary: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO context_summaries (manga, chapter, summary, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(manga, chapter) DO UPDATE SET
                    summary=excluded.summary,
                    updated_at=datetime('now');
                """,
                (manga, chapter, summary),
            )
            conn.commit()

    def get_summaries_upto(self, manga: str, chapter_inclusive: int) -> List[Tuple[int, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT chapter, summary
                FROM context_summaries
                WHERE manga=? AND chapter<=?
                ORDER BY chapter;
                """,
                (manga, chapter_inclusive),
            )
            return [(row[0], row[1]) for row in cur.fetchall()]

