"""
db.py (detection service)
─────────────────────────
Database connection for the detection pipeline.
"""

import os
import sqlalchemy as sa

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://purplle:purplle_secret@localhost:5432/store_intel"
        )
        _engine = sa.create_engine(db_url, pool_pre_ping=True)
    return _engine
