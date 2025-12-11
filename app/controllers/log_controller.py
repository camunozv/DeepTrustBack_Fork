from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from services.log_service import LogService

log_handler = APIRouter()
log_service = LogService()

@log_handler.get("/all")
def get_all_logs():
    
    list_of_logs = log_service.get_all_logs()       
        
    print(list_of_logs)
    
    return ""


@log_handler.get("/by_state")
def get_logs_by_state(state : str):
    
    list_of_logs = log_service.get_logs_by_state(state)
    
    return ""


@log_handler.delete("/delete_by_id")
def delete_log(id : int):
    
    result_of_deletion = log_service.delete_log_by_id(id)
    
    return ""
