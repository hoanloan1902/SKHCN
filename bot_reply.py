import os
import json
import threading
import gspread
import telebot
from flask import Flask
from oauth2client.service_account import ServiceAccountCredentials

TOKEN       = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
SHEET_NAME  = "DANH_SACH_VAN_BAN"
PORT        = int(os.environ.get("PORT", 10000))

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot HSCV đang hoạt động!", 200

def lay_thong_ke():
    try:
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(GOOGLE_JSON), scope)
        client = gspread.authorize(creds)
        ws = client.open(SHEET_NAME).worksheet("STATUS")
        records = ws.get_all_records()
        return {row['THÔNG SỐ']: row['GIÁ TRỊ'] for row in records}
    except Exception as e:
        print(f"❌ Lỗi đọc Sheets: {e}")
        return None

def soan_tin():
    data = lay_thong_ke()
    if not data:
        return "❌ Không đọc được dữ liệu từ Google Sheets."
    return (
        f"📊 *THỐNG KÊ HỆ THỐNG*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📩 Đang chờ xử lý: `{data.get('tong_so', 0)}`\n"
        f"🆕 Lần quét cuối thêm: `{data.get('moi_phien_nay', 0)}` văn bản\n"
        f"⏰ Cập nhật lúc: {data.get('cap_nhat_cuoi', 'Chưa rõ')}"
    )

@bot.message_handler(commands=['thongke', 'start'])
def cmd_thongke(message):
    bot.reply_to(message, soan_tin(), parse_mode='Markdown')

@bot.message_handler(func=lambda msg: True)
def chat_tu_dong(message):
    keywords = ['thống kê', 'thong ke', 'bao nhiêu', 'tình hình', 'công văn']
    if any(w in message.text.lower() for w in keywords):
        bot.reply_to(message, soan_tin(), parse_mode='Markdown')
    else:
        bot.reply_to(message,
            "Chào anh Hoàn! Gõ 'thống kê' hoặc /thongke để xem báo cáo nhé.")

def chay_bot():
    print("🤖 Bot đang lắng nghe tin nhắn...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Chạy bot trong thread riêng
    t = threading.Thread(target=chay_bot)
    t.daemon = True
    t.start()
    # Flask mở cổng để Render không báo lỗi "No open ports"
    print(f"🌐 Web server khởi động trên cổng {PORT}...")
    app.run(host='0.0.0.0', port=PORT)
