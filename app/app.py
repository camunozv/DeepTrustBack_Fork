from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.log_controller import log_handler
from controllers.media_controller import media_handler

app = FastAPI()

# Configure CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)
app.include_router(log_handler)
app.include_router(media_handler)


@app.get("/")
def root():
    return {"Hello ": "World"}
