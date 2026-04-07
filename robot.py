import os
import json
import gspread
import telebot
import requests
import urllib3
import time
import re
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# Tắt cảnh báo bảo mật cho trang .gov.vn
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- BIẾN MÔI TRƯỜNG (Cấu hình trên GitHub/Render Secrets) ---
USER_NAME = os.environ.get("SKHCN_USER")
PASS_WORD = os.environ.get("SKHCN_PASS")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT")
CHAT_ID = os.environ.get("CHAT_ID")
SHEET_NAME = "DANH_SACH_VAN_BAN"

bot = telebot.TeleBot(TOKEN)

def ket_noi_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_JSON), scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME)
    except Exception as e:
        print(f"❌ Lỗi kết nối Google Sheets: {e}")
        return None

def lay_thong_ke_tu_sheet():
    try:
        workbook = ket_noi_sheets()
        ws = workbook.worksheet("STATUS")
        records = ws.get_all_records()
        # Chuyển dữ liệu sheet thành dictionary để dễ lấy
        return {row['THÔNG SỐ']: row['GIÁ TRỊ'] for row in records}
    except Exception as e:
        print(f"❌ Lỗi đọc tab STATUS: {e}")
        return None

def soan_tin_nhan():
    data = lay_thong_ke_tu_sheet()
    if not data:
        return "❌ Em không đọc được dữ liệu từ tab 'STATUS' trong Google Sheets của anh."
    
    return (
        f"📊 *THỐNG KÊ HỆ THỐNG*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📩 Đang chờ xử lý: `{data.get('tong_so', 0)}`\n"
        f"🆕 Lần quét cuối thêm: `{data.get('moi_phien_nay', 0)}` văn bản\n"
        f"⏰ Cập nhật lúc: {data.get('cap_nhat_cuoi', 'Chưa rõ')}\n\n"
        f"📂 [Nhấn để xem bảng chi tiết](https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE)"
    )

# --- XỬ LÝ TIN NHẮN TELEGRAM ---

# 1. Lệnh /thongke hoặc /start
@bot.message_handler(commands=['thongke', 'start'])
def command_thongke(message):
    bot.reply_to(message, soan_tin_nhan(), parse_mode='Markdown')

# 2. Đọc tin nhắn thường (Khi anh gõ chữ 'thống kê', 'bao nhiêu'...)
@bot.message_handler(func=lambda msg: True)
def chat_tu_dong(message):
    noi_dung = message.text.lower()
    keywords = ['thống kê', 'thong ke', 'bao nhiêu', 'bao nhieu', 'tình hình', 'công văn']
    
    if any(word in noi_dung for word in keywords):
        bot.reply_to(message, soan_tin_nhan(), parse_mode='Markdown')
    else:
        bot.reply_to(message, "Chào anh Hoàn! Anh muốn xem 'thống kê' công văn hay cần em giúp gì không?")

# --- CHẠY BOT ---
if __name__ == "__main__":
    print("🤖 Bot của anh Hoàn đang trực 24/7...")
    # Thêm dòng này để Render không báo lỗi Port
    bot.infinity_polling()
