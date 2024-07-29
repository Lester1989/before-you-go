import unittest
from fastapi.testclient import TestClient
import sys
from sqlmodel import Session, select,delete
sys.path.append(".")
from app.controller import user_create
from app.main import app
from app.utility import get_db, engine
from app.models import Article, Storage, User, UserStorage

class TestWebInterface(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.token = self.client.post("/token", data={"username": "admin", "password": "admin"}).json()["access_token"]




    def test_seed_view(self):
        with Session(engine) as session:
            session.exec(delete(User))
            session.exec(delete(Storage))
            session.exec(delete(Article))
            session.exec(delete(UserStorage))
            session.commit()
        response = self.client.get("/seed")
        self.assertEqual(response.status_code, 200)

    def test_login_view(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

    def test_login_view_post(self):
        with Session(engine) as session:
            admin_user = session.exec(select(User).where(User.name == "admin")).first()
            if not admin_user:
                user_create(session, "admin", "admin")
        response = self.client.post("/token", data={"username": "admin", "password": "admin"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("access_token", response.json(), response.json())
        self.assertFalse(response.json()["access_token"].startswith("Bearer"), response.json())

        response_fail = self.client.post("/token", data={"username": "admin", "password": "wrong"})
        self.assertEqual(response_fail.status_code, 401, response_fail.text)


    def test_storage_view(self):
        with Session(engine) as session:
            articles = session.exec(select(Article).join(Storage).join(UserStorage).where(UserStorage.user_id == 1)).all()
            storages = session.exec(select(Storage).join(UserStorage).where(UserStorage.user_id == 1)).all()
        response = self.client.get("/storage", cookies={"access_token": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.text.count("<tr>") , len(articles)+len(storages))
        # Add more assertions for the expected behavior

    def test_checkin_view(self):
        with Session(engine) as session:
            articles = session.exec(select(Article).join(Storage).join(UserStorage).where(UserStorage.user_id == 1)).all()
        response = self.client.get("/checkin", cookies={"access_token": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.count("<tr>") , len(articles)+1)
        # Add more assertions for the expected behavior

    def test_checkin_view_post(self):
        response = self.client.post("/checkin", data={"barcode": "4037400344799", "storage_id": 2}, cookies={"access_token": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("selected", [option_line for option_line in response.text.split("\n") if 'option value="2"' in option_line][0])
        # Add more assertions for the expected behavior

    def test_checkin_date_view(self):
        response = self.client.get("/checkin_date?name=Milk&storage_id=1", cookies={"access_token": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        # Add more assertions for the expected behavior

    def test_checkin_date_view_post(self):
        with Session(engine) as session:
            session.exec(delete(Article).filter(Article.name == "Milk"))
            session.commit()
        response = self.client.post("/checkin_date", data={"name": "Milk", "storage_id": 2, "expiration_date": "2022-01-01"}, cookies={"access_token": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(">Milk</td>", response.text)
        # Add more assertions for the expected behavior

    def test_set_expiration_view(self):
        response = self.client.get("/set_expiration/1/7", cookies={"access_token": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        # Add more assertions for the expected behavior

    def test_remove_article_view(self):
        response = self.client.get("/remove_article/1", cookies={"access_token": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        # Add more assertions for the expected behavior


if __name__ == "__main__":
    unittest.main()