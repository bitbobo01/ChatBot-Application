import os
import sys
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
# Thêm đường dẫn thư mục modules/ vào sys.path
sys.path.append(os.path.join(os.getcwd(), "File Processing"))
from fileProcessing import read_file
import nltk

# Xác định thư mục đích
nltk.data.path.append("G:\\NCKH\\ChatBot Application\\.venv\\nltk_data")

# Tải xuống gói punkt_tab vào thư mục đã chọn
nltk.download("punkt_tab", download_dir="G:\\NCKH\\ChatBot Application\\.venv\\nltk_data")

# Định nghĩa thư mục chứa file test
UPLOAD_DIR = "uploads"  # Thư mục chứa file test (đảm bảo có sẵn file trong đó)

# Danh sách file test (đặt file này vào thư mục `uploads/`)
test_files = [
    # "test.pdf",    # PDF chứa văn bản + hình ảnh
    "Ship Creator Document.docx"   # DOCX chứa văn bản + hình ảnh
    # "test.png",    # Ảnh chụp màn hình có text
    # "test.jpg"     # Ảnh chứa chữ viết tay
]

# Chạy test từng file
for file in test_files:
    print(f"\n🔍 Testing file: {file}")

    file_path = os.path.join(UPLOAD_DIR, file)
    if not os.path.exists(file_path):
        print(f"⚠️ File {file} not found in {UPLOAD_DIR}. Please add the file before testing.")
        continue

    # Đọc nội dung file
    result = read_file(file)
    
    # In ra kết quả
    print(f"📄 Filename: {result['filename']}")
    print(f"📜 Content:\n{result['content']}\n")
    print("=" * 80)
    


testTxt=f"Quyền và trách nhiệm của nhân viên trong công tyTrong nội quy công ty cần có quyền hạn, trách nhiệm của các nhân viên với các thông tin như:Xác định rõ ràng vai trò, quyền hạn, trách nhiệm của từng nhân viên và bộ phận trong doanh nghiệp.Nêu rõ quyền lợi, trách nhiệm của ban giám đốc, các cấp quản lý.Nói đề quyền hạn, trách nhiệm của một nhân viên đối với việc tuân thủ quy định trong doanh nghiệp.Ví dụ, trong nội quy công ty có thể đề cập đến các quyền lợi của người lao động như: Thời gian nghỉ ngơi, quyền bảo hộ lao động, quyền được tham gia đóng góp ý kiến, quyền được khiếu nại, tranh chấp lao động… Trong khi đó, một số trách nhiệm thuộc về người lao động gồm: Hoàn thành công việc, đi làm đủ và đúng giờ, giữ bí mật kinh doanh, bảo vệ tài sản công ty Thời gian làm việc của nhân viênThời gian làm việc, nghỉ ngơi của nhân viên cũng cần được quy định rõ ràng trong nội quy công ty.Xác định giờ làm việc chuẩn, thời gian bắt đầu, thời gian kết thúc, mỗi ca làm việc bao nhiêu tiếng.Quy định về thời gian nghỉ trưa, nghỉ giữa giờ, thời gian đi muộn, về sớm.Quy định về nghỉ phép, nghỉ ngày lễ, nghỉ ốm hưởng lương, nghỉ không lương.Có quy định rõ ràng về nguyên tắc đăng ký nghỉ phép, nghỉ không lương, nghỉ hưởng lương bảo hiểm, nghỉ sinh (với phụ nữ).Xem thêm: Hướng dẫn đầy đủ về cách tính lương và quy chế trả lương trong doanh nghiệp3.3. Quy định sử dụng tài sảnPhần nội dung này gồm những thông tin liên quan đến việc sử dụng tài sản của công ty.Quy định cách sử dụng, bảo vệ các tài sản chung gồm tài sản vật chất và tài sản vô hình như thông tin, dữ liệu.Làm rõ trách nhiệm của nhân viên trong bảo vệ cũng như sử dụng tài sản trong doanh nghiệp hợp lý và có trách nhiệm.3.4. Quy định về bảo mật thông tin, dữ liệuDữ liệu của một doanh nghiệp rất quan trọng, tổ chức cũng nên có những quy định cụ thể cho phần này.Xác định rõ ràng các biện pháp bảo mật thông tin, dữ liệu cũng như hồ sơ công ty.Quy định về việc truy cập thông tin, dữ liệu, gồm thông tin cá nhân, thông tin phòng ban và khách hàng.Đảm bảo tuân thủ theo các quy định về bảo mật quyền riêng tư giữa hai bên cũng như quy định từ phía pháp luật Quy định về kỷ luật lao độngCác nội dung trong mục này gồm có:Xác định quy tắc, quy định về việc thực hiện kỷ luật lao động trong công ty.Chỉ rõ hình thức kỷ luật sẽ áp dụng theo từng mức độ vi phạm.Quy định về việc khiếu nại của nhân viên."


def summarize_text_lightly(text, num_sentences=5):
    """
    Tóm tắt văn bản nhưng vẫn giữ ý chính, không cắt quá nhiều.
    """
    parser = PlaintextParser.from_string(text, Tokenizer("vietnamese"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, num_sentences)
    
    return " ".join(str(sentence) for sentence in summary)

# Gọi hàm tóm tắt
short_text = summarize_text_lightly(testTxt, num_sentences=2)

# In ra độ dài trước và sau khi tóm tắt
print(f"Độ dài ban đầu: {len(testTxt)} ký tự")
print(f"Độ dài sau tóm tắt: {len(short_text)} ký tự")
print("Nội dung sau khi tóm tắt:", short_text)