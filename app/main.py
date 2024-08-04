import calendar
import random
import string
import urllib.parse
from datetime import date, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.auth import app as auth_app
from app.auth import create_access_token, get_current_user
from app.controller import (
    article_create,
    article_delete,
    article_list,
    lookup_data,
    storage_create,
    storage_delete,
    user_create,
    user_login,
    valid_article,
    valid_storage,
)
from app.models import Session, SQLModel, User, engine
from app.utility import get_db, get_flashed_messages, flash, get_translations, templates
from app.route_user import app as user_app

SQLModel.metadata.create_all(engine)

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="".join([random.choice(string.ascii_letters) for _ in range(32)]),
)
app.include_router(user_app)
app.include_router(auth_app)



@app.get("/seed")
async def seed_view(request: Request,db: Session = Depends(get_db)):
    user = user_create(db, "admin", "admin")
    fridge = storage_create(db, user.id, "Fridge")
    freezer = storage_create(db, user.id, "Freezer")
    article_create(db, user.id, "Milk", fridge.id, date.today() + timedelta(days=7))
    article_create(
        db, user.id, "Ice Cream", freezer.id, date.today() + timedelta(days=300)
    )
    flash(request,"Seeded database", "success")
    return RedirectResponse(url="/login")



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


@app.get("/checkin")
async def checkin_view(
    request: Request,
    storage_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    storages = user.storages(db)
    articles = user.articles(db)
    return templates.TemplateResponse(
        request,
        "article_check_in.html",
        {
            "storages": storages,
            "articles": articles,
            "user": user,
            "selected_storage_id": storage_id,
        }
        | get_translations(request)
        | get_flashed_messages(request),
    )


@app.post("/checkin")
async def checkin_view_post(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    barcode: Optional[str] = Form(""),
    name: Optional[str] = Form(""),
    storage_id: int = Form(...),
):
    if barcode and not name:
        name = lookup_data(db, barcode)
    elif not barcode and not name:
        raise ValueError("Barcode or name required")
    storage = valid_storage(db, storage_id, user.id)
    if not storage:
        raise ValueError("Invalid storage")
    result = RedirectResponse(
        url=f"/checkin_date?name={urllib.parse.quote_plus(name)}&storage_id={storage.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    result.set_cookie(
        key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}'
    )
    return result


@app.get("/checkin_date")
async def checkin_date_view(
    request: Request,
    name: str,
    storage_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    storage = valid_storage(db, storage_id, user.id)
    storages = user.storages(db)

    first_of_month, first_of_next_month, days = calculate_calendar_dates()

    result = templates.TemplateResponse(
        request,
        "article_check_in_date.html",
        {
            "name": name,
            "selected_storage": storage,
            "user": user,
            "today": date.today(),
            "days": days,
            "storages": storages,
            "first_of_month": first_of_month,
            "first_of_next_month": first_of_next_month,
            "this_month": first_of_month.strftime("%B %Y"),
            "next_month": first_of_next_month.strftime("%B %Y"),
        }
        | get_translations(request)
        | get_flashed_messages(request),
    )
    return result

def calculate_calendar_dates():
    first_of_month = date.today().replace(day=1)
    first_of_next_month = first_of_month + timedelta( days=calendar.monthrange(first_of_month.year, first_of_month.month)[1] )
    last_of_next_month = first_of_next_month + timedelta( days=calendar.monthrange(first_of_next_month.year, first_of_next_month.month)[1] - 1 )

    days = {}
    for i in range((last_of_next_month - first_of_month).days + 1):
        day = first_of_month + timedelta(days=i)
        days[day] = (day.month, day.weekday(), (day - date.today()).days)
    return first_of_month,first_of_next_month,days


@app.post("/checkin_date")
async def checkin_date_view_post(
    request: Request,
    name: str = Form(...),
    storage_id: int = Form(...),
    expiration_date: date = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    storage = valid_storage(db, storage_id, user.id)
    new_article = article_create(db, user.id, name, storage.id, expiration_date)
    flash(
        request,
        f"Article added: {new_article.name} in {storage.name} with expiration date {new_article.expiration_date}",
        "success"
    )
    result = RedirectResponse(
        url=f"/checkin?storage_id={storage_id}", status_code=status.HTTP_303_SEE_OTHER
    )
    result.set_cookie(
        key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}'
    )
    return result


@app.get("/set_expiration/{article_id}/{remaining_days}")
async def set_expiration_view(
    request: Request,
    article_id: int,
    remaining_days: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = valid_article(db, article_id, user.id)
    if article:
        article.expiration_date = date.today() + timedelta(days=remaining_days)
        db.commit()
        flash(request,f"Expiration date updated to {article.expiration_date.strftime('%Y-%m-%d')}","success")
    result = RedirectResponse(url="/storage")
    result.set_cookie(
        key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}'
    )
    return result


@app.get("/remove_article/{article_id}")
async def remove_article_view(
    request: Request,
    article_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = valid_article(db, article_id, user.id)
    if article:
        article_delete(db, user.id, article_id)
        flash(request,f"Article {article.name} removed","success")
    else:
        flash(request,"Article not found","danger")
    result = RedirectResponse(url="/storage")
    result.set_cookie(
        key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}'
    )
    return result


@app.get("/remove_storage/{storage_id}")
async def remove_storage_view(
    request: Request,
    storage_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    storage = valid_storage(db, storage_id, user.id)
    if storage:
        articles = article_list(db, user.id, storage_id)
        if articles:
            flash(request,"Storage not empty","danger")
        else:
            storage_delete(db, user.id, storage_id)
            flash(request,f"Storage {storage.name} removed","success")
    else:
        flash(request,"Storage not found","danger")
    result = RedirectResponse(url="/storage")
    result.set_cookie(
        key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}'
    )
    return result


@app.post("/create_storage")
async def create_storage_view(
    request: Request,
    storage_name: str = Form(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    storage_create(db, user.id, storage_name)
    flash(request,f"Storage {storage_name} created","success")
    result = RedirectResponse(url="/storage",status_code=status.HTTP_303_SEE_OTHER)
    result.set_cookie(
        key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}'
    )
    return result




@app.exception_handler(HTTPException)
def page_not_found(request:Request, description:HTTPException):
    print('trigger exception handler',type(description),description)
    if description.detail.endswith('Not authenticated'):
        flash(request,"Not authenticated","danger")
        result = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        result.delete_cookie("access_token")
        return result
    return templates.TemplateResponse(request,"error.html", { 'description':description}|get_translations(request)|get_flashed_messages(request),status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

