# -*- coding: utf-8 -*-
import openai
import json
from collections import defaultdict
from FileProcessing.CategorizeDocument import get_category_tree, add_category, save_summary,update_category_parent_and_split
import sys
import os
import json
import re
# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from chatgptModule import client

# Hàm chia nhỏ văn bản nếu quá dài
def split_text(text, max_tokens=4000):
    words = text.split()  # Chia văn bản thành từ
    chunks = []
    chunk = []
    tokens = 0

    for word in words:
        tokens += len(word) // 3  # Tính ước lượng tokens (1 token ~ 3 ký tự)
        chunk.append(word)
        
        if tokens >= max_tokens:
            chunks.append(" ".join(chunk))
            chunk = []
            tokens = 0

    if chunk:
        chunks.append(" ".join(chunk))

    return chunks

# Hàm gửi lên GPT-4o để tóm tắt + phân loại từng ý
def process_with_gpt(content,categories):
    if not content.strip():
        return []

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Bạn là một AI chuyên xử lý văn bản. "
                    "Hãy đọc đoạn văn và trích xuất các ý chính (ngắn gọn nhất có thể) cùng danh mục phù hợp. "
                    "Danh mục hiện có: " + ", ".join(cat["name"] for cat in categories) + ". "
                    "Trả về dưới dạng JSON với format:\n\n"
                    "{\"categories\": {\"Category 1\": [\"ý chính 1\", \"ý chính 2\"], \"Category 2\": [\"ý chính 3\"]}}"
                ),
            },
            {"role": "user", "content": f"Hãy phân tích văn bản sau và nhóm thành các category:\n\n{content}"}
        ],
        max_tokens=5000
    )

    gpt_output_str =  response.choices[0].message.content
    # gpt_output_str = '```json\n{\n  "categories": {\n    "Quyền và Trách nhiệm của Nhân viên": [\n      "Xác định rõ vai trò, quyền hạn, trách nhiệm của từng nhân viên và bộ phận.",\n      "Nêu rõ quyền lợi và trách nhiệm của ban giám đốc và các cấp quản lý.",\n      "Quyền lợi của người lao động: Thời gian nghỉ ngơi, quyền bảo hộ lao động, quyền được tham gia đóng góp ý kiến.",\n      "Trách nhiệm của người lao động: Hoàn thành công việc đúng giờ, giữ bí mật kinh doanh, bảo vệ tài sản công ty."\n    ],\n    "Thời gian làm việc của Nhân viên": [\n      "Quy định thời gian làm việc chuẩn, giờ làm việc bắt đầu và kết thúc.",\n      "Quy định về thời gian nghỉ trưa, nghỉ giữa giờ, đi muộn, về sớm.",\n      "Quy định về nghỉ phép, nghỉ hưởng lương, nghỉ không lương, nghỉ sinh."\n    ],\n    "Quy định sử dụng Tài sản": [\n      "Quy định cách sử dụng, bảo vệ tài sản chung và dữ liệu.",\n      "Trách nhiệm của nhân viên trong việc bảo vệ và sử dụng tài sản hợp lý."\n    ],\n    "Quy định về Bảo mật Thông tin, Dữ liệu": [\n      "Xác định các biện pháp bảo mật thông tin, dữ liệu, hồ sơ công ty.",\n      "Quy định truy cập thông tin cá nhân, phòng ban, khách hàng.",\n      "Tuân thủ quy định bảo mật quyền riêng tư và pháp luật."\n    ],\n    "Quy định về Kỷ luật Lao động": [\n      "Xác định quy tắc kỷ luật lao động trong công ty.",\n      "Chỉ rõ hình thức kỷ luật áp dụng theo mức độ vi phạm.",\n      "Quy định về việc khiếu nại của nhân viên."\n    ]\n  }\n}\n```'
    gpt_output_str = re.sub(r"```json\n(.*)\n```", r"\1", gpt_output_str, flags=re.DOTALL)
    print("gpt_output_str:", gpt_output_str)  # Debugging line
    try:
        gpt_output_dict = json.loads(gpt_output_str)  # Parse JSON
        return gpt_output_dict
    except json.JSONDecodeError:
        # print("Lỗi parse JSON từ GPT:", response)
        return {}

