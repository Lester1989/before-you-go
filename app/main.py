# create the fastapi app in main.py. the app is a webapp showing the pages from the templates folder using jinja2 templating

import os
import json
import pathlib
import calendar
from typing import Optional
from fastapi import FastAPI, Request, Form, Depends,status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from datetime import date,timedelta
from app.models import User, Session, engine, SQLModel
from app.utility import get_db
from app.controller import (
    article_create,
    article_list,
    article_delete,
    article_update,
    valid_storage,
    valid_article,
    storage_create,
    storage_delete,
    storage_list,
    storage_update,
    user_create,
    user_delete,
    user_list,
    user_login,
    user_update,
    lookup_data
)
from app.auth import get_current_user,create_access_token,app as auth_app
import urllib.parse
import string

SQLModel.metadata.create_all(engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_app)

def string_to_slug(raw_string:str):
    result = "".join([char if char in string.ascii_lowercase + string.digits else "-" for char in raw_string.lower()])
    return result.replace("--","-")

templates.env.globals["string_to_slug"] = string_to_slug


locales: dict[str, dict[str, str]] = {
    file_name.stem.lower(): json.loads(file_name.read_text(encoding='utf-8'))
    for file_name in pathlib.Path('app/', 'locale').iterdir()
}

def get_translations(request:Request)->dict[str,str]:
    requested_languages:list[str] = request.headers.get('Accept-Language','en').split(',')
    for language in requested_languages:
        clean_language = language.split('-')[0].lower()
        if clean_language in locales:
            return locales[clean_language]
    return locales['en']


@app.get("/seed")
async def seed_view(db: Session = Depends(get_db)):
    user = user_create(db, "admin", "admin")
    fridge = storage_create(db, user.id, "Fridge")
    freezer = storage_create(db, user.id, "Freezer")
    article_create(db, user.id, "Milk", fridge.id, date.today() + timedelta(days=7))
    article_create(db, user.id, "Ice Cream", freezer.id, date.today() + timedelta(days=300))
    return RedirectResponse(url="/login")

@app.get("/login")
async def login_view(request: Request):
    return templates.TemplateResponse(request,"login.html",get_translations(request))

@app.post("/login")
async def login_view_post(request: Request, name: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = user_login(db, name, password)
    if user:
        result = RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)
        result.set_cookie(key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}')
        return result
    return RedirectResponse(url="/login")

@app.get("/storage")
async def storage_view(request: Request, user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    storages = user.storages(db)
    articles = user.articles(db)
    return templates.TemplateResponse(request,"storage_view.html", { "storages": storages, "articles": articles, "user": user}|get_translations(request))

@app.get("/checkin")
async def checkin_view(request: Request,storage_id:Optional[int]=None, user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    storages = user.storages(db)
    articles = user.articles(db)
    return templates.TemplateResponse(request,"article_check_in.html", {  "storages": storages, "articles": articles, "user": user,"selected_storage_id":storage_id}|get_translations(request))

@app.post("/checkin")
async def checkin_view_post(request: Request, user:User=Depends(get_current_user), db: Session = Depends(get_db),barcode:Optional[str]=Form(""), name:Optional[str]=Form(""), storage_id:int=Form(...)):
    if barcode and not name:
        name = lookup_data(db,barcode)
    elif not barcode and not name:
        raise ValueError("Barcode or name required")
    storage = valid_storage(db, storage_id, user.id)
    if not storage:
        raise ValueError("Invalid storage")
    result = RedirectResponse(url=f"/checkin_date?name={urllib.parse.quote_plus(name)}&storage_id={storage.id}", status_code=status.HTTP_303_SEE_OTHER)
    result.set_cookie(key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}')
    return result

@app.get("/checkin_date")
async def checkin_date_view(request: Request, name:str,storage_id:int, user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    
    storage = valid_storage(db, storage_id, user.id)
    print('valid storage', storage)
    storages = user.storages(db)

    first_of_month = date.today().replace(day=1)
    first_of_next_month = first_of_month + timedelta(days=calendar.monthrange(first_of_month.year, first_of_month.month)[1])
    last_of_next_month = first_of_next_month + timedelta(days=calendar.monthrange(first_of_next_month.year, first_of_next_month.month)[1]-1)

    days = {}
    for i in range((last_of_next_month-first_of_month).days+1):
        day = first_of_month+timedelta(days=i)
        days[day] = (day.month,day.weekday(),(day-date.today()).days)

    return templates.TemplateResponse(
        request,
        "article_check_in_date.html",
        {
            "name": name,
            "selected_storage": storage,
            "user": user,
            "today": date.today(),
            "days":days,
            "storages": storages,
            "first_of_month":first_of_month,
            "first_of_next_month":first_of_next_month,
            "this_month":first_of_month.strftime("%B %Y"),
            "next_month":first_of_next_month.strftime("%B %Y"),
        }|get_translations(request))

@app.post("/checkin_date")
async def checkin_date_view_post(request: Request, name:str=Form(...), storage_id:int=Form(...), expiration_date:date=Form(...), user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    storage = valid_storage(db, storage_id, user.id)
    print('valid storage',storage)
    new_article = article_create(db, user.id, name, storage.id, expiration_date)
    print(new_article)
    result = RedirectResponse(url=f"/checkin?storage_id={storage_id}", status_code=status.HTTP_303_SEE_OTHER)
    result.set_cookie(key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}')
    return result

@app.get("/set_expiration/{article_id}/{remaining_days}")
async def set_expiration_view(request: Request, article_id:int, remaining_days:int, user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    article = valid_article(db, article_id, user.id)
    if article:
        article.expiration_date = date.today() + timedelta(days=remaining_days)
        db.commit()
    result = RedirectResponse(url="/storage")
    result.set_cookie(key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}')
    return result

@app.get("/remove_article/{article_id}")
async def remove_article_view(request: Request, article_id:int, user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    article = valid_article(db, article_id, user.id)
    if article:
        article_delete(db,user.id, article_id)
    result = RedirectResponse(url="/storage")
    result.set_cookie(key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}')
    return result

@app.get("remove_storage/{storage_id}")
async def remove_storage_view(request: Request, storage_id:int, user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    storage = valid_storage(db, storage_id, user.id)
    if storage:
        storage_delete(db,user.id, storage_id)
    result = RedirectResponse(url="/storage")
    result.set_cookie(key="access_token", value=f'Bearer {create_access_token({"sub": user.name})}')
    return result

@app.get("/create_storage")
async def create_storage_view(request: Request,storage_name:str=Form(), user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    storage_create(db, user.id, storage_name)
    return RedirectResponse(url="/storage")
