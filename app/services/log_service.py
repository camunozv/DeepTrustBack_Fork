from schemas.detection_log_schema import DetectionLog
from models.detection_log_model import detection_log
from config.db import conn

class LogService:
    
    def __init__(self):
        pass
    
    def save_log(self, log_to_save: DetectionLog):        
        return conn.execute(detection_log.insert().values(log_to_save))

    def get_all_logs(self):        
        return conn.execute(detection_log.select()).fetchall()
    
    def get_logs_by_state(self, state : str):
                
        return conn.execute(
            detection_log.select().where(detection_log.c.isDeepFake == state.lower())
        ).fetchall()
    
    
    def delete_log_by_id(log_id: int):
        return "deleted successfully"
    