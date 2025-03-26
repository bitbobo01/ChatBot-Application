from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from passlib.context import CryptContext  # Hash mật khẩu
import jwt
import datetime
import os
from datetime import datetime, timedelta

# Load API keys từ .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SECRET_KEY = "supersecretkey"  # Thay bằng key an toàn hơn
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 tiếng

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Cấu hình Hash Password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Sinh Token JWT
def create_access_token(username: str, role: str):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    print("Get current user")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")

        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return {"username": username, "role": role}  
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
# Khởi tạo FastAPI
app = FastAPI()

# Define User Model
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str

# Define Login Model
class LoginRequest(BaseModel):
    username: str
    password: str
