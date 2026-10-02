"""PathPilot API.

Run locally:  .venv/bin/uvicorn backend.app.main:app --reload
Then open:    http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from backend.app.config import Settings, get_settings
from backend.app.db import close_mongo, database_status, redact
from backend.app.deps import get_recommender
from backend.app.routes import auth, catalog, feedback, progress, recommend

API_PREFIX = "/api"  # frontend and API share one domain on Vercel: /api/* goes to FastAPI
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"  # built by `npm run build`
log = logging.getLogger("pathpilot")


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

    @app.exception_handler(PyMongoError)
    async def database_error(request: Request, exc: PyMongoError):
        # Full details go to the server log (Vercel → Logs); users get a clear, safe message.
        log.error("Database error on %s %s: %s: %s", request.method, request.url.path,
                  type(exc).__name__, redact(exc))
        return JSONResponse(status_code=503,
                            content={"detail": "Can't reach the database right now. Please try again shortly."})

    @app.get(f"{API_PREFIX}/health", tags=["meta"])
    async def health(settings: Settings = Depends(get_settings)):
        meta = get_recommender()
        return {
            "status": "ok",
            "model": {"careers": len(meta.classes), "alpha": meta.alpha, "trained_at": meta.trained_at},
            "database": await database_status(settings),
            "auth": "configured" if settings.jwt_secret else "JWT_SECRET missing",
        }

    for module in (recommend, catalog, auth, progress, feedback):
        app.include_router(module.router, prefix=API_PREFIX)

    # Serve the built React app for every non-API path. On Vercel these files are served from the
    # CDN. "index.html" fallback lets deep links like /roadmap/data_analyst load the app, which then
    # shows the right page. In local development (no build yet) Vite serves the frontend instead.
    if FRONTEND_DIST.is_dir():
        app.frontend("/", directory=FRONTEND_DIST, fallback="index.html")
    return app


app = create_app()
