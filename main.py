from fastapi import FastAPI, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from schemas import PostCreate, PostResponse

app = FastAPI(
    title="FastAPI Blog",
    description="A backend engineering project focused on building a reliable REST API.",
    version="0.1.0",
)

templates = Jinja2Templates(directory="templates")

posts: list[dict] = [
    {
        "id": 1,
        "author": "This is author",
        "title": "This is title",
        "content": "This is content",
        "date_posted": "April 20, 2025",
    },
    {
        "id": 2,
        "author": "This is author",
        "title": "This is title",
        "content": "This is content",
        "date_posted": "April 20, 2025",
    },
]

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
def get_post():
    return posts


@app.post("/api/posts", response_model=PostCreate, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate):
    new_id = max(p["id"] for p in posts) + 1 if posts else 1
    new_post = {
        "id": new_id,
        "author": data.author,
        "title": data.title,
        "content": data.content,
        "date_posted": "",
    }

    posts.append(new_post)
    return new_post


@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_single_post(post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            return post

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="PostBase not found!"
    )
