import os

from sqlalchemy import Table, Column, Boolean, Integer, Date, Time, Float, String, text
from app.config.db import meta, engine

detection_log = Table(
    "DetectionLog",
    meta,
    Column("id", Integer, primary_key=True),
    Column("isDeepFake", Boolean, index=True, default=False),
    Column("date", Date, index=True),
    Column("hour", Time, index=True),
    Column("classification", String, index=True, nullable=True),
    Column("score", Float, nullable=True),
)

# Wrap table creation in try-except to prevent startup failures
def init_db():
    """Initialize database tables. Call this on app startup."""
    try:
        # NOTE: Never drop tables on import. If you need a local reset, set RESET_DB=true.
        if os.getenv("RESET_DB", "").lower() == "true":
            meta.drop_all(engine)
        
        meta.create_all(engine)
        
        # Lightweight "migration" for existing DBs: add new columns if missing.
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        'ALTER TABLE "DetectionLog" '
                        'ADD COLUMN IF NOT EXISTS "classification" VARCHAR'
                    )
                )
                connection.execute(
                    text(
                        'ALTER TABLE "DetectionLog" '
                        'ADD COLUMN IF NOT EXISTS "score" DOUBLE PRECISION'
                    )
                )
        except Exception as e:
            # Columns may already exist, that's okay
            print(f"Note: Could not add columns (may already exist): {e}")
    except Exception as e:
        print(f"Warning: Database initialization error (may be expected on first run): {e}")
        # Don't fail startup - let the app start and handle DB errors at runtime

# Only create tables if explicitly requested via environment variable
# This prevents failures during import
if os.getenv("INIT_DB_ON_IMPORT", "").lower() == "true":
    init_db()