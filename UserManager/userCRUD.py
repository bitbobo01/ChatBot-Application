from fastapi import FastAPI, HTTPException, Depends,APIRouter
from pydantic import BaseModel
from pymongo import MongoClient
from openai import OpenAI
import os
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr
import UserManager.userManager as userManager
import bcrypt
import UserManager.command_add as gptCommand
from schema import UserCreate
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
SECRET_KEY = "supersecretkey"  # Thay bằng key an toàn hơn
ALGORITHM = "HS256"
# Kết nối MongoDB
clientDb = MongoClient(MONGO_URI)
db = clientDb["company_data"]
users_collection = db["users"]

# Khởi tạo FastAPI
router = APIRouter()

    
@router.post("/add_user")
async def add_user(user: UserCreate,current_user: dict):
    user.role = user.role.upper()  # Chuyển hết thành chữ hoa
    if user.role not in ["ADMIN", "HR", "USER"]:
        return {"error": "Invalid role"}

    existing_user = users_collection.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
    if existing_user:
        return {"error": "Username or Email already exists"}

    hashed_password = userManager.hash_password(user.password)

    users_collection.insert_one({
        "username": user.username,
        "email": user.email,
        "password": hashed_password,
        "role": user.role
    })
    return {"message": f"User {user.username} added as {user.role}"}

@router.post("/process_command_to_add_user")
async def process_command_to_add_user(command: str,current_user: dict = Depends(userManager.get_current_user)):
    print("Current user:", current_user)
    print("Current user role:", current_user["role"].lower())
    if current_user["role"].lower() != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can add new users")
    
    user_data = gptCommand.extract_user_data_command(command)
    print("Extracted user data:", user_data)
    
    # 🔥 Nếu GPT-4o báo lỗi thiếu field
    if isinstance(user_data, dict) and user_data.get("error") == "missing_fields":
        missing_fields = user_data.get("missing", [])
        raise HTTPException(
            status_code=400,
            detail={"error": "GPT-4o failed to extract all required fields", "missing_fields": missing_fields}
        )
        
    if user_data:
        required_fields = ["username", "email", "password", "role"]
        missing_fields = [field for field in required_fields if field not in user_data or not user_data[field]]
        if missing_fields:
            raise HTTPException(
            status_code=400,
            detail={"missing_fields": missing_fields}  # ✅ Chỉ trả về những field bị thiếu
            )
        print(missing_fields)
        user = UserCreate(**user_data)
        try:
            return await add_user(user,current_user)  
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error while adding user: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="GPT-4o failed to extract user data.")

@router.post("/login")
async def login(user: userManager.LoginRequest):
    user_data = users_collection.find_one({"email": user.username})  # 🔥 Đổi từ username -> email

    if not user_data:
        raise HTTPException(status_code=400, detail="Email not found")

    if not userManager.verify_password(user.password, user_data["password"]):
        raise HTTPException(status_code=400, detail="Invalid password")

    # Tạo Token
    access_token = userManager.create_access_token(user_data["username"], user_data["role"])

    return {"username":user_data["username"],"access_token": access_token, "token_type": "bearer"}

#API Set role
@router.post("/set_role")
async def set_user_role(username: str, role: str,current_user: dict = Depends(userManager.get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Only Admin can change roles")

    if role not in ["Admin", "HR", "User"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    db.users.update_one({"username": username}, {"$set": {"role": role}})
    return {"message": f"Role of {username} updated to {role}"}

@router.get("/me")
async def read_users_me(current_user: dict = Depends(userManager.get_current_user)):
    if not isinstance(current_user, dict):
        raise HTTPException(status_code=500, detail="Unexpected format from get_current_user")

    return {"username": current_user["username"], "role": current_user["role"]}  