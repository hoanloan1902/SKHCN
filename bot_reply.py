"""
Bot trả lời tin nhắn Telegram - Dùng webhook hoặc polling
"""

import os
import json
from datetime import datetime
import telebot

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
DA_GUI_FILE = "da_gui.json"

bot = telebot.TeleBot(TOKEN)

def load_da_gui():
    """Đọc danh sách đã gửi"""
    if os.path.exists(DA_GUI_FILE):
        with open(DA_GUI_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('da_gui', []))
    return set()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "🤖 *Bot HSCV - Quản lý văn bản đến*\n\n"
        "Các lệnh:\n"
        "/stats - Xem thống kê\n"
        "/last - Xem 5 văn bản mới nhất\n"
        "/check - Kiểm tra bot còn sống\n"
        "/help - Hiển thị trợ giúp",
        parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def send_stats(message):
    da_gui = load_da_gui()
    msg = f"📊 *Thống kê*\n"
    msg += f"- Đã gửi: {len(da_gui)} văn bản\n"
    msg += f"- Cập nhật cuối: {datetime.now().strftime('%H:%M %d/%m/%Y')}"
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['check'])
def check_alive(message):
    bot.reply_to(message, "✅ Bot đang hoạt động!")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    bot.reply_to(message, "❓ Gõ /help để xem các lệnh")

if __name__ == "__main__":
    print("🤖 Bot đang chạy polling mode...")
    bot.infinity_polling()
