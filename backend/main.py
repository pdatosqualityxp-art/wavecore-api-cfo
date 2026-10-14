from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.agent_cfo import router as agent_cfo_router
from app.routers.ingesta import router as ingest_router


app = FastAPI(title="Wavecore API CFO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router, prefix="/api")
app.include_router(agent_cfo_router, prefix="/api")
