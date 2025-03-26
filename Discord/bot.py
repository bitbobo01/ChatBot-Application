import discord
from discord.ext import commands
from discord.ui import View, Button
import openai
import os
import pymongo
import pytesseract
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# Kết nối MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client["company_data"]
documents_collection = db["documents"]

# Cấu hình OpenAI
openaiClient = openai.OpenAI(api_key=OPENAI_API_KEY)

# Khởi tạo bot Discord với Intents đầy đủ
intents = discord.Intents.all()

# Role-based access
ADMIN_ROLE = "Admin"
USER_ROLE = "User"
GUEST_ROLE = "Guest"
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} đã online!")

    # Đăng ký lại view để tránh mất event sau khi bot restart
    bot.add_view(StartAskingView())  
    print("✅ Đã đăng ký lại event cho nút bấm.")

    # Tìm channel `start-asking`
    channel = discord.utils.get(bot.get_all_channels(), name="start-asking")
    if channel:
        async for message in channel.history(limit=10):  # Kiểm tra 10 tin nhắn gần nhất
            if message.author == bot.user and not message.flags.ephemeral:
                print("⚠️ Tin nhắn hướng dẫn đã tồn tại, không gửi lại.")
                return  

        # Nếu chưa có, gửi tin nhắn hướng dẫn mới
        embed = discord.Embed(
            title="💬 Hệ thống Chatbot 1v1",
            description="Nhấn vào nút bên dưới để bắt đầu cuộc trò chuyện riêng với chatbot.",
            color=discord.Color.blue()
        )
        view = StartAskingView()
        await channel.send(embed=embed, view=view)
        print("✅ Đã gửi tin nhắn hướng dẫn vào `#start-asking`")


