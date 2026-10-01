"""PathPilot API.

Run locally:  .venv/bin/uvicorn backend.app.main:app --reload
Then open:    http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.db import close_mongo
from backend.app.deps import get_recommender
from backend.app.routes import auth, catalog, feedback, progress, recommend

API_PREFIX = "/api"  # frontend and API share one domain on Vercel: /api/* goes to FastAPI
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"  # built by `npm run build`


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
        version="0.5.0",
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
        return {"status": "ok", "model": {"careers": len(meta.classes), "alpha": meta.alpha, "trained_at": meta.trained_at}}

    for module in (recommend, catalog, auth, progress, feedback):
        app.include_router(module.router, prefix=API_PREFIX)

    # Serve the built React app for every non-API path. On Vercel these files are served from the
    # CDN. "index.html" fallback lets deep links like /roadmap/data_analyst load the app, which then
    # shows the right page. In local development (no build yet) Vite serves the frontend instead.
    if FRONTEND_DIST.is_dir():
        app.frontend("/", directory=FRONTEND_DIST, fallback="index.html")
    return app


app = create_app()
