import pdfplumber
import pytesseract
from PIL import Image
from docx import Document
import io,sys,os
from dotenv import load_dotenv
from openai import OpenAI
from FileProcessing.TextProcessing import process_document
# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from chatgptModule import client
load_dotenv()
UPLOAD_DIR = "uploads"  # Thư mục lưu file

# Đường dẫn Tesseract OCR (chỉnh lại theo nơi đã cài)
tesseract_path = r"G:\NCKH\ChatBot Application\tesseract\tesseract.exe"

# Trỏ `pytesseract` đến đường dẫn đã cài
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# Gửi nội dung lên OpenAI GPT-4o để xử lý
def process_with_gpt(content):
    if not content.strip():
        return "Không tìm thấy nội dung quan trọng trong tài liệu."

    # response = client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=[
    #         {"role": "system", "content": "Bạn là một trợ lý AI chuyên xử lý văn bản. Hãy tóm tắt nội dung tài liệu bằng tiếng Việt và phải đảm bảo giữ lại được tất cả nội dung."},
    #         {"role": "user", "content": f"Hãy tóm tắt tài liệu sau bằng tiếng Việt:\n\n{content}"}
    #     ],
    #     max_tokens=2000
    # )
    # answer = response.choices[0].message.content
    # print("answer:", answer)  # Debugging line
    answer = content
    process_document(answer)  # Gọi hàm xử lý tài liệu
    return answer

# Gửi ảnh lên GPT-4o để phân tích
def read_image(file, filename):
    file.seek(0)  # Reset file pointer
    image_data = file.read()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Bạn là một AI chuyên phân tích hình ảnh. Hãy mô tả nội dung và văn bản trong ảnh bằng tiếng Việt."}
        ],
        max_tokens=500,
        temperature=0.7,
        images=[{"data": image_data, "mime_type": f"image/{filename.split('.')[-1]}"}]
    )
    answer = response.choices[0].message.content
    return answer

# Xử lý ảnh bằng OCR trước, nếu OCR lỗi thì gửi ảnh lên GPT-4o
def process_image(image, filename):
    text = pytesseract.image_to_string(image).strip()

    # Nếu OCR thất bại (text quá ít), gửi ảnh lên GPT-4o
    if len(text) < 10:
        print(f"OCR failed for {filename}, sending to GPT-4o...")
        return read_image(io.BytesIO(), filename)

    return text

# Đọc nội dung từ file PDF (kết hợp text + ảnh OCR)
def read_pdf(file):
    text = ""
    images_text = ""

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            # Lấy text
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

            # Tìm ảnh trong PDF
            for img in page.images:
                image_data = img["stream"].get_data()
                image = Image.open(io.BytesIO(image_data))
                images_text += process_image(image, "pdf_image") + "\n"

    combined_text = text + "\n[Extracted from images]\n" + images_text
    return process_with_gpt(combined_text) if combined_text.strip() else "No text found in PDF."

# Đọc nội dung từ file DOCX (kết hợp text + ảnh OCR)
def read_docx(file):
    doc = Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])

    images_text = ""
    for rel in doc.part.rels:
        if "image" in doc.part.rels[rel].target_ref:
            image_data = doc.part.rels[rel].target_part.blob
            image = Image.open(io.BytesIO(image_data))
            images_text += process_image(image, "docx_image") + "\n"

    combined_text = text + "\n[Extracted from images]\n" + images_text
    return process_with_gpt(combined_text) if combined_text.strip() else "No text found in DOCX."


# Hàm đọc nội dung file từ UploadFile
def read_uploaded_file(file: io.BytesIO, filename: str):
    ext = filename.split(".")[-1].lower()

    if ext == "pdf":
        return read_pdf(file)
    elif ext == "docx":
        return read_docx(file)
    elif ext in ["png", "jpg", "jpeg", "bmp"]:
        return read_image(file)
    else:
        return "Unsupported file type"