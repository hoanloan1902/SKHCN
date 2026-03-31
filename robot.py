import time
import os
import json
import re
import gspread
from datetime import datetime
import telebot
from oauth2client.service_account import ServiceAccountCredentials

# --- CẤU HÌNH ---
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_JSON = os.environ.get("GSPREAD_SERVICE_ACCOUNT", "")

bot = telebot.TeleBot(TOKEN)

def ket_noi_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_JSON), scope)
        return gspread.authorize(creds).open("DANH_SACH_VAN_BAN").sheet1
    except: return None

# --- BỘ NÃO XỬ LÝ KỊCH BẢN THÔNG MINH ---
@bot.message_handler(func=lambda message: True)
def handle_assistant(message):
    txt = message.text.lower().strip()
    sheet = ket_noi_sheets()
    if not sheet: return
    
    all_data = sheet.get_all_values()[1:] # Bỏ tiêu đề
    all_data.reverse() # Cái mới nhất lên đầu
    today_str = datetime.now().strftime("%d/%m/%Y")

    # 1. KỊCH BẢN: TÌM KIẾM THEO ĐƠN VỊ/NỘI DUNG (Ví dụ: "văn bản ủy ban", "tìm sở tài chính")
    # Đây là phần giải quyết lỗi trong ảnh image_04e55a.png của anh
    keywords_tim = ["liệt kê các văn bản", "tìm văn bản", "lọc văn bản", "văn bản của"]
    is_searching = any(k in txt for k in keywords_tim) or (len(txt.split()) > 2 and "văn bản" in txt)

    if is_searching and not re.search(r'\d+', txt): # Nếu không hỏi số lượng mà hỏi chữ
        # Trích xuất từ khóa tìm kiếm (bỏ các từ thừa)
        query = txt.replace("liệt kê","").replace("các","").replace("văn bản","").replace("của","").replace("tìm","").strip()
        
        results = [r for r in all_data if query in r[2].lower() or query in r[0].lower()]
        
        if results:
            msg = f"🔎 **KẾT QUẢ TÌM KIẾM: '{query.upper()}'**\n(Tìm thấy {len(results)} văn bản)\n\n"
            for r in results[:10]: # Hiện tối đa 10 cái gần nhất cho đỡ loãng
                msg += f"✅ `{r[0]}` | {r[1]}\n📝 {r[2][:120]}...\n\n"
            bot.reply_to(message, msg, parse_mode="Markdown")
        else:
            bot.reply_to(message, f"🔎 Em đã rà soát nhưng chưa thấy văn bản nào liên quan đến '{query}' ạ.")
        return

    # 2. KỊCH BẢN: LẤY SỐ LƯỢNG (Ví dụ: "Liệt kê 20 văn bản")
    match_num = re.search(r'(\d+)', txt)
    if match_num and any(k in txt for k in ["liệt kê", "danh sách", "hiện", "xem"]):
        n = int(match_num.group(1))
        results = all_data[:n]
        msg = f"📋 **DANH SÁCH {len(results)} VĂN BẢN MỚI NHẤT**\n\n"
        for r in results:
            msg += f"📌 `{r[0]}` | {r[1]}\n📝 {r[2][:150]}...\n\n"
        
        if len(msg) > 4000:
            for i in range(0, len(msg), 4000): bot.send_message(message.chat.id, msg[i:i+4000], parse_mode="Markdown")
        else: bot.reply_to(message, msg, parse_mode="Markdown")
        return

    # 3. KỊCH BẢN: THỐNG KÊ NHANH
    if any(k in txt for k in ["bao nhiêu", "thống kê", "tổng"]):
        count_today = len([r for r in all_data if today_str in r[1]])
        bot.reply_to(message, f"📊 **THỐNG KÊ VĂN BẢN**\n✅ Tổng số đã nhận: **{len(all_data)}**\n📅 Hôm nay mới về: **{count_today}** cái.")
        return

    bot.reply_to(message, "🤖 Em chưa hiểu rõ. Anh thử nhắn: 'Liệt kê văn bản ủy ban', 'Danh sách 10 cái' hoặc 'Sáng nay có gì' nhé!")

if __name__ == "__main__":
    print("Trợ lý văn bản đến đang trực tuyến...")
    bot.polling(none_stop=True)
