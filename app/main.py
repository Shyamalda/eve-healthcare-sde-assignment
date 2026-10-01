from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from pathlib import Path

from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import Base, engine
from .routers import auth, bookings, centres, payments, tests
from .utils import configure_logging

configure_logging(settings.log_level)
logger = logging.getLogger("eve_healthcare")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("database tables ready")
    yield


app = FastAPI(
    title=settings.app_name,
    description="Backend service for diagnostic centre discovery, test bookings, mock payments, and idempotent payment webhooks.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info("%s %s -> %s (%.2f ms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
def home() -> HTMLResponse:
    html_path = BASE_DIR / "templates" / "index.html"
    with open(html_path, "r", encoding="utf-8") as file:
        return HTMLResponse(file.read())


@app.get("/docs", include_in_schema=False)
def swagger_ui() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{settings.app_name} · Swagger UI",
        swagger_css_url="/static/swagger.css",
        swagger_ui_parameters={"docExpansion": "list", "filter": True, "displayRequestDuration": True},
    )


@app.get("/redoc", include_in_schema=False)
def redoc_ui() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{settings.app_name} · ReDoc",
    )


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("unhandled application error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router)
app.include_router(centres.router)
app.include_router(tests.router)
app.include_router(bookings.router)
app.include_router(payments.router)
