import os
import random
import requests
from datetime import datetime, timedelta
from typing import Tuple

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"

# =========================
# OTP STORE (in-memory)
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

def verify_otp(username: str, otp: str) -> Tuple[bool, str]:
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
# GENERIC EMAIL SENDER (Brevo)
# =========================

def _send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Central reusable email sender for Brevo.
    """

    if not BREVO_API_KEY or not SENDER_EMAIL:
        print("⚠️ Brevo email not configured")
        return False

    payload = {
        "sender": {"email": SENDER_EMAIL, "name": "Akin Analytics"},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    try:
        response = requests.post(
            BREVO_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return True

    except requests.RequestException as e:
        print(f"❌ Email send failed: {e}")
        return False


# =========================
# SEND OTP EMAIL
# =========================

def send_otp_email(to_email: str, otp: str) -> bool:
    subject = "Your OTP Code"

    body = f"""
Hello,

Your OTP code is: {otp}

This OTP is valid for 5 minutes.

Akin Analytics
"""

    return _send_email(to_email, subject, body)


# =========================
# SEND DOWNLOAD LINK EMAIL
# =========================

def send_download_link_email(to_email: str, download_link: str) -> bool:
    subject = "Your Download Link Is Ready"

    body = f"""
Hello,

Your file is ready for download.

Click the link below:
{download_link}

Thank you for using Akin Analytics.
"""

    return _send_email(to_email, subject, body)


# =========================
# SEND REJECTION EMAIL
# =========================

def send_rejection_email(to_email: str, reason: str = "Your request was rejected") -> bool:
    subject = "Request Rejected"

    body = f"""
Hello,

We regret to inform you that your request was rejected.

Reason:
{reason}

If you believe this is an error, please contact support.

Akin Analytics
"""

    return _send_email(to_email, subject, body)
