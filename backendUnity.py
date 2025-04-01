from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from pymongo import MongoClient
from openai import OpenAI
from FileProcessing.fileProcessing import read_uploaded_file
import io
import shutil
import os
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr
import UserManager.userManager as userManager
from UserManager.userManager import get_current_user
import UserManager.userCRUD as userCRUD
from UserManager.userCRUD import router as user_router  # Import router từ userCRUD.py
from chatgptModule import client
from database import db,summaries_collection
from FileProcessing.CategorizeDocument import get_catergory_base_on_content
import chatgptCommand
print("bcrypt imported successfully!")
# Load API keys từ .env
load_dotenv()

# Khởi tạo FastAPI
app = FastAPI()
app.include_router(user_router, prefix="/users")

# Thư mục lưu file
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Tạo thư mục nếu chưa có


@app.get("/")
async def root():
    return {"message": "Backend is running!"}

@app.get("/ask")
async def ask_chatbot(username: str, query: str):
    user = userCRUD.users_collection.find_one({"username": username})
    if not user:
        return {"error": "User not found"}
    
    categories = get_catergory_base_on_content(query)
    print("User ask "+"categories: ", categories)
    # Lấy tất cả _id của các category
    category_ids = [cat["_id"] for cat in categories]
    
    # Tìm tất cả summaries thuộc các category này
    summaries_cursor = summaries_collection.find({"category_id": {"$in": category_ids}})
    
    # Combine tất cả summaries thành 1 chuỗi
    combined_text = " ".join(summary["summary"] for summary in summaries_cursor)
    

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Bạn là một chatbot nội bộ."},
            {"role": "user", "content": f"Dữ liệu: {combined_text}. Câu hỏi: {query}"}
        ]
    )
    answer = response.choices[0].message.content
    return {"answer": answer}


# API upload tài liệu
# @app.post("/upload")
# async def upload_document(username: str, content: str, category: str):
#     user = userCRUD.users_collection.find_one({"username": username})
#     if not user:
#         return {"error": "User not found"}

#     role = user.get("role", "User")
#     if role == "HR" and category != "HR":
#         return {"error": "HR can only upload HR-related documents"}

#     document = {"uploaded_by": username, "content": content, "category": category}
#     documents_collection.insert_one(document)
#     return {"message": "Document uploaded successfully"}

@app.post("/upload")
async def upload_document(
    username: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...)
):
    
    print(f"Received username: {username}")
    print(f"Received category: {category}")
    print(f"Received file: {file.filename if file else 'No file'}")

    # Đọc nội dung file ngay sau khi upload
    file_content = read_uploaded_file(io.BytesIO(await file.read()), file.filename)
    # Trả về nội dung file thay vì lưu vào local
    return {
        "message": "File processed successfully",
        "filename": file.filename,
        "content": file_content
    }

    # # Kiểm tra user (nếu có user collection)
    # user = db["users"].find_one({"username": username})
    # if not user:
    #     raise HTTPException(status_code=404, detail="User not found")

    # role = user.get("role")
    # if role != "HR" or role != "Admin":
    #     raise HTTPException(status_code=403, detail="Only Hr can upload documents")

    # Lưu file vào thư mục
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Lưu thông tin file vào database
    document = {
        "uploaded_by": username,
        "category": category,
        "file_path": file_path
    }
    documents_collection.insert_one(document)

    return {"message": "File uploaded successfully", "file_path": file_path}


class ChatRequest(BaseModel):
    username: str
    query: str
@app.post("/process_chat")
async def process_chat(request: ChatRequest,current_user: dict = Depends(userManager.get_current_user)):
    """
    Xử lý câu hỏi của user và quyết định action:
    - Nếu là thêm user => gọi `process_command_to_add_user`
    - Nếu là câu hỏi thường => gọi `ask_chatbot`
    """
    action = chatgptCommand.ask_gpt4o(request.query).strip('"').lower()
    print("Action:", repr(action))  # In ra dạng chuẩn hóa để kiểm tra
    print("Action type:", type(action))
    if action == "add_user":
        try:
            result = await userCRUD.process_command_to_add_user(request.query,current_user=current_user)
            # 🔥 Format lại result để gửi cho GPT-4o
            result_text = f"Kết quả xử lý lệnh: {result}"
            return await process_text_to_gpt(f"Hãy viết lại kết quả này theo cách tự nhiên hơn: {result_text}")
        except Exception as e:
            return await process_text_to_gpt(f"Hãy viết lại kết quả này theo cách tự nhiên hơn: {str(e)}")
            # return {"answer": human_like_response} 
            # raise HTTPException(status_code=500, detail=f"Error in process_command_to_add_user: {str(e)}")
    elif action == "chat":
        return await ask_chatbot(request.username, request.query)
    else:
        raise HTTPException(status_code=400, detail="Invalid command format")

async def process_text_to_gpt(responseText:str):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Bạn là một trợ lý AI thực hiện các lệnh cho người dùng. "
                    "Trả lời ngắn gọn, tự nhiên, theo phong cách trợ lý thực tế. "
                    "Không chỉ thông báo về kết quả, mà hãy phản hồi như thể bạn đang trực tiếp thực hiện hành động đó."
                )
            },
            {"role": "user", "content": responseText}
        ]
    )
    answer = response.choices[0].message.content
    return {"answer": answer}