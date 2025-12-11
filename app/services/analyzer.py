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
    
    
    def analyze_video(self, video : str):
        
        result = self.video_analyzer.analyze_video()
        
        return result