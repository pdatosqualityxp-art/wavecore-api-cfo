from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.agent_cfo import router as agent_cfo_router
from app.routers.health import router as health_router
from app.routers.ingesta import router as ingest_router


def create_app(cors_allowed_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(title="Wavecore API CFO")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=(
            settings.cors_allowed_origins
            if cors_allowed_origins is None
            else cors_allowed_origins
        ),
        allow_credentials=False,
        allow_methods=["POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(ingest_router, prefix="/api")
    app.include_router(agent_cfo_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    return app


app = create_app()
