"""PathPilot API.

Run locally:  .venv/bin/uvicorn backend.app.main:app --reload
Then open:    http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.db import close_mongo
from backend.app.deps import get_recommender
from backend.app.routes import auth, catalog, recommend

API_PREFIX = "/api"  # frontend and API share one domain on Vercel: /api/* goes to FastAPI


@asynccontextmanager
async def lifespan(app):
    get_recommender()  # load the model at startup so the first request isn't slow
    yield
    await close_mongo()


def create_app():
    settings = get_settings()
    app = FastAPI(
        title="PathPilot API",
        description="Career recommendations and personalised learning roadmaps, "
                    "powered by a from-scratch NumPy model.",
        version="0.3.0",
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(f"{API_PREFIX}/health", tags=["meta"])
    def health():
        meta = get_recommender()
        return {"status": "ok", "model": {"careers": len(meta.classes), "alpha": meta.alpha}}

    for module in (recommend, catalog, auth):
        app.include_router(module.router, prefix=API_PREFIX)
    return app


app = create_app()
