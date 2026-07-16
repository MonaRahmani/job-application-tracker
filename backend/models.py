from datetime import datetime

from sqlalchemy import CheckConstraint

from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    applications = db.relationship(
        "Application",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {"id": self.id, "email": self.email}


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
            "created_at": self.created_at.isoformat()
            if self.created_at
            else None,
        }
