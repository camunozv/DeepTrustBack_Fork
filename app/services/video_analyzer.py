class VideoAnalyzer:
    """
    Here must be loaded the video analysis model. The goal is to access the model through the instance
    of this class.
    """
    
    def __init__(self):
        pass
    
    
    def analyze_video(self, video_bytes: bytes):
        raise NotImplementedError("Video analysis is not implemented yet.")
    