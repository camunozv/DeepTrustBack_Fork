from sqlalchemy import Table, Column, Boolean, Integer, Date, Time
from config.db import meta, engine

detection_log = Table(
    "DetectionLog",
    meta,
    Column("id", Integer, primary_key=True),
    Column("isDeepFake", Boolean, index=True, default=False),
    Column("date", Date, index=True),
    Column("hour", Time, index=True),
)

meta.drop_all(engine) # Uncomment for just creating not dropping.
meta.create_all(engine)