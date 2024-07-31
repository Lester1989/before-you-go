
from sqlmodel import Session,create_engine
from fastapi import Request
import typing

engine = create_engine("sqlite:///database/database.db")

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
