from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re,sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from chatgptModule import client as clientAI
app = FastAPI()

class CommandRequest(BaseModel):
    command: str

def extract_user_data_command(command: str):
    """
    Gửi câu lệnh đến GPT-4o để phân tích và trả về JSON chứa email, password, role.
    """
    prompt = f"""
    You are an AI that extracts structured data from natural language commands. Given the following command, 
    extract the 'username', 'email', 'password', and 'role' in JSON format.
    
    Rules:
    1. **All four fields must be explicitly mentioned in the input.**
    2. **If any field is missing, do NOT infer, guess, or autofill. Instead, return an error message listing the missing fields.**
    3. **Do NOT generate default values like 'unknown'.** Missing fields must be explicitly listed as an error.
    4. **Always return a valid JSON object** without Markdown formatting.
    5. **If all required fields are extracted, return the user data in JSON format.**
    6. **If any field is missing, return the following error format:**
        ```json
        {{
            "error": "missing_fields",
            "missing": ["field1", "field2"]
        }}
    
    Example Input:
    "Thêm vào cho tôi nguyenhoangmai@gmail.com username hoangmai123 password 123456 role user"

    Expected Output:
    {{
        "username": "hoangmai123",
        "email": "nguyenhoangmai@gmail.com",
        "password": "123456",
        "role": "user"
    }}
    Example Input missings fields:
    "Thêm vào cho tôi user nguyenhoangmai@gmail.com password 123456 role user"
    
    Expected Error Output:
    {{
        "error": "missing_fields",
        "missing": ["username"]
    }}
    Now process this command: "{command}"
    """

    response = clientAI.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        temperature=0
    )

    gpt_output = response.choices[0].message.content.strip().lower()
    print("GPT-4o Response:", repr(gpt_output))  # ✅ In ra response để debug
    # 🔥 Remove Markdown formatting (```json ... ```)
    gpt_output = re.sub(r"```json\s*([\s\S]*?)\s*```", r"\1", gpt_output).strip()
    try:
        user_data = json.loads(gpt_output)  # ✅ Parse JSON an toàn
        return user_data
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        return None



