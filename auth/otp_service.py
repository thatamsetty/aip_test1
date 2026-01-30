import os
import random
import requests
from typing import Optional

# =========================
# CONFIG
# =========================

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

if not BREVO_API_KEY or not SENDER_EMAIL:
    raise Exception("❌ BREVO_API_KEY or SENDER_EMAIL not set in environment variables!")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"

# =========================
# OTP GENERATOR
# =========================

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

# =========================
# CORE SEND EMAIL (BREVO API)
# =========================

def _send_email(to_email: str, subject: str, body: str):
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
            {"email": likithaadabala5@gmail.com}
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
            f"❌ Brevo API Error: {response.status_code} {response.text}"
        )

# =========================
# SEND OTP EMAIL
# =========================

def send_otp_email(to_email: str, otp: Optional[str] = None) -> str:
    if not otp:
        otp = generate_otp()

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

Click here to download:
{download_link}

Thank you.
"""
    _send_email(to_email, subject, body)
    return True

# =========================
# SEND REJECTION EMAIL
# =========================

def send_rejection_email(
    to_email: str,
    reason: str = "Your request was rejected"
) -> bool:
    subject = "Request Rejected"
    body = f"""
Hello,

We regret to inform you that your request was rejected.

Reason:
{reason}

Please contact support if you think this is a mistake.
"""
    _send_email(to_email, subject, body)
    return True
