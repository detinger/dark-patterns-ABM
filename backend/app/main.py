from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def get_cors_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ORIGINS")
    if not configured_origins:
        return list(DEFAULT_CORS_ORIGINS)

    return [origin.strip().rstrip("/") for origin in configured_origins.split(",") if origin.strip()]


app = FastAPI(
    title="Dark Patterns Mesa API",
    version="0.1.0",
    description="FastAPI wrapper around a Mesa-based ABM for trust erosion under dark patterns.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
