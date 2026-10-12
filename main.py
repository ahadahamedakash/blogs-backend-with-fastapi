from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Request, HTTPException, status, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from starlette.exceptions import HTTPException as StarletteHTTPException

from database import Base, engine, get_db
from routers import posts, users

from database import DBSession


# Base.metadata.create_all(bind=engine)
@asynccontextmanager
async def lifespan(__app: FastAPI):
    # # startup
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    # yield
    # # shutdown
    # await engine.dispose()

    yield
    # shutdown
    await engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    # //
    title="FastAPI Blog",
    description="A backend engineering project focused on building a reliable REST API.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])

"""
    @app.get("/")
    @app.get("/post")
        -> will show for both route

    @app.get("/", response_class=HTMLResponse) -> will show html respnse
    @app.get("/", include_in_schema=False) -> won't show on the documentation
"""


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    response.headers["X-Content-Type-Options"] = "nosniff"

    if "referrer-Policy" not in response.headers:
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if request.url.hostname not in ("localhost", "127.0.0.1"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )

    return response


@app.get("/health")
async def health_check(db: DBSession):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailabe",
        ) from exc

    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html")
