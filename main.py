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

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from database import Base, engine, get_db
from schemas import (
    PostCreate,
    PostUpdate,
    PostResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
)


# Base.metadata.create_all(bind=engine)
@asynccontextmanager
async def lifespan(__app: FastAPI):
    # startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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

DBSession = Annotated[AsyncSession, Depends(get_db)]

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

"""
    @app.get("/")
    @app.get("/post")
        -> will show for both route

    @app.get("/", response_class=HTMLResponse) -> will show html respnse
    @app.get("/", include_in_schema=False) -> won't show on the documentation
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html")


@app.get("/api/posts", response_model=list[PostResponse])
async def get_post(db: DBSession):
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author))
    )

    posts = result.scalars().all()

    return posts


@app.post(
    "/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED
)
async def create_post(post: PostCreate, db: DBSession):
    result = await db.execute(select(models.User).where(models.User.id == post.user_id))

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User not found!"
        )

    new_post = models.Post(
        author=user,
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["authro"])

    return new_post


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_single_post(post_id: int, db: DBSession):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )

    post = result.scalars().first()

    if post:
        return post

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!")


@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_entire_post(post_id: int, post_data: PostCreate, db: DBSession):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    if post_data.user_id != post.user_id:
        result = await db.execute(
            select(models.User).where(models.User.id == post_data.user_id)
        )

        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    await db.commit()
    await db.refresh(post, attribute_names=["authro"])

    return post


@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def update_partial(post_id: int, post_data: PostUpdate, db: DBSession):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    update_data = post_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["authro"])

    return post


@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: DBSession):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    await db.delete(post)
    await db.commit()


@app.post("/api/register", response_model=UserResponse)
async def register(user: UserCreate, db: DBSession):
    result = await db.execute(
        select(models.User).where(models.User.username == user.username)
    )

    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exist!"
        )

    result = await db.execute(
        select(models.User).where(models.User.email == user.email)
    )

    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exist!"
        )

    new_user = models.User(username=user.username, email=user.email)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_users_data(user_id: int, db: DBSession):
    result = await db.execute(select(models.User).where(models.User.id == user_id))

    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")


@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: DBSession):
    result = await db.execute(select(models.User).where(models.User.id == user_id))

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
    )

    posts = result.scalars().all()

    return posts


@app.patch("/api/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, data: UserUpdate, db: DBSession):
    result = await db.execute(select(models.User).where(models.User.id == user_id))

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    if data.username is not None and data.username != user.username:
        result = await db.execute(
            select(models.User).where(models.User.username == data.username)
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Username already exist!"
            )

        if data.email is not None and data.email != user.email:
            existing_email = result.scalars().first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Email already registered",
                )

        if data.username is not None:
            user.username = data.username
        if data.email is not None:
            user.email = data.email
        if data.image_file is not None:
            user.image_file = data.image_file

        await db.commit()
        await db.refresh(user)

        return user


@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: DBSession):
    result = await db.execute(select(models.User).where(models.User.id == user_id))

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    await db.delete(user)
    await db.commit()
