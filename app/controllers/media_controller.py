from services.analyzer import Analyzer
#from config.db import conn
from fastapi import APIRouter, UploadFile, File
from schemas.detection_log_schema import DetectionLog
from fastapi.encoders import jsonable_encoder

from models.detection_log_model import detection_log
from config.db import conn

from services.log_service import LogService


media_handler = APIRouter()

@media_handler.post("/analyze_video")
def post_video(received_video):
    """
    This function is going to:
    1. Receive the information from a video.
    2. Use an ML model to classify the video as deep fake or not.
    3. Save the detection log within the database.
    4. Return a response about what the ML model has detected.
    """    
    analyzer = Analyzer()
    result = analyzer.analyze_video(received_video)
    
    return jsonable_encoder(result)


@media_handler.post("/analyze_audio")
async def post_audio(file: UploadFile = File(...)):
    """
    This function is going to:
    1. Receive the information from an audio.
    2. Use an ML model to classify the audio as deep fake or not.
    3. Save the detection log within the database.
    4. Return a response about what the ML model has detected.
    """
    
    analyzer = Analyzer()

    audio_data = await file.read()
    
    result = analyzer.analyze_audio(audio_data)
    
    mock_log = {"isDeepFake" : True, "date" : "11/11/2021", "hour" : "(00:00:00)"}
        
    log_service = LogService()
    
    log_service.save_log(mock_log)
    
    return jsonable_encoder(result)