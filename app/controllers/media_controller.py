from app.services.analyzer import Analyzer
from fastapi import APIRouter, UploadFile, File
from fastapi.encoders import jsonable_encoder
from app.services.log_service import LogService
from datetime import date, datetime

media_handler = APIRouter()

@media_handler.post("/analyze_video")
async def post_video(file: UploadFile = File(...)):
    """
    This function is going to:
    1. Receive the information from a video.
    2. Use an ML model to classify the video as deep fake or not.
    3. Save the detection log within the database.
    4. Return a response about what the ML model has detected.
    """    
    
    analyzer = Analyzer()

    audio_data = await file.read()
    
    #result = analyzer.analyze_video(audio_data)
            
    log_service = LogService()
    
    log = {"isDeepFake" : True, "date" : date.today(), "hour" : datetime.now().time()}
            
    log_service.save_log(log)
    
    result = {"Mock" : "Result"}
    
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
    
    log = {"isDeepFake" : True, "date" : date.today(), "hour" : datetime.now().time()}
        
    log_service = LogService()
    
    log_service.save_log(log)
    
    return jsonable_encoder(result)
