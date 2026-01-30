from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
import jwt

from .auth_models import LoginRequest, OTPVerifyRequest
from .otp_service import (
    generate_otp,
    save_otp,
    verify_otp,
    send_otp_email,
    OTP_STORE
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = "akin-777"
ALGORITHM = "HS256"

ALLOWED_OTP_EMAIL = "thrinethra098@gmail.com"

# =========================
# USER STORE
# =========================

USERS_DB = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "email": "thrinethra098@gmail.com"
    }
}

# =========================
# LOGIN → SEND OTP
# =========================

@router.post("/login")
def login(data: LoginRequest):
    user = USERS_DB.get(data.username)

    if (
        not user
        or user["password"] != data.password
        or user["role"] != data.required_role
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if user["email"] != ALLOWED_OTP_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OTP not allowed for this email"
        )

    otp = generate_otp()

    # ✅ STORE OTP USING USERNAME
    save_otp(data.username, otp)

    # ✅ SEND OTP ONLY TO FIXED EMAIL
    send_otp_email(
        to_email=ALLOWED_OTP_EMAIL,
        otp=otp
    )

    return {"message": "OTP sent successfully"}

# =========================
# VERIFY OTP
# =========================

@router.post("/verify-otp")
def verify(data: OTPVerifyRequest):
    success, message = verify_otp(data.username, data.otp)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"status": "success", "message": message}

# =========================
# ISSUE TOKEN
# =========================

@router.get("/success")
def get_success(username: str):
    record = OTP_STORE.get(username)

    if not record or not record["verified"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP verification required"
        )

    user = USERS_DB.get(username)

    payload = {
        "sub": username,
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(minutes=5)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    # cleanup
    OTP_STORE.pop(username, None)

    return {
        "status": "success",
        "access_token": token,
        "role": user["role"]
    }
