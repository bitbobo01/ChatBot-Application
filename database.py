from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
import jwt
import datetime
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta


# Load API keys từ .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
SECRET_KEY = "supersecretkey"  # Thay bằng key an toàn hơn
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 tiếng

# Kết nối MongoDB
clientDb = MongoClient(MONGO_URI)
db = clientDb["company_data"]
users_collection = db["users"]
summaries_collection = db["summaries"]