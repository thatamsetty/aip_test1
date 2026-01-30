import os
import random
import requests
from typing import Optional, Tuple
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"

if not BREVO_API_KEY or not SENDER_EMAIL:
    print("⚠️ Email skipped: Brevo not configured")

# =========================
# OTP STORE
# =========================

OTP_STORE = {}

# =========================
# OTP GENERATOR
# =========================

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

# =========================
# SAVE OTP
# =========================

def save_otp(email: str, otp: str, ttl_minutes: int = 5):
    OTP_STORE[email] = {
        "otp": otp,
        "expires_at": datetime.utcnow() + timedelta(minutes=ttl_minutes),
        "verified": False
    }

# =========================
# VERIFY OTP (🔥 FIXED)
# =========================

def verify_otp(email: str, otp: str) -> Tuple[bool, str]:
    record = OTP_STORE.get(email)

    if not record:
        return False, "OTP not found"

    if datetime.utcnow() > record["expires_at"]:
        return False, "OTP expired"

    if record["otp"] != otp:
        return False, "Invalid OTP"

    # ✅ MARK VERIFIED
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
        "sender": {
            "email": SENDER_EMAIL,
            "name": "Akin Analytics"
        },
        "to": [{"email": "thrinethra098@gmail.com"}],
        "subject": subject,
        "textContent": body,
    }

    requests.post(BREVO_URL, json=payload, headers=headers, timeout=30)

# =========================
# SEND OTP
# =========================

def send_otp_email(to_email: str, otp: Optional[str] = None) -> str:
    if not otp:
        otp = generate_otp()

    save_otp(to_email, otp)

    subject = "Your OTP Code"
    body = f"""
Hello,

Your OTP code is: {otp}

Valid for 5 minutes.
"""

    _send_email(to_email, subject, body)
    return otp
