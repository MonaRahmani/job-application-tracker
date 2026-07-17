from datetime import datetime
import json

from sqlalchemy import CheckConstraint

from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    resume_filename = db.Column(db.String(255))
    resume_text = db.Column(db.Text)
    resume_uploaded_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    applications = db.relationship(
        "Application",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "resume_filename": self.resume_filename,
            "resume_uploaded_at": self.resume_uploaded_at.isoformat()
            if self.resume_uploaded_at
            else None,
        }


class Application(db.Model):
    __tablename__ = "applications"

    ALLOWED_STATUSES = ("Applied", "Interview", "Offer", "Rejected")

    __table_args__ = (
        CheckConstraint(
            "status IN ('Applied', 'Interview', 'Offer', 'Rejected')",
            name="ck_application_status_allowed",
        ),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    company = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    date_applied = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    job_description = db.Column(db.Text)
    match_score = db.Column(db.Integer)
    match_suggestions = db.Column(db.Text)
    matched_keywords = db.Column(db.Text)
    missing_keywords = db.Column(db.Text)
    matched_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", back_populates="applications")

    def to_dict(self):
        return {
            "id": self.id,
            "company": self.company,
            "position": self.position,
            "date_applied": self.date_applied.isoformat()
            if self.date_applied
            else None,
            "status": self.status,
            "notes": self.notes,
            "job_description": self.job_description,
            "match_score": self.match_score,
            "match_suggestions": json.loads(self.match_suggestions)
            if self.match_suggestions
            else [],
            "matched_keywords": json.loads(self.matched_keywords)
            if self.matched_keywords
            else [],
            "missing_keywords": json.loads(self.missing_keywords)
            if self.missing_keywords
            else [],
            "matched_at": self.matched_at.isoformat() if self.matched_at else None,
            "created_at": self.created_at.isoformat()
            if self.created_at
            else None,
        }
