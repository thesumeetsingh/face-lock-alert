# Face Lock Alert System

A full-stack biometric authentication system built with **React, Flask, MySQL and OpenCV LBPH**. It combines password authentication with face verification and records account security activity.

## Features

- User registration with name, username, email, phone and password.
- Automatic multi-image face registration with configurable capture count.
- Face samples and trained LBPH model stored in MySQL.
- Single-step login: username/password submission automatically captures a live face image.
- Password and face verification before dashboard access.
- Browser geolocation captured during login when permission is granted.
- Failed face/password attempts stored with time, location, reason and captured image.
- Email alert with suspicious-login image attachment.
- Optional Twilio SMS alert.
- Dashboard with account information, login statistics and recent authentication activity.
- Minimal black/grey/white React interface.

## Technology Stack

- **Frontend:** React, Vite, JavaScript, CSS
- **Backend:** Python, Flask, Flask-CORS
- **Database:** MySQL
- **Biometrics:** OpenCV LBPH + Haar Cascade face detection
- **Alerts:** Gmail SMTP and Twilio

## Project Structure

```text
face-lock-alert-system/
├── backend/
│   ├── app.py
│   ├── alerts.py
│   ├── db.py
│   ├── face_service.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       └── styles.css
└── .gitignore
```

## Database Setup

Install MySQL Server and MySQL Workbench, then open a SQL tab in Workbench and run:

```sql
CREATE DATABASE IF NOT EXISTS face_lock_alert;
```

The Flask backend creates the required tables automatically when it starts.

Configure the MySQL connection in `backend/.env`:

```text
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-mysql-password
DB_NAME=face_lock_alert
```

## Backend Setup

Use a normal Python installation; a Python virtual environment is not required.

```powershell
cd backend
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Backend API:

```text
http://127.0.0.1:5000
```

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

Allow camera access when requested. Location permission is optional and is used for security-attempt records and alerts.

## Environment Configuration

Create the actual file **`backend/.env`** by copying `.env.example`. Put all real credentials in `.env`.

For Gmail alerts:

```text
ALERT_EMAIL=your-sender@gmail.com
ALERT_EMAIL_PASSWORD=your-gmail-app-password
```

`ALERT_EMAIL_PASSWORD` must be a **Gmail App Password** generated for the sender account. Do not use the normal Gmail account password.

For Twilio SMS:

```text
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
```

The `.env.example` file contains placeholders only. Never commit the real `.env` file.

## API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Backend health check |
| GET | `/api/config` | Face capture configuration |
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/register-face` | Store face samples and train model |
| POST | `/api/auth/login` | Password + automatic face verification |
| GET | `/api/me` | Current authenticated user |
| GET | `/api/dashboard` | Login statistics and recent attempts |
| GET | `/api/dashboard/attempts/<id>/image` | Retrieve a stored failed-login image |
| POST | `/api/auth/logout` | End authenticated session |

## Authentication Workflow

```text
Registration
    ↓
Account details → Automatic face capture → Face detection → LBPH model → MySQL

Login
    ↓
Username + password → Automatic camera capture → Optional location →
Password verification → LBPH face verification
    ↓
 ┌───────────────┬───────────────────┐
 │ Match         │ Verification fail │
 ↓               ↓
Dashboard        Store attempt + image
                 ↓
                 Email / SMS alert
```

## Configuration

`backend/.env` controls the face capture and matching settings:

```text
FACE_CAPTURE_COUNT=15
FACE_CONFIDENCE_THRESHOLD=70
```

At least 10 usable face samples are required for model training. LBPH confidence is lower for a closer match.

## Notes

- Camera and geolocation permissions are controlled by the browser.
- `localhost` is suitable for camera/geolocation during local development.
- MySQL stores registration data, face samples, the trained model and login-attempt records.
- Failed-login images are stored in MySQL as binary data.
- This is a project implementation and does not include production-grade liveness detection or anti-spoofing.
