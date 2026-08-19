import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

from dotenv import load_dotenv

try:
    from twilio.rest import Client
except ImportError:
    Client = None

load_dotenv()


def build_alert_text(user, location, timestamp):
    location_text = "Location unavailable"
    if location and location.get("latitude") is not None and location.get("longitude") is not None:
        latitude = location["latitude"]
        longitude = location["longitude"]
        location_text = (
            f"Latitude: {latitude}, Longitude: {longitude}\n"
            f"Map: https://www.google.com/maps?q={latitude},{longitude}"
        )

    return (
        "Face Lock Alert\n\n"
        f"Hello {user['name']},\n\n"
        f"An unsuccessful facial verification attempt was detected for your account "
        f"({user['username']}).\n\n"
        f"Time: {timestamp}\n"
        f"{location_text}\n\n"
        "The captured image is attached to this alert."
    )


def send_email_alert(user, image_blob, location, timestamp):
    sender = os.getenv("ALERT_EMAIL")
    password = os.getenv("ALERT_EMAIL_PASSWORD")
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))

    if not sender or not password:
        return False, "Email alert is not configured."

    message = EmailMessage()
    message["From"] = sender
    message["To"] = user["email"]
    message["Subject"] = "Face Lock Alert - Suspicious Login Attempt"
    message.set_content(build_alert_text(user, location, timestamp))
    message.add_attachment(
        image_blob,
        maintype="image",
        subtype="jpeg",
        filename="suspicious_login.jpg",
    )

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(message)
        return True, None
    except Exception as exc:
        return False, str(exc)


def send_sms_alert(user, location, timestamp):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not account_sid or not auth_token or not twilio_number:
        return False, "SMS alert is not configured."

    if Client is None:
        return False, "Twilio package is not installed."

    location_text = "Location unavailable"
    if location and location.get("latitude") is not None and location.get("longitude") is not None:
        location_text = f"https://www.google.com/maps?q={location['latitude']},{location['longitude']}"

    body = (
        f"Face Lock Alert: suspicious login attempt for {user['username']} "
        f"at {timestamp}. Location: {location_text}. Check your email for the captured image."
    )

    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=body,
            from_=twilio_number,
            to=user["phone"],
        )
        return True, None
    except Exception as exc:
        return False, str(exc)


def send_security_alert(user, image_blob, location):
    timestamp = datetime.now().astimezone().strftime("%d %B %Y at %I:%M:%S %p %Z")
    email_sent, email_error = send_email_alert(user, image_blob, location, timestamp)
    sms_sent, sms_error = send_sms_alert(user, location, timestamp)

    return {
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "email_error": email_error,
        "sms_error": sms_error,
        "timestamp": timestamp,
    }
