from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
import jwt

from .auth_models import LoginRequest, OTPVerifyRequest
from .otp_service import (
    generate_otp,
    save_otp,
    verify_otp,
    send_otp_email,
    OTP_STORE,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = "akin-777"
ALGORITHM = "HS256"

# =========================
# USER STORE
# =========================
USERS_DB = {
    "admin": {
        "password": "admin123",
        "role": "admin",
    },
    "user": {
        "password": "user123",
        "role": "user",
    },
    "super_root": {
        "password": "super123",
        "role": "superadmin",
    },
}

# =========================
# LOGIN → SEND OTP
# =========================
@router.post("/login")
def login(data: LoginRequest):
    username = data.username.lower()
    user = USERS_DB.get(username)

    if not user or user["password"] != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # OPTIONAL ROLE CHECK
    if hasattr(data, "required_role") and user["role"] != data.required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid role",
        )

    otp = generate_otp()
    save_otp(username, otp)

    # ✅ ALWAYS SEND OTP TO FIXED EMAIL
    send_otp_email(otp)

    return {"message": "OTP sent successfully"}


# =========================
# VERIFY OTP
# =========================
@router.post("/verify-otp")
def verify(data: OTPVerifyRequest):
    username = data.username.lower()
    success, message = verify_otp(username, data.otp)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"status": "success", "message": message}


# =========================
# ISSUE TOKEN
# =========================
@router.get("/success")
def get_success(username: str):
    username = username.lower()
    record = OTP_STORE.get(username)

    if not record or not record["verified"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP verification required",
        )

    user = USERS_DB.get(username)

    payload = {
        "sub": username,
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(minutes=5),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    # cleanup
    OTP_STORE.pop(username, None)

    return {
        "status": "success",
        "access_token": token,
        "role": user["role"],
    }
