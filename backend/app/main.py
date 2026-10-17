from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db, seed
from .services import ml
from .config import get_settings
from .routers import admin_routes, auth_routes, chat_routes, document_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db(get_settings().vaultrag_db_path)
    seed.ensure_seeded()
    ml.ensure()  # train on-server models at startup (≈1 s)
    yield


app = FastAPI(title="VaultRAG", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
for r in (auth_routes.router, chat_routes.router, document_routes.router, admin_routes.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    s = get_settings()
    return {"ok": True, "llm_provider": s.llm_provider,
            "llm_configured": s.llm_provider == "extractive" or bool(s.llm_api_key),
            "demo_mode": s.demo_mode, "ml_available": ml.AVAILABLE}


_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
