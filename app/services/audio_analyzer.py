import requests
import os
import base64
from dotenv import load_dotenv

load_dotenv()

class AudioAnalyzer:
    """
    Here must be loaded the video analysis model. The goal is to access the model through the instance
    of this class.
    """
        
    def __init__(self):
        self.api_url = os.getenv("HUGGINGFACE_API_URL")
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        
    
    def analyze_audio(self, audio_bytes):
        # The handler expects {"inputs": <base64_encoded_audio>}
        # Encode bytes to base64 string
        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        
        payload = {
            "inputs": base64_audio
        }

        headers = {
            "Accept" : "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            # Handler returns a list [{...}]
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result
            
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
