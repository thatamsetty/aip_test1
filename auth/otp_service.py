import os
import random
import requests
from datetime import datetime, timedelta
from typing import Tuple

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"

# =========================
# OTP STORE
# =========================

OTP_STORE = {}

# =========================
# GENERATE OTP
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

    if record["otp"] != str(otp):
        return False, "Invalid OTP"

    record["verified"] = True
    return True, "OTP verified successfully"

# =========================
# SEND OTP EMAIL
# =========================

def send_otp_email(to_email: str, otp: str):
    if not BREVO_API_KEY or not SENDER_EMAIL:
        print("⚠️ Brevo email not configured")
        return

    payload = {
        "sender": {"email": SENDER_EMAIL, "name": "Akin Analytics"},
        "to": [{"email": to_email}],
        "subject": "Your OTP Code",
        "textContent": f"""
Hello,

Your OTP code is: {otp}

This OTP is valid for 5 minutes.
""",
    }

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    requests.post(BREVO_URL, json=payload, headers=headers, timeout=30)
