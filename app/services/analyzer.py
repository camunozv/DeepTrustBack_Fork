from app.services.audio_analyzer import AudioAnalyzer
from app.services.video_analyzer import VideoAnalyzer

class Analyzer:
    
    audio_analyzer = None
    video_analyzer = None
    
    def __init__(self):
        self.audio_analyzer = AudioAnalyzer()
        self.video_analyzer = VideoAnalyzer()
            
    def analyze_audio(self, audio_data: bytes):
        
        result = self.audio_analyzer.analyze_audio(audio_data)
        
        return result
    
    
    def analyze_video(self, video_data: bytes, filename: str | None = None):
        
        result = self.video_analyzer.analyze_video(video_data, filename=filename)
        
        return result