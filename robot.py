import os
import json
import gspread
import telebot
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CẤU HÌNH BIẾN MÔI TRƯỜNG (Lấy từ Github Secrets) ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
# Tên file Google Sheets anh đã tạo trong ảnh image_054674.png
SHEET_NAME = "DANH_SACH_VAN_BAN" 

bot = telebot.TeleBot(TOKEN)

def ket_noi_sheets():
    try:
        # Giải mã JSON từ Secret Github
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(GOOGLE_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).sheet1
    except Exception as e:
        print(f"Lỗi kết nối Sheets: {e}")
        return None

def luu_van_ban_moi(so_hieu, ngay, noi_dung):
    sheet = ket_noi_sheets()
    if sheet:
        # Kiểm tra xem số hiệu đã tồn tại chưa để tránh trùng
        existing_ids = sheet.col_values(1)
        if so_hieu not in existing_ids:
            sheet.append_row([so_hieu, ngay, noi_dung])
            return True
    return False

# --- PHẦN XỬ LÝ TIN NHẮN TỪ ANH HOÀN ---
@bot.message_handler(func=lambda message: True)
def reply_assistant(message):
    txt = message.text.lower()
    sheet = ket_noi_sheets()
    
    if "liệt kê" in txt or "danh sách" in txt:
        if not sheet:
            bot.reply_to(message, "❌ Robot chưa kết nối được với Google Sheets. Anh kiểm tra lại Secret nhé!")
            return
            
        data = sheet.get_all_values()[1:] # Bỏ hàng tiêu đề
        if not data:
            bot.reply_to(message, "📭 Hiện tại chưa có văn bản nào trong danh sách anh ạ.")
            return

        # Lọc theo từ khóa (Ví dụ: "ủy ban")
        query = txt.replace("liệt kê", "").replace("văn bản", "").strip()
        results = [r for r in data if query in r[2].lower() or query in r[0].lower()] if query else data[-10:]

        msg = f"📋 **KẾT QUẢ CHO: {query.upper() if query else '10 CÁI MỚI NHẤT'}**\n\n"
        for r in results[-10:]: # Hiện 10 cái gần nhất
            msg += f"📌 `{r[0]}` | 📅 {r[1]}\n📝 {r[2][:100]}...\n\n"
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "🤖 Em đang trực! Anh muốn xem danh sách gì cứ bảo em nhé.")

if __name__ == "__main__":
    # Đây là phần để Github Actions chạy quét văn bản tự động
    # Giả sử anh có đoạn code quét web ở đây, hãy gọi hàm luu_van_ban_moi()
    print("Robot đang hoạt động...")
    # Nếu chạy trên Github Actions thì không dùng bot.polling, chỉ dùng để test tin nhắn
    bot.polling(none_stop=True)
