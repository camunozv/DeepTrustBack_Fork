from fastapi import Depends, FastAPI, HTTPException, status
# from app.api.v1.router import api_router
# from app.core.config import settings


#@app.get("/test/{hello_there}/")
#async def test_endpoint(hello_there: str, query_param_1: int):
   # return {"hello": hello_there, "your param is ": query_param_1}


# Use pydantic models for automatically validating the data you are
# receiving
#@app.post("/create_user")
#async def test_endpoint2(new_user: User):  # In this way the endpoints
    # know that they have to receive data in JSON format
    #return new_user


app = FastAPI(
    title="Diffusion Maps v1",
    # version=settings.VERSION,
    # openapi_url=f"{settings.API_V1_STR}/openapi.json",
)