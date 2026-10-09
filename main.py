from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

"""
    @app.get("/")
    @app.get("/post")
        -> will show for both route

    @app.get("/", response_class=HTMLResponse) -> will show html respnse
    @app.get("/", include_in_schema=False) -> won't show on the documentation
"""


@app.get("/")
def home():
    return {"message": "hello from home!"}
