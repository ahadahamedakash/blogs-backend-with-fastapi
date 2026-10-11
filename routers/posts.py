from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

import models
from database import get_db, DBSession
from schemas import PostCreate, PostUpdate, PostResponse

from auth import CurrentUser

router = APIRouter()


@router.get("", response_model=list[PostResponse])
async def get_post(db: DBSession):
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author))
    )

    posts = result.scalars().all()

    return posts


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, current_user: CurrentUser, db: DBSession):

    new_post = models.Post(
        author=current_user,
        title=post.title,
        content=post.content,
        user_id=current_user.id,
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])

    return new_post


@router.get("/{post_id}", response_model=PostResponse)
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


@router.put("/{post_id}", response_model=PostResponse)
async def update_entire_post(
    post_id: int, post_data: PostCreate, current_user: CurrentUser, db: DBSession
):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this!",
        )

    post.title = post_data.title
    post.content = post_data.content

    await db.commit()
    await db.refresh(post, attribute_names=["author"])

    return post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_partial(
    post_id: int, post_data: PostUpdate, current_user: CurrentUser, db: DBSession
):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this!",
        )

    update_data = post_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])

    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, current_user: CurrentUser, db: DBSession):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))

    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found!"
        )

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post!",
        )

    await db.delete(post)
    await db.commit()
