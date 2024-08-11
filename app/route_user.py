import os
from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import RedirectResponse

from app.controller_user import user_activate, user_create, user_login, user_update
from app.models import Session, User
from app.utility import get_db, flash, get_flashed_messages, get_translations, templates
from app.auth import create_access_token, get_current_user

app = APIRouter()


@app.get("/logout")
async def logout_view(request: Request):
    flash(request,"Logged out","success")
    result = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    result.delete_cookie("access_token")
    return result

@app.get("/login")
async def login_view(request: Request,username:str=None):
    return templates.TemplateResponse(request, "login.html",{"username":username}| get_translations(request) | get_flashed_messages(request))


@app.post("/login")
async def login_view_post(
    request: Request,
    name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        if user := user_login(db, name, password):
            result = RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)
            result.set_cookie(
                key="access_token",
                value=f'Bearer {create_access_token({"sub": user.name})}',
            )
            flash(request,"Login success","success")
            return result
    except ValueError as e:
        flash(request,f"Wrong Username or Password {e}","danger")

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/register")
async def register_view(request: Request):
    if not os.environ.get("enable_signup"):
        flash(request,"Signup disabled","danger")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "register.html", get_translations(request) | get_flashed_messages(request))

@app.post("/register")
async def register_view_post(
    request: Request,
    name: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    if not os.environ.get("enable_signup"):
        flash(request,"Signup disabled","danger")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    try:
        user_create(db, name, password, email, with_registration=True)
        flash(request,"User created, check you mail before you can log in","success")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as e:
        flash(request,str(e),"danger")
        return RedirectResponse(url="/register", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/confirm_registration/{token}")
async def activate_user_view(request: Request, token: str, db: Session = Depends(get_db)):
    user = user_activate(db,token)
    return RedirectResponse(url=f"/login?username={user.name}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/clear_mail")
async def clear_mail_view(request: Request, db: Session = Depends(get_db), user:User = Depends(get_current_user)):
    user_update(db, user.id, email="")
    flash(request,"Mail cleared","success")
    return RedirectResponse(url="/storage", status_code=status.HTTP_303_SEE_OTHER)