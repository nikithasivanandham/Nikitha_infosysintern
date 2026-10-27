from fastapi import FastAPI

from app.config import settings
from app.logger import logger
from app.api.auth import router as auth_router
from app.api.workflow import router as workflow_router
from app.api.permission import router as permission_router
from app.api.audit import router as audit_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend APIs for Airport Operations Coordination"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(workflow_router)
app.include_router(permission_router)
app.include_router(audit_router)

@app.get("/")
def home():
    logger.info("Home endpoint accessed")

    return {
        "message": settings.app_name,
        "version": settings.app_version
    }


@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")

    return {
        "status": "healthy"
    }