import os
import random
import requests
from typing import Optional
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"

if not BREVO_API_KEY or not SENDER_EMAIL:
    print("⚠️ WARNING: Brevo email variables not set")

# =========================
# IN-MEMORY OTP STORE
# =========================

OTP_STORE = {}

# =========================
# OTP GENERATOR
# =========================

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

# =========================
# OTP STORAGE
# =========================

def save_otp(email: str, otp: str, ttl_minutes: int = 5):
    OTP_STORE[email] = {
        "otp": otp,
        "expires_at": datetime.utcnow() + timedelta(minutes=ttl_minutes)
    }

def verify_otp(email: str, otp: str) -> bool:
    data = OTP_STORE.get(email)
    if not data:
        return False

    if datetime.utcnow() > data["expires_at"]:
        return False

    return data["otp"] == otp

# =========================
# CORE EMAIL SENDER
# =========================

def _send_email(to_email: str, subject: str, body: str):
    if not BREVO_API_KEY or not SENDER_EMAIL:
        print("⚠️ Email skipped: Brevo not configured")
        return

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    payload = {
        "sender": {
            "email": SENDER_EMAIL,
            "name": "Akin Analytics"
        },
        "to": [
            {"email": "thrinethra098@gmail.com"}
        ],
        "subject": subject,
        "textContent": body,
    }

    response = requests.post(
        BREVO_URL,
        json=payload,
        headers=headers,
        timeout=30
    )

    if response.status_code not in (200, 201, 202):
        raise Exception(
            f"Brevo API Error: {response.status_code} {response.text}"
        )

# =========================
# SEND OTP EMAIL
# =========================

def send_otp_email(to_email: str, otp: Optional[str] = None) -> str:
    if not otp:
        otp = generate_otp()

    save_otp(to_email, otp)

    subject = "Your OTP Code"
    body = f"""
Hello,

Your OTP code is: {otp}

This OTP is valid for 5 minutes.

If you did not request this, please ignore this email.
"""

    _send_email(to_email, subject, body)
    return otp

# =========================
# SEND DOWNLOAD LINK EMAIL
# =========================

def send_download_link_email(to_email: str, download_link: str) -> bool:
    subject = "Your Download Link Is Ready"
    body = f"""
Hello,

Your file is ready for download.

Click here:
{download_link}
"""
    _send_email(to_email, subject, body)
    return True

# =========================
# SEND REJECTION EMAIL
# =========================

def send_rejection_email(to_email: str, reason: str) -> bool:
    subject = "Request Rejected"
    body = f"""
Hello,

We regret to inform you that your request was rejected.

Reason:
{reason}
"""
    _send_email(to_email, subject, body)
    return True
