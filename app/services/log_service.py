from app.schemas.detection_log_schema import DetectionLog
from app.models.detection_log_model import detection_log
from app.config.db import engine
from typing import Any, Dict, Optional

class LogService:
    
    def __init__(self):
        pass
    
    def _get_conn(self):
        """Get a database connection when needed."""
        return engine.connect()
    
    def save_log(self, log_to_save: Dict[str, Any]):
        conn = self._get_conn()
        try:
            return conn.execute(detection_log.insert().values(log_to_save))
        finally:
            conn.close()
    
    def delete_log_by_id(self, id: int):
        conn = self._get_conn()
        try:
            return conn.execute(detection_log.delete().where(detection_log.c.id == id))
        finally:
            conn.close()
    
    def get_log_by_id(self, id: int):
        conn = self._get_conn()
        try:
            return conn.execute(detection_log.select().where(detection_log.c.id == id)).fetchone()
        finally:
            conn.close()

    def get_all_logs(self):
        conn = self._get_conn()
        try:
            return conn.execute(detection_log.select()).fetchall()
        finally:
            conn.close()
    
    def get_logs_by_classification(self, classification: str):
        conn = self._get_conn()
        try:
            return conn.execute(
                detection_log.select().where(detection_log.c.classification == classification)
            ).fetchall()
        finally:
            conn.close()
        