from app.services import audio_analyzer
from app.services import video_analyzer
from services.audio_analyzer import AudioAnalyzer
from services.video_analyzer import VideoAnalyzer

class Analyzer:
    
    audio_analyzer = AudioAnalyzer()
    video_analyzer = VideoAnalyzer()
    
    def __init__(self):
        print("", end = "")
            
    def analyze_audio(self, audio_data: bytes):
        
        result = self.audio_analyzer.analyze_audio(audio_data)
        
        return result
    
    
    def analyze_video(video : str):
        
        result = video_analyzer.analyze_video()
        
        return result