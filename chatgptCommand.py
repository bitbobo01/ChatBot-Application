from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from openai import OpenAI
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from chatgptModule import client as clientAI

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
# Kết nối MongoDB
client = MongoClient(MONGO_URI)
db = client["chatbot_db"]


def ask_gpt4o(command: str):
    """
    Gửi câu lệnh đến GPT-4o để phân tích xem có phải thêm user không.
    """
    prompt = f"""
    You are an AI that classifies user commands into two categories: 
    1. "add_user" - when the command is about adding a new user.
    2. "chat" - when the command is just a normal conversation.

    Given the following command, return only "add_user" or "chat".

    Example Input:
    "Thêm vào cho tôi user nguyenhoang@gmail.com password 123456 role user"
    Expected Output: "add_user"

    Example Input:
    "Làm thế nào để tối ưu hiệu suất của mô hình AI?"
    Expected Output: "chat"

    Now process this command: "{command}"
    """

    response =  clientAI.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        temperature=0
    )

    gpt_output = response.choices[0].message.content.strip().lower()
    print(gpt_output)
    return gpt_output


