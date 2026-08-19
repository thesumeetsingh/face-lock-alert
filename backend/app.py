import base64
import os
import re
from datetime import datetime

import cv2
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from alerts import send_security_alert
from db import (
    create_login_attempt,
    create_user,
    email_exists,
    get_attempt_image,
    get_login_stats,
    get_recent_attempts,
    get_user_by_id,
    get_user_by_username,
    init_db,
)
from face_service import decode_image, train_user_model, verify_face

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-key")

CORS(
    app,
    supports_credentials=True,
    origins=["http://localhost:5173", "http://127.0.0.1:5173"],
)

CAPTURE_COUNT = int(os.getenv("FACE_CAPTURE_COUNT", "15"))
FACE_THRESHOLD = float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "70"))

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+?[1-9]\d{9,14}$")


def now_utc():
    return datetime.utcnow()


def user_response(user):
    created_at = user.get("created_at")
    return {
        "id": user["id"],
        "name": user["name"],
        "username": user["username"],
        "email": user["email"],
        "phone": user["phone"],
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
    }


def location_values(location):
    if not isinstance(location, dict):
        return None, None

    try:
        latitude = float(location["latitude"]) if location.get("latitude") is not None else None
        longitude = float(location["longitude"]) if location.get("longitude") is not None else None
    except (TypeError, ValueError):
        return None, None

    if latitude is not None and not -90 <= latitude <= 90:
        latitude = None
    if longitude is not None and not -180 <= longitude <= 180:
        longitude = None
    return latitude, longitude


def serialize_attempt(row):
    attempted_at = row.get("attempted_at")
    latitude = float(row["latitude"]) if row.get("latitude") is not None else None
    longitude = float(row["longitude"]) if row.get("longitude") is not None else None
    confidence = float(row["confidence"]) if row.get("confidence") is not None else None

    return {
        "id": row["id"],
        "success": bool(row["success"]),
        "reason": row["reason"],
        "confidence": confidence,
        "latitude": latitude,
        "longitude": longitude,
        "attempted_at": attempted_at.isoformat() if hasattr(attempted_at, "isoformat") else attempted_at,
        "has_image": bool(row["has_image"]),
    }


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/config")
def config():
    return jsonify({"capture_count": CAPTURE_COUNT})


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    password = data.get("password", "")

    if not all([name, username, email, phone, password]):
        return jsonify({"error": "All registration fields are required."}), 400

    if not EMAIL_RE.match(email):
        return jsonify({"error": "Enter a valid email address."}), 400

    if not PHONE_RE.match(phone):
        return jsonify({"error": "Enter phone number in international format, e.g. +919876543210."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must contain at least 6 characters."}), 400

    if get_user_by_username(username):
        return jsonify({"error": "Username already exists."}), 409

    if email_exists(email):
        return jsonify({"error": "Email is already registered."}), 409

    try:
        user_id = create_user(
            name=name,
            username=username,
            email=email,
            phone=phone,
            password_hash=generate_password_hash(password),
            created_at=now_utc(),
        )
    except Exception as exc:
        return jsonify({"error": f"Could not create the account: {exc}"}), 500

    return jsonify(
        {
            "message": "Account created. Capture your face to finish registration.",
            "user_id": user_id,
            "capture_count": CAPTURE_COUNT,
        }
    ), 201


@app.post("/api/auth/register-face")
def register_face():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    images = data.get("images", [])

    if not user_id or not isinstance(images, list):
        return jsonify({"error": "Registration face data is required."}), 400

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if len(images) < CAPTURE_COUNT:
        return jsonify({"error": f"Please provide {CAPTURE_COUNT} captured images."}), 400

    decoded_images = []
    try:
        for image_data in images[:CAPTURE_COUNT]:
            decoded_images.append(decode_image(image_data))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        valid_count = train_user_model(user_id, decoded_images, now_utc())
    except Exception as exc:
        return jsonify({"error": f"Could not store face data: {exc}"}), 500

    if valid_count < 10:
        return jsonify(
            {
                "error": (
                    f"Only {valid_count} usable face images were detected. "
                    "Please capture the registration images again with one clear face visible."
                )
            }
        ), 400

    session.clear()
    session["user_id"] = user_id

    return jsonify(
        {
            "message": "Registration completed successfully.",
            "user": user_response(user),
            "valid_images": valid_count,
        }
    )


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")
    image_data = data.get("image")
    location = data.get("location") or {}
    latitude, longitude = location_values(location)
    attempted_at = now_utc()

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    if not image_data:
        return jsonify({"error": "Face capture is required for login."}), 400

    user = get_user_by_username(username)

    try:
        image = decode_image(image_data)
        ok, encoded_image = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            raise ValueError("Could not encode captured image.")
        image_blob = encoded_image.tobytes()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not user or not check_password_hash(user["password_hash"], password):
        create_login_attempt(
            user_id=user["id"] if user else None,
            username_attempted=username,
            success=False,
            reason="Invalid password",
            confidence=None,
            latitude=latitude,
            longitude=longitude,
            attempted_at=attempted_at,
            image_blob=image_blob if user else None,
        )
        if user:
            alert_result = send_security_alert(user, image_blob, location)
        else:
            alert_result = {"email_sent": False, "sms_sent": False}
        session.clear()
        return jsonify(
            {
                "error": "Invalid username or password.",
                "alert": alert_result,
            }
        ), 401

    try:
        matched, confidence = verify_face(user["id"], image, FACE_THRESHOLD)
    except Exception as exc:
        return jsonify({"error": f"Could not verify the registered face: {exc}"}), 500

    if not matched:
        create_login_attempt(
            user_id=user["id"],
            username_attempted=username,
            success=False,
            reason="Face verification failed",
            confidence=confidence,
            latitude=latitude,
            longitude=longitude,
            attempted_at=attempted_at,
            image_blob=image_blob,
        )
        alert_result = send_security_alert(user, image_blob, location)
        session.clear()
        return jsonify(
            {
                "error": "Face verification failed. A security alert was triggered.",
                "alert": alert_result,
                "confidence": confidence,
            }
        ), 401

    create_login_attempt(
        user_id=user["id"],
        username_attempted=username,
        success=True,
        reason="Password and face verified",
        confidence=confidence,
        latitude=latitude,
        longitude=longitude,
        attempted_at=attempted_at,
        image_blob=None,
    )

    session.clear()
    session["user_id"] = user["id"]

    return jsonify(
        {
            "message": "Login successful.",
            "confidence": confidence,
            "user": user_response(user),
        }
    )


@app.get("/api/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated."}), 401

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({"error": "User not found."}), 401

    return jsonify({"user": user_response(user)})


@app.get("/api/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated."}), 401

    stats = get_login_stats(user_id)
    attempts = get_recent_attempts(user_id)

    return jsonify(
        {
            "stats": {
                "total_attempts": int(stats["total_attempts"] or 0),
                "successful_attempts": int(stats["successful_attempts"] or 0),
                "unsuccessful_attempts": int(stats["unsuccessful_attempts"] or 0),
                "last_successful_login": (
                    stats["last_successful_login"].isoformat()
                    if stats["last_successful_login"]
                    else None
                ),
            },
            "attempts": [serialize_attempt(row) for row in attempts],
        }
    )


@app.get("/api/dashboard/attempts/<int:attempt_id>/image")
def attempt_image(attempt_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated."}), 401

    image_blob = get_attempt_image(user_id, attempt_id)
    if not image_blob:
        return jsonify({"error": "Image not found."}), 404

    return Response(image_blob, mimetype="image/jpeg")


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out."})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
else:
    init_db()
