import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch
from pathlib import Path

from app import create_app
from database import db
from matcher import InvalidResumeError


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

    def test_resume_upload_and_job_description_match(self):
        client = self.app.test_client()
        self.register(client, "matcher@example.com")
        resume = (
            b"Software engineer with Python Flask SQL REST API testing and cloud "
            b"experience. Improved service performance by 30 percent."
        )
        uploaded = client.post(
            "/api/profile/resume",
            data={"resume": (BytesIO(resume), "resume.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(uploaded.status_code, 200)
        self.assertEqual(uploaded.get_json()["user"]["resume_filename"], "resume.txt")

        application = client.post(
            "/api/applications",
            json={"company": "Example", "position": "Engineer", "status": "Applied"},
        ).get_json()
        with patch(
            "app.match_resume",
            return_value={
                "score": 78,
                "suggestions": ["Emphasize API outcomes.", "Add cloud scale if accurate."],
                "matched_keywords": ["python", "flask", "sql"],
                "missing_keywords": ["kubernetes"],
            },
        ):
            matched = client.post(
                f"/api/applications/{application['id']}/match",
                json={
                    "job_description": (
                        "Build Python and Flask REST services with SQL, Docker, Kubernetes, "
                        "automated testing, monitoring, and cloud deployment."
                    )
                },
            )
        self.assertEqual(matched.status_code, 200)
        result = matched.get_json()
        self.assertGreaterEqual(result["match_score"], 0)
        self.assertLessEqual(result["match_score"], 100)
        self.assertTrue(result["match_suggestions"])
        self.assertIn("python", result["matched_keywords"])

    def test_match_cannot_use_another_users_application(self):
        owner = self.app.test_client()
        other = self.app.test_client()
        self.register(owner, "owner@example.com")
        self.register(other, "other@example.com")
        application = owner.post(
            "/api/applications",
            json={"company": "Private", "position": "Analyst", "status": "Applied"},
        ).get_json()
        response = other.post(
            f"/api/applications/{application['id']}/match",
            json={"job_description": "Detailed private job description with analytics and reporting"},
        )
        self.assertEqual(response.status_code, 404)

    def test_non_resume_document_is_rejected_before_match_is_saved(self):
        client = self.app.test_client()
        self.register(client, "curriculum@example.com")
        document = (
            b"Course curriculum weekly schedule learning objectives required readings "
            b"assignments grading policy lectures and classroom activities."
        )
        client.post(
            "/api/profile/resume",
            data={"resume": (BytesIO(document), "curriculum.txt")},
            content_type="multipart/form-data",
        )
        application = client.post(
            "/api/applications",
            json={"company": "Example", "position": "Engineer", "status": "Applied"},
        ).get_json()

        with patch(
            "app.match_resume",
            side_effect=InvalidResumeError("It appears to be a course curriculum."),
        ):
            response = client.post(
                f"/api/applications/{application['id']}/match",
                json={"job_description": "Build production software and collaborate with engineers."},
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("does not look like a resume", response.get_json()["error"])
        saved = client.get(f"/api/applications/{application['id']}").get_json()
        self.assertIsNone(saved["match_score"])


if __name__ == "__main__":
    unittest.main()
