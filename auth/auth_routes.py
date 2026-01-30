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

# =========================
# USER STORE (IN-MEMORY)
# =========================

USERS_DB = {
    "super_root": {
        "password": "super123",
        "role": "superadmin",
        "email": "super@example.com"
    },
    "admin": {
        "password": "admin123",
        "role": "admin",
        "email": "admin@example.com"
    },
    **{
        f"user_{i:02d}": {
            "password": "user123",
            "role": "user",
            "email": f"user{i:02d}@example.com"
        }
        for i in range(1, 11)
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
            detail="Invalid username, password, or role"
        )

    otp = generate_otp()
    save_otp(data.username, otp)

    send_otp_email(
        to_email=user["email"],
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

    if not record or not record.get("verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP verification required"
        )

    user = USERS_DB.get(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    payload = {
        "sub": username,
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(minutes=5)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    OTP_STORE.pop(username, None)

    return {
        "status": "success",
        "access_token": token,
        "role": user["role"]
    }
