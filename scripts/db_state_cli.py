"""
CLI helper for ChapterStateDB.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.db.state import ChapterStateDB


def cmd_list(args):
    db = ChapterStateDB(Path(args.db))
    rows = db.list_processed(args.manga)
    for rec in rows:
        print(f"{rec.manga} ch{rec.chapter}: {rec.status}, json={rec.json_path}, updated={rec.updated_at}")


def cmd_mark(args):
    db = ChapterStateDB(Path(args.db))
    db.mark_chapter(
        manga=args.manga,
        chapter=args.chapter,
        status=args.status,
        json_path=Path(args.json) if args.json else None,
        page_count=args.page_count,
        content_hash=args.content_hash,
    )
    print("OK")


def cmd_pending(args):
    db = ChapterStateDB(Path(args.db))
    pending = db.list_pending(args.manga, args.chapters)
    print(" ".join(str(c) for c in pending))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Chapter state DB helper")
    p.add_argument("--db", default="data/state.db")
    sub = p.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--manga", required=True)
    p_list.set_defaults(func=cmd_list)

    p_mark = sub.add_parser("mark")
    p_mark.add_argument("--manga", required=True)
    p_mark.add_argument("--chapter", type=int, required=True)
    p_mark.add_argument("--status", choices=["processed", "pending", "failed"], required=True)
    p_mark.add_argument("--json")
    p_mark.add_argument("--page-count", type=int, dest="page_count")
    p_mark.add_argument("--content-hash")
    p_mark.set_defaults(func=cmd_mark)

    p_pending = sub.add_parser("pending")
    p_pending.add_argument("--manga", required=True)
    p_pending.add_argument("chapters", type=int, nargs="+")
    p_pending.set_defaults(func=cmd_pending)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
"""
Simple CLI to manage chapter state database.

Examples:
  python scripts/db_state_cli.py --db data/state.db list --manga 2200_Nen_Neko_no_Kuni_Nippon
  python scripts/db_state_cli.py --db data/state.db mark --manga 2200... --chapter 3 --status processed --json outputs/ch3.json
  python scripts/db_state_cli.py --db data/state.db pending --manga 2200... --chapters 1 2 3 4
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.db import ChapterStateDB


def cmd_list(args):
    db = ChapterStateDB(Path(args.db))
    rows = db.list_processed(args.manga)
    for rec in rows:
        print(f"{rec.manga} ch{rec.chapter}: {rec.status}, json={rec.json_path}, updated={rec.updated_at}")


def cmd_mark(args):
    db = ChapterStateDB(Path(args.db))
    db.mark_chapter(
        manga=args.manga,
        chapter=args.chapter,
        status=args.status,
        json_path=Path(args.json) if args.json else None,
        page_count=args.page_count,
        content_hash=args.content_hash,
    )
    print("OK")


def cmd_pending(args):
    db = ChapterStateDB(Path(args.db))
    chapters = args.chapters
    pending = db.list_pending(args.manga, chapters)
    print(" ".join(str(c) for c in pending))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chapter state DB helper")
    parser.add_argument("--db", default="data/state.db", help="Path to sqlite db (will be created)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List processed chapters")
    p_list.add_argument("--manga", required=True)
    p_list.set_defaults(func=cmd_list)

    p_mark = sub.add_parser("mark", help="Mark chapter status")
    p_mark.add_argument("--manga", required=True)
    p_mark.add_argument("--chapter", type=int, required=True)
    p_mark.add_argument("--status", choices=["processed", "pending", "failed"], required=True)
    p_mark.add_argument("--json", help="Path to generated json")
    p_mark.add_argument("--page-count", type=int, dest="page_count")
    p_mark.add_argument("--content-hash")
    p_mark.set_defaults(func=cmd_mark)

    p_pending = sub.add_parser("pending", help="List chapters not processed among input")
    p_pending.add_argument("--manga", required=True)
    p_pending.add_argument("chapters", type=int, nargs="+")
    p_pending.set_defaults(func=cmd_pending)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

