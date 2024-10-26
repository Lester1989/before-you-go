
from datetime import datetime, timedelta, timezone
from fastapi.responses import RedirectResponse
from sqlmodel import Session,create_engine
from fastapi import Request,status
import typing
from fastapi.templating import Jinja2Templates
import string
import json
import pathlib
import os
from jose import JWTError, jwt


engine = create_engine("sqlite:///database/database.db")


# get secret from environment variable
JWT_KEY = os.environ.get(
    "JWT_KEY", "".join(string.ascii_letters + string.digits for _ in range(32))
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 180

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_KEY, algorithm=ALGORITHM)

def get_db():
    with Session(engine) as session:
        yield session


def flash(request: Request, message: typing.Any, category: typing.Literal['primary','success','warning','danger','info'] = "primary") -> None:
    colors = {
        "primary":"bg-blue-500 text-white",
        "success":"bg-green-500 text-white",
        "warning":"bg-yellow-500 text-black",
        "danger":"bg-red-500 text-white",
        "info":"bg-white text-black"
    }
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category,"color":colors[category]})

def get_flashed_messages(request: Request):
    if '_messages' not in request.session:
        return {}
    messages = request.session.pop("_messages") if "_messages" in request.session else []
    return {'flashed_messages':messages}

templates = Jinja2Templates(directory="app/templates")



def string_to_slug(raw_string: str):
    result = "".join(
        [
            char if char in string.ascii_lowercase + string.digits else "-"
            for char in raw_string.lower()
        ]
    )
    return result.replace("--", "-")


templates.env.globals["string_to_slug"] = string_to_slug
templates.env.globals["get_flashed_messages"] = get_flashed_messages


locales: dict[str, dict[str, str]] = {
    file_name.stem.lower(): json.loads(file_name.read_text(encoding="utf-8"))
    for file_name in pathlib.Path("app/", "locale").iterdir()
}


def get_translations(request: Request) -> dict[str, str]:
    requested_languages: list[str] = request.headers.get("Accept-Language", "en").split(
        ","
    )
    for language in requested_languages:
        clean_language = language.split("-")[0].lower()
        if clean_language in locales:
            return locales[clean_language]
    return locales["en"]

def redirect_with_token(request: Request, user: "User",url:str,status_code:int=status.HTTP_303_SEE_OTHER) -> RedirectResponse:
    result = RedirectResponse(url=url, status_code=status_code)
    result.set_cookie(
        key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}'
    )
    return result
