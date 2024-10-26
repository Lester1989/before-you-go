from datetime import date, timedelta
import sys
import unittest

from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

sys.path.append(".")
from app.controller_storage import storage_create
from app.controller_user import user_create
from app.main import app
from app.models import Article, Storage, User, UserStorage
from app.utility import engine


class TestWebInterface(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        with Session(engine) as session:
            if test_users := list(
                session.exec(select(User).where(User.name == "test")).all()
            ):
                self.assertTrue(len(test_users) == 1)
                self.test_user = test_users[0]
            else:
                self.test_user = user_create(session, "test", "admin", "admin@mail.de")
        response = self.client.post(
            "/token", data={"username": "test", "password": "admin"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("access_token", response.json(), response.json())
        self.token = response.json()["access_token"]

    def tearDown(self) -> None:
        with Session(engine) as session:
            session.exec(delete(User).where(User.name == "test"))
            session.exec(delete(Storage).where(Storage.name == "testFridge"))
            session.exec(delete(Storage).where(Storage.name == "testFreezer"))
            session.exec(delete(Article).where(Article.name == "testMilk"))
            session.exec(
                delete(UserStorage).where(UserStorage.user_id == self.test_user.id)
            )
            session.commit()

    def test_login_view(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

    def test_login_view_post(self):
        self.assertTrue(self.test_user.is_activated)
        response = self.client.post(
            "/login", data={"name": "test", "password": "admin"}
        )
        self.assertEqual(
            response.status_code,
            200,
            response.text.split("<main ")[1].split('<div class="flex')[0],
        )
        self.assertTrue(
            "Login success" in response.text,
            response.text.split("<main ")[1].split('<div class="flex')[0],
        )

        response_fail = self.client.post(
            "/login", data={"name": "admin", "password": "wrong"}
        )
        self.assertIn(
            "Wrong Username or Password", response_fail.text, response_fail.text
        )

    def test_storage_view(self):
        with Session(engine) as session:
            articles = session.exec(
                select(Article)
                .join(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == self.test_user.id)
            ).all()
            storages = session.exec(
                select(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == self.test_user.id)
            ).all()
        response = self.client.get(
            "/storage", cookies={"access_token": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.text.count("<tr>"), len(articles) + len(storages))

    def test_storage_create_remove_recreate_view(self):
        # create storage
        response = self.client.post(
            "/create_storage",
            data={"storage_name": "testFridge"},
            cookies={"access_token": f"Bearer {self.token}"},
            headers={"authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with Session(engine) as session:
            storages = session.exec(
                select(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == self.test_user.id)
            ).all()
            test_storage = next(
                (storage for storage in storages if storage.name == "testFridge"), None
            )
            self.assertIsNotNone(test_storage)
        # remove storage
        response = self.client.get(
            f"/remove_storage/{test_storage.id}",
            cookies={"access_token": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with Session(engine) as session:
            storages = session.exec(
                select(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == self.test_user.id)
            ).all()
            test_storage = next(
                (storage for storage in storages if storage.name == "testFridge"), None
            )
            self.assertIsNone(test_storage, response.content)
        # create storage again
        response = self.client.post(
            "/create_storage",
            data={"storage_name": "testFridge"},
            cookies={"access_token": f"Bearer {self.token}"},
            headers={"authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with Session(engine) as session:
            storages = session.exec(
                select(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == self.test_user.id)
            ).all()
            self.assertEqual(len(storages), 1, response.text)
        self.assertEqual(response.text.count("<tr>"), len(storages), response.text)

    def test_storage_create_remove_empty_storage(self):
        # create storage
        response = self.client.post(
            "/create_storage",
            data={"storage_name": "testFridge"},
            cookies={"access_token": f"Bearer {self.token}"},
            headers={"authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with Session(engine) as session:
            test_storages = list(
                session.exec(
                    select(Storage)
                    .join(UserStorage)
                    .where(
                        UserStorage.user_id == self.test_user.id,
                        Storage.name == "testFridge",
                    )
                ).all()
            )
            self.assertTrue(len(test_storages) == 1)
            test_storage = test_storages[0]

        self.assertEqual(response.text.count("<tr>"), 1, response.text)
        # remove storage
        response = self.client.get(
            f"/remove_storage/{test_storage.id}",
            cookies={"access_token": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with Session(engine) as session:
            storages = session.exec(
                select(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == self.test_user.id)
            ).all()
            test_storage = next(
                (storage for storage in storages if storage.name == "testFridge"), None
            )
            self.assertIsNone(test_storage, response.content)
        self.assertEqual(response.text.count("<tr>"), 0, response.text)

    def test_storage_create_remove_filled_storage(self):
        # create storage
        response = self.client.post(
            "/create_storage",
            data={"storage_name": "testFridge"},
            cookies={"access_token": f"Bearer {self.token}"},
            headers={"authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with Session(engine) as session:
            storages = session.exec(
                select(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == self.test_user.id)
            ).all()
            test_storage = next(
                (storage for storage in storages if storage.name == "testFridge"), None
            )
            self.assertIsNotNone(test_storage)
        # add article
        response = self.client.post(
            "/checkin_date",
            data={
                "name": "testMilk",
                "storage_id": test_storage.id,
                "expiration_date": "2022-01-01",
            },
            cookies={"access_token": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with Session(engine) as session:
            articles = session.exec(
                select(Article)
                .join(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == self.test_user.id)
            ).all()
            test_article = next(
                (article for article in articles if article.name == "testMilk"), None
            )
            self.assertIsNotNone(test_article)
            self.assertEqual(test_article.storage_id, test_storage.id)
        # remove storage
        response = self.client.get(
            f"/remove_storage/{test_storage.id}",
            cookies={"access_token": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response)
        self.assertTrue("Storage not empty" in response.text, response.text)
        with Session(engine) as session:
            storages = session.exec(
                select(Storage).join(UserStorage).where(UserStorage.user_id == self.test_user.id)
            ).all()
            test_storage = next(
                (storage for storage in storages if storage.name == "testFridge"), None
            )
            self.assertIsNotNone(test_storage,session.exec(select(Storage)).all())
        # remove article
        response = self.client.get(
            f"/remove_article/{test_article.id}",
            cookies={"access_token": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with Session(engine) as session:
            articles = session.exec(
                select(Article)
                .join(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == 1)
            ).all()
            test_article = next(
                (article for article in articles if article.name == "testMilk"), None
            )
            self.assertIsNone(test_article)
        # remove storage
        response = self.client.get(
            f"/remove_storage/{test_storage.id}",
            cookies={"access_token": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        with Session(engine) as session:
            storages = session.exec(
                select(Storage).join(UserStorage).where(UserStorage.user_id == 1)
            ).all()
            test_storage = next(
                (storage for storage in storages if storage.name == "testFridge"), None
            )
            self.assertIsNone(test_storage, response.content)

    def test_checkin_view(self):
        with Session(engine) as session:
            articles = session.exec(
                select(Article)
                .join(Storage)
                .join(UserStorage)
                .where(UserStorage.user_id == 1)
            ).all()
        response = self.client.get(
            "/checkin", cookies={"access_token": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.count("<tr>"), len(articles) +1)
        # Add more assertions for the expected behavior

    def test_checkin_view_post(self):
        with Session(engine) as session:
            storage_first = storage_create(
                session,
                self.test_user.id,
                "testFridge",
            )
            storage_second = storage_create(
                session,
                self.test_user.id,
                "testFreezer",
            )
        response = self.client.post(
            "/checkin",
            data={"barcode": "4037400344799", "storage_id": storage_second.id},
            cookies={"access_token": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "selected",
            [
                option_line
                for option_line in response.text.split("\n")
                if f'option value="{storage_second.id}"' in option_line
            ][0],
        )
        # Add more assertions for the expected behavior

    def test_checkin_date_view(self):
        with Session(engine) as session:
            storage_first = storage_create(
                session,
                self.test_user.id,
                "testFridge",
            )
        response = self.client.get(
            f"/checkin_date?name=testMilk&storage_id={storage_first.id}",
            cookies={"access_token": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        # Add more assertions for the expected behavior

    def test_checkin_date_view_post(self):
        with Session(engine) as session:
            storage = storage_create(
                session,
                self.test_user.id,
                "testFridge",
            )
            session.refresh(storage)

        response = self.client.post(
            "/checkin_date",
            data={
                "name": "testMilk",
                "storage_id": storage.id,
                "expiration_date": "2022-01-01",
            },
            cookies={"access_token": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(">testMilk</td>", response.text)
        # Add more assertions for the expected behavior

    def test_set_expiration_view(self):
        with Session(engine) as session:
            storage = storage_create(
                session,
                self.test_user.id,
                "testFridge",
            )
            article = Article(
                name="testMilk",
                storage_id=storage.id,
                expiration_date=date.today() + timedelta(days=10),
            )
            session.add(article)
            session.commit()
            session.refresh(article)
        response = self.client.post(
            "/set_expiration",
            data={
                "article_id": article.id,
                "remaining_days": 10,
            }, cookies={"access_token": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 200)
        # Add more assertions for the expected behavior

    def test_remove_article_view(self):
        response = self.client.get(
            "/remove_article/1", cookies={"access_token": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 200)
        # Add more assertions for the expected behavior


if __name__ == "__main__":
    unittest.main()
