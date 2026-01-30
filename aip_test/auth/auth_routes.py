from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
import jwt

# Internal imports
from .auth_models import LoginRequest, OTPVerifyRequest
from .otp_service import (
    generate_otp, save_otp, verify_otp, 
    send_otp_email, OTP_STORE
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
SECRET_KEY = "akin-777"

# 12-USER STORE (In-memory database simulation)
USERS_DB = {
    "super_root": {"password": "super123", "role": "superadmin"},
    "admin":      {"password": "admin123", "role": "admin"},
    **{f"user_{i:02d}": {"password": "user123", "role": "user"} for i in range(1, 11)}
}

@router.post("/login")
def login(data: LoginRequest):
    user = USERS_DB.get(data.username)
    
    # 1. Validate Credentials
    if not user or user["role"] != data.required_role or user["password"] != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid username, password, or role selection."
        )
    
    # 2. Generate and Send OTP
    otp = generate_otp()
    save_otp(data.username, otp)
    send_otp_email(otp=otp, role=user["role"])
    
    return {"message": "Verification code has been sent to your registered email."}

@router.post("/verify-otp")
def verify(data: OTPVerifyRequest):
    success, message = verify_otp(data.username, data.otp)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return {"status": "success", "message": "Identity verified. You may now proceed to get your token."}

@router.get("/success")
def get_success(username: str):
    record = OTP_STORE.get(username)
    
    # Check if OTP was actually verified in the previous step
    if not record or not record.get("verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="OTP verification required before token issuance."
        )

    user = USERS_DB.get(username)
    
    # Create JWT Payload
    payload = {
        "sub": username,
        "r": user["role"],
        "exp": datetime.utcnow() + timedelta(minutes=5)
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    
    # Clean up the OTP store after successful login
    if username in OTP_STORE:
        del OTP_STORE[username]

    return {
        "status": "success",
        "access_token": token,
        "role": user["role"],              
    }

