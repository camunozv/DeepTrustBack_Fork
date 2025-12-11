from schemas.detection_log_schema import DetectionLog


class LogService:
    # Pending to implement data base onnections
    
    def __init__(self):
        pass
    
    def save_log(detection_log: DetectionLog):
        
        return "saved_successfully"    


    def get_all_logs():
        
        return "returned successfully"
    
    def get_logs_by_state(state : str):
        
        return "retured successfully"
    
    
    def delete_log_by_id(log_id: int):
        
        return "deleted successfully"
    