import os
import random
import requests
from datetime import datetime, timedelta
from typing import Tuple, Optional

# =========================
# CONFIG
# =========================

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"

ALLOWED_OTP_EMAIL = "thrinethra098@gmail.com"

# =========================
# OTP STORE (KEY = username)
# =========================

OTP_STORE: dict[str, dict] = {}

# =========================
# OTP GENERATOR
# =========================

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

# =========================
# SAVE OTP
# =========================

def save_otp(username: str, otp: str, ttl_minutes: int = 5):
    OTP_STORE[username] = {
        "otp": otp,
        "expires_at": datetime.utcnow() + timedelta(minutes=ttl_minutes),
        "verified": False,
    }

# =========================
# VERIFY OTP
# =========================

def verify_otp(username: str, otp) -> Tuple[bool, str]:
    record = OTP_STORE.get(username)

    if not record:
        return False, "OTP not found"

    if datetime.utcnow() > record["expires_at"]:
        OTP_STORE.pop(username, None)
        return False, "OTP expired"

    # ✅ FORCE BOTH TO STRING
    if record["otp"] != str(otp):
        return False, "Invalid OTP"

    record["verified"] = True
    return True, "OTP verified successfully"


# =========================
# EMAIL SENDER
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
        "sender": {"email": SENDER_EMAIL, "name": "Akin Analytics"},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }

    response = requests.post(BREVO_URL, json=payload, headers=headers, timeout=30)

    if response.status_code not in (200, 201, 202):
        raise Exception(f"Brevo error: {response.text}")

# =========================
# SEND OTP EMAIL
# =========================

def send_otp_email(to_email: str, otp: str):
    if to_email != ALLOWED_OTP_EMAIL:
        raise Exception("OTP email not authorized")

    subject = "Your OTP Code"
    body = f"""
Hello,

Your OTP code is: {otp}

This OTP is valid for 5 minutes.
"""

    _send_email(to_email, subject, body)
