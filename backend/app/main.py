from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger import get_logger
from app.routes import upload, jobs, voices

log = get_logger(__name__)

app = FastAPI(title="Localizer AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.client_cors_origin_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(jobs.router)
app.include_router(voices.router)


@app.on_event("startup")
async def on_startup() -> None:
    log.info("Localizer AI backend starting up")
    log.info("CORS origin: %s", settings.client_cors_origin_url)


@app.get("/health")
def health():
    log.info("Health check requested")
    return {"status": "ok"}
