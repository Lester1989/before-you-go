from sqlmodel import Session, select, delete

from app.models import Storage, UserStorage
from app.validators import valid_storage


def storage_create(session: Session, user_id: int, name: str):
    storage = Storage(name=name)
    session.add(storage)
    session.commit()
    session.refresh(storage)
    session.add(UserStorage(user_id=user_id, storage_id=storage.id))
    session.commit()
    session.refresh(storage)
    return storage


def storage_list(session: Session, user_id: int):
    return session.exec(
        select(Storage).join(UserStorage).where(UserStorage.user_id == user_id)
    ).all()


def storage_delete(session: Session, user_id: int, storage_id: int):
    storage = valid_storage(session, storage_id, user_id)
    if not storage:
        raise ValueError("Invalid storage")
    session.exec(delete(UserStorage).where(UserStorage.storage_id == storage.id))
    session.delete(storage)
    session.commit()
    print("Deleted", storage)
    return storage


def storage_update(session: Session, user_id: int, storage_id: int, name: str):
    storage = valid_storage(session, storage_id, user_id)
    if not storage:
        raise ValueError("Invalid storage")
    storage.name = name
    session.commit()
    session.refresh(storage)
    return storage
