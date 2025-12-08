# Here we define how our objects are going to look like.
from pydantic import BaseModel


class DetectionLog(BaseModel):
    id: int
    isDeepfake: bool
    date: str
    hour: str
