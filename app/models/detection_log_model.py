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
    # Minimal audio inference summary (nullable for non-audio logs)
    Column("classification", String, index=True, nullable=True),  # "Deepfake" | "Bonafide"
    Column("score", Float, nullable=True),  # normalized 0..100
)

# NOTE: Never drop tables on import. If you need a local reset, set RESET_DB=true.
if os.getenv("RESET_DB", "").lower() == "true":
    meta.drop_all(engine)

meta.create_all(engine)

# Lightweight "migration" for existing DBs: add new columns if missing.
# This avoids 500s when the table already exists from an older version.
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