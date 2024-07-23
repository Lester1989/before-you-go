from __future__ import annotations
from typing import Optional
from datetime import datetime,timedelta
from sqlmodel import Field, Session, SQLModel, select
from app.utility import engine

class Article(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    storage_id: Optional[int] = Field(default=None, foreign_key="storage.id")
    expiration_date: datetime = Field(default_factory= lambda: datetime.today() + timedelta(days=3))
    price: Optional[float] = Field(default=None)
    insertion_date: datetime = Field(default_factory= datetime.today)

    @property
    def is_expired(self):
        return self.expiration_date < datetime.today()+timedelta(days=1)
    
    @property
    def days_left(self):
        return (self.expiration_date - datetime.today()).days

class Storage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    def articles(self, session: Session):
        return session.exec(select(Article).where(Article.storage_id == self.id)).all()


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default=None, index=True)
    password_hash: str
    email: Optional[str] = None

    def storages(self, session: Session):
        return session.exec(select(Storage).join(UserStorage).where(UserStorage.user_id == self.id)).all()

    def articles(self, session: Session):
        return session.exec(select(Article).join(Storage).join(UserStorage).where(UserStorage.user_id == self.id)).all()


class UserStorage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    storage_id: Optional[int] = Field(default=None, foreign_key="storage.id")




def main():
    SQLModel.metadata.create_all(engine)
    fridge = Storage(name="Fridge")
    user = User(name="John")
    with Session(engine) as session:
        session.add(user)
        session.add(fridge)

        session.commit()
        session.refresh(fridge)
        session.refresh(user)
        session.add(UserStorage(user_id=user.id, storage_id=fridge.id))

        sausage = Article(name="Sausage", storage_id=fridge.id, price=3.5, expiration_date=datetime.today() + timedelta(days=7))
        cheese = Article(name="Cheese", storage_id=fridge.id, price=2.5, expiration_date=datetime.today() + timedelta(days=5))
        eggs = Article(name="Eggs", storage_id=fridge.id, price=1.5, expiration_date=datetime.today() + timedelta(days=10))
        session.add(cheese)
        session.add(sausage)
        session.add(eggs)
        session.commit()
        session.refresh(fridge)
        for article in fridge.articles(session):
            print(fridge.name,article.name)

        for article in user.articles(session):
            print(user.name,article.name)

        for storage in user.storages(session):
            print(user.name,storage.name)


if __name__ == "__main__":
    main()