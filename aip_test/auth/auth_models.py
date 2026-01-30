from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str
    required_role: str

class OTPVerifyRequest(BaseModel):
    username: str
    otp: int



