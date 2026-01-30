from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
import jwt

# Internal imports
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
    "super_root": {"password": "super123", "role": "superadmin"},
    "admin": {"password": "admin123", "role": "admin"},
    **{f"user_{i:02d}": {"password": "user123", "role": "user"} for i in range(1, 11)}
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

    # ✅ FIXED: pass to_email correctly
    send_otp_email(
        to_email=data.username,
        otp=otp,
        role=user["role"]
    )

    return {"message": "OTP sent successfully"}

# =========================
# VERIFY OTP
# =========================

@router.post("/verify-otp")
def verify(data: OTPVerifyRequest):
    is_valid = verify_otp(data.username, data.otp)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    # ✅ mark OTP as verified
    OTP_STORE[data.username]["verified"] = True

    return {
        "status": "success",
        "message": "OTP verified successfully"
    }

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

    payload = {
        "sub": username,
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(minutes=5)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    # cleanup OTP
    OTP_STORE.pop(username, None)

    return {
        "status": "success",
        "access_token": token,
        "role": user["role"]
    }
