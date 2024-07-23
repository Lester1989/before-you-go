# create the fastapi app in main.py. the app is a webapp showing the pages from the templates folder using jinja2 templating

import os
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
)
from app.auth import get_current_user,create_access_token
from app.barcode_lookup import lookup_data
import urllib.parse

SQLModel.metadata.create_all(engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


@app.get("/seed")
async def seed_view(request: Request, db: Session = Depends(get_db)):
    user = user_create(db, "admin", "admin")
    fridge = storage_create(db, user.id, "Fridge")
    freezer = storage_create(db, user.id, "Freezer")
    article_create(db, user.id, "Milk", fridge.id, date.today() + timedelta(days=7))
    article_create(db, user.id, "Ice Cream", freezer.id, date.today() + timedelta(days=300))
    return RedirectResponse(url="/login")

@app.get("/login")
async def login_view(request: Request):
    return templates.TemplateResponse(request,"login.html")

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
    return templates.TemplateResponse(request,"storage_view.html", { "storages": storages, "articles": articles, "user": user})

@app.get("/checkin")
async def checkin_view(request: Request, user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    storages = user.storages(db)
    articles = user.articles(db)
    return templates.TemplateResponse(request,"article_check_in.html", {  "storages": storages, "articles": articles, "user": user})

@app.post("/checkin")
async def checkin_view_post(request: Request, user:User=Depends(get_current_user), db: Session = Depends(get_db),barcode:Optional[str]=Form(""), name:Optional[str]=Form(""), storage_id:int=Form(...)):
    if barcode and not name:
        name = lookup_data(barcode)
    elif not barcode and not name:
        raise ValueError("Barcode or name required")
    storage = valid_storage(db, storage_id, user.id)
    if not storage:
        raise ValueError("Invalid storage")
    return RedirectResponse(url=f"/checkin_date?name={urllib.parse.quote_plus(name)}&storage_id={storage.id}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/checkin_date")
async def checkin_date_view(request: Request, name:str,storage_id:int, user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    storage = valid_storage(db, storage_id, user.id)
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
            "storage": storage,
            "user": user,
            "today": date.today(),
            "days":days,
            "storages": storages,
            "first_of_month":first_of_month,
            "first_of_next_month":first_of_next_month,
            "this_month":first_of_month.strftime("%B %Y"),
            "next_month":first_of_next_month.strftime("%B %Y"),
        })

@app.post("/checkin_date")
async def checkin_date_view_post(request: Request, name:str=Form(...), storage_id:int=Form(...), expiration_date:date=Form(...), user:User=Depends(get_current_user), db: Session = Depends(get_db)):
    storage = valid_storage(db, storage_id, user.id)
    new_article = article_create(db, user.id, name, storage.id, expiration_date)
    print(new_article)
    return RedirectResponse(url="/checkin")