import datetime
from bson.objectid import ObjectId
import sys
import json
import os
import re
# Thêm thư mục gốc vào sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from chatgptModule import client
from database import db
categories_collection = db["categories"]
summaries_collection = db["summaries"]
# Lấy danh sách category hiện có
def get_category_tree():
    """Lấy danh sách category từ MongoDB"""
    categories = list(categories_collection.find({}, {"_id": 1, "name": 1}))
    return [{"id": str(cat["_id"]), "name": cat["name"]} for cat in categories]
def get_catergory_base_on_content(content):
    categories = get_category_tree()
    category_names = [cat["name"] for cat in categories]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content":
                "Bạn là một AI chuyên xử lý văn bản. "
                "Hãy đọc câu hỏi và trích xuất nội dung để tìm danh mục phù hợp. "
                "Chỉ trả về tên danh mục, cách nhau bằng dấu phẩy nếu có nhiều. "
                "Danh mục hiện có: " + ", ".join(category_names) + ". "
            },
            {"role": "user", "content": f"Hãy đọc và phân loại ý của câu hỏi:\n\n{content}"}
        ],
        max_tokens=200
    )

    # Trích nội dung phản hồi
    raw_text = response.choices[0].message.content
    print("🔍 GPT Response:", raw_text)

    # Dùng regex để trích các tên danh mục (sau dấu ':' hoặc lấy hết nếu không có)
    match = re.search(r":\s*(.+)", raw_text)
    extracted = match.group(1) if match else raw_text

    # Cắt thành danh sách, loại bỏ khoảng trắng dư thừa
    matched_names = [name.strip().lower() for name in extracted.split(",")]

    # Tìm tất cả category trong DB có tên trùng khớp (không phân biệt hoa thường)
    matched_categories = list(categories_collection.find({
        "$expr": {"$in": [{"$toLower": "$name"}, matched_names]}
    }))

    return matched_categories
# Thêm category mới (nếu chưa tồn tại)
def add_category(name, parent_id=None):
    existing_category = categories_collection.find_one({"name": name})
    
    # Nếu category đã tồn tại, trả về ID cũ
    if existing_category:
        return str(existing_category["_id"])

    # Xác định xem có category cha không
    parent_id = None
    for parent in categories_collection.find():  # Duyệt toàn bộ categories có sẵn
        if parent["name"] in name:  # Nếu tên category mới chứa tên của category cha
            parent_id = parent["_id"]
            break  # Tìm được cha thì dừng lại

    # Tạo category mới
    category_data = {
        "name": name,
        "parent_id": parent_id  # Gán parent_id đúng
    }
    
    result = categories_collection.insert_one(category_data)
    return str(result.inserted_id)

# Lưu bản tóm tắt vào MongoDB
def save_summary(summary, category_name):
    category = categories_collection.find_one({"name": category_name})
    if not category:
        category_id = add_category(category_name)  # Nếu category chưa có, tạo mới
    else:
        category_id = str(category["_id"])

    summary_data = {
        "category_id": ObjectId(category_id),
        "summary": summary,
        "created_at": datetime.datetime.utcnow()
    }
    summaries_collection.insert_one(summary_data)
    return summary_data

# def update_category_tree():
#     """
#     Duyệt lại toàn bộ categories và cập nhật `parent_id` nếu cần.
#     """
#     categories = list(categories_collection.find())  # Lấy toàn bộ danh mục
#     print("bắt đầu cập nhật")
#     for category in categories:
#         if category["parent_id"] is None:  # Nếu chưa có parent
#             for potential_parent in categories:
#                 if category["_id"] != potential_parent["_id"] and potential_parent["name"] in category["name"]:
#                     # Nếu tên cha nằm trong tên category con thì gán `parent_id`
#                     categories_collection.update_one(
#                         {"_id": category["_id"]},
#                         {"$set": {"parent_id": potential_parent["_id"]}}
#                     )
#                     print(f"✅ Cập nhật {category['name']} -> Parent: {potential_parent['name']}")
#                     break  # Chỉ cần tìm 1 cha đúng là đủ

