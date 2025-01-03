import random
import string
import os
from datetime import date, timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from app.auth import app as auth_app
from app.auth import create_access_token, get_current_user
from app.controller_article import article_create, article_delete, article_list
from app.controller_storage import storage_create, storage_delete
from app.controller_user import user_create
from app.models import Article, SQLModel, User
from app.route_user import app as user_app
from app.route_checkin import app as checkin_app
from app.utility import flash, get_db, get_flashed_messages, get_translations, redirect_with_token, templates, engine
from app.validators import valid_article, valid_storage

SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    if not os.environ.get("enable_signup") and session.exec(select(User)).first() is None:
        user_create(session, "admin", os.environ.get("admin_password","not_a_save_password"), "a@b.com")


app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="".join([random.choice(string.ascii_letters) for _ in range(32)]),
)
app.include_router(user_app)
app.include_router(checkin_app)
app.include_router(auth_app)

@app.get("/repair")
async def repair_view(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):
    all_articles = db.exec(select(Article)).all()
    repaired = 0
    for article in all_articles:
        if article.quantity is None:
            article.quantity = 1
            repaired += 1
    db.commit()
    flash(request, f"Repaired {repaired} Articles", "success")

    return redirect_with_token(request, user,"/storage")


@app.get("/storage")
async def storage_view(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    storages = user.storages(db)
    articles = user.articles(db)
    return templates.TemplateResponse(
        request,
        "storage_view.html",
        {"storages": storages, "articles": articles, "user": user}
        | get_translations(request)
        | get_flashed_messages(request),
    )

@app.get("/full_storage")
async def full_storage_view(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    storages = user.storages(db)
    articles = user.articles(db)
    return templates.TemplateResponse(
        request,
        "full_storage_view.html",
        {"storages": storages, "articles": articles, "user": user}
        | get_translations(request)
        | get_flashed_messages(request),
    )


@app.post("/set_expiration")
async def set_expiration_view(
    request: Request,
    article_id: int= Form(...),
    remaining_days: int= Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if article := valid_article(db, article_id, user.id):
        article.expiration_date = date.today() + timedelta(days=remaining_days)
        db.commit()
        flash(
            request,
            f"Expiration date updated to {article.expiration_date.strftime('%Y-%m-%d')}",
            "success",
        )
    return redirect_with_token(request, user,"/storage",status_code=status.HTTP_303_SEE_OTHER)


@app.post("/move_article")
async def move_article(
    request: Request,
    article_id: int= Form(...),
    storage_id: int = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):
    if article := valid_article(db, article_id, user.id):
        article.storage_id = storage_id
        db.commit()
        flash(request, f"Article moved to storage {storage_id}", "success")
    return redirect_with_token(request, user,"/storage",status_code=status.HTTP_303_SEE_OTHER)


@app.get("/remove_article/{article_id}")
async def remove_article_view(
    request: Request,
    article_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if article := valid_article(db, article_id, user.id):
        article_delete(db, user.id, article_id)
        flash(request, f"Article {article.name} removed", "success")
    else:
        flash(request, "Article not found", "danger")
    return redirect_with_token(request, user,"/storage")


@app.get("/remove_storage/{storage_id}")
async def remove_storage_view(
    request: Request,
    storage_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if storage := valid_storage(db, storage_id, user.id):
        if articles := article_list(db, user.id, storage_id):
            flash(
                request,
                f"Storage not empty, {len(articles)} entries in Storage",
                "danger",
            )
        else:
            storage_delete(db, user.id, storage_id)
            flash(request, f"Storage {storage.name} removed", "success")
    else:
        flash(request, "Storage not found", "danger")
    return redirect_with_token(request, user,"/storage")


@app.post("/create_storage")
async def create_storage_view(
    request: Request,
    storage_name: str = Form(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    storage_create(db, user.id, storage_name)
    flash(request, f"Storage {storage_name} created", "success")
    return redirect_with_token(request, user,"/storage",status_code=status.HTTP_303_SEE_OTHER)

@app.exception_handler(RequestValidationError)
def request_error(request: Request, description: HTTPException):
    return templates.TemplateResponse(
        request,
        "error.html",
        {"description": description}
        | get_translations(request)
        | get_flashed_messages(request),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

@app.exception_handler(HTTPException)
def page_not_found(request: Request, description: HTTPException):
    print("trigger exception handler", type(description), description)
    if description.detail.endswith("Not authenticated"):
        flash(request, "Not authenticated", "danger")
        result = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        result.delete_cookie("access_token")
        return result
    return templates.TemplateResponse(
        request,
        "error.html",
        {"description": description}
        | get_translations(request)
        | get_flashed_messages(request),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
