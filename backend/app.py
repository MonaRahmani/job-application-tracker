from datetime import datetime
from functools import wraps
from io import BytesIO
import json
import os
from pathlib import Path

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import db

from models import Application, User
from matcher import InvalidResumeError, MatchServiceError, match_resume


load_dotenv(Path(__file__).with_name(".env"))


def create_app(test_config=None):
    frontend_path = Path(__file__).resolve().parent.parent / "frontend"
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=str(frontend_path),
        static_url_path="",
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db_path = Path(app.instance_path) / "database.db"
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path.resolve().as_posix()}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    CORS(
        app,
        supports_credentials=True,
        origins=["null", "http://127.0.0.1:8000", "http://localhost:8000"],
    )
    db.init_app(app)

    with app.app_context():
        User.__table__.create(db.engine, checkfirst=True)
        _migrate_existing_database()
        db.create_all()

    register_routes(app)
    return app


def _add_columns(table, columns):
    existing = {column["name"] for column in inspect(db.engine).get_columns(table)}
    for name, definition in columns.items():
        if name not in existing:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))


def _migrate_existing_database():
    """Upgrade older SQLite databases without deleting user data."""
    _add_columns(
        "users",
        {
            "resume_filename": "VARCHAR(255)",
            "resume_text": "TEXT",
            "resume_uploaded_at": "DATETIME",
        },
    )
    if not inspect(db.engine).has_table("applications"):
        db.session.commit()
        return
    existing = {column["name"] for column in inspect(db.engine).get_columns("applications")}
    _add_columns(
        "applications",
        {
            "owner_id": "INTEGER REFERENCES users(id)",
            "job_description": "TEXT",
            "match_score": "INTEGER",
            "match_suggestions": "TEXT",
            "matched_keywords": "TEXT",
            "missing_keywords": "TEXT",
            "matched_at": "DATETIME",
        },
    )
    if "owner_id" not in existing:
        db.session.execute(
            text("CREATE INDEX IF NOT EXISTS ix_applications_owner_id ON applications (owner_id)")
        )
    db.session.commit()


def _extract_resume(file):
    filename = secure_filename(file.filename or "")
    extension = Path(filename).suffix.lower()
    data = file.read()
    if not data:
        raise ValueError("The resume file is empty")
    if extension == ".txt":
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("The text resume must use UTF-8 encoding") from error
    elif extension == ".pdf":
        try:
            from pypdf import PdfReader

            content = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages)
        except ImportError as error:
            raise ValueError("PDF support is not installed; run pip install -r requirements.txt") from error
        except Exception as error:
            raise ValueError("The PDF could not be read") from error
    else:
        raise ValueError("Resume must be a PDF or UTF-8 text file")
    content = content.strip()
    if len(content) < 50:
        raise ValueError("The resume does not contain enough readable text")
    return filename, content


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("user_id") is None:
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped_view


def _email_from_request(data):
    email = data.get("email")
    if not isinstance(email, str) or not email.strip():
        return None
    return email.strip().lower()