class StartAskingView(View):
    """Tạo UI với một nút để mở thread chat với bot"""
    def __init__(self):
        super().__init__(timeout=None)  # Đặt timeout=None để giữ event sau khi restart

    @discord.ui.button(label="💬 Bắt đầu chat với bot", style=discord.ButtonStyle.primary, custom_id="start_chat_button")
    async def start_chat(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        channel = interaction.channel

        # Kiểm tra xem thread đã tồn tại chưa
        existing_thread = discord.utils.get(channel.threads, name=f"Chat-{user.name}")
        if existing_thread:
            await interaction.response.send_message(
                f"⚠️ Bạn đã có một cuộc trò chuyện đang mở: {existing_thread.mention}", ephemeral=True
            )
            return
        
        # Tạo một thread riêng
        thread = await channel.create_thread(
        name=f"Chat-{user.name}",
        type=discord.ChannelType.private_thread,  # 🔥 Chuyển thành `private_thread`
        auto_archive_duration=60  # 📌 Đặt auto archive để tránh thông báo hệ thống
        )
        
        # Gửi tin nhắn chào mừng vào thread
        await thread.send(f"🎉 **Chào mừng {user.mention}**, đây là cuộc trò chuyện riêng với chatbot.\nHãy nhập câu hỏi của bạn!")

        await interaction.response.send_message(f"✅ Đã tạo thread: {thread.mention}", ephemeral=True)


# @client.event
# async def on_ready():
#     print(f'✅ Bot {client.user} đã online!')

@bot.event
async def on_message(message):
    print(f"📩 Nhận tin nhắn từ {message.author}: {message.content}")
    if message.author == bot.user:
        return  # Không phản hồi chính mình

    # Lấy danh sách role của user
    roles = [role.name for role in message.author.roles]
    
    if message.content.startswith("!insert ") and message.author != client.user and (ADMIN_ROLE in roles or USER_ROLE in roles):
        admin_content = message.content[len("!insert "):].strip()
        documents_collection.insert_one({"file_name": f"User_Input_{message.author.id}", "content": admin_content})
        await message.channel.send(f"✅ Đã lưu tin nhắn từ {message.author.name} vào MongoDB")
    
    # ✅ Upload tài liệu (Admin & User)
    if message.attachments and (ADMIN_ROLE in roles or USER_ROLE in roles):
        for attachment in message.attachments:
            if attachment.filename.endswith((".pdf", ".png", ".jpg", ".jpeg")):
                # Tạo thư mục nếu chưa có
                os.makedirs("./downloads", exist_ok=True)
                
                file_path = f"./downloads/{attachment.filename}"
                await attachment.save(file_path)

                extracted_text = extract_text(file_path)
                if extracted_text:
                    documents_collection.insert_one({"file_name": attachment.filename, "content": extracted_text})
                    await message.channel.send(f"📄 Đã lưu tài liệu: **{attachment.filename}**")
                else:
                    await message.channel.send("❌ Không thể trích xuất văn bản từ tài liệu này.")

    # # ✅ Truy vấn chatbot (chỉ Guest có thể chat)
    # if message.content.startswith("!chat ") and GUEST_ROLE in roles:
    #     user_query = message.content[len("!chat "):].strip()
        
    #     if not user_query:
    #         await message.channel.send("Bạn cần nhập câu hỏi sau `!chat`.")
    #         return
        
    #     # Lấy dữ liệu từ tài liệu
    #     documents = documents_collection.find()
    #     combined_text = " ".join([doc["content"] for doc in documents])

    #     response = openaiClient.chat.completions.create(
    #         model="gpt-4o",
    #         messages=[
    #             {"role": "system", "content": "Bạn là một chatbot nội bộ, chỉ trả lời dựa trên thông tin đã có."},
    #             {"role": "user", "content": f"Dữ liệu từ thông tin nội bộ: {combined_text}. Câu hỏi: {user_query}"}
    #         ]
    #     )
    #     answer = response.choices[0].message.content
    #     # Xử lý xuống dòng trước khi đưa vào f-string
    #     formatted_text = answer.replace('. ', '.\n\n')  # Xuống dòng tự nhiên

    #     formatted_answer = (
    #         f"{formatted_text}\n\n"
    #         "📌 Nếu cần thêm thông tin, hãy hỏi tiếp bằng `!chat [câu hỏi]`"
    #     )       
        
    #     await message.channel.send(formatted_answer)
    
    # Kiểm tra nếu tin nhắn nằm trong một thread
    if isinstance(message.channel, discord.Thread):
        user_query = message.content.strip()  # Lấy câu hỏi của user
        # Lấy dữ liệu từ tài liệu
        documents = documents_collection.find()
        combined_text = " ".join([doc["content"] for doc in documents])

        response = openaiClient.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là một chatbot nội bộ, chỉ trả lời dựa trên thông tin đã có."},
                {"role": "user", "content": f"Dữ liệu từ thông tin nội bộ: {combined_text}. Câu hỏi: {user_query}"}
            ]
        )
        answer = response.choices[0].message.content
        # Xử lý xuống dòng trước khi đưa vào f-string
        formatted_text = answer.replace('. ', '.\n\n')  # Xuống dòng tự nhiên

        formatted_answer = (
            f"{formatted_text}\n\n"
        )       
        
        await message.channel.send(formatted_answer)


@bot.event
async def on_raw_reaction_add(payload):
    """Khi user thả reaction vào tin nhắn trong #welcome, gán role Guest"""
    guild = discord.utils.get(client.guilds, id=payload.guild_id)
    if not guild:
        return

    role = discord.utils.get(guild.roles, name="Guest")
    if not role:
        print("❌ Role 'Guest' không tồn tại!")
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return  # Không xử lý bot

    # ID của tin nhắn bot đã gửi trong #welcome (thay bằng ID thật)
    WELCOME_MESSAGE_ID = 1339299224579477656  # Thay bằng ID tin nhắn thực tế

    if payload.message_id == WELCOME_MESSAGE_ID:
        await member.add_roles(role)
        print(f"✅ Đã cấp quyền Guest cho {member.name}")

        # Gửi thông báo xác nhận
        channel = discord.utils.get(guild.channels, name="start-asking")
        if channel:
            await channel.send(f"🎉 Chào mừng {member.mention}! Bạn đã có quyền hỏi chatbot.")


# ✅ OCR xử lý file
def extract_text(file_path):
    if file_path.endswith(".pdf"):
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        return text
    elif file_path.endswith((".png", ".jpg", ".jpeg")):
        return pytesseract.image_to_string(file_path, lang="vie")
    return None

bot.run(DISCORD_TOKEN)
