from schemas.detection_log_schema import DetectionLog
from models.detection_log_model import detection_log
from config.db import conn

class LogService:
    # Pending to implement data base onnections
    
    def __init__(self):
        pass
    
    def save_log(self, detection_log: DetectionLog):
        return "saved_successfully"


    def get_all_logs(self):        
        return conn.execute(detection_log.select()).fetchall()
    
    def get_logs_by_state(state : str):
        
        return "retured successfully"
    
    
    def delete_log_by_id(log_id: int):
        
        return "deleted successfully"
    