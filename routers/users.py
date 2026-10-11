from typing import Annotated
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

import models
from config import settings
from database import get_db, DBSession
from schemas import (
    UserCreate,
    UserUpdate,
    PostResponse,
    Token,
    UserPrivate,
    UserPublic,
)
from auth import (
    create_access_token,
    hash_password,
    verify_password,
    CurrentUser,
)

router = APIRouter()


@router.post("", response_model=UserPrivate)
async def register(user: UserCreate, db: DBSession):
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.username) == user.username.lower()
        )
    )

    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exist!"
        )

    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == user.email.lower())
    )

    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exist!"
        )

    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/token", response_model=Token)
async def loging_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DBSession
):
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower()
        )
    )

    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password,",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivate)
async def get_current_user(current_user: CurrentUser):
    return current_user


@router.get("/{user_id}", response_model=UserPublic)
async def get_users_data(user_id: int, db: DBSession):
    result = await db.execute(select(models.User).where(models.User.id == user_id))

    user = result.scalars().first()

    if user:
        return user

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found!")


@router.get("/{user_id}/posts", response_model=list[PostResponse])
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


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
    user_id: int, current_user: CurrentUser, data: UserUpdate, db: DBSession
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user!",
        )

    result = await db.execute(select(models.User).where(models.User.id == user_id))

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    if data.username is not None and data.username.lower() != user.username.lower():
        result = await db.execute(
            select(models.User).where(
                func.lower(models.User.username) == data.username.lower()
            )
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Username already exist!"
            )

        if data.email is not None and data.email.lower() != user.email.lower():
            result = await db.execute(
                select(models.User).where(
                    func.lower(models.User.email) == data.email.lower()
                )
            )
            existing_email = result.scalars().first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Email already registered",
                )

        if data.username is not None:
            user.username = data.username
        if data.email is not None:
            user.email = data.email.lower()
        if data.image_file is not None:
            user.image_file = data.image_file

        await db.commit()
        await db.refresh(user)

        return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, current_user: CurrentUser, db: DBSession):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user!",
        )

    result = await db.execute(select(models.User).where(models.User.id == user_id))

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found!"
        )

    await db.delete(user)
    await db.commit()
