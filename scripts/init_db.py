"""
Create database tables using SQLAlchemy models.
"""

from src.db.session import _engine
from src.db import models


def main():
    engine = _engine()
    models.Base.metadata.create_all(bind=engine)
    print("DB schema created.")


if __name__ == "__main__":
    main()
"""
Create database tables using SQLAlchemy models.

Usage:
  DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname \\
  python -m scripts.init_db
"""

from __future__ import annotations

from src.db.session import _engine
from src.db import models


def main():
    engine = _engine()
    models.Base.metadata.create_all(bind=engine)
    print("DB schema created.")


if __name__ == "__main__":
    main()

