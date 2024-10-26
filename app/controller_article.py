from datetime import date
from typing import Optional

from sqlmodel import Session, select

from app.models import Article
from app.validators import valid_article, valid_storage


def article_create(
    session: Session,
    user_id,
    name: str,
    storage_id_or_name: str | int,
    expiration_date: date,
    quantity: int = 1,
    price: Optional[float] = None,
):
    storage = valid_storage(session, storage_id_or_name, user_id)
    if not storage:
        raise ValueError("Invalid storage")
    article = Article(
        name=name, storage_id=storage.id, price=price, expiration_date=expiration_date, quantity=quantity
    )
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


def article_list(session: Session, user_id: int, storage_id_or_name: str | int):
    if storage := valid_storage(session, storage_id_or_name, user_id):
        return session.exec(
            select(Article).where(Article.storage_id == storage.id)
        ).all()
    raise ValueError("Invalid storage")


def article_delete(session: Session, user_id: int, article_id: int):
    article = session.exec(select(Article).where(Article.id == article_id)).first()
    if not article:
        raise ValueError("Invalid article")
    storage = valid_storage(session, article.storage_id, user_id)
    if not storage:
        raise ValueError("Invalid storage")
    session.delete(article)
    session.commit()
    return article


def article_update(
    session: Session,
    user_id: int,
    article_id: int,
    name: str = None,
    quantity: int = None,
    storage_id_or_name: str | int = None,
    expiration_date: date = None,
    price: Optional[float] = None,
):
    article = valid_article(session, article_id, user_id)
    if not article:
        raise ValueError("Invalid article")
    if storage := valid_storage(session, storage_id_or_name, user_id):
        article.storage_id = storage.id
    if name:
        article.name = name
    if expiration_date:
        article.expiration_date = expiration_date
    if price:
        article.price = price
    if quantity:
        article.quantity = quantity
    session.commit()
    session.refresh(article)
    return article
