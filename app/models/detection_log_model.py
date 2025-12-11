from sqlalchemy import Table, Column, Boolean, ForeignKey, Integer, String, Date, Time
from config.db import Base

class DetectionLogs (Base):
    __tablename__ = "DetectionLog"
    id = Column (Integer, primary_key = True)
    is_deepfake = Column(Boolean, index = True, default = False)
    date = Column(Date, index = True)
    hour = Column(Time, index = True)
