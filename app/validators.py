import re
from typing import Optional

from sqlmodel import select,Session
from app.models import (
    Article,
    Storage,
    User,
    UserStorage,
)

def validate_new_user_name(session: Session, name: str):
    if not re.match("^[A-Za-z0-9_-]*$", name):
        raise ValueError("Only letters, numbers, - and _ are allowed")
    if _ := session.exec(select(User).where(User.name == name)).first():
        raise ValueError("User with that name already exists")


def valid_storage(
    session: Session, storage_id_or_name: int | str, user_id: int
) -> Optional[Storage]:
    if isinstance(storage_id_or_name, int):
        if _ := session.exec(
            select(UserStorage).where(
                UserStorage.storage_id == storage_id_or_name
                and UserStorage.user_id == user_id
            )
        ).all():
            return session.exec(
                select(Storage).where(Storage.id == storage_id_or_name)
            ).first()
        return None
    storage = session.exec(
        select(Storage).where(Storage.name == storage_id_or_name)
    ).first()
    if not storage:
        return None
    user_storage = session.exec(
        select(UserStorage).where(
            UserStorage.storage_id == storage.id and UserStorage.user_id == user_id
        )
    ).first()
    return storage if user_storage else None


def valid_article(session: Session, article_id: int, user_id: int) -> Optional[Article]:
    article = session.exec(select(Article).where(Article.id == article_id)).first()
    if not article:
        return None
    storage = valid_storage(session, article.storage_id, user_id)
    return article if storage else None