# Hàm xử lý tài liệu
def process_document(content):
    category_tree = get_category_tree()  # Lấy danh sách category hiện có
    chunks = split_text(content,5000)  # Chia nhỏ tài liệu nếu quá dài
    category_data = defaultdict(list)  # Tạo dict chứa category và danh sách ý chính

    # Gửi từng phần nhỏ lên GPT và lưu vào dict
    for chunk in chunks:
        gpt_output = process_with_gpt(chunk,category_tree)
        # Duyệt qua từng category và gộp ý chính vào danh sách
        for category, ideas in gpt_output["categories"].items():
            category_data[category].extend(ideas)
    haveNewCategory=False
    # Sau khi gom hết ý, kiểm tra category nào đã tồn tại, nếu chưa có thì thêm mới
    # for category in category_data:
    #     if category not in category_tree:
    #         add_category(category)  # Thêm category mới vào database
    #         haveNewCategory=True
    # if haveNewCategory: # Nếu có category mới, cập nhật lại cây category (tốn tiền lắm)
    #     update_category_parent_and_split()

    # Sau khi cập nhật cây category, lưu ý chính vào DB
    for category, summaries in category_data.items():
        merged_summary = " ".join(summaries)  # Gộp tất cả ý chính trong cùng category
        save_summary(merged_summary, category)

    return category_data  # Trả về kết quả phân loại

# Test với tài liệu
test_document = """Quyền và trách nhiệm của nhân viên trong công ty. Nhân viên cần tuân thủ các quy định về thời gian làm việc. Nhân viên có quyền được hưởng phúc lợi. Công ty đảm bảo quyền lợi lao động theo quy định của pháp luật. Nếu nhân viên vi phạm quy chế công ty, sẽ bị xử lý kỷ luật theo hợp đồng lao động. Ngoài ra, nhân viên có quyền khiếu nại nếu bị đối xử không công bằng..."""
testTxt=f"Quy Định Về Lương & ThưởngChính sách lương cơ bảnLương được tính theo bậc, cấp độ công việc và hiệu suất làm việc.Nhân viên mới sẽ được hưởng mức lương thử việc bằng 85% lương chính thức trong 2 tháng đầu.Mỗi năm, công ty sẽ xét duyệt tăng lương định kỳ dựa trên kết quả đánh giá hiệu suất.Thưởng hiệu suấtNhân viên hoàn thành xuất sắc công việc có thể nhận được mức thưởng từ 5-15% lương tháng.Thưởng đặc biệt dành cho cá nhân hoặc nhóm có đóng góp nổi bật theo quyết định của quản lý cấp cao.Thưởng Lễ, TếtNhân viên sẽ được nhận thưởng Tết Nguyên Đán tối thiểu một tháng lương nếu không vi phạm kỷ luật.Các ngày lễ lớn khác như 30/4, 1/5, 2/9, nhân viên sẽ được hỗ trợ tài chính hoặc quà tặng theo chính sách của công ty.Chính sách phạt và điều chỉnhNếu nhân viên bị cảnh cáo chính thức vì vi phạm nội quy, thưởng quý sẽ bị giảm 50%.Nghỉ không phép quá 5 ngày/năm có thể ảnh hưởng đến xét duyệt lương thưởng cuối năm.Cơ chế minh bạchLương và thưởng được thanh toán qua tài khoản ngân hàng vào ngày 5 hàng tháng.Mọi thắc mắc về chế độ lương thưởng cần được gửi về phòng nhân sự trong vòng 7 ngày kể từ ngày nhận lương."

# result = process_document(testTxt)
# print("Kết quả phân loại:", result)
