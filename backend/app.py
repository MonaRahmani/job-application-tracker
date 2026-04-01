from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from database import db

app = Flask(__name__, instance_relative_config=True)
Path(app.instance_path).mkdir(parents=True, exist_ok=True)
db_path = Path(app.instance_path) / "database.db"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.resolve().as_posix()}"
app.config["SQLALCHEMY_TRACKING_MODIFICATIONS"] = False

CORS(app)

db.init_app(app)

from models import Application

with app.app_context():
    db.create_all()


@app.route("/api/applications", methods=["GET"])
def get_applications():
    try:
        applications = Application.query.all()
        return jsonify([a.to_dict() for a in applications])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/applications/<int:id>", methods=["GET"])
def get_application(id):
    try:
        application = Application.query.get(id)
        if application is None:
            return jsonify({"error": "Application not found"}), 404
        return jsonify(application.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/applications/<int:id>", methods=["PUT"])
def update_application(id):
    try:
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Request body must be JSON"}), 400

        application = Application.query.get(id)
        if application is None:
            return jsonify({"error": "Application not found"}), 404

        if "company" in data:
            company = data["company"]
            if company is None or (isinstance(company, str) and not company.strip()):
                return jsonify({"error": "company cannot be empty"}), 400
            application.company = company.strip() if isinstance(company, str) else company

        if "position" in data:
            position = data["position"]
            if position is None or (isinstance(position, str) and not position.strip()):
                return jsonify({"error": "position cannot be empty"}), 400
            application.position = position.strip() if isinstance(position, str) else position

        if "status" in data:
            status = data["status"]
            if status is None or (isinstance(status, str) and not status.strip()):
                return jsonify({"error": "status cannot be empty"}), 400
            if status not in Application.ALLOWED_STATUSES:
                return jsonify({"error": "status must be one of: Applied, Interview, Offer, Rejected"}), 400
            application.status = status.strip() if isinstance(status, str) else status

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
            notes = data["notes"]
            application.notes = None if notes == "" else notes

        db.session.commit()
        return jsonify(application.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/applications/<int:id>", methods=["DELETE"])
def delete_application(id):
    try:
        application = Application.query.get(id)
        if application is None:
            return jsonify({"error": "Application not found"}), 404
        db.session.delete(application)
        db.session.commit()
        return "", 204
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/applications", methods=["POST"])
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
        if notes == "":
            notes = None

        application = Application(
            company=company.strip() if isinstance(company, str) else company,
            position=position.strip() if isinstance(position, str) else position,
            date_applied=date_applied,
            status=status.strip() if isinstance(status, str) else status,
            notes=notes,
        )
        db.session.add(application)
        db.session.commit()
        return jsonify(application.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
