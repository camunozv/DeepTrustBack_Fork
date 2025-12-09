from sqlalchemy import Table, Column
from sqlalchemy.types import Integer, Date, Time, Boolean
#from config.db import meta, engine

DetectionLogs = Table(
    "DetectionLog",
    #meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("isDeepfake", Boolean),
    Column("date", Date),
    Column("hour", Time),
)

#meta.drop_all(engine)
#meta.create_all(engine)
