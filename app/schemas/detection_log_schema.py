from pydantic import BaseModel

class DetectionLog(BaseModel):
    isDeepfake: bool
    date: str
    hour: str