def register_routes(app):
    @app.get("/")
    def frontend():
        return app.send_static_file("index.html")

    @app.post("/api/auth/register")
    def register():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be JSON"}), 400

        email = _email_from_request(data)
        password = data.get("password")
        if email is None or "@" not in email:
            return jsonify({"error": "A valid email is required"}), 400
        if not isinstance(password, str) or len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400
        if User.query.filter_by(email=email).first() is not None:
            return jsonify({"error": "An account with that email already exists"}), 409

        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session.clear()
        session["user_id"] = user.id
        return jsonify({"user": user.to_dict()}), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be JSON"}), 400

        email = _email_from_request(data)
        password = data.get("password")
        user = User.query.filter_by(email=email).first() if email else None
        if user is None or not isinstance(password, str) or not check_password_hash(
            user.password_hash, password
        ):
            return jsonify({"error": "Invalid email or password"}), 401

        session.clear()
        session["user_id"] = user.id
        return jsonify({"user": user.to_dict()})

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return "", 204

    @app.get("/api/auth/me")
    @login_required
    def current_user():
        user = db.session.get(User, session["user_id"])
        if user is None:
            session.clear()
            return jsonify({"error": "Authentication required"}), 401
        return jsonify({"user": user.to_dict()})

    @app.get("/api/profile")
    @login_required
    def get_profile():
        user = db.session.get(User, session["user_id"])
        return jsonify({"user": user.to_dict()})

    @app.post("/api/profile/resume")
    @login_required
    def upload_resume():
        file = request.files.get("resume")
        if file is None:
            return jsonify({"error": "Choose a resume file"}), 400
        try:
            filename, content = _extract_resume(file)
        except MatchServiceError as error:
            status = 503 if "not configured" in str(error) else 502
            return jsonify({"error": str(error)}), status
        user = db.session.get(User, session["user_id"])
        user.resume_filename = filename
        user.resume_text = content
        user.resume_uploaded_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"user": user.to_dict()})

    @app.get("/api/applications")
    @login_required
    def get_applications():
        applications = Application.query.filter_by(owner_id=session["user_id"]).all()
        return jsonify([application.to_dict() for application in applications])

    @app.get("/api/applications/<int:application_id>")
    @login_required
    def get_application(application_id):
        application = Application.query.filter_by(
            id=application_id, owner_id=session["user_id"]
        ).first()
        if application is None:
            return jsonify({"error": "Application not found"}), 404
        return jsonify(application.to_dict())

    @app.post("/api/applications")
    @login_required
    def create_application():
        try:
            data = request.get_json(silent=True)
            if data is None:
                return jsonify({"error": "Request body must be JSON"}), 400

            company = data.get("company")
            position = data.get("position")
            status = data.get("status")

            if company is None or (isinstance(company, str) and not company.strip()):
                return jsonify({"error": "company is required"}), 400
            if position is None or (isinstance(position, str) and not position.strip()):
                return jsonify({"error": "position is required"}), 400
            if status is None or (isinstance(status, str) and not status.strip()):
                return jsonify({"error": "status is required"}), 400
            if status not in Application.ALLOWED_STATUSES:
                return jsonify({"error": "status must be one of: Applied, Interview, Offer, Rejected"}), 400

            date_applied = None
            raw_date = data.get("date_applied")
            if raw_date is not None and raw_date != "":
                try:
                    date_applied = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    return jsonify({"error": 'date_applied must be a string in "%Y-%m-%d" format'}), 400

            notes = data.get("notes")
            application = Application(
                owner_id=session["user_id"],
                company=company.strip() if isinstance(company, str) else company,
                position=position.strip() if isinstance(position, str) else position,
                date_applied=date_applied,
                status=status.strip() if isinstance(status, str) else status,
                notes=None if notes == "" else notes,
                job_description=data.get("job_description") or None,
            )
            db.session.add(application)
            db.session.commit()
            return jsonify(application.to_dict()), 201
        except Exception as error:
            db.session.rollback()
            return jsonify({"error": str(error)}), 500

    @app.put("/api/applications/<int:application_id>")
    @login_required
    def update_application(application_id):
        try:
            data = request.get_json(silent=True)
            if data is None:
                return jsonify({"error": "Request body must be JSON"}), 400

            application = Application.query.filter_by(
                id=application_id, owner_id=session["user_id"]
            ).first()
            if application is None:
                return jsonify({"error": "Application not found"}), 404

            for field in ("company", "position"):
                if field in data:
                    value = data[field]
                    if value is None or (isinstance(value, str) and not value.strip()):
                        return jsonify({"error": f"{field} cannot be empty"}), 400
                    setattr(application, field, value.strip() if isinstance(value, str) else value)

            if "status" in data:
                status = data["status"]
                if status not in Application.ALLOWED_STATUSES:
                    return jsonify({"error": "status must be one of: Applied, Interview, Offer, Rejected"}), 400
                application.status = status

            if "date_applied" in data:
                raw_date = data["date_applied"]
                if raw_date is None or raw_date == "":
                    application.date_applied = None
                else:
                    try:
                        application.date_applied = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        return jsonify({"error": 'date_applied must be a string in "%Y-%m-%d" format'}), 400

            if "notes" in data:
                application.notes = None if data["notes"] == "" else data["notes"]

            if "job_description" in data:
                application.job_description = data["job_description"] or None
                application.match_score = None
                application.match_suggestions = None
                application.matched_keywords = None
                application.missing_keywords = None
                application.matched_at = None

            db.session.commit()
            return jsonify(application.to_dict())
        except Exception as error:
            db.session.rollback()
            return jsonify({"error": str(error)}), 500

    @app.post("/api/applications/<int:application_id>/match")
    @login_required
    def match_application(application_id):
        application = Application.query.filter_by(
            id=application_id, owner_id=session["user_id"]
        ).first()
        if application is None:
            return jsonify({"error": "Application not found"}), 404
        user = db.session.get(User, session["user_id"])
        if not user.resume_text:
            return jsonify({"error": "Upload a resume to your profile first"}), 400
        data = request.get_json(silent=True) or {}
        job_description = data.get("job_description", application.job_description)
        if not isinstance(job_description, str) or not job_description.strip():
            return jsonify({"error": "Paste a job description first"}), 400
        try:
            result = match_resume(user.resume_text, job_description)
        except InvalidResumeError as error:
            return jsonify({"error": f"This file does not look like a resume: {error}"}), 422
        except MatchServiceError as error:
            status = 503 if "not configured" in str(error) else 502
            return jsonify({"error": str(error)}), status

        application.job_description = job_description.strip()
        application.match_score = result["score"]
        application.match_suggestions = json.dumps(result["suggestions"])
        application.matched_keywords = json.dumps(result["matched_keywords"])
        application.missing_keywords = json.dumps(result["missing_keywords"])
        application.matched_at = datetime.utcnow()
        db.session.commit()
        return jsonify(application.to_dict())

    @app.delete("/api/applications/<int:application_id>")
    @login_required
    def delete_application(application_id):
        application = Application.query.filter_by(
            id=application_id, owner_id=session["user_id"]
        ).first()
        if application is None:
            return jsonify({"error": "Application not found"}), 404
        db.session.delete(application)
        db.session.commit()
        return "", 204


app = create_app()

if __name__ == "__main__":
    app.run(port=5000, debug=True)
