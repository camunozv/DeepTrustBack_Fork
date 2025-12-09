from app.services import Analyzer
from config.db import conn
from fastapi import APIRouter
from models.detection_log_model import DetectionLogs
from schemas.detection_log import DetectionLog # used for receiving information from the front.
from fastapi.encoders import jsonable_encoder

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
def post_audio(received_audio):
    """
    This function is going to:
    1. Receive the information from an audio.
    2. Use an ML model to classify the audio as deep fake or not.
    3. Save the detection log within the database.
    4. Return a response about what the ML model has detected.
    """
    
    analyzer = Analyzer()
    result = analyzer.analyze_audio(received_audio)
    
    return jsonable_encoder(result)