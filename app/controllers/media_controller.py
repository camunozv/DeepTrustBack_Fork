from config.db import conn
from fastapi import APIRouter
from models.detection_log_model import DetectionLogs
from schemas.detection_log import DetectionLog
from fastapi.encoders import jsonable_encoder


media_handler = APIRouter()

@media_handler.get("/get_all_appointments")
def get_all_appointments():
    
    result = conn.execute(DetectionLogs.select()).fetchall()
                
    return jsonable_encoder(result)

