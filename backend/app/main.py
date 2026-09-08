"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine

settings = get_settings()

app = FastAPI(
    title="Cyber Risk & Compliance Assessment Platform",
    description=(
        "Educational portfolio project. Uses a fictional organisation and synthetic "
        "data. Does not perform a regulatory audit and provides no compliance "
        "certification or legal assurance."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/api/openapi.json",
)

# Explicit origin allowlist. A wildcard is never used: with credentialed
# requests it is both rejected by browsers and unsafe by design.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness and database connectivity check."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        # The exception is deliberately not returned to the caller. Database
        # errors leak host names, ports and driver versions to unauthenticated
        # clients. Detail belongs in server logs, not in an HTTP response.
        database_status = "unavailable"

    return {
        "status": "ok",
        "database": database_status,
        "environment": settings.ENVIRONMENT,
    }