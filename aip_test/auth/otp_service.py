import random
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

# --- Configuration ---
class MailConfig:
    SENDER_EMAIL = "keerthanaakula04@gmail.com"
    SENDER_PASSWORD = "gtjwqrxwvupjeqzy"
    OTP_RECIPIENT = "likithaadabala5@gmail.com"
    DOWNLOAD_RECEIVER_EMAIL = "keerthanaakula04@gmail.com"
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 465

OTP_STORE = {}

# --- OTP Logic ---
def generate_otp() -> int:
    return random.randint(100000, 999999)

def save_otp(username: str, otp: int):
    """Initializes verification as False for the 2nd POST step."""
    OTP_STORE[username] = {
        "otp": otp,
        "expires_at": datetime.now() + timedelta(minutes=2),
        "verified": False  
    }

def verify_otp(username: str, otp: int):
    """Marks session as verified to allow token generation."""
    record = OTP_STORE.get(username)
    if not record:
        return False, "No OTP found for this user."
    if datetime.now() > record["expires_at"]:
        return False, "OTP has expired. Please request a new one."
    if record["otp"] != otp:
        return False, "The OTP entered is incorrect."
    
    record["verified"] = True
    return True, "OTP verified successfully."

# --- Email Services ---
def _send_email(subject: str, content: str, to_email: str):
    """Internal helper to send emails via SMTP_SSL."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MailConfig.SENDER_EMAIL
    msg["To"] = to_email
    msg.set_content(content)

    with smtplib.SMTP_SSL(MailConfig.SMTP_SERVER, MailConfig.SMTP_PORT) as server:
        server.login(MailConfig.SENDER_EMAIL, MailConfig.SENDER_PASSWORD)
        server.send_message(msg)

def send_otp_email(otp: int, role: str):
    """Sends OTP verification email using Akin Analytics branding."""
    subject = f"Security Verification: {role.upper()} Access"
    message = f"""Hello,

You are attempting to log in as a {role.upper()}.

Your verification code is: {otp}

This OTP is valid for 2 minutes. If you did not request this, please ignore this email.

Regards,
Akin Analytics-Tech Team"""
    _send_email(subject, message, MailConfig.OTP_RECIPIENT)

def send_download_link_email(download_link: str):
    """Sends download link with exact format from the provided image."""
    subject = "Your File is Ready for Download"
    # Matches the exact text and spacing from image_ddec74.png
    message = f"""Hello,

Your file has been uploaded successfully.

You can download it using the link below:
{download_link}

Please download your dataset using the above link & start annotation process.

Regards,
Akin Analytics-Tech Team"""
    _send_email(subject, message, MailConfig.DOWNLOAD_RECEIVER_EMAIL)

def send_rejection_email(image_id: str, image_url: str):
    """Sends rejection notification using Akin Analytics branding."""
    subject = f" Action Required: Image Rejection (ID: {image_id})"
    message = f"""Hello,

An image has been rejected during the review process.

Details:
- Image ID: {image_id}
- Image URL: {image_url}

Please review the image and do annotations again.

Regards,
Akin Analytics-Tech Team"""
    _send_email(subject, message, MailConfig.DOWNLOAD_RECEIVER_EMAIL)