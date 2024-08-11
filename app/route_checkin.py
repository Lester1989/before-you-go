import calendar
import urllib.parse
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse

from app.auth import create_access_token, get_current_user
from app.controller import lookup_data
from app.controller_article import article_create
from app.models import Session, User
from app.utility import flash, get_db, get_flashed_messages, get_translations, templates
from app.validators import valid_storage

app = APIRouter()


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

    return templates.TemplateResponse(
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


def calculate_calendar_dates():
    first_of_month = date.today().replace(day=1)
    first_of_next_month = first_of_month + timedelta(
        days=calendar.monthrange(first_of_month.year, first_of_month.month)[1]
    )
    last_of_next_month = first_of_next_month + timedelta(
        days=calendar.monthrange(first_of_next_month.year, first_of_next_month.month)[1]
        - 1
    )

    days = {}
    for i in range((last_of_next_month - first_of_month).days + 1):
        day = first_of_month + timedelta(days=i)
        days[day] = (day.month, day.weekday(), (day - date.today()).days)
    return first_of_month, first_of_next_month, days


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
        "success",
    )
    result = RedirectResponse(
        url=f"/checkin?storage_id={storage_id}", status_code=status.HTTP_303_SEE_OTHER
    )
    result.set_cookie(
        key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}'
    )
    return result