def classify_and_split_categories(categories):
    """Gửi danh mục lên GPT để phân loại cha-con & tách nhánh nếu cần"""
    content = json.dumps(categories, ensure_ascii=False, indent=2)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": 
                "Bạn là một AI chuyên sắp xếp danh mục thành cấu trúc cây cha-con hợp lý. "
                "Hãy phân nhóm danh mục dựa trên ý nghĩa thực tế, nếu một danh mục có thể là cha của danh mục khác, hãy đặt `parent_id` hợp lý. "
                "Không tự động nhóm danh mục vào một nhóm cố định như 'Trách nhiệm', 'Quyền', v.v. mà phải suy luận dựa trên nội dung thực tế của từng danh mục. "
                "Nếu một danh mục có nội dung chung chung, nó có thể là danh mục cha của các danh mục cụ thể hơn. "
                "Nếu không có quan hệ cha-con hợp lý, giữ `parent_id = null`. "
                "Trả về JSON với format:\n\n"
                "{ \"categories\": [ { \"id\": \"1\", \"name\": \"Category A\", \"parent_id\": \"2\" }, { \"id\": \"6\", \"name\": \"Category A.1\", \"parent_id\": \"1\" } ] }\n\n"
                "Quan trọng: \n"
                "- **Hãy xác định danh mục nào có nội dung tổng quát hơn để làm cha của danh mục nhỏ hơn.**\n"
                "- **Nếu hai danh mục có nội dung liên quan, hãy nhóm chúng vào cùng một cây cha-con hợp lý.**\n"
                "- **Không tự động gán một nhóm cố định cho danh mục, hãy phân tích dựa trên ngữ nghĩa thực tế.**\n"
                "- Nếu một danh mục có thể tách thành các nhánh con, hãy chia nhỏ nhưng không giữ lại danh mục gốc.\n"
                "- Nếu danh mục không có quan hệ rõ ràng với danh mục khác, giữ `parent_id = null`.\n"
                "- Loại bỏ các từ không cần thiết như 'Quy định về', 'Thông tin', 'Nhân viên' nếu không cần thiết.\n"
                "- **Không tạo quan hệ cha-con một cách gượng ép, chỉ khi thực sự hợp lý.**"
            },
            {"role": "user", "content": f"Hãy phân loại danh mục sau thành cây cha-con hợp lý, đảm bảo mỗi danh mục có quan hệ logic với danh mục khác:\n\n{content}"}
        ],
        max_tokens=1000
    )

    try:
        gpt_output_str = response.choices[0].message.content.strip().lower()
        gpt_output_str = re.sub(r"```json\n(.*)\n```", r"\1", gpt_output_str, flags=re.DOTALL)
        
        return json.loads(gpt_output_str)  # Parse JSON trả về
    except json.JSONDecodeError:
        print("❌ Lỗi parse JSON từ GPT:", gpt_output_str)
        return {"categories": []}  # Trả về danh sách rỗng nếu lỗi

def update_category_parent_and_split():
    """Gửi danh mục lên GPT để cập nhật parent_id và loại bỏ danh mục tổng quát nếu đã chia nhỏ"""
    categories = get_category_tree()
    structured_tree = classify_and_split_categories(categories)
    # Mapping từ ID dạng string sang ObjectId
    id_mapping = {cat["id"]: ObjectId() for cat in structured_tree["categories"]}

    for cat in structured_tree["categories"]:
        category_id = id_mapping[cat["id"]]
        parent_id = id_mapping.get(cat["parent_id"]) if cat["parent_id"] else None  # Chuyển parent_id hợp lệ

        # Cập nhật parent_id vào MongoDB
        categories_collection.update_one(
            {"_id": category_id},
            {"$set": {"parent_id": parent_id, "name": cat["name"]}},
            upsert=True
        )
        print(f"✅ Cập nhật {cat['name']} -> Parent ID: {cat['parent_id']}")

    # Xóa những danh mục gốc bị chia nhỏ và không còn tồn tại
    category_ids = set(id_mapping.values())
    for original_category in categories_collection.find():
        if original_category["_id"] not in category_ids:
            categories_collection.delete_one({"_id": original_category["_id"]})
            print(f"❌ Xóa danh mục tổng quát: {original_category['name']} (Đã bị chia nhỏ)")

    print("🎯 Hoàn tất cập nhật cây category!")

# Chạy cập nhật tự động bằng GPT với khả năng chia nhánh con
# update_category_parent_and_split()
