from pydantic import BaseModel
from datetime import date, time

class DetectionLog(BaseModel):
    id: int
    is_deepfake: bool
    date: date
    hour: time
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            time: lambda v: v.isoformat()
        }
