import tempfile
import unittest
from pathlib import Path

from app import create_app
from database import db


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            }
        )

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temp_dir.cleanup()

    @staticmethod
    def register(client, email):
        return client.post(
            "/api/auth/register",
            json={"email": email, "password": "password123"},
        )

    def test_applications_require_authentication(self):
        response = self.app.test_client().get("/api/applications")
        self.assertEqual(response.status_code, 401)

    def test_register_logout_and_login(self):
        client = self.app.test_client()
        self.assertEqual(self.register(client, "person@example.com").status_code, 201)
        self.assertEqual(client.get("/api/auth/me").status_code, 200)
        self.assertEqual(client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(client.get("/api/auth/me").status_code, 401)
        self.assertEqual(
            client.post(
                "/api/auth/login",
                json={"email": "person@example.com", "password": "password123"},
            ).status_code,
            200,
        )

    def test_users_only_see_and_modify_their_own_applications(self):
        first_client = self.app.test_client()
        second_client = self.app.test_client()
        self.register(first_client, "first@example.com")
        self.register(second_client, "second@example.com")

        created = first_client.post(
            "/api/applications",
            json={"company": "Private Co", "position": "Engineer", "status": "Applied"},
        )
        application_id = created.get_json()["id"]

        self.assertEqual(len(first_client.get("/api/applications").get_json()), 1)
        self.assertEqual(second_client.get("/api/applications").get_json(), [])
        self.assertEqual(
            second_client.get(f"/api/applications/{application_id}").status_code, 404
        )
        self.assertEqual(
            second_client.put(
                f"/api/applications/{application_id}", json={"status": "Offer"}
            ).status_code,
            404,
        )
        self.assertEqual(
            second_client.delete(f"/api/applications/{application_id}").status_code,
            404,
        )
        self.assertEqual(first_client.get("/api/applications").get_json()[0]["status"], "Applied")


if __name__ == "__main__":
    unittest.main()
