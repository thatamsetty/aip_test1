from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
import jwt

from .auth_models import LoginRequest, OTPVerifyRequest
from .otp_service import generate_otp, save_otp, verify_otp, send_otp_email, OTP_STORE

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = "akin-777"
ALGORITHM = "HS256"

# ✅ FIXED OTP RECEIVER EMAIL
OTP_RECEIVER_EMAIL = "likithaadabala@gmail.com"

# =========================
# USERS DATABASE
# =========================

USERS_DB = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "email": "admin@test.com",
    },
    "superadmin": {
        "password": "super123",
        "role": "superadmin",
        "email": "superadmin@test.com",
    },
    "user": {
        "password": "user123",
        "role": "user",
        "email": "user@test.com",
    },
}

# =========================
# LOGIN → SEND OTP
# =========================

@router.post("/login")
def login(data: LoginRequest):
    username = data.username.lower()
    user = USERS_DB.get(username)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username")

    if user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Invalid password")

    if user["role"] != data.required_role:
        raise HTTPException(status_code=403, detail="Invalid role")

    otp = generate_otp()

    # ✅ STORE OTP BY USERNAME
    save_otp(username, otp)

    # ✅ SEND OTP TO FIXED EMAIL
    send_otp_email(
        to_email=OTP_RECEIVER_EMAIL,
        otp=otp
    )

    return {
        "message": f"OTP sent to {OTP_RECEIVER_EMAIL}"
    }

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
# ISSUE JWT
# =========================

@router.get("/success")
def success(username: str):
    username = username.lower()
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
        "exp": datetime.utcnow() + timedelta(minutes=10),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    # ✅ CLEAR OTP AFTER SUCCESS
    OTP_STORE.pop(username, None)

    return {
        "status": "success",
        "access_token": token,
        "role": user["role"],
    }
