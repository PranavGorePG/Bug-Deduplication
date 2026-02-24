from fastapi import HTTPException
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_vector_store, routes_dedupe
from app.core.logging import logger

app = FastAPI(title="Bug Deduplication API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(routes_vector_store.router)
app.include_router(routes_dedupe.router)


@app.get("/")
async def root():
    return {"message": "Bug Deduplication API is running"}


@app.get("/api/external-bugs")
async def get_external_bugs():
    url = "https://untillable-tyra-monarchically.ngrok-free.dev/api/bugs/bugs-res-ai/e915b62d-b6b1-4780-b0e7-8320278991f2"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            raise HTTPException(
                status_code=502, detail="Error fetching from external API")
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching external bugs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
