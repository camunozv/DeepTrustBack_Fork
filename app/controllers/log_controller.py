from fastapi import APIRouter
from services.log_service import LogService
from schemas.detection_log_schema import DetectionLog
from typing import List

log_handler = APIRouter()
log_service = LogService()

@log_handler.get("/all", response_model=List[DetectionLog])
def get_all_logs():
    list_of_logs = log_service.get_all_logs()
    
    result = []
    for log in list_of_logs:
        result.append(DetectionLog(
            id=log[0],
            is_deepfake=log[1],
            date=log[2],
            hour=log[3]
        ))
    
    return result


@log_handler.get("/by_state")
def get_logs_by_state(state : str, response_model=List[DetectionLog]):
        
    list_of_logs = log_service.get_logs_by_state(state)
    
    result = []
    for log in list_of_logs:
        result.append(DetectionLog(
            id=log[0],
            is_deepfake=log[1],
            date=log[2],
            hour=log[3]
        ))
    
    return result


@log_handler.delete("/delete_by_id")
def delete_log(id : int):
    """
    Not implemented yet.
    """
    
    result_of_deletion = log_service.delete_log_by_id(id)
    
    return ""
