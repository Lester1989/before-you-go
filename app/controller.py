from datetime import date
from typing import Optional
from app.models import BarCodeCache, User, Storage, UserStorage, Article, Session, engine, SQLModel
from sqlmodel import select,delete
import bcrypt
import openfoodfacts

api = openfoodfacts.API(user_agent="BeforeYouGo/0.1")

def valid_storage(session:Session, storage_id_or_name:int|str, user_id:int)-> Optional[Storage]:
    if isinstance(storage_id_or_name, int):
        user_storages = session.exec(select(UserStorage).where(UserStorage.storage_id == storage_id_or_name and UserStorage.user_id == user_id)).all()
        if user_storages:
            return session.exec(select(Storage).where(Storage.id == storage_id_or_name)).first()
        return None
    storage = session.exec(select(Storage).where(Storage.name == storage_id_or_name)).first()
    if not storage:
        return None
    user_storage = session.exec(select(UserStorage).where(UserStorage.storage_id == storage.id and UserStorage.user_id == user_id)).first()
    return storage if user_storage else None

def valid_article(session:Session, article_id:int, user_id:int)-> Optional[Article]:
    article = session.exec(select(Article).where(Article.id == article_id)).first()
    if not article:
        return None
    storage = valid_storage(session, article.storage_id, user_id)
    return article if storage else None

def article_create(session:Session, user_id, name:str, storage_id_or_name:str|int, expiration_date:date, price:Optional[float]=None):
    storage = valid_storage(session, storage_id_or_name, user_id)
    if not storage:
        raise ValueError("Invalid storage")
    article = Article(name=name, storage_id=storage.id, price=price, expiration_date=expiration_date)
    session.add(article)
    session.commit()
    session.refresh(article)
    return article

def article_list(session:Session, user_id:int, storage_id_or_name:str|int):
    storage = valid_storage(session, storage_id_or_name, user_id)
    if not storage:
        raise ValueError("Invalid storage")
    return session.exec(select(Article).where(Article.storage_id == storage.id)).all()

def article_delete(session:Session, user_id:int, article_id:int):
    article = session.exec(select(Article).where(Article.id == article_id)).first()
    if not article:
        raise ValueError("Invalid article")
    storage = valid_storage(session, article.storage_id, user_id)
    if not storage:
        raise ValueError("Invalid storage")
    session.delete(article)
    session.commit()
    return article

def article_update(session:Session, user_id:int, article_id:int, name:str=None, storage_id_or_name:str|int=None, expiration_date:date=None, price:Optional[float]=None):
    article = valid_article(session, article_id, user_id)
    if not article:
        raise ValueError("Invalid article")
    storage = valid_storage(session, storage_id_or_name, user_id)
    if storage:
        article.storage_id = storage.id
    if name:
        article.name = name
    if expiration_date:
        article.expiration_date = expiration_date
    if price:
        article.price = price
    session.commit()
    session.refresh(article)
    return article

def storage_create(session:Session, user_id:int, name:str):
    storage = Storage(name=name)
    session.add(storage)
    session.commit()
    session.refresh(storage)
    session.add(UserStorage(user_id=user_id, storage_id=storage.id))
    session.commit()
    session.refresh(storage)
    return storage

def storage_list(session:Session, user_id:int):
    return session.exec(select(Storage).join(UserStorage).where(UserStorage.user_id == user_id)).all()

def storage_delete(session:Session, user_id:int, storage_id:int):
    storage = valid_storage(session, storage_id, user_id)
    if not storage:
        raise ValueError("Invalid storage")
    session.exec(delete(UserStorage).where(UserStorage.storage_id == storage.id))
    session.delete(storage)
    session.commit()
    print("Deleted",storage)
    return storage

def storage_update(session:Session, user_id:int, storage_id:int, name:str):
    storage = valid_storage(session, storage_id, user_id)
    if not storage:
        raise ValueError("Invalid storage")
    storage.name = name
    session.commit()
    session.refresh(storage)
    return storage

def user_create(session:Session, name:str, password:str, email:str=None):
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(name=name, password_hash=password_hash, email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def user_list(session:Session):
    return session.exec(select(User)).all()

def user_delete(session:Session, user_id:int):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise ValueError("Invalid user")
    session.delete(user)
    session.commit()
    return user

def user_update(session:Session, user_id:int, name:str=None, password:str=None, email:str=None):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise ValueError("Invalid user")
    if name:
        user.name = name
    if password:
        user.password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    if email:
        user.email = email
    session.commit()
    session.refresh(user)
    return user

def user_login(session:Session, name:str, password:str):
    user = session.exec(select(User).where(User.name == name)).first()
    if not user:
        raise ValueError("Invalid user")
    if bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return user
    raise ValueError("Invalid password")

def lookup_data(session:Session, barcode:str):
    cache = session.exec(select(BarCodeCache).where(BarCodeCache.barcode == barcode)).first()
    if cache:
        return cache.data
    # Call external API
    try:
        data = api.product.get(code=barcode,fields=["product_name","quantity","brands"])
        if data:
            data_str = f'{data["product_name"]} ({data["brands"]}) - {data["quantity"]}'
            session.add(BarCodeCache(barcode=barcode, data=data_str))
            session.commit()
            return data_str
    except Exception as e:
        print(e)
    return ""

