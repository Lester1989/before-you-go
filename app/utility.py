
from sqlmodel import Session,create_engine

engine = create_engine("sqlite:///database/database.db")

def get_db():
    with Session(engine) as session:
        yield session
