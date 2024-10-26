import asyncio
import os
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, Optional
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Request, status
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import JSON, Column, Integer, String, create_engine, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, select

from app.models import User
from app.utility import ALGORITHM, JWT_KEY, create_access_token, get_db


# Hash a password using bcrypt
def hash_password(password: str):
    pwd_bytes = password.encode()
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode()


# Check if the provided password matches the stored password (hashed)
def verify_password(plain_password: str, hashed_password: str):
    password_byte_enc = plain_password.encode()
    return bcrypt.checkpw(
        password=password_byte_enc, hashed_password=hashed_password.encode()
    )




class UserResponse(BaseModel):
    id: int
    name: str
    password_hash: str
    access_token: str


class UserRequest(BaseModel):
    name: str
    password: str


class NotAuthenticatedException(Exception):
    pass


class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.cookies.get(
            "access_token"
        )  # changed to accept access token from httpOnly Cookie

        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="token")


app = APIRouter()


async def fake_delay():
    await asyncio.sleep(random.random() * 3)


def get_password_hash(password):
    return hash_password(password)


def get_user(name: str,session:Session) -> User | None:
    if user := session.exec(select(User).where(User.name == name)).first():
        return user


def authenticate_user(name: str, password: str,session:Session) -> User | bool:
    if user := get_user(name,session):
        return user if verify_password(password, user.password_hash) else False
    return False



async def get_current_user(token: str = Depends(oauth2_scheme),db:Session=Depends(get_db)) -> User:
    if token is None:
        return None
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    name: str = ""
    try:
        if token.startswith("Bearer "):
            token = token.split("Bearer ")[1]
        payload = jwt.decode(token, JWT_KEY, algorithms=[ALGORITHM])
        name: str = payload.get("sub")  # type: ignore
        if name is None:
            raise NotAuthenticatedException
    except JWTError as e:
        print("JWTError", e)
        raise credentials_exception from e
    user = get_user(name,db)  # type: ignore
    if user is None:
        raise NotAuthenticatedException
    if not user.is_activated:
        raise ValueError("User not activated")
    return user


@app.post(
    "/token", response_model=UserResponse, tags=["auth"], description="coming soon"
)
async def login_for_access_token(
    request: Request, form_data: OAuth2PasswordRequestForm = Depends(),db:Session=Depends(get_db)
):
    user = authenticate_user(form_data.username, form_data.password,db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.name}
    )
    return UserResponse(
        id=user.id,
        name=user.name,
        password_hash=user.password_hash,
        access_token=access_token,
    )


@app.post("/create_user", tags=["auth"], description="coming soon")
async def create_user(request: Request, user: UserRequest, session: Session = Depends(get_db)):
    hashed_password = get_password_hash(user.password)
    existing = session.exec(select(User)).all()
    if existing_user := next((x for x in existing if user.name == x.name), False):
        return {
            "success": False,
            "message": "User already exists",
            "login_id": existing_user.id,
        }
    db_login = User(
        name=user.name,
        password_hash=hashed_password,
        settings={},
    )
    session.add(db_login)
    session.commit()
    session.refresh(db_login)
    return {"success": True, "message": "User created", "login_id": db_login.id}
