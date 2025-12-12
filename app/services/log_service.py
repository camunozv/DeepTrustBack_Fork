from app.schemas.detection_log_schema import DetectionLog
from app.models.detection_log_model import detection_log
from app.config.db import conn
from typing import Any, Dict, Optional

class LogService:
    
    def __init__(self):
        pass
    
    def save_log(self, log_to_save: Dict[str, Any]):
        """
        Persists a log entry. Keys must match DB column names.
        Example keys: isDeepFake, date, hour, overallDeepfakeScorePercent, detectedManipulationProbability
        """
        return conn.execute(detection_log.insert().values(log_to_save))
    
    def delete_log_by_id(self, id : int):
        return conn.execute(detection_log.delete().where(detection_log.c.id == id))
    
    def get_log_by_id(self, id: int):
        return conn.execute(detection_log.select().where(detection_log.c.id == id)).fetchone()

    def get_all_logs(self):        
        return conn.execute(detection_log.select()).fetchall()
    
    def get_logs_by_classification(self, classification: str):
        return conn.execute(
            detection_log.select().where(detection_log.c.classification == classification)
        ).fetchall()
        