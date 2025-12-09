from fastapi import FastAPI
from controllers.log_controller import log_handler
from controllers.media_controller import media_handler

app = FastAPI()

app.include_router(log_handler)
app.include_router(media_handler)


@app.get("/")
def root():
    return {"Hello ": "World"}
